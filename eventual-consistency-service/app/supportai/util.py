import asyncio
import base64
import json
import logging
import re
import traceback
from glob import glob
from typing import Callable

import httpx
from supportai import workers
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

tg_sem = asyncio.Semaphore(10)

async def install_queries(
    requried_queries: list[str],
    conn: TigerGraphConnection,
):
    # queries that are currently installed
    installed_queries = [q.split("/")[-1] for q in conn.getEndpoints(dynamic=True)]

    # doesn't need to be parallel since tg only does it one at a time
    for q in requried_queries:
        # only install n queries at a time (n=n_workers)
        q_name = q.split("/")[-1]
        # if the query is not installed, install it
        if q_name not in installed_queries:
            res = await workers.install_query(conn, q)
            # stop system if a required query doesn't install
            if res["error"]:
                raise Exception(res["message"])


async def init_embedding_index(s: MilvusEmbeddingStore, vertex_field: str):
    content = "init"
    vec = embedding_service.embed_query(content)
    await s.aadd_embeddings([(content, vec)], [{vertex_field: content}])
    s.remove_embeddings(expr=f"{vertex_field} in ['{content}']")


async def init(
    conn: TigerGraphConnection,
) -> tuple[BaseExtractor, dict[str, MilvusEmbeddingStore]]:
    # install requried queries
    requried_queries = [
        "common/gsql/supportai/Scan_For_Updates",
        "common/gsql/supportai/Update_Vertices_Processing_Status",
        "common/gsql/supportai/ECC_Status",
        "common/gsql/supportai/Check_Nonexistent_Vertices",
        "common/gsql/graphRAG/StreamIds",
        "common/gsql/graphRAG/StreamDocContent",
        # "common/gsql/graphRAG/SetEpochProcessing",
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
            "Relationship"
        ],
    )
    index_stores = {}
    async with asyncio.TaskGroup() as tg:
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
                drop_old=True,
            )

            LogWriter.info(f"Initializing {name}")
            # init collection if it doesn't exist
            if not s.check_collection_exists():
                tg.create_task(init_embedding_index(s, vertex_field))

            index_stores[name] = s

    return extractor, index_stores


def make_headers(conn: TigerGraphConnection):
    if conn.apiToken is None or conn.apiToken == "":
        tkn = base64.b64encode(f"{conn.username}:{conn.password}".encode()).decode()
        headers = {"Authorization": f"Basic {tkn}"}
    else:
        headers = {"Authorization": f"Bearer {conn.apiToken}"}

    return headers


async def stream_ids(
    conn: TigerGraphConnection, v_type: str, current_batch: int, ttl_batches: int
) -> dict[str, str | list[str]]:
    headers = make_headers(conn)

    try:
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            async with tg_sem:
                res = await client.post(
                    f"{conn.restppUrl}/query/{conn.graphname}/StreamIds",
                    params={
                        "current_batch": current_batch,
                        "ttl_batches": ttl_batches,
                        "v_type": v_type,
                    },
                    headers=headers,
                )
        ids = res.json()["results"][0]["@@ids"]
        return {"error": False, "ids": ids}

    except Exception as e:
        exc = traceback.format_exc()
        LogWriter.error(f"/{conn.graphname}/query/StreamIds\nException Trace:\n{exc}")

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


def process_id(v_id: str):
    v_id = v_id.replace(" ", "_").replace("/", "")

    has_func = re.compile(r"(.*)\(").findall(v_id)
    if len(has_func) > 0:
        v_id = has_func[0]
    if v_id == "''" or v_id == '""':
        return ""

    return v_id


async def upsert_vertex(
    conn: TigerGraphConnection,
    vertex_type: str,
    vertex_id: str,
    attributes: dict,
):
    logger.info(f"Upsert vertex: {vertex_type} {vertex_id}")
    vertex_id = vertex_id.replace(" ", "_")
    attrs = map_attrs(attributes)
    data = json.dumps({"vertices": {vertex_type: {vertex_id: attrs}}})
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        async with tg_sem:
            try:
                res = await client.post(
                    f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
                )

                res.raise_for_status()
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}.")
                logger.error(f"Request body: {data}")
                logger.error(f"Details: {exc}")
                # Check if the exception has a response attribute
                if hasattr(exc, 'response') and exc.response is not None:
                    logger.error(f"Response content: {exc.response.content}")
            except httpx.HTTPStatusError as exc:
                logger.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
                logger.error(f"Response content: {exc.response.content}")
                logger.error(f"Request body: {data}")


async def check_vertex_exists(conn, v_id: str):
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        async with tg_sem:
            try:
                res = await client.get(
                    f"{conn.restppUrl}/graph/{conn.graphname}/vertices/Entity/{v_id}",
                    headers=headers,
                )

                res.raise_for_status()
                return res.json()
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}.")
                logger.error(f"Details: {exc}")
                # Check if the exception has a response attribute
                if hasattr(exc, 'response') and exc.response is not None:
                    logger.error(f"Response content: {exc.response.content}")
                return {"error": "Request failed"}
            except httpx.HTTPStatusError as exc:
                logger.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
                logger.error(f"Response content: {exc.response.content}")
                return {"error": f"HTTP status error {exc.response.status_code}"}



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
    src_v_id = src_v_id.replace(" ", "_")
    tgt_v_id = tgt_v_id.replace(" ", "_")
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
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        async with tg_sem:
            try:
                res = await client.post(
                    f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
                )
                res.raise_for_status()
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}.")
                logger.error(f"Request body: {data}")
                logger.error(f"Details: {exc}")
                # Check if the exception has a response attribute
                if hasattr(exc, 'response') and exc.response is not None:
                    logger.error(f"Response content: {exc.response.content}")
            except httpx.HTTPStatusError as exc:
                logger.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
                logger.error(f"Response content: {exc.response.content}")
                logger.error(f"Request body: {data}")
