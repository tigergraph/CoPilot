import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials
from pyTigerGraph import TigerGraphConnection

from app.config import (db_config, embedding_service, get_llm_service,
                        llm_config, milvus_config, security)
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.metrics.tg_proxy import TigerGraphConnectionProxy
from app.sync.eventual_consistency_checker import EventualConsistencyChecker

logger = logging.getLogger(__name__)
consistency_checkers = {}


def get_db_connection(
    graphname, credentials: Annotated[HTTPBasicCredentials, Depends(security)]
) -> TigerGraphConnectionProxy:
    conn = TigerGraphConnection(
        host=db_config["hostname"],
        username=credentials.username,
        password=credentials.password,
        graphname=graphname,
    )

    if db_config["getToken"]:
        try:
            apiToken = conn._post(
                conn.restppUrl + "/requesttoken",
                authMode="pwd",
                data=str({"graph": conn.graphname}),
                resKey="results",
            )["token"]
        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )

        conn = TigerGraphConnection(
            host=db_config["hostname"],
            username=credentials.username,
            password=credentials.password,
            graphname=graphname,
            apiToken=apiToken,
        )

    conn.customizeHeader(
        timeout=db_config["default_timeout"] * 1000, responseSize=5000000
    )
    conn = TigerGraphConnectionProxy(conn)

    return conn


async def get_eventual_consistency_checker(graphname: str):
    if not db_config.get("enable_consistency_checker", True):
        logger.debug("Eventual consistency checker disabled")
        return

    check_interval_seconds = milvus_config.get("sync_interval_seconds", 30 * 60)
    credentials = HTTPBasicCredentials(
        username=db_config["username"], password=db_config["password"]
    )
    conn = get_db_connection(graphname, credentials)

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

        # TODO: chunker and extractor needs to be configurable
        from app.supportai.chunkers.semantic_chunker import SemanticChunker
        from app.supportai.extractors import LLMEntityRelationshipExtractor

        chunker = SemanticChunker(embedding_service, "percentile", 0.95)
        extractor = LLMEntityRelationshipExtractor(get_llm_service(llm_config))
        checker = EventualConsistencyChecker(
            check_interval_seconds,
            graphname,
            vertex_field,
            embedding_service,
            index_names,
            vector_indices,
            conn,
            chunker,
            extractor,
        )
        await checker.initialize()
        consistency_checkers[graphname] = checker
    return consistency_checkers[graphname]
