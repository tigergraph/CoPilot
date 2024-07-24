import base64
import json
import time
import traceback
from urllib.parse import quote_plus

import ecc_util
import httpx
from aiochannel import Channel
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


async def stream_docs(
    conn: TigerGraphConnection,
    docs_chan: Channel,
    ttl_batches: int = 10,
):
    """
    Streams the document contents into the docs_chan
    """
    headers = make_headers(conn)
    for i in range(ttl_batches):
        doc_ids = await stream_doc_ids(conn, i, ttl_batches)
        if doc_ids["error"]:
            break  # TODO: handle error

        print("********")
        print(doc_ids)
        print("********")
        for d in doc_ids["ids"]:
            async with httpx.AsyncClient(timeout=None) as client:
                res = await client.get(
                    f"{conn.restppUrl}/query/{conn.graphname}/StreamDocContent/",
                    params={"doc": d},
                    headers=headers,
                )
                # TODO: check for errors
                # this will block and wait if the channel is full
                await docs_chan.put(res.json()["results"][0]["DocContent"][0])
        #     break  # single doc test FIXME: delete
        # break  # single batch test FIXME: delete

    # close the docs chan -- this function is the only sender
    docs_chan.close()


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
    # TODO: n chunks at a time
    for i, chunk in enumerate(chunks):
        # send chunks to be upserted (func, args)
        await upsert_chan.put((upsert_chunk, (conn, v_id, f"{v_id}_chunk_{i}", chunk)))

        # send chunks to be embedded
        await embed_chan.put(chunk)

        # send chunks to have entities extracted
        await extract_chan.put(chunk)

        # break  # single chunk FIXME: delete

    return doc["v_id"]


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
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.post(
            f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
        )
        print("upsert vertex>>>", res.json())


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
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.post(
            f"{conn.restppUrl}/graph/{conn.graphname}", data=data, headers=headers
        )
        print("upsert edge >>>", res.json())


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
    await upsert_edge(
        conn, "DocumentChunk", chunk_id, "HAS_CONTENT", "Content", chunk_id
    )
    await upsert_edge(conn, "Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id)
    if int(chunk_id.split("_")[-1]) > 0:
        await upsert_edge(
            conn,
            "DocumentChunk",
            chunk_id,
            "IS_AFTER",
            "DocumentChunk",
            doc_id + "_chunk_" + str(int(chunk_id.split("_")[-1]) - 1),
        )
