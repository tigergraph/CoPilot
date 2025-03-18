import asyncio
import json
import logging
import time
import traceback
from collections import defaultdict

import httpx
from aiochannel import Channel, ChannelClosed
from graphrag import workers
from graphrag.util import (
    check_all_ents_resolved,
    check_vertex_has_desc,
    check_embedding_rebuilt,
    http_timeout,
    init,
    load_q,
    loading_event,
    make_headers,
    stream_ids,
    tg_sem,
    upsert_batch,
    add_rels_between_types
)
from pyTigerGraph import AsyncTigerGraphConnection

from common.config import embedding_service
from common.config import milvus_config, embedding_store_type, reuse_embedding
from common.embeddings.base_embedding_store import EmbeddingStore
from common.extractors.BaseExtractor import BaseExtractor

logger = logging.getLogger(__name__)

consistency_checkers = {}

async def stream_docs(
    conn: AsyncTigerGraphConnection,
    docs_chan: Channel,
    ttl_batches: int = 10,
):
    """
    Streams the document contents into the docs_chan
    """
    logger.info("streaming docs")
    for i in range(ttl_batches):
        doc_ids = await stream_ids(conn, "Document", i, ttl_batches)
        if doc_ids["error"]:
            # continue to the next batch.
            # These docs will not be marked as processed, so the ecc will process it eventually.
            continue

        for d in doc_ids["ids"]:
            try:
                async with tg_sem:
                    res = await conn.runInstalledQuery(
                        "StreamDocContent",
                        params={"doc": d},
                    )
                logger.info(f"stream_docs writes {d} to docs")
                await docs_chan.put(res[0]["DocContent"][0])
            except Exception as e:
                exc = traceback.format_exc()
                logger.error(f"Error retrieving doc: {d} --> {e}\n{exc}")
                continue  # try retrieving the next doc

    logger.info("stream_docs done")
    # close the docs chan -- this function is the only sender
    logger.info("closing docs chan")
    docs_chan.close()


async def chunk_docs(
    conn: AsyncTigerGraphConnection,
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
        while True:
            try:
                content = await docs_chan.get()
                task = grp.create_task(
                    workers.chunk_doc(conn, content, upsert_chan, embed_chan, extract_chan)
                )
                doc_tasks.append(task)
            except ChannelClosed:
                break
            except Exception:
                raise

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
        while True:
            try:
                (func, args) = await upsert_chan.get()
                logger.info(f"{func.__name__}, {args[1]}")
                # execute the task
                grp.create_task(func(*args))
            except ChannelClosed:
                break
            except Exception:
                raise

    logger.info("upsert done")
    logger.info("closing load_q chan")
    load_q.close()


async def load(conn: AsyncTigerGraphConnection):
    logger.info("Reading from load_q")
    dd = lambda: defaultdict(dd)  # infinite default dict
    batch_size = 500
    # while the load q is still open or has contents
    while not load_q.closed() or not load_q.empty():
        if load_q.closed():
            logger.info(
                f"load queue closed. Flushing load queue (final load for this stage)"
            )
        # if there's `batch_size` entities in the channel, load it
        # or if the channel is closed, flush it
        if load_q.qsize() >= batch_size or load_q.closed() or load_q.should_flush():
            batch = {
                "vertices": defaultdict(dict[str, any]),
                "edges": dd(),
            }
            n_verts = 0
            n_edges = 0
            size = (
                load_q.qsize()
                if load_q.closed() or load_q.should_flush()
                else batch_size
            )
            for _ in range(size):
                t, elem = await load_q.get()
                if t == "FLUSH":
                    logger.debug(f"flush recieved: {t}")
                    load_q._should_flush = False
                    break
                match t:
                    case "vertices":
                        vt, v_id, attr = elem
                        batch[t][vt][v_id] = attr
                        n_verts += 1
                    case "edges":
                        src_v_type, src_v_id, edge_type, tgt_v_type, tgt_v_id, attrs = (
                            elem
                        )
                        batch[t][src_v_type][src_v_id][edge_type][tgt_v_type][
                            tgt_v_id
                        ] = attrs
                        n_edges += 1
                    case _:
                        logger.debug(f"Unexpected data {t} -> {elem} in load_q")

            data = json.dumps(batch)
            logger.info(
                f"Upserting batch size of {size}. ({n_verts} verts | {n_edges} edges. {len(data.encode())/1000:,} kb)"
            )

            loading_event.clear()
            if n_verts >0 or n_edges >0:
                await upsert_batch(conn, data)
                await asyncio.sleep(5)
            loading_event.set()
        else:
            await asyncio.sleep(1)

    # TODO: flush q if it's not empty
    if not load_q.empty():
        raise Exception(f"load_q not empty: {load_q.qsize()}", flush=True)


async def embed(
    embed_chan: Channel, index_stores: dict[str, EmbeddingStore], graphname: str
):
    """
    Creates and starts one worker for each embed job
    chan expects:
    (v_id, content, index_name) <- q.get()
    """
    logger.info("Reading from embed channel")
    async with asyncio.TaskGroup() as grp:
        # consume task queue
        while True:
            try:
                (v_id, content, index_name) = await embed_chan.get()
                if embedding_store_type == "tigergraph":
                    embedding_store = index_stores["tigergraph"]
                    v_id = (v_id, index_name)
                else:
                    embedding_store = index_stores[f"{graphname}_{index_name}"]
                logger.info(f"Embed to {graphname}_{index_name}: {v_id}")
                if reuse_embedding and embedding_store.has_embeddings([v_id]):
                    logger.info(f"Embeddings for {v_id} already exists, skipping to save cost")
                    continue
                grp.create_task(
                    workers.embed(
                        embedding_service,
                        embedding_store,
                        v_id,
                        content,
                    )
                )
            except ChannelClosed:
                break
            except Exception:
                raise

    logger.info(f"embed done")


async def extract(
    extract_chan: Channel,
    upsert_chan: Channel,
    embed_chan: Channel,
    extractor: BaseExtractor,
    conn: AsyncTigerGraphConnection,
):
    """
    Creates and starts one worker for each extract job
    chan expects:
    (chunk , chunk_id) <- q.get()
    """
    logger.info("Reading from extract channel")
    # consume task queue
    async with asyncio.TaskGroup() as grp:
        while True:
            try:
                item = await extract_chan.get()
                grp.create_task(
                    workers.extract(upsert_chan, embed_chan, extractor, conn, *item)
                )
            except ChannelClosed:
                break
            except Exception:
                raise

    logger.info(f"extract done")

    logger.info("closing upsert and embed chan")
    upsert_chan.close()
    embed_chan.close()


async def stream_entities(
    conn: AsyncTigerGraphConnection,
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
                if embedding_store_type == "tigergraph":
                    await entity_chan.put((i, "Entity"))
                else:
                    await entity_chan.put(i)

    logger.info("stream_enities done")
    # close the docs chan -- this function is the only sender
    logger.info("closing entities chan")
    entity_chan.close()


async def resolve_entities(
    conn: AsyncTigerGraphConnection,
    emb_store: EmbeddingStore,
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
        while True:
            try:
                entity_id = await entity_chan.get()
                grp.create_task(
                    workers.resolve_entity(conn, upsert_chan, emb_store, entity_id)
                )
                logger.debug(f"Added Entity to resolve: {entity_id}")
            except ChannelClosed:
                break
            except Exception:
                raise
    logger.info("closing upsert_chan")
    upsert_chan.close()
    logger.info("resolve_entities done")

async def resolve_relationships(
    conn: AsyncTigerGraphConnection
):
    """
    Copy RELATIONSHIP edges to RESOLVED_RELATIONSHIP
    """
    logger.info("Running ResolveRelationships")
    async with tg_sem:
        res = await conn.runInstalledQuery(
            "ResolveRelationships"
        )
    logger.info("resolve_relationships done")

async def communities(conn: AsyncTigerGraphConnection, comm_process_chan: Channel):
    """
    Run louvain
    """
    # first pass: Group ResolvedEntities into Communities
    logger.info("Initializing Communities (first louvain pass)")

    async with tg_sem:
        try:
            res = await conn.runInstalledQuery(
                "graphrag_louvain_init",
                params={"n_batches": 1}
            )
        except Exception as e:
            exc = traceback.format_exc()
            logger.error(f"Error running query: graphrag_louvain_init\n{exc}")

    # get the modularity
    async with tg_sem:
        try:
            res = await conn.runInstalledQuery(
                "modularity",
                params={"iteration": 1, "batch_num": 1}
            )
        except Exception as e:
            exc = traceback.format_exc()
            logger.error(f"Error running query: modularity\n{exc}")

    mod = res[0]["mod"]
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
        async with tg_sem:
            res = await conn.runInstalledQuery(
                "graphrag_louvain_communities",
                params={"n_batches": 1, "iteration": i},
            )

        # get the modularity
        async with tg_sem:
            res = await conn.runInstalledQuery(
                "modularity",
                params={"iteration": i + 1, "batch_num": 1},
            )
        mod = res[0]["mod"]
        logger.info(f"mod pass {i+1}: {mod} (diff= {abs(prev_mod - mod)})")
        # write iter to chan for layer to be processed
        await stream_communities(conn, i + 1, comm_process_chan)

        if mod == 0 or mod - prev_mod <= -0.05:
            break


    # TODO: erase last run since it's ∆q to the run before it will be small
    logger.info("closing communities chan")
    comm_process_chan.close()
    logger.info("communities done")


async def stream_communities(
    conn: AsyncTigerGraphConnection,
    i: int,
    comm_process_chan: Channel,
):
    """
    Streams Community IDs from the grpah for a given iteration (from the channel)
    """
    logger.info("streaming communities")

    headers = make_headers(conn)

    # async for i in community_chan:
    # get the community from that layer
    async with tg_sem:
        resp = await conn.runInstalledQuery(
            "stream_community",
            params={"iter": i}
        )
    comms = resp[0]["Comms"]

    for c in comms:
        await comm_process_chan.put((i, c["v_id"]))

    # Wait for all communities for layer i to be processed before doing next layer
    # all community descriptions must be populated before the next layer can be processed
    if len(comms) > 0:
        n_waits = 0
        while not await check_vertex_has_desc(conn, i):
            logger.info(f"Waiting for layer{i} to finish processing")
            await asyncio.sleep(5)
            n_waits += 1
            if n_waits > 3:
                logger.info("Flushing load_q")
                await load_q.flush(("FLUSH", None))
        await asyncio.sleep(3)
    logger.info("stream_communities done")


async def summarize_communities(
    conn: AsyncTigerGraphConnection,
    comm_process_chan: Channel,
    upsert_chan: Channel,
    embed_chan: Channel,
):
    async with asyncio.TaskGroup() as tg:
        while True:
            try:
                c = await comm_process_chan.get()
                tg.create_task(workers.process_community(conn, upsert_chan, embed_chan, *c))
                logger.debug(f"Added community to process: {c}")
            except ChannelClosed:
                break
            except Exception:
                raise

    logger.info("closing upsert_chan")
    upsert_chan.close()
    embed_chan.close()
    logger.info("summarize_communities done")


async def run(graphname: str, conn: AsyncTigerGraphConnection):
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
        embed_chan = Channel()
        upsert_chan = Channel()
        extract_chan = Channel()
        async with asyncio.TaskGroup() as grp:
            # get docs
            grp.create_task(stream_docs(conn, docs_chan, 100))
            # process docs
            grp.create_task(
                chunk_docs(conn, docs_chan, embed_chan, upsert_chan, extract_chan)
            )
            # upsert chunks
            grp.create_task(upsert(upsert_chan))
            grp.create_task(load(conn))
            # embed
            grp.create_task(embed(embed_chan, index_stores, graphname))
            # extract entities
            grp.create_task(
                extract(extract_chan, upsert_chan, embed_chan, extractor, conn)
            )
    logger.info("Join docs_chan")
    await docs_chan.join()
    logger.info("Join extract_chan")
    await extract_chan.join()
    logger.info("Join embed_chan")
    await embed_chan.join()
    logger.info("Join upsert_chan")
    await upsert_chan.join()
    init_end = time.perf_counter()
    logger.info("Doc Processing End")

    # Type Resolution
    type_start = time.perf_counter()
    logger.info("Type Processing Start")
    res = await add_rels_between_types(conn)
    if res.get("error", False):
        logger.error(f"Error adding relationships between types: {res}")
    else:
        logger.info(f"Added relationships between types: {res}")
    logger.info("Type Processing End")
    type_end = time.perf_counter()
    # Entity Resolution
    entity_start = time.perf_counter()

    if entity_resolution_switch:
        logger.info("Entity Processing Start")
        if embedding_store_type == "tigergraph":
            while not await check_embedding_rebuilt(conn, "Entity"):
                logger.info(f"Waiting for embedding to finish rebuilding")
                await asyncio.sleep(1)
        entities_chan = Channel()
        upsert_chan = Channel()
        load_q.reopen()
        async with asyncio.TaskGroup() as grp:
            grp.create_task(stream_entities(conn, entities_chan, 50))
            if embedding_store_type == "tigergraph":
                embedding_store = index_stores["tigergraph"]
            else:
                embedding_store = index_stores[f"{conn.graphname}_Entity"]
            grp.create_task(
                resolve_entities(
                    conn,
                    embedding_store,
                    entities_chan,
                    upsert_chan,
                )
            )
            grp.create_task(upsert(upsert_chan))
            grp.create_task(load(conn))
        logger.info("Join entities_chan")
        await entities_chan.join()
        logger.info("Join upsert_chan")
        await upsert_chan.join()
        #Resolve relationsihps
        await resolve_relationships(conn)

    entity_end = time.perf_counter()
    logger.info("Entity Processing End")
    while not await check_all_ents_resolved(conn):
        logger.info(f"Waiting for resolved entites to finish loading")
        await asyncio.sleep(1)

    # Community Detection
    community_start = time.perf_counter()
    if community_detection_switch:
        logger.info("Community Processing Start")
        comm_process_chan = Channel()
        upsert_chan = Channel()
        embed_chan = Channel()
        load_q.reopen()
        async with asyncio.TaskGroup() as grp:
            # run louvain
            # get the communities
            grp.create_task(communities(conn, comm_process_chan))
            # summarize each community
            grp.create_task(
                summarize_communities(conn, comm_process_chan, upsert_chan, embed_chan)
            )
            grp.create_task(upsert(upsert_chan))
            grp.create_task(load(conn))
            grp.create_task(embed(embed_chan, index_stores, graphname))
        logger.info("Join comm_process_chan")
        await comm_process_chan.join()
        logger.info("Join embed_chan")
        await embed_chan.join()
        logger.info("Join upsert_chan")
        await upsert_chan.join()

    community_end = time.perf_counter()
    logger.info("Community Processing End")

    # Community Summarization
    end = time.perf_counter()
    logger.info(f"DONE. graphrag system initializer dT: {init_end-init_start}")
    logger.info(f"DONE. graphrag entity resolution dT: {entity_end-entity_start}")
    logger.info(f"DONE. graphrag type creation dT: {type_end-type_start}")
    logger.info(
        f"DONE. graphrag community initializer dT: {community_end-community_start}"
    )
    logger.info(f"DONE. graphrag.run() total time elaplsed: {end-init_start}")
