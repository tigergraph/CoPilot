import logging
import re
from typing import Annotated

import requests
from fastapi import (APIRouter, Cookie, Depends, HTTPException, Request,
                     WebSocket, status)
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pyTigerGraph import TigerGraphConnection

from common.config import db_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ui")


security = HTTPBasic()


GRAPH_NAME_RE = re.compile("- Graph (.*)\(")


def ui_basic_auth(
    creds: Annotated[HTTPBasicCredentials, Depends(security)],
) -> list[str]:
    """
    1) Try authenticating with DB.
    2) Get list of graphs user has access to
    """
    conn = TigerGraphConnection(
        db_config["hostname"], username=creds.username, password=creds.password
    )
    try:
        # print(conn.getSecrets())
        # parse user info
        info = conn.gsql("LS USER")
        graphs = []
        for m in GRAPH_NAME_RE.finditer(info):
            groups = m.groups()
            graphs.extend(groups)
        return graphs

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            # headers={"WWW-Authenticate": "Basic"},
        )
    except Exception as e:
        raise e


@router.post("/ui-login")
def login(graphs: Annotated[HTTPBasicCredentials, Depends(ui_basic_auth)]):
    return {"graphs": graphs}


@router.websocket("/chat")
async def websocket_endpoint(
    websocket: WebSocket, cookie: Annotated[str | None, Cookie()]
):
    # TODO: cookie auth
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


# @router.websocket("/wss")
# async def websocket_endpoint(websocket: WebSocket, graphname: str, session_id: str, credentials: Annotated[HTTPBase, Depends(security)]):
#     session = session_handler.get_session(session_id)
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         res = retrieve_answer(
#             graphname, NaturalLanguageQuery(query=data), session.db_conn
#         )
#         await websocket.send_text(f"{res.natural_language_response}")
@router.get("/home")
async def get():
    html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ui/ui-ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""
    return HTMLResponse(html)
