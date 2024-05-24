import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPBase

from common.config import (
    db_config,
    embedding_service,
    get_llm_service,
    llm_config,
    milvus_config,
    security,
    doc_processing_config,
)
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.logs.logwriter import LogWriter
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.db.connections import elevate_db_connection_to_token
from app.eventual_consistency_checker import EventualConsistencyChecker
import json
import multiprocessing

logger = logging.getLogger(__name__)
consistency_checkers = {}
processes = {}

app = FastAPI()

@app.on_event("startup")
def startup_event():
    if not db_config.get("enable_consistency_checker", True):
        LogWriter.info("Eventual consistency checker disabled")
        return

    startup_checkers = db_config.get("graph_names", [])
    for graphname in startup_checkers:
        conn = elevate_db_connection_to_token(db_config["hostname"], db_config["username"], db_config["password"], graphname)
        run_ecc(graphname, conn)

def run_ecc(graphname: str, conn: TigerGraphConnectionProxy):
    process = multiprocessing.Process(target=initialize_eventual_consistency_checker, args=(graphname, conn), daemon=True)
    process.start()
    processes[process.pid] = process
    status = f"Eventual consistency checker started for graph {graphname} at pid: {process.pid}"
    LogWriter.info(status)
    return {"status": status, "pid": process.pid}

def initialize_eventual_consistency_checker(graphname: str, conn: TigerGraphConnectionProxy):
    check_interval_seconds = milvus_config.get("sync_interval_seconds", 30 * 60)
    if graphname not in consistency_checkers:
        vector_indices = {}
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
                )

        if doc_processing_config.get("chunker") == "semantic":
            from common.chunkers.semantic_chunker import SemanticChunker

            chunker = SemanticChunker(
                embedding_service,
                doc_processing_config["chunker_config"].get("method", "percentile"),
                doc_processing_config["chunker_config"].get("threshold", 0.95),
            )
        elif doc_processing_config.get("chunker") == "regex":
            from common.chunkers.regex_chunker import RegexChunker

            chunker = RegexChunker(
                pattern=doc_processing_config["chunker_config"].get(
                    "pattern", "\\r?\\n"
                )
            )
        elif doc_processing_config.get("chunker") == "character":
            from common.chunkers.character_chunker import CharacterChunker

            chunker = CharacterChunker(
                chunk_size=doc_processing_config["chunker_config"].get(
                    "chunk_size", 1024
                ),
                overlap_size=doc_processing_config["chunker_config"].get(
                    "overlap_size", 0
                ),
            )
        else:
            raise ValueError("Invalid chunker type")

        if doc_processing_config.get("extractor") == "llm":
            from common.extractors import LLMEntityRelationshipExtractor

            extractor = LLMEntityRelationshipExtractor(get_llm_service(llm_config))
        else:
            raise ValueError("Invalid extractor type")

        checker = EventualConsistencyChecker(
            check_interval_seconds,
            graphname,
            vertex_field,  # FIXME: if milvus is not enabled, this is not defined and will crash here (vertex_field used before assignment)
            embedding_service,
            index_names,
            vector_indices,
            conn,
            chunker,
            extractor,
        )
        consistency_checkers[graphname] = checker
        checker.initialize()
    return consistency_checkers[graphname]

@app.get("/{graphname}/consistency_status")
def consistency_status(graphname: str, credentials: Annotated[HTTPBase, Depends(security)]):
    if graphname in consistency_checkers:
        ecc = consistency_checkers[graphname]
        status = json.dumps(ecc.get_status())
    else:
        conn = elevate_db_connection_to_token(db_config["hostname"], credentials.username, credentials.password, graphname)
        status = run_ecc(graphname, conn)

    LogWriter.info(f"Returning consistency status for {graphname}: {status}")
    return status

@app.post("/stop-checker/{pid}")
def stop_checker(pid: int):
    LogWriter.info(f"Stopping process {pid}")
    process = processes.get(pid)
    if process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    process.terminate()
    process.join()
    del processes[pid]
    return {"status": "checker stopped"}