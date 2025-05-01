import asyncio
import base64
import logging
import time
import json
import traceback
from urllib.parse import quote_plus
from typing import Iterable, List, Optional, Tuple

import ecc_util
import httpx
from aiochannel import Channel
from graphrag import community_summarizer, util
from langchain_community.graphs.graph_document import GraphDocument, Node
from pyTigerGraph import AsyncTigerGraphConnection

from common.config import milvus_config
from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.base_embedding_store import EmbeddingStore
from common.extractors import BaseExtractor, LLMEntityRelationshipExtractor
from common.logs.logwriter import LogWriter

vertex_field = milvus_config.get("vertex_field", "vertex_id")

logger = logging.getLogger(__name__)

async def install_query(
    conn: AsyncTigerGraphConnection, query_path: str, install: bool = True
) -> dict[str, httpx.Response | str | None]:
    LogWriter.info(f"Installing query {query_path}")
    with open(f"{query_path}.gsql", "r") as f:
        query = f.read()

    query_name = query_path.split("/")[-1]
    query = f"""\
USE GRAPH {conn.graphname}
{query}
"""
    if install:
       query += f"""
INSTALL QUERY {query_name}
"""
    async with util.tg_sem:
        res = await conn.gsql(query)

    if "error" in res:
        LogWriter.error(res)
        return {
            "result": None,
            "error": True,
            "message": f"Failed to install query {query_name}",
        }

    return {"result": res, "error": False}


chunk_sem = asyncio.Semaphore(20)


async def chunk_doc(
    conn: AsyncTigerGraphConnection,
    doc: dict[str, str],
    upsert_chan: Channel,
    embed_chan: Channel,
    extract_chan: Channel,
):
    """
    Chunks a document.
    Places the resulting chunks into the upsert channel (to be upserted to TG)
    and the embed channel (to be embedded and written to the vector store)
    """

    # if loader is running, wait until it's done
    if not util.loading_event.is_set():
        logger.info("Chunk worker waiting for loading event to finish")
        await util.loading_event.wait()

    async with chunk_sem:
        if "ctype" in doc["attributes"]:
            chunker_type = doc["attributes"]["ctype"].lower().strip()
        else:
            chunker_type = ""
        chunker = ecc_util.get_chunker(chunker_type)
        # decode the text return from tigergraph as it was encoded when written into jsonl file for uploading
        chunks = chunker.chunk(doc["attributes"]["text"].encode('utf-8').decode('unicode_escape'))
        v_id = util.process_id(doc["v_id"])
        if v_id != doc["v_id"]:
            logger.info(f"""Cloning doc/content {doc["v_id"]} -> {v_id}""")
            await upsert_chan.put((upsert_doc, (conn, v_id, chunker_type, doc["attributes"]["text"])))
       
        logger.info(f"Chunking {v_id}")
        for i, chunk in enumerate(chunks):
            chunk_id = f"{v_id}_chunk_{i}"
            logger.info(f"Processing chunk {chunk_id}")

            # send chunks to be upserted (func, args)
            logger.info("chunk writes to upsert_chan")
            await upsert_chan.put((upsert_chunk, (conn, v_id, chunk_id, chunk)))

            # send chunks to have entities extracted
            logger.info("chunk writes to extract_chan")
            await extract_chan.put((chunk, chunk_id))

            # send chunks to be embedded
            logger.info("chunk writes to embed_chan")
            await embed_chan.put((chunk_id, chunk, "DocumentChunk"))

    return v_id


async def upsert_doc(conn: AsyncTigerGraphConnection, doc_id, ctype, content_text):
    date_added = int(time.time())
    await util.upsert_vertex(
        conn,
        "Document",
        doc_id,
        attributes={"epoch_added": date_added, "epoch_processed": date_added},
    )
    await util.upsert_vertex(
        conn,
        "Content",
        doc_id,
        attributes={"ctype": ctype, "text": content_text, "epoch_added": date_added},
    )
    await util.upsert_edge(
        conn, "Document", doc_id, "HAS_CONTENT", "Content", doc_id
    )

async def upsert_chunk(conn: AsyncTigerGraphConnection, doc_id, chunk_id, chunk):
    logger.info(f"Upserting chunk {chunk_id}")
    date_added = int(time.time())
    await util.upsert_vertex(
        conn,
        "DocumentChunk",
        chunk_id,
        attributes={"epoch_added": date_added, "idx": int(chunk_id.split("_")[-1])},
    )
    await util.upsert_vertex(
        conn,
        "Content",
        chunk_id,
        attributes={"text": chunk, "epoch_added": date_added},
    )
    await util.upsert_edge(
        conn, "DocumentChunk", chunk_id, "HAS_CONTENT", "Content", chunk_id
    )
    await util.upsert_edge(
        conn, "Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id
    )
    if int(chunk_id.split("_")[-1]) > 0:
        await util.upsert_edge(
            conn,
            "DocumentChunk",
            chunk_id,
            "IS_AFTER",
            "DocumentChunk",
            doc_id + "_chunk_" + str(int(chunk_id.split("_")[-1]) - 1),
        )


embed_sem = asyncio.Semaphore(20)


async def embed(
    embed_svc: EmbeddingModel,
    embed_store: EmbeddingStore,
    v_id: str | Tuple[str, str],
    content: str,
):
    """
    Args:
        graphname: str
            the name of the graph the documents are in
        embed_svc: EmbeddingModel
            The class used to vectorize text
        embed_store:
            The class used to store the vectore to a vector DB
        v_id: str
            the vertex id that will be embedded
        content: str
            the content of the document/chunk
        index_name: str
            the vertex index to write to
    """
    async with embed_sem:
        logger.info(f"Embedding {v_id}")

        # if loader is running, wait until it's done
        if not util.loading_event.is_set():
            logger.info("Embed worker waiting for loading event to finish")
            await util.loading_event.wait()
        try:
            await embed_store.aadd_embeddings([(content, [])], [{vertex_field: v_id}])
        except Exception as e:
            logger.error(f"Failed to add embeddings for {v_id}: {e}")


async def get_vert_desc(conn, v_id, node: Node):
    desc = [node.properties.get("description", "")]
    exists = await util.check_vertex_exists(conn, v_id)
    # if vertex exists, get description content and append this description to it
    if not exists.get("error", False):
        # deduplicate descriptions
        desc.extend(exists["resp"][0]["attributes"]["description"])
        desc = list(set(desc))
    return desc


extract_sem = asyncio.Semaphore(20)


async def extract(
    upsert_chan: Channel,
    embed_chan: Channel,
    extractor: BaseExtractor,
    conn: AsyncTigerGraphConnection,
    chunk: str,
    chunk_id: str,
):
    # if loader is running, wait until it's done
    if not util.loading_event.is_set():
        logger.info("Extract worker waiting for loading event to finish")
        await util.loading_event.wait()

    async with extract_sem:
        try:
            extracted: list[GraphDocument] = await extractor.aextract(chunk)
            logger.info(
                f"Extracting chunk: {chunk_id} ({len(extracted)} graph docs extracted)"
            )
        except Exception as e:
            logger.error(f"Failed to extract chunk {chunk_id}: {e}")
            extracted = []

        # upsert nodes and edges to the graph
        for doc in extracted:
            for i, node in enumerate(doc.nodes):
                logger.info(f"extract writes entity vert to upsert\nNode: {node.id}")
                v_id = util.process_id(str(node.id))
                if len(v_id) == 0:
                    continue
                desc = await get_vert_desc(conn, v_id, node)

                # embed the entity
                # embed with the v_id if the description is blank
                if len(desc[0]) == 0:
                    desc[0] = str(node.id)

                # (v_id, content, index_name)
                await embed_chan.put((v_id, desc[0], "Entity"))

                await upsert_chan.put(
                    (
                        util.upsert_vertex,  # func to call
                        (
                            conn,
                            "Entity",  # v_type
                            v_id,  # v_id
                            {  # attrs
                                "description": desc,
                                "epoch_added": int(time.time()),
                            },
                        ),
                    )
                )
                if isinstance(extractor, LLMEntityRelationshipExtractor):
                    logger.info("extract writes type vert to upsert")
                    type_id = util.process_id(node.type)
                    if len(type_id) == 0:
                        continue
                    await upsert_chan.put(
                        (
                            util.upsert_vertex,  # func to call
                            (
                                conn,
                                "EntityType",  # v_type
                                type_id,  # v_id
                                {  # attrs
                                    "epoch_added": int(time.time()),
                                },
                            )
                        )
                    )
                    logger.info("extract writes entity_has_type edge to upsert")
                    await upsert_chan.put(
                        (
                            util.upsert_edge,
                            (
                                conn,
                                "Entity",  # src_type
                                v_id,  # src_id
                                "ENTITY_HAS_TYPE",  # edgeType
                                "EntityType",  # tgt_type
                                type_id,  # tgt_id
                                None,  # attributes
                            ),
                        )
                    )

                # link the entity to the chunk it came from
                logger.info("extract writes contains edge to upsert")
                await upsert_chan.put(
                    (
                        util.upsert_edge,
                        (
                            conn,
                            "DocumentChunk",  # src_type
                            chunk_id,  # src_id
                            "CONTAINS_ENTITY",  # edge_type
                            "Entity",  # tgt_type
                            v_id,  # tgt_id
                            None,  # attributes
                        ),
                    )
                )
                for node2 in doc.nodes[i + 1:]:
                    v_id2 = util.process_id(str(node2.id))
                    if len(v_id2) == 0:
                        continue
                    await upsert_chan.put(
                    (
                        util.upsert_edge,
                        (
                            conn,
                            "Entity",  # src_type
                            v_id,  # src_id
                            "RELATIONSHIP",  # edgeType
                            "Entity",  # tgt_type
                            v_id2,  # tgt_id
                            {"relation_type": "DOC_CHUNK_COOCCURRENCE"},  # attributes
                        ),
                    )
                )

            for edge in doc.relationships:
                logger.info(
                    f"extract writes relates edge to upsert:{edge.source.id} -({edge.type})->  {edge.target.id}"
                )
                # upsert verts first to make sure their ID becomes an attr
                v_id = util.process_id(edge.source.id)  # src_id
                if len(v_id) == 0:
                    continue
                desc = await get_vert_desc(conn, v_id, edge.source)
                if len(desc[0]) == 0:
                    await embed_chan.put((v_id, v_id, "Entity"))
                else:
                    # (v_id, content, index_name)
                    await embed_chan.put((v_id, desc[0], "Entity"))
                await upsert_chan.put(
                    (
                        util.upsert_vertex,  # func to call
                        (
                            conn,
                            "Entity",  # v_type
                            v_id,
                            {  # attrs
                                "description": desc,
                                "epoch_added": int(time.time()),
                            },
                        ),
                    )
                )
                v_id = util.process_id(edge.target.id)
                if len(v_id) == 0:
                    continue
                desc = await get_vert_desc(conn, v_id, edge.target)
                if len(desc[0]) == 0:
                    await embed_chan.put((v_id, v_id, "Entity"))
                else:
                    # (v_id, content, index_name)
                    await embed_chan.put((v_id, desc[0], "Entity"))
                await upsert_chan.put(
                    (
                        util.upsert_vertex,  # func to call
                        (
                            conn,
                            "Entity",  # v_type
                            v_id,  # src_id
                            {  # attrs
                                "description": desc,
                                "epoch_added": int(time.time()),
                            },
                        ),
                    )
                )

                # upsert the edge between the two entities
                await upsert_chan.put(
                    (
                        util.upsert_edge,
                        (
                            conn,
                            "Entity",  # src_type
                            util.process_id(edge.source.id),  # src_id
                            "RELATIONSHIP",  # edgeType
                            "Entity",  # tgt_type
                            util.process_id(edge.target.id),  # tgt_id
                            {"relation_type": edge.type},  # attributes
                        ),
                    )
                )
                # embed "Relationship",
                # (v_id, content, index_name)
                # right now, we're not embedding relationships in graphrag


resolve_sem = asyncio.Semaphore(20)


async def resolve_entity(
    conn: AsyncTigerGraphConnection,
    upsert_chan: Channel,
    embed_store: EmbeddingStore,
    entity_id: str | Tuple[str, str],
):
    """
    get all vectors of E (one name can have multiple discriptions)
    get ents close to E
    for e in ents:
        if e is 95% similar to E and edit_dist(E,e) <=3:
            merge
            mark e as processed

    mark as processed
    """

    # if loader is running, wait until it's done
    if not util.loading_event.is_set():
        logger.info("Entity Resolution worker waiting for loading event to finish")
        await util.loading_event.wait()

    async with resolve_sem:
        try:
            logger.info(f"Resolving Entity {entity_id}")
            results = await embed_store.aget_k_closest(entity_id)
            logger.info(f"Resolving Entity {entity_id} to {results}")

        except Exception:
            err = traceback.format_exc()
            logger.error(err)
            return

        if len(results) == 0:
            logger.error(
                f"aget_k_closest should, minimally, return the entity itself.\n{results}"
            )
            raise Exception()

        # merge all entities into the ResolvedEntity vertex
        # use the longest v_id as the resolved entity's v_id
        if isinstance(entity_id, tuple):
          resolved_entity_id = entity_id[0]
        else:
          resolved_entity_id = entity_id
        for v in results:
            if len(v) > len(resolved_entity_id):
                resolved_entity_id = v

        logger.debug(f"Merging {results} to ResolvedEntity {resolved_entity_id}")
        # upsert the resolved entity
        await upsert_chan.put(
            (
                util.upsert_vertex,  # func to call
                (
                    conn,
                    "ResolvedEntity",  # v_type
                    resolved_entity_id,  # v_id
                    {  # attrs
                    },
                ),
            )
        )

        # create RESOLVES_TO edges from each entity to the ResolvedEntity
        for v in results:
            await upsert_chan.put(
                (
                    util.upsert_edge,
                    (
                        conn,
                        "Entity",  # src_type
                        v,  # src_id
                        "RESOLVES_TO",  # edge_type
                        "ResolvedEntity",  # tgt_type
                        resolved_entity_id,  # tgt_id
                        None,  # attributes
                    ),
                )
            )


comm_sem = asyncio.Semaphore(20)


async def process_community(
    conn: AsyncTigerGraphConnection,
    upsert_chan: Channel,
    embed_chan: Channel,
    i: int,
    comm_id: str,
):
    """
    https://github.com/microsoft/graphrag/blob/main/graphrag/prompt_tune/template/community_report_summarization.py

    Get children verts (Entity for layer-1 Communities, Community otherwise)
    if the commuinty only has one child, use its description -- no need to summarize

    embed summaries
    """
    # if loader is running, wait until it's done
    if not util.loading_event.is_set():
        logger.info("Process Community worker waiting for loading event to finish")
        await util.loading_event.wait()

    async with comm_sem:
        logger.info(f"Processing Community: {comm_id}")
        # get the children of the community
        children = await util.get_commuinty_children(conn, i, comm_id)
        comm_id = util.process_id(comm_id)
        err = False

        # if the community only has one child, use its description
        if len(children) == 1:
            summary = children[0]
        else:
            llm = ecc_util.get_llm_service()
            summarizer = community_summarizer.CommunitySummarizer(llm)
            summary = await summarizer.summarize(comm_id, children)
            if summary["error"]:
                summary = await summarizer.summarize(comm_id, children)
                if summary["error"]:
                    logger.error(f"Failed to summarize community {comm_id} with message {summary['message']}")
                summary = "Should ignore due to summary error."
            else:
                summary = summary["summary"]

        if not err:
            logger.debug(f"Community {comm_id}: {children}, {summary}")
            await upsert_chan.put(
                (
                    util.upsert_vertex,  # func to call
                    (
                        conn,
                        "Community",  # v_type
                        comm_id,  # v_id
                        {  # attrs
                            "description": summary,
                            "iteration": i,
                        },
                    ),
                )
            )

            # (v_id, content, index_name)
            await embed_chan.put((comm_id, summary, "Community"))
