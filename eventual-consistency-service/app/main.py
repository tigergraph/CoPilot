import os

os.environ["ECC"] = "true"
import json
import time
import logging
from contextlib import asynccontextmanager
from threading import Thread
from typing import Annotated, Callable

import ecc_util
import graphrag
import supportai
from eventual_consistency_checker import EventualConsistencyChecker
from fastapi import BackgroundTasks, Depends, FastAPI, Response, status
from fastapi.security.http import HTTPBase

from common.config import (
    db_config,
    doc_processing_config,
    embedding_service,
    get_llm_service,
    llm_config,
    milvus_config,
    security,
)
from common.db.connections import elevate_db_connection_to_token
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.logs.logwriter import LogWriter
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.py_schemas.schemas import SupportAIMethod

logger = logging.getLogger(__name__)
consistency_checkers = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not db_config.get("enable_consistency_checker", False):
        LogWriter.info("Eventual Consistency Checker not run on startup")

    else:
        startup_checkers = db_config.get("graph_names", [])
        for graphname in startup_checkers:
            conn = elevate_db_connection_to_token(
                db_config["hostname"],
                db_config["username"],
                db_config["password"],
                graphname,
                async_conn=True
            )
            start_ecc_in_thread(graphname, conn)
    yield
    LogWriter.info("ECC Shutdown")


app = FastAPI(lifespan=lifespan)


def start_ecc_in_thread(graphname: str, conn: TigerGraphConnectionProxy):
    thread = Thread(
        target=initialize_eventual_consistency_checker,
        args=(graphname, conn),
        daemon=True,
    )
    thread.start()
    LogWriter.info(f"Eventual consistency checker started for graph {graphname}")


def initialize_eventual_consistency_checker(
    graphname: str, conn: TigerGraphConnectionProxy
):
    if graphname in consistency_checkers:
        return consistency_checkers[graphname]

    try:
        process_interval_seconds = milvus_config.get(
            "process_interval_seconds", 1800
        )  # default 30 minutes
        cleanup_interval_seconds = milvus_config.get(
            "cleanup_interval_seconds", 86400
        )  # default 30 days,
        batch_size = milvus_config.get("batch_size", 10)
        vector_indices = {}
        vertex_field = None

        if milvus_config.get("enabled") == "true":
            vertex_field = milvus_config.get("vertex_field", "vertex_id")
            index_names = milvus_config.get(
                "indexes",
                ["Document", "DocumentChunk", "Entity", "Relationship", "Concept"],
            )
            for index_name in index_names:
                vector_indices[graphname + "_" + index_name] = MilvusEmbeddingStore(
                    embedding_service,
                    host=milvus_config["host"],
                    port=milvus_config["port"],
                    support_ai_instance=True,
                    collection_name=graphname + "_" + index_name,
                    username=milvus_config.get("username", ""),
                    password=milvus_config.get("password", ""),
                    vector_field=milvus_config.get("vector_field", "document_vector"),
                    text_field=milvus_config.get("text_field", "document_content"),
                    vertex_field=vertex_field,
                    alias=milvus_config.get("alias", "default"),
                )

        chunker = ecc_util.get_chunker()

        if doc_processing_config.get("extractor") == "llm":
            from common.extractors import LLMEntityRelationshipExtractor

            extractor = LLMEntityRelationshipExtractor(get_llm_service(llm_config))
        else:
            raise ValueError("Invalid extractor type")

        if vertex_field is None:
            raise ValueError(
                "vertex_field is not defined. Ensure Milvus is enabled in the configuration."
            )

        checker = EventualConsistencyChecker(
            process_interval_seconds,
            cleanup_interval_seconds,
            graphname,
            vertex_field,
            embedding_service,
            index_names,
            vector_indices,
            conn,
            chunker,
            extractor,
            batch_size,
        )
        consistency_checkers[graphname] = checker

        # start the longer cleanup process that will run in further spaced-out intervals
        if milvus_config.get("cleanup_enabled", True):
            cleanup_thread = Thread(target=checker.initialize_cleanup, daemon=True)
            cleanup_thread.start()

        # start the main ECC process that searches for new vertices that need to be processed
        checker.initialize()

        return checker
    except Exception as e:
        LogWriter.error(
            f"Failed to start eventual consistency checker for graph {graphname}: {e}"
        )


def start_func_in_thread(f: Callable, *args, **kwargs):
    thread = Thread(
        target=f,
        args=args,
        kwargs=kwargs,
        daemon=True,
    )
    thread.start()
    LogWriter.info(f'Thread started for function: "{f.__name__}"')


@app.get("/")
def root():
    LogWriter.info(f"Healthcheck")
    return {"status": "ok"}


@app.get("/{graphname}/consistency_status/{ecc_method}")
def consistency_status(
    graphname: str,
    ecc_method: str,
    background: BackgroundTasks,
    credentials: Annotated[HTTPBase, Depends(security)],
    response: Response,
):
    conn = elevate_db_connection_to_token(
        db_config["hostname"],
        credentials.username,
        credentials.password,
        graphname,
        async_conn=True
    )
    match ecc_method:
        case SupportAIMethod.SUPPORTAI:
            background.add_task(supportai.run, graphname, conn)

            ecc_status = f"SupportAI initialization on {graphname} {time.ctime()}"       
        case SupportAIMethod.GRAPHRAG:
            background.add_task(graphrag.run, graphname, conn)

            ecc_status = f"GraphRAG initialization on {conn.graphname} {time.ctime()}"
        case _:
            response.status_code = status.HTTP_404_NOT_FOUND
            return f"Method unsupported, must be {SupportAIMethod.SUPPORTAI}, {SupportAIMethod.GRAPHRAG}"

    return ecc_status
