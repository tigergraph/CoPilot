import base64
import json
import time
import traceback
from urllib.parse import quote_plus

import httpx
from pyTigerGraph import TigerGraphConnection

from common.logs.logwriter import LogWriter


def make_headers(conn: TigerGraphConnection):
    if conn.apiToken is None or conn.apiToken == "":
        tkn = base64.b64encode(f"{conn.username}:{conn.password}".encode()).decode()
        headers = {"Authorization": f"Basic {tkn}"}
    else:
        headers = {"Authorization": f"Bearer {conn.apiToken}"}

    return headers


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


async def stream_doc_ids(
    conn: TigerGraphConnection, current_batch: int, ttl_batches: int
) -> dict[str, str | list[str]]:
    headers = make_headers(conn)

    try:
        async with httpx.AsyncClient(timeout=None) as client:
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


async def stream_docs(conn: TigerGraphConnection, ttl_batches: int = 10):
    headers = make_headers(conn)
    for i in range(ttl_batches):
        doc_ids = await stream_doc_ids(conn, i, ttl_batches)
        if doc_ids["error"]:
            print(doc_ids)
            break  # TODO: handle error

        print("*******")
        print(doc_ids)
        print("*******")
        for d in doc_ids["ids"]:
            async with httpx.AsyncClient(timeout=None) as client:
                res = await client.get(
                    f"{conn.restppUrl}/query/{conn.graphname}/StreamDocContent/",
                    params={"doc": d},
                    headers=headers,
                )

                # TODO: check for errors
                yield res.json()["results"][0]["DocContent"][0]
            return  # single doc test FIXME: delete
        # return # single batch test FIXME: delete


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
    attributes: dict = None,
):
    attrs = map_attrs(attributes)
    data = json.dumps({"vertices": {vertex_type: {vertex_id: attrs}}})
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.post(
            f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
        )
        print(res)

async def upsert_edge(
    conn: TigerGraphConnection,
    vertex_type: str,
    vertex_id: str,
    attributes: dict = None,
):
   TODO 
    attrs = map_attrs(attributes)
    data = json.dumps({"vertices": {vertex_type: {vertex_id: attrs}}})
    headers = make_headers(conn)
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.post(
            f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
        )
        print(res)

async def upsert_chunk(conn: TigerGraphConnection, doc_id, chunk_id, chunk):
    date_added = int(time.time())
    await upsert_vertex(
        conn,
        "DocumentChunk",
        chunk_id,
        attributes={"epoch_added": date_added, "idx": int(chunk_id.split("_")[-1])},
    )
    await upsert_vertex(
        conn,
        "Content",
        chunk_id,
        attributes={"text": chunk, "epoch_added": date_added},
    )
    conn.upsertEdge("DocumentChunk", chunk_id, "HAS_CONTENT", "Content", chunk_id)
    # self.conn.upsertEdge("Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id)
    # if int(chunk_id.split("_")[-1]) > 0:
    #     self.conn.upsertEdge(
    #         "DocumentChunk",
    #         chunk_id,
    #         "IS_AFTER",
    #         "DocumentChunk",
    #         doc_id + "_chunk_" + str(int(chunk_id.split("_")[-1]) - 1),
    #     )
