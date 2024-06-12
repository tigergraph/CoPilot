import base64
import logging
import re
from typing import Annotated

import requests
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pyTigerGraph import TigerGraphConnection

from common.config import db_config

logger = logging.getLogger(__name__)
route_prefix = "/ui"  # APIRouter's prefix doesn't work with the websocket, so it has to be done here
router = APIRouter()


security = HTTPBasic()
GRAPH_NAME_RE = re.compile(r"- Graph (.*)\(")


def auth(usr: str, password: str) -> tuple[list[str], TigerGraphConnection]:
    conn = TigerGraphConnection(db_config["hostname"], username=usr, password=password)
    try:
        # parse user info
        info = conn.gsql("LS USER")
        graphs = []
        for m in GRAPH_NAME_RE.finditer(info):
            groups = m.groups()
            graphs.extend(groups)

        return graphs, conn

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    except Exception as e:
        raise e


def ws_basic_auth(auth_info: str):
    auth_info = base64.b64decode(auth_info.encode()).decode()
    auth_info = auth_info.split(":")
    user = auth_info[0]
    password = auth_info[1]
    return auth(user, password)


def ui_basic_auth(
    creds: Annotated[HTTPBasicCredentials, Depends(security)],
) -> list[str]:
    """
    1) Try authenticating with DB.
    2) Get list of graphs user has access to
    """
    graphs = auth(creds.username, creds.password)[0]
    return graphs


@router.post(f"{route_prefix}/ui-login")
def login(graphs: Annotated[list[str], Depends(ui_basic_auth)]):
    return {"graphs": graphs}


@router.websocket(f"{route_prefix}/chat")
async def websocket_endpoint( websocket: WebSocket):
    await websocket.accept()

    # this will error if auth does not pass. FastAPI will correctly respond depending on error
    msg = await websocket.receive_text()
    graphs, conn = ws_basic_auth(msg)
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
@router.get(f"{route_prefix}/home")
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
