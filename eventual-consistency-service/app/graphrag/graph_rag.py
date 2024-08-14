import asyncio
import logging
import time
import traceback

import httpx
from aiochannel import Channel
from graphrag import workers
from graphrag.util import (
    check_vertex_has_desc,
    http_timeout,
    init,
    make_headers,
    stream_ids,
)
from pyTigerGraph import TigerGraphConnection

from common.config import embedding_service
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors.BaseExtractor import BaseExtractor

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
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        for i in range(ttl_batches):
            doc_ids = await stream_ids(conn, "Document", i, ttl_batches)
            if doc_ids["error"]:
                # continue to the next batch.
                # These docs will not be marked as processed, so the ecc will process it eventually.
                continue

            for d in doc_ids["ids"]:
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
    async with asyncio.TaskGroup() as grp:
        async for func, args in upsert_chan:
            logger.info(f"{func.__name__}, {args[1]}")
            # execute the task
            grp.create_task(func(*args))

    logger.info(f"upsert done")


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


async def stream_entities(
    conn: TigerGraphConnection,
    entity_chan: Channel,
    ttl_batches: int = 50,
):
    """
    Streams entity IDs from the grpah
    """
    logger.info("streaming entities")
    for i in range(ttl_batches):
        ids = await stream_ids(conn, "Entity", i, ttl_batches)
        if ids["error"]:
            # continue to the next batch.
            # These docs will not be marked as processed, so the ecc will process it eventually.
            continue

        for i in ids["ids"]:
            if len(i) > 0:
                await entity_chan.put(i)

    logger.info("stream_enities done")
    # close the docs chan -- this function is the only sender
    logger.info("closing entities chan")
    entity_chan.close()


async def resolve_entities(
    conn: TigerGraphConnection,
    emb_store: MilvusEmbeddingStore,
    entity_chan: Channel,
    upsert_chan: Channel,
):
    """
    Merges entities into their ResolvedEntity form
        Groups what should be the same entity into a resolved entity (e.g. V_type and VType should be merged)

    Copies edges between entities to their respective ResolvedEntities
    """
    async with asyncio.TaskGroup() as grp:
        # for every entity
        async for entity_id in entity_chan:
            grp.create_task(
                workers.resolve_entity(conn, upsert_chan, emb_store, entity_id)
            )
    logger.info("closing upsert_chan")
    upsert_chan.close()

    # Copy RELATIONSHIP edges to RESOLVED_RELATIONSHIP
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        res = await client.get(
            f"{conn.restppUrl}/query/{conn.graphname}/ResolveRelationships/",
            headers=headers,
        )
        res.raise_for_status()


async def communities(conn: TigerGraphConnection, comm_process_chan: Channel):
    """
    Run louvain
    """
    # first pass: Group ResolvedEntities into Communities
    logger.info("Initializing Communities (first louvain pass)")
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.get(
            f"{conn.restppUrl}/query/{conn.graphname}/graphrag_louvain_init",
            params={"n_batches": 1},
            headers=headers,
        )
        res.raise_for_status()
    # get the modularity
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.get(
            f"{conn.restppUrl}/query/{conn.graphname}/modularity",
            params={"iteration": 1, "batch_num": 1},
            headers=headers,
        )
        res.raise_for_status()
    mod = res.json()["results"][0]["mod"]
    logger.info(f"****mod pass 1: {mod}")
    await stream_communities(conn, 1, comm_process_chan)

    # nth pass: Iterate on Resolved Entities until modularity stops increasing
    prev_mod = -10
    i = 0
    while abs(prev_mod - mod) > 0.0000001 and prev_mod != 0:
        prev_mod = mod
        i += 1
        logger.info(f"Running louvain on Communities (iteration: {i})")
        # louvain pass
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                f"{conn.restppUrl}/query/{conn.graphname}/graphrag_louvain_communities",
                params={"n_batches": 1, "iteration": i},
                headers=headers,
            )

        res.raise_for_status()

        # get the modularity
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                f"{conn.restppUrl}/query/{conn.graphname}/modularity",
                params={"iteration": i + 1, "batch_num": 1},
                headers=headers,
            )
        res.raise_for_status()
        mod = res.json()["results"][0]["mod"]
        logger.info(f"*** mod pass {i+1}: {mod} (diff= {abs(prev_mod - mod)})")

        # write iter to chan for layer to be processed
        await stream_communities(conn, i + 1, comm_process_chan)

    # TODO: erase last run since it's ∆q to the run before it will be small
    logger.info("closing communities chan")
    comm_process_chan.close()


async def stream_communities(
    conn: TigerGraphConnection,
    i: int,
    comm_process_chan: Channel,
):
    """
    Streams Community IDs from the grpah for a given iteration (from the channel)
    """
    logger.info("streaming communities")

    headers = make_headers(conn)
    # TODO:
    # can only do one layer at a time to ensure that every child community has their descriptions

    # async for i in community_chan:
    # get the community from that layer
    async with httpx.AsyncClient(timeout=None) as client:
        resp = await client.get(
            f"{conn.restppUrl}/query/{conn.graphname}/stream_community",
            params={"iter": i},
            headers=headers,
        )
    resp.raise_for_status()
    comms = resp.json()["results"][0]["Comms"]

    for c in comms:
        await comm_process_chan.put((i, c["v_id"]))

    # Wait for all communities for layer i to be processed before doing next layer
    # all community descriptions must be populated before the next layer can be processed
    if len(comms) > 0:
        while not await check_vertex_has_desc(conn, i):
            logger.info(f"Waiting for layer{i} to finish processing")
            await asyncio.sleep(5)
        await asyncio.sleep(3)

    logger.info("stream_communities done")
    logger.info("closing comm_process_chan")


async def summarize_communities(
    conn: TigerGraphConnection,
    comm_process_chan: Channel,
    upsert_chan: Channel,
    embed_chan: Channel,
):
    async with asyncio.TaskGroup() as tg:
        async for c in comm_process_chan:
            tg.create_task(workers.process_community(conn, upsert_chan, embed_chan, *c))

    logger.info("closing upsert_chan")
    upsert_chan.close()
    embed_chan.close()


async def run(graphname: str, conn: TigerGraphConnection):
    """
    Set up GraphRAG:
        - Install necessary queries.
        - Process the documents into:
            - chunks
            - embeddings
            - entities/relationships (and their embeddings)
            - upsert everything to the graph
        - Resolve Entities
            Ex: "Vincent van Gogh" and "van Gogh" should be resolved to "Vincent van Gogh"
    """

    extractor, index_stores = await init(conn)
    init_start = time.perf_counter()

    doc_process_switch = True
    entity_resolution_switch = True
    community_detection_switch = True
    if doc_process_switch:
        logger.info("Doc Processing Start")
        docs_chan = Channel(1)
        embed_chan = Channel(100)
        upsert_chan = Channel(100)
        extract_chan = Channel(100)
        async with asyncio.TaskGroup() as grp:
            # get docs
            grp.create_task(stream_docs(conn, docs_chan, 10))
            # process docs
            grp.create_task(
                chunk_docs(conn, docs_chan, embed_chan, upsert_chan, extract_chan)
            )
            # upsert chunks
            grp.create_task(upsert(upsert_chan))
            # embed
            grp.create_task(embed(embed_chan, index_stores, graphname))
            # extract entities
            grp.create_task(
                extract(extract_chan, upsert_chan, embed_chan, extractor, conn)
            )
    init_end = time.perf_counter()
    logger.info("Doc Processing End")

    # Entity Resolution
    entity_start = time.perf_counter()

    if entity_resolution_switch:
        logger.info("Entity Processing Start")
        entities_chan = Channel(100)
        upsert_chan = Channel(100)
        async with asyncio.TaskGroup() as grp:
            grp.create_task(stream_entities(conn, entities_chan, 50))
            grp.create_task(
                resolve_entities(
                    conn,
                    index_stores[f"{conn.graphname}_Entity"],
                    entities_chan,
                    upsert_chan,
                )
            )
            grp.create_task(upsert(upsert_chan))
    entity_end = time.perf_counter()
    logger.info("Entity Processing End")

    # Community Detection
    community_start = time.perf_counter()
    if community_detection_switch:
        logger.info("Community Processing Start")
        upsert_chan = Channel(10)
        comm_process_chan = Channel(100)
        upsert_chan = Channel(100)
        embed_chan = Channel(100)
        async with asyncio.TaskGroup() as grp:
            # run louvain
            # grp.create_task(communities(conn, communities_chan))
            grp.create_task(communities(conn, comm_process_chan))
            # get the communities
            # grp.create_task( stream_communities(conn, communities_chan, comm_process_chan))
            # summarize each community
            grp.create_task(
                summarize_communities(conn, comm_process_chan, upsert_chan, embed_chan)
            )
            grp.create_task(upsert(upsert_chan))
            grp.create_task(embed(embed_chan, index_stores, graphname))

    community_end = time.perf_counter()
    logger.info("Community Processing End")

    # Community Summarization
    end = time.perf_counter()
    logger.info(f"DONE. graphrag system initializer dT: {init_end-init_start}")
    logger.info(f"DONE. graphrag entity resolution dT: {entity_end-entity_start}")
    logger.info(f"DONE. graphrag community initializer dT: {community_end-community_start}")
    logger.info(f"DONE. graphrag.run() total time elaplsed: {end-init_start}")
