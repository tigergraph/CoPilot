import base64
import logging
import time
from urllib.parse import quote_plus

import ecc_util
import httpx
from aiochannel import Channel
from common.config import milvus_config
from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from common.extractors.BaseExtractor import BaseExtractor
from common.logs.logwriter import LogWriter
from graphrag import util  # import upsert_edge, upsert_vertex
from langchain_community.graphs.graph_document import GraphDocument
from pyTigerGraph import TigerGraphConnection

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
    v_id = doc["v_id"]
    logger.info(f"Chunking {v_id}")
    for i, chunk in enumerate(chunks):
        chunk_id = f"{v_id}_chunk_{i}"
        # send chunks to be upserted (func, args)
        logger.info("chunk writes to upsert_chan")
        await upsert_chan.put((upsert_chunk, (conn, v_id, chunk_id, chunk)))

        # send chunks to be embedded
        logger.info("chunk writes to embed_chan")
        await embed_chan.put((v_id, chunk, "DocumentChunk"))

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
            v_id = str(node.id)
            desc = node.properties.get("description", "")
            await upsert_chan.put(
                (
                    util.upsert_vertex,  # func to call
                    # conn, v_id, chunk_id, chunk
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
                        str(node.id),  # tgt_id
                        None,  # attributes
                    ),
                )
            )

            # embed the entity
            # (v_id, content, index_name)
            await embed_chan.put((v_id, desc, "Entity"))

        for edge in doc.relationships:
            logger.info(
                f"extract writes relates edge to upsert\n{edge.source.id} -({edge.type})->  {edge.target.id}"
            )
            await upsert_chan.put(
                (
                    util.upsert_edge,
                    (
                        conn,
                        "Entity",  # src_type
                        edge.source.id,  # src_id
                        "RELATIONSHIP",  # edgeType
                        "Entity",  # tgt_type
                        edge.target.id,  # tgt_id
                        {"relation_type": edge.type},  # attributes
                    ),
                )
            )
            # embed "Relationship",
            # (v_id, content, index_name)
