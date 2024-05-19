import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials, HTTPAuthorizationCredentials
from pyTigerGraph import TigerGraphConnection
from requests import HTTPError

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
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from app.eventual_consistency_checker import EventualConsistencyChecker
from app.tools.logwriter import LogWriter

logger = logging.getLogger(__name__)
consistency_checkers = {}


def get_eventual_consistency_checker(graphname: str, conn: TigerGraphConnectionProxy):
    if not db_config.get("enable_consistency_checker", True):
        logger.debug("Eventual consistency checker disabled")
        return

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
        checker.initialize()
        consistency_checkers[graphname] = checker
    return consistency_checkers[graphname]