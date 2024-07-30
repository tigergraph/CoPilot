import asyncio
import logging
import time
import traceback

import httpx
from aiochannel import Channel
from common.config import embedding_service
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors.BaseExtractor import BaseExtractor
from graphrag import workers
from graphrag.util import http_timeout, init, make_headers, stream_doc_ids
from pyTigerGraph import TigerGraphConnection

http_logs = logging.getLogger("httpx")
http_logs.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

consistency_checkers = {}


async def stream_docs(
    conn: TigerGraphConnection,
    docs_chan: Channel,
    ttl_batches: int = 10,
):
    """
    Streams the document contents into the docs_chan
    """
    logger.info("streaming docs")
    headers = make_headers(conn)
    for i in range(ttl_batches):
        doc_ids = await stream_doc_ids(conn, i, ttl_batches)
        if doc_ids["error"]:
            # continue to the next batch.
            # These docs will not be marked as processed, so the ecc will process it eventually.
            continue

        for d in doc_ids["ids"]:
            async with httpx.AsyncClient(timeout=http_timeout) as client:
                try:
                    res = await client.get(
                        f"{conn.restppUrl}/query/{conn.graphname}/StreamDocContent/",
                        params={"doc": d},
                        headers=headers,
                    )
                    if res.status_code != 200:
                        # continue to the next doc.
                        # This doc will not be marked as processed, so the ecc will process it eventually.
                        continue
                    logger.info("steam_docs writes to docs")
                    await docs_chan.put(res.json()["results"][0]["DocContent"][0])
                except Exception as e:
                    exc = traceback.format_exc()
                    logger.error(f"Error retrieving doc: {d} --> {e}\n{exc}")
                    continue  # try retrieving the next doc

    logger.info("stream_docs done")
    # close the docs chan -- this function is the only sender
    logger.info("closing docs chan")
    docs_chan.close()


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
    logger.info("Reading from docs channel")
    doc_tasks = []
    async with asyncio.TaskGroup() as grp:
        async for content in docs_chan:
            v_id = content["v_id"]
            txt = content["attributes"]["text"]
            # send the document to be embedded
            logger.info("chunk writes to extract")
            await embed_chan.put((v_id, txt, "Document"))

            task = grp.create_task(
                workers.chunk_doc(conn, content, upsert_chan, embed_chan, extract_chan)
            )
            doc_tasks.append(task)

    logger.info("chunk_docs done")

    # close the extract chan -- chunk_doc is the only sender
    # and chunk_doc calls are kicked off from here
    logger.info("closing extract_chan")
    extract_chan.close()


async def upsert(upsert_chan: Channel):
    """
    Creates and starts one worker for each upsert job
    chan expects:
    (func, args) <- q.get()
    """

    logger.info("Reading from upsert channel")
    # consume task queue
    upsert_tasks = []
    async with asyncio.TaskGroup() as grp:
        async for func, args in upsert_chan:
            logger.info(f"{func.__name__}, {args[1]}")
            # continue
            # execute the task
            t = grp.create_task(func(*args))
            upsert_tasks.append(t)

    logger.info(f"upsert done")
    # do something with doc_tasks?
    # for t in upsert_tasks:
    #     logger.info(t.result())


async def embed(
    embed_chan: Channel, index_stores: dict[str, MilvusEmbeddingStore], graphname: str
):
    """
    Creates and starts one worker for each embed job
    chan expects:
    (v_id, content, index_name) <- q.get()
    """
    logger.info("Reading from embed channel")
    async with asyncio.TaskGroup() as grp:
        # consume task queue
        async for v_id, content, index_name in embed_chan:
            # continue
            embedding_store = index_stores[f"{graphname}_{index_name}"]
            logger.info(f"Embed to {graphname}_{index_name}: {v_id}")
            grp.create_task(
                workers.embed(
                    embedding_service,
                    embedding_store,
                    v_id,
                    content,
                )
            )

    logger.info(f"embed done")


async def extract(
    extract_chan: Channel,
    upsert_chan: Channel,
    embed_chan: Channel,
    extractor: BaseExtractor,
    conn: TigerGraphConnection,
):
    """
    Creates and starts one worker for each extract job
    chan expects:
    (chunk , chunk_id) <- q.get()
    """
    logger.info("Reading from extract channel")
    # consume task queue
    async with asyncio.TaskGroup() as grp:
        async for item in extract_chan:
            grp.create_task(
                workers.extract(upsert_chan, embed_chan, extractor, conn, *item)
            )

    logger.info(f"extract done")

    logger.info("closing upsert and embed chan")
    upsert_chan.close()
    embed_chan.close()


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

    extractor, index_stores = await init(conn)
    # return
    start = time.perf_counter()

    tasks = []
    docs_chan = Channel(1)
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
        t = grp.create_task(embed(embed_chan, index_stores, graphname))
        tasks.append(t)
        # extract entities
        t = grp.create_task(
            extract(extract_chan, upsert_chan, embed_chan, extractor, conn)
        )
        tasks.append(t)
    end = time.perf_counter()

    logger.info(f"DONE. graphrag.run elapsed: {end-start}")
