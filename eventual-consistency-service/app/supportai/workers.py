import base64
import time
import logging
import httpx
from urllib.parse import quote_plus

import ecc_util

from aiochannel import Channel
from supportai import util
from pyTigerGraph import TigerGraphConnection
from common.config import milvus_config
from langchain_community.graphs.graph_document import GraphDocument, Node
from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors.BaseExtractor import BaseExtractor
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
    chunker = ecc_util.get_chunker()
    chunks = chunker.chunk(doc["attributes"]["text"])
    v_id = util.process_id(doc["v_id"])
    logger.info(f"Chunking {v_id}")
    for i, chunk in enumerate(chunks):
        chunk_id = f"{v_id}_chunk_{i}"
        # send chunks to be upserted (func, args)
        logger.info("chunk writes to upsert_chan")
        await upsert_chan.put((upsert_chunk, (conn, v_id, chunk_id, chunk)))

        # send chunks to be embedded
        logger.info("chunk writes to embed_chan")
        await embed_chan.put((chunk_id, chunk, "DocumentChunk"))

        # send chunks to have entities extracted
        logger.info("chunk writes to extract_chan")
        await extract_chan.put((chunk, chunk_id))

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
    logger.info(f"Embedding {v_id}")

    vec = await embed_svc.aembed_query(content)
    await embed_store.aadd_embeddings([(content, vec)], [{vertex_field: v_id}])


async def get_vert_desc(conn, v_id, node: Node):
    desc = [node.properties.get("description", "")]
    exists = await util.check_vertex_exists(conn, v_id)
    # if vertex exists, get description content and append this description to it
    if not exists["error"]:
        # deduplicate descriptions
        desc.extend(exists["results"][0]["attributes"]["description"])
        desc = list(set(desc))
    return desc


async def extract(
    upsert_chan: Channel,
    embed_chan: Channel,
    extractor: BaseExtractor,
    conn: TigerGraphConnection,
    chunk: str,
    chunk_id: str,
):
    logger.info(f"Extracting chunk: {chunk_id}")
    extracted: list[GraphDocument] = await extractor.aextract(chunk)
    # upsert nodes and edges to the graph
    for doc in extracted:
        for node in doc.nodes:
            logger.info(f"extract writes entity vert to upsert\nNode: {node.id}")
            v_id = util.process_id(str(node.id))
            if len(v_id) == 0:
                continue
            desc = await get_vert_desc(conn, v_id, node)

            # embed the entity
            # embed with the v_id if the description is blank
            if len(desc[0]):
                await embed_chan.put((v_id, v_id, "Entity"))
            else:
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

        for edge in doc.relationships:
            # upsert verts first to make sure their ID becomes an attr
            v_id = edge.type
            if len(v_id) == 0:
                continue
            # embed "Relationship"
            await embed_chan.put((v_id, v_id, "Relationship"))

            await upsert_chan.put(
                (
                    util.upsert_vertex,  # func to call
                    (
                        conn,
                        "Relationship",  # v_type
                        v_id,
                        {  # attrs
                            "epoch_added": int(time.time()),
                        },
                    ),
                )
            )
            v_id = util.process_id(edge.source.id) # source id
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
            v_id = util.process_id(edge.target.id) # target id
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
                        "IS_HEAD_OF",  # edgeType
                        "Relationship",  # tgt_type
                        edge.type,  # tgt_id
                    ),
                )
            )
            await upsert_chan.put(
                (
                    util.upsert_edge,
                    (
                        conn,
                        "Relationship",  # src_type
                        edge.type, # src_id
                        "HAS_TAIL",  # edgeType
                        "Entity",  # tgt_type
                        util.process_id(edge.target.id),  # tgt_id
                    ),
                )
            )

            # link the relationship to the chunk it came from
            logger.info("extract writes mentions edge to upsert")
            await upsert_chan.put(
                (
                    util.upsert_edge,
                    (
                        conn,
                        "DocumentChunk",  # src_type
                        chunk_id,  # src_id
                        "MENTIONS_RELATIONSHIP",  # edge_type
                        "Relationship",  # tgt_type
                        edge.type,  # tgt_id
                    ),
                )
            )