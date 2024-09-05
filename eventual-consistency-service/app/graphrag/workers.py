import asyncio
import base64
import logging
import time
import traceback
from urllib.parse import quote_plus

import ecc_util
import httpx
from aiochannel import Channel
from graphrag import community_summarizer, util
from langchain_community.graphs.graph_document import GraphDocument, Node
from pyTigerGraph import TigerGraphConnection

from common.config import milvus_config
from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors import BaseExtractor, LLMEntityRelationshipExtractor
from common.logs.logwriter import LogWriter

vertex_field = milvus_config.get("vertex_field", "vertex_id")

logger = logging.getLogger(__name__)


async def install_query(
    conn: TigerGraphConnection, query_path: str
) -> dict[str, httpx.Response | str | None]:
    LogWriter.info(f"Installing query {query_path}")
    with open(f"{query_path}.gsql", "r") as f:
        query = f.read()

    query_name = query_path.split("/")[-1]
    query = f"""\
USE GRAPH {conn.graphname}
{query}
INSTALL QUERY {query_name}"""
    tkn = base64.b64encode(f"{conn.username}:{conn.password}".encode()).decode()
    headers = {"Authorization": f"Basic {tkn}"}

    async with httpx.AsyncClient(timeout=None) as client:
        async with util.tg_sem:
            res = await client.post(
                conn.gsUrl + "/gsqlserver/gsql/file",
                data=quote_plus(query.encode("utf-8")),
                headers=headers,
            )

    if "error" in res.text.lower():
        LogWriter.error(res.text)
        return {
            "result": None,
            "error": True,
            "message": f"Failed to install query {query_name}",
        }

    return {"result": res, "error": False}


chunk_sem = asyncio.Semaphore(20)


async def chunk_doc(
    conn: TigerGraphConnection,
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
        chunker = ecc_util.get_chunker()
        chunks = chunker.chunk(doc["attributes"]["text"])
        v_id = util.process_id(doc["v_id"])
        logger.info(f"Chunking {v_id}")
        for i, chunk in enumerate(chunks):
            chunk_id = f"{v_id}_chunk_{i}"
            # send chunks to be upserted (func, args)
            logger.info("chunk writes to upsert_chan")
            await upsert_chan.put((upsert_chunk, (conn, v_id, chunk_id, chunk)))

            # send chunks to have entities extracted
            logger.info("chunk writes to extract_chan")
            await extract_chan.put((chunk, chunk_id))

            # send chunks to be embedded
            logger.info("chunk writes to embed_chan")
            await embed_chan.put((chunk_id, chunk, "DocumentChunk"))

    return doc["v_id"]


async def upsert_chunk(conn: TigerGraphConnection, doc_id, chunk_id, chunk):
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
    embed_store: MilvusEmbeddingStore,
    v_id: str,
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
            vec = await embed_svc.aembed_query(content)
        except Exception as e:
            logger.error(f"Failed to embed {v_id}: {e}")
            return
        try:
            await embed_store.aadd_embeddings([(content, vec)], [{vertex_field: v_id}])
        except Exception as e:
            logger.error(f"Failed to add embeddings for {v_id}: {e}")


async def get_vert_desc(conn, v_id, node: Node):
    desc = [node.properties.get("description", "")]
    exists = await util.check_vertex_exists(conn, v_id)
    # if vertex exists, get description content and append this description to it
    if not exists.get("error", False):
        # deduplicate descriptions
        desc.extend(exists["results"][0]["attributes"]["description"])
        desc = list(set(desc))
    return desc


extract_sem = asyncio.Semaphore(20)


async def extract(
    upsert_chan: Channel,
    embed_chan: Channel,
    extractor: BaseExtractor,
    conn: TigerGraphConnection,
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
    conn: TigerGraphConnection,
    upsert_chan: Channel,
    emb_store: MilvusEmbeddingStore,
    entity_id: str,
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
            results = await emb_store.aget_k_closest(entity_id)

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
        resolved_entity_id = entity_id
        for v in results:
            if len(v) > len(resolved_entity_id):
                resolved_entity_id = v

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
    conn: TigerGraphConnection,
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
                logger.error(f"Failed to summarize community {comm_id}")
                err = True
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
