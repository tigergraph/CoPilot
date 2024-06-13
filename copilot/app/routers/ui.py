import base64
import logging
import os
import re
from typing import Annotated

import requests
from agent.agent import TigerGraphAgent, make_agent
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     WebSocket, status)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pyTigerGraph import TigerGraphConnection

from common.config import db_config, embedding_service
from common.db.connections import get_db_connection_pwd_manual
from common.metrics.prometheus_metrics import metrics as pmetrics

logger = logging.getLogger(__name__)

use_cypher = os.getenv("USE_CYPHER", "false").lower() == "true"
route_prefix = "/ui"  # APIRouter's prefix doesn't work with the websocket, so it has to be done here
router = APIRouter()
security = HTTPBasic()
GRAPH_NAME_RE = re.compile(r"- Graph (.*)\(")


def auth(usr: str, password: str, conn=None) -> tuple[list[str], TigerGraphConnection]:
    if conn is None:
        conn = TigerGraphConnection(
            host=db_config["hostname"], graphname="", username=usr, password=password
        )

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


def ws_basic_auth(auth_info: str, graphname=None):
    auth_info = base64.b64decode(auth_info.encode()).decode()
    auth_info = auth_info.split(":")
    username = auth_info[0]
    password = auth_info[1]
    conn = get_db_connection_pwd_manual(graphname, username, password)
    return auth(username, password, conn)


def ui_basic_auth(
    creds: Annotated[HTTPBasicCredentials, Depends(security)],
) -> list[str]:
    """
    1) Try authenticating with DB.
    2) Get list of graphs user has access to
    """
    print(creds.username, creds.password)
    graphs = auth(creds.username, creds.password)[0]
    return graphs


@router.post(f"{route_prefix}/ui-login")
def login(graphs: Annotated[list[str], Depends(ui_basic_auth)]):
    return {"graphs": graphs}


def a(agent: TigerGraphAgent, data):
    pmetrics.llm_success_response_total.labels(embedding_service.model_name).inc()
    return agent.question_for_agent(data)


def write_message_to_history():
    print(db_config.get("chat-history-api", "not turned on"))
    print("write_message_to_history")


@router.websocket(route_prefix + "/{graphname}/chat")
async def chat(
    graphname: str,
    websocket: WebSocket,
    bg_tasks: BackgroundTasks,
):
    # TODO: conversation_id instead of graph name? (convos will need to keep track of the graph name)

    await websocket.accept()

    # AUTH
    # this will error if auth does not pass. FastAPI will correctly respond depending on error
    msg = await websocket.receive_text()
    _, conn = ws_basic_auth(msg, graphname)

    # continuous convo setup
    conversation_history = []
    agent = make_agent(graphname, conn, use_cypher)

    while True:
        data = await websocket.receive_text()
        print(data)
        conversation_history.append(data)
        # TODO: send message to chat history
        # bg_tasks.add_task(write_message_to_history)
        # message = a(agent, data)
        await websocket.send_text(f"Message text was: {data}")
        # await websocket.send_text(str(message))
        # TODO: send response to chat history
        # bg_tasks.add_task(write_message_to_history)
