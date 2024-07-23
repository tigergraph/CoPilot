import asyncio
import logging

import ecc_util
from graphrag.util import install_query, stream_docs, upsert_chunk
from graphrag.worker import worker
from pyTigerGraph import TigerGraphConnection

from common.chunkers.base_chunker import BaseChunker
from common.config import (
    doc_processing_config,
    embedding_service,
    get_llm_service,
    llm_config,
    milvus_config,
)
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors import GraphExtractor, LLMEntityRelationshipExtractor
from common.extractors.BaseExtractor import BaseExtractor

logger = logging.getLogger(__name__)
consistency_checkers = {}


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
        q_name = q.split("/")[-1]
        if q_name not in installed_queries:
            tq.put_nowait((install_query, (conn, q)))

    # start workers
    for n in range(min(tq.qsize(), n_workers)):
        task = loop.create_task(worker(n, tq))
        tasks.append(task)

    # wait for workers to finish jobs
    await tq.join()
    for t in tasks:
        print(t.result())
        # TODO: Check if anything had an error
    return "", "", ""


async def process_doc(
    conn: TigerGraphConnection, doc: dict[str, str], sem: asyncio.Semaphore
):
    # TODO: Embed document and chunks
    chunker = ecc_util.get_chunker()
    try:
        print(">>>>>", doc["v_id"], len(doc["attributes"]["text"]))
        # await asyncio.sleep(5)
        chunks = chunker.chunk(doc["attributes"]["text"])
        v_id = doc["v_id"]
        # TODO: n chunks at a time
        for i, chunk in enumerate(chunks):
            await upsert_chunk(conn, v_id, f"{v_id}_chunk_{i}", chunk)
            # break  # single chunk FIXME: delete
    finally:
        sem.release()

    return doc["v_id"]


async def init(
    graphname: str, conn: TigerGraphConnection
) -> tuple[BaseChunker, dict[str, MilvusEmbeddingStore], BaseExtractor]:
    # install requried queries
    requried_queries = [
        # "common/gsql/supportai/Scan_For_Updates",
        # "common/gsql/supportai/Update_Vertices_Processing_Status",
        # "common/gsql/supportai/ECC_Status",
        # "common/gsql/supportai/Check_Nonexistent_Vertices",
        "common/gsql/graphRAG/StreamDocIds",
        "common/gsql/graphRAG/StreamDocContent",
    ]
    # await install_queries(requried_queries, conn)
    return await install_queries(requried_queries, conn)

    # init processing tools
    chunker = ecc_util.get_chunker()

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

    # init configurable objects
    chunker, vector_indices, extractor = await init(graphname, conn)

    # process docs
    doc_workers = 48  # TODO: make configurable
    doc_tasks = []
    doc_sem = asyncio.Semaphore(doc_workers)

    async with asyncio.TaskGroup() as tg:
        async for content in stream_docs(conn):
            # only n workers at a time -- held up by semaphore
            print(">>>>>>>>>>>>>>>>>>>>>>>>\n", len(doc_tasks), "<<<<<<<<<")
            await doc_sem.acquire()
            task = tg.create_task(process_doc(conn, content, doc_sem))
            doc_tasks.append(task)
            break

    # do something with doc_tasks
    for t in doc_tasks:
        print(t.result())

    print("DONE")
    return f"hi from graph rag ecc: {conn.graphname} ({graphname})"
