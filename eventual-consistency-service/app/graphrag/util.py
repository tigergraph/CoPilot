import base64
from urllib.parse import quote_plus

import httpx
from pyTigerGraph import TigerGraphConnection

from common.logs.logwriter import LogWriter


async def install_query(
    conn: TigerGraphConnection, query_name: str
) -> dict[str, httpx.Response | str | None]:
    print("install --", query_name)
    LogWriter.info(f"Installing query {query_name}")
    with open(f"common/gsql/supportai/{query_name}.gsql", "r") as f:
        query = f.read()

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
        return {"result": None, "error": f"Failed to install query {query_name}"}

    return {"result": res, "error": False}
