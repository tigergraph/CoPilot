import asyncio
import logging

from graphrag.util import install_query
from graphrag.worker import worker
from pyTigerGraph import TigerGraphConnection

from common.chunkers import character_chunker, regex_chunker, semantic_chunker
from common.chunkers.base_chunker import BaseChunker
from common.config import (doc_processing_config, embedding_service,
                           get_llm_service, llm_config, milvus_config)
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors import GraphExtractor, LLMEntityRelationshipExtractor
from common.extractors.BaseExtractor import BaseExtractor

logger = logging.getLogger(__name__)
consistency_checkers = {}


def get_chunker():
    if doc_processing_config.get("chunker") == "semantic":
        chunker = semantic_chunker.SemanticChunker(
            embedding_service,
            doc_processing_config["chunker_config"].get("method", "percentile"),
            doc_processing_config["chunker_config"].get("threshold", 0.95),
        )
    elif doc_processing_config.get("chunker") == "regex":
        chunker = regex_chunker.RegexChunker(
            pattern=doc_processing_config["chunker_config"].get("pattern", "\\r?\\n")
        )
    elif doc_processing_config.get("chunker") == "character":
        chunker = character_chunker.CharacterChunker(
            chunk_size=doc_processing_config["chunker_config"].get("chunk_size", 1024),
            overlap_size=doc_processing_config["chunker_config"].get("overlap_size", 0),
        )
    else:
        raise ValueError("Invalid chunker type")

    return chunker


async def install_queries(
    requried_queries: list[str], conn: TigerGraphConnection, n_workers=8
):
    loop = asyncio.get_event_loop()
    tasks: list[asyncio.Task] = []

    # queries that are currently installed
    installed_queries = [q.split("/")[-1] for q in conn.getEndpoints(dynamic=True)]

    # add queries to be installed into the queue
    tq = asyncio.Queue()
    for q in requried_queries:
        if q not in installed_queries:
            tq.put_nowait((install_query, (conn, q)))
            # break

    print("starting workers")
    # start workers
    for n in range(min(tq.qsize(), n_workers)):
        task = loop.create_task(worker(n, tq))
        tasks.append(task)

    # wait for workers to finish jobs
    await tq.join()
    for t in tasks:
        print(t.result())
    return "", "", ""


async def init(
    graphname: str, conn: TigerGraphConnection
) -> tuple[BaseChunker, dict[str, MilvusEmbeddingStore], BaseExtractor]:
    # install requried queries
    requried_queries = [
        "Scan_For_Updates",
        "Update_Vertices_Processing_Status",
        "ECC_Status",
        "Check_Nonexistent_Vertices",
    ]
    await install_queries(requried_queries, conn)

    # init processing tools
    chunker = get_chunker()
    vector_indices = {}
    vertex_field = milvus_config.get("vertex_field", "vertex_id")
    index_names = milvus_config.get(
        "indexes",
        ["Document", "DocumentChunk", "Entity", "Relationship"],
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

    if doc_processing_config.get("extractor") == "llm":
        extractor = GraphExtractor()
    elif doc_processing_config.get("extractor") == "llm":
        extractor = LLMEntityRelationshipExtractor(get_llm_service(llm_config))
    else:
        raise ValueError("Invalid extractor type")

    if vertex_field is None:
        raise ValueError(
            "vertex_field is not defined. Ensure Milvus is enabled in the configuration."
        )

    return chunker, vector_indices, extractor


async def run(graphname: str, conn: TigerGraphConnection):
    """
    ecc flow

    initialize_eventual_consistency_checker
        instantiates ecc object
        writes checker to checker dict
        runs ecc_obj.initialize()

    ECC.initialize
        loops and calls fetch and process

    """

    chunker, vector_indices, extractor = await init(graphname, conn)

    # process docs

    return f"hi from graph rag ecc: {conn.graphname} ({graphname})"
