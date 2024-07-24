import asyncio
import logging
import time

import ecc_util
from aiochannel import Channel
from graphrag.util import chunk_doc, install_query, stream_docs
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
    # queries that are currently installed
    installed_queries = [q.split("/")[-1] for q in conn.getEndpoints(dynamic=True)]

    tasks = []
    async with asyncio.TaskGroup() as grp:
        for q in requried_queries:
            async with asyncio.Semaphore(n_workers):
                q_name = q.split("/")[-1]
                # if the query is not installed, install it
                if q_name not in installed_queries:
                    task = grp.create_task(install_query(conn, q))
                    tasks.append(task)

    for t in tasks:
        print(t.result())
        # TODO: Check if anything had an error
    return "", "", ""


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


async def chunk_docs(
    conn: TigerGraphConnection,
    docs_chan: Channel,
    embed_chan: Channel,
    upsert_chan: Channel,
    extract_chan: Channel,
):
    """
    Creates and starts one worker for each document
    in the docs channel.
    """
    doc_tasks = []
    async with asyncio.TaskGroup() as grp:
        async for content in docs_chan:
            await embed_chan.put(content)  # send the document to be embedded
            task = grp.create_task(
                chunk_doc(conn, content, upsert_chan, embed_chan, extract_chan)
            )
            doc_tasks.append(task)
            # break  # single doc  FIXME: delete

    # do something with doc_tasks?
    for t in doc_tasks:
        print(t.result())

    # FIXME: don't close these there, other functions will send to them
    upsert_chan.close()
    embed_chan.close()

    # close the extract chan -- chunk_doc is the only sender
    # and chunk_doc calls are kicked off from here (this is technically the sender)
    extract_chan.close()


async def upsert(upsert_chan: Channel):
    """
    Creates and starts one worker for each upsert job
    queue expects:
    (func, args) <- q.get()
    """

    # consume task queue
    upsert_tasks = []
    async with asyncio.TaskGroup() as grp:
        async for func, args in upsert_chan:
            # print("func name >>>>>", func.__name__, args)
            # grp.create_task(todo())
            # continue

            # execute the task
            t = grp.create_task(func(*args))
            upsert_tasks.append(t)

    print(f"upsert done")
    # do something with doc_tasks?
    for t in upsert_tasks:
        print(t.result())


async def embed(embed_chan: Channel):
    """
    Creates and starts one worker for each embed job
    """

    # consume task queue
    responses = []
    async with asyncio.TaskGroup() as grp:
        async for item in embed_chan:
            print("embed item>>>>>", type(item))
            grp.create_task(todo())
            continue
            # execute the task
            # response = await func(*args)

            # append task results to worker results/response
            # responses.append(response)

    print(f"embed done")
    return responses


async def extract(extract_chan: Channel):
    """
    Creates and starts one worker for each extract job
    """

    # consume task queue
    responses = []
    async with asyncio.TaskGroup() as grp:
        async for item in extract_chan:
            print("extract item>>>>>", type(item))
            grp.create_task(todo())
            continue
            # execute the task
            # response = await func(*args)

            # append task results to worker results/response
            # responses.append(response)

    print(f"embed done")
    return responses


async def todo():
    await asyncio.sleep(1)


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
    await init(graphname, conn)
    # return
    start = time.perf_counter()

    # TODO: make configurable
    tasks = []
    docs_chan = Channel(15)  # process n chunks at a time max
    embed_chan = Channel(100)
    upsert_chan = Channel(100)
    extract_chan = Channel(100)
    async with asyncio.TaskGroup() as grp:
        # get docs
        t = grp.create_task(stream_docs(conn, docs_chan, 10))
        tasks.append(t)
        # process docs
        t = grp.create_task(
            chunk_docs(conn, docs_chan, embed_chan, upsert_chan, extract_chan)
        )
        tasks.append(t)
        # upsert chunks
        t = grp.create_task(upsert(upsert_chan))
        tasks.append(t)
        # # embed
        t = grp.create_task(embed(embed_chan))
        tasks.append(t)
        # extract entities
        t = grp.create_task(extract(extract_chan))
        tasks.append(t)
    end = time.perf_counter()

    print("DONE")
    print(end - start)
