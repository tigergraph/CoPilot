import asyncio
import base64
import json
import logging
import traceback

import httpx
from graphrag import workers
from pyTigerGraph import TigerGraphConnection

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
from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)
http_timeout = httpx.Timeout(15.0)


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
                    task = grp.create_task(workers.install_query(conn, q))
                    tasks.append(task)

    for t in tasks:
        logger.info(t.result())
        # TODO: Check if anything had an error


async def init(
    conn: TigerGraphConnection,
) -> tuple[BaseExtractor, dict[str, MilvusEmbeddingStore]]:
    # install requried queries
    requried_queries = [
        # "common/gsql/supportai/Scan_For_Updates",
        # "common/gsql/supportai/Update_Vertices_Processing_Status",
        # "common/gsql/supportai/ECC_Status",
        # "common/gsql/supportai/Check_Nonexistent_Vertices",
        "common/gsql/graphRAG/StreamDocIds",
        "common/gsql/graphRAG/StreamDocContent",
    ]
    await install_queries(requried_queries, conn)

    # extractor
    if doc_processing_config.get("extractor") == "graphrag":
        extractor = GraphExtractor()
    elif doc_processing_config.get("extractor") == "llm":
        extractor = LLMEntityRelationshipExtractor(get_llm_service(llm_config))
    else:
        raise ValueError("Invalid extractor type")
    vertex_field = milvus_config.get("vertex_field", "vertex_id")
    index_names = milvus_config.get(
        "indexes",
        [
            "Document",
            "DocumentChunk",
            "Entity",
            "Relationship",
            # "Concept",
        ],
    )
    index_stores = {}
    content = "init"
    # TODO:do concurrently 
    for index_name in index_names:
        name = conn.graphname + "_" + index_name
        s = MilvusEmbeddingStore(
            embedding_service,
            host=milvus_config["host"],
            port=milvus_config["port"],
            support_ai_instance=True,
            collection_name=name,
            username=milvus_config.get("username", ""),
            password=milvus_config.get("password", ""),
            vector_field=milvus_config.get("vector_field", "document_vector"),
            text_field=milvus_config.get("text_field", "document_content"),
            vertex_field=vertex_field,
        )
        # TODO: only do this if collection doesn't exist
        vec = embedding_service.embed_query(content)
        LogWriter.info(f"Initializing {name}")
        s.add_embeddings([(content, vec)], [{vertex_field: content}])
        s.remove_embeddings(expr=f"{vertex_field} in ['{content}']")
        index_stores[name] = s

    return extractor, index_stores


def make_headers(conn: TigerGraphConnection):
    if conn.apiToken is None or conn.apiToken == "":
        tkn = base64.b64encode(f"{conn.username}:{conn.password}".encode()).decode()
        headers = {"Authorization": f"Basic {tkn}"}
    else:
        headers = {"Authorization": f"Bearer {conn.apiToken}"}

    return headers


async def stream_doc_ids(
    conn: TigerGraphConnection, current_batch: int, ttl_batches: int
) -> dict[str, str | list[str]]:
    headers = make_headers(conn)

    try:
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            res = await client.post(
                f"{conn.restppUrl}/query/{conn.graphname}/StreamDocIds",
                params={
                    "current_batch": current_batch,
                    "ttl_batches": ttl_batches,
                },
                headers=headers,
            )
        ids = res.json()["results"][0]["@@doc_ids"]
        return {"error": False, "ids": ids}

    except Exception as e:
        exc = traceback.format_exc()
        LogWriter.error(
            f"/{conn.graphname}/query/StreamDocIds\nException Trace:\n{exc}"
        )

        return {"error": True, "message": str(e)}


def map_attrs(attributes: dict):
    # map attrs
    attrs = {}
    for k, v in attributes.items():
        if isinstance(v, tuple):
            attrs[k] = {"value": v[0], "op": v[1]}
        elif isinstance(v, dict):
            attrs[k] = {
                "value": {"keylist": list(v.keys()), "valuelist": list(v.values())}
            }
        else:
            attrs[k] = {"value": v}
    return attrs


async def upsert_vertex(
    conn: TigerGraphConnection,
    vertex_type: str,
    vertex_id: str,
    attributes: dict,
):
    attrs = map_attrs(attributes)
    data = json.dumps({"vertices": {vertex_type: {vertex_id: attrs}}})
    headers = make_headers(conn)
    # print("upsert vertex>>>", vertex_id)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        res = await client.post(
            f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
        )

        res.raise_for_status()


async def upsert_edge(
    conn: TigerGraphConnection,
    src_v_type: str,
    src_v_id: str,
    edge_type: str,
    tgt_v_type: str,
    tgt_v_id: str,
    attributes: dict = None,
):
    if attributes is None:
        attrs = {}
    else:
        attrs = map_attrs(attributes)
    data = json.dumps(
        {
            "edges": {
                src_v_type: {
                    src_v_id: {
                        edge_type: {
                            tgt_v_type: {
                                tgt_v_id: attrs,
                            }
                        }
                    },
                }
            }
        }
    )
    headers = make_headers(conn)
    # print("upsert edge >>>", src_v_id, tgt_v_id)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        res = await client.post(
            f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
        )
        res.raise_for_status()
