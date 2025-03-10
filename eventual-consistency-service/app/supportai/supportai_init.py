import asyncio
import logging
import time
import traceback
import httpx

from aiochannel import Channel
from pyTigerGraph import TigerGraphConnection

from common.config import embedding_service
from common.embeddings.base_embedding_store import EmbeddingStore
from common.extractors.BaseExtractor import BaseExtractor
from supportai import workers
from supportai.util import (
    init,
    make_headers,
    http_timeout,
    stream_ids,
    tg_sem
)

logger = logging.getLogger(__name__)

consistency_checkers = {}


async def stream_docs(
    conn: TigerGraphConnection,
    docs_chan: Channel,
    ttl_batches: int = 10
):
    """
    Streams the document contents into the docs_chan
    """
    logger.info("streaming docs")
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        for i in range(ttl_batches):
            doc_ids = await stream_ids(conn, "Document", i, ttl_batches)
            if doc_ids["error"]:
                continue

            for d in doc_ids["ids"]:
                try:
                    async with tg_sem:
                        res = await conn.runInstalledQuery(
                            "StreamDocContent",
                            params={"doc": d},
                        )
                    logger.info("stream_docs writes to docs")    
                    await docs_chan.put(res[0]["DocContent"][0])
                except Exception as e:
                    exc = traceback.format_exc()
                    logger.error(f"Error retrieveing doc: {d} --> {e}\n{exc}")
                    continue
    logger.info("stream_docs done")
    logger.info("closing docs chan")
    docs_chan.close()


async def chunk_docs(
    conn: TigerGraphConnection,
    docs_chan: Channel,
    embed_chan: Channel,
    upsert_chan: Channel,
    extract_chan: Channel
):
    """
    Creates and starts one worker for each document
    in the docs channel.
    """
    logger.info("Reading form docs channel")
    doc_task = []
    async with asyncio.TaskGroup() as sp:
        async for content in docs_chan:
            # v_id = content["v_id"]
            # txt = content["attributes"]["text"]

            logger.info("chunk writes to extract")
            # await embed_chan.put((v_id, txt, "Document"))

            task = sp.create_task(
                workers.chunk_doc(conn, content, upsert_chan, embed_chan, extract_chan)
            )
            doc_task.append(task)

    logger.info("chunk_docs done")
    logger.info("closing extract_chan")
    extract_chan.close()
    

async def upsert(
    upsert_chan: Channel
):
    """
    Creates and starts one worker for each upsert job
    chan expects:
    (func, args) <- q.get()
    """

    logger.info("Reading from upsert channel")
    # consume task queue
    async with asyncio.TaskGroup() as sp:
        async for func, args in upsert_chan:
            logger.info(f"{func.__name__}, {args[1]}")
            # execute the task
            sp.create_task(func(*args))

    logger.info(f"upsert done")
    

async def embed(
    embed_chan: Channel,
    index_stores: dict[str, EmbeddingStore],
    graphname: str
):  
    """
    Creates and starts one worker for each embed job
    chan expects:
    (v_id, content, index_name) <- q.get()
    """
    logger.info("Reading from embed channel")
    async with asyncio.TaskGroup() as sp:
        # consume task queue
        async for v_id, content, index_name in embed_chan:
            if "all" in index_stores:
                embedding_store = index_stores["all"]
            else:
                embedding_store = index_stores[f"{graphname}_{index_name}"]
            logger.info(f"Embed to {graphname}_{index_name}: {v_id}")
            sp.create_task(
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
    conn: TigerGraphConnection
):  
    """
    Creates and starts one worker for each extract job
    chan expects:
    (chunk , chunk_id) <- q.get()
    """
    logger.info("Reading from extract channel")
    # consume task queue
    async with asyncio.TaskGroup() as sp:
        async for item in extract_chan:
            sp.create_task(
                workers.extract(upsert_chan, embed_chan, extractor, conn, *item)
            )

    logger.info(f"extract done")

    logger.info("closing upsert and embed chan")
    upsert_chan.close()
    embed_chan.close()


async def run(
    graphname: str, 
    conn: TigerGraphConnection,
    upsert_limit=100
):
    """
    Set up SupportAI:
        - Install necessary queries.
        - Process the documents into:
            - chuncks
            - embeddings
            - entities/relationshio (and their embeddings)
            - upsert everything to the graph
    """

    extractor, index_stores = await init(conn)
    init_start = time.perf_counter()

    doc_process_switch = True

    if doc_process_switch:
        logger.info("Doc Processing Start")
        docs_chan = Channel(1)
        embed_chan = Channel(100)
        upsert_chan = Channel(100)
        extract_chan = Channel(100)
        async with asyncio.TaskGroup() as sp:
            # Get docs
            sp.create_task(stream_docs(conn, docs_chan, 10))
            # Process docs
            sp.create_task(
                chunk_docs(conn, docs_chan, embed_chan, upsert_chan, extract_chan)
            )
            # Upsert chunks
            sp.create_task(upsert(upsert_chan))
            # Embed
            sp.create_task(embed(embed_chan, index_stores, graphname))
            # Extract entities
            sp.create_task(
                extract(extract_chan, upsert_chan, embed_chan, extractor, conn)
            )
    init_end = time.perf_counter()
    logger.info("Doc Processing End")
    logger.info(f"DONE. supportai system initializer dT: {init_end-init_start}")
