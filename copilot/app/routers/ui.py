import base64
import logging
import os
import re
import time
import traceback
import uuid
from typing import Annotated

import httpx
import requests
from agent.agent import TigerGraphAgent, make_agent
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from langchain_core.messages import message_to_dict
from pyTigerGraph import TigerGraphConnection
from tools.validation_utils import MapQuestionToSchemaException

from common.config import db_config, embedding_service, llm_config
from common.db.connections import get_db_connection_pwd_manual
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter
from common.metrics.prometheus_metrics import metrics as pmetrics
from common.py_schemas.schemas import CoPilotResponse, Message, Role

logger = logging.getLogger(__name__)

use_cypher = os.getenv("USE_CYPHER", "false").lower() == "true"
route_prefix = "/ui"  # APIRouter's prefix doesn't work with the websocket, so it has to be done here
router = APIRouter(tags=["UI"])
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

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    except Exception as e:
        raise e
    return graphs, conn


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
    graphs = auth(creds.username, creds.password)[0]
    return graphs


@router.post(f"{route_prefix}/ui-login")
def login(graphs: Annotated[list[str], Depends(ui_basic_auth)]):
    return {"graphs": graphs}


@router.post(f"{route_prefix}/feedback")
def add_feedback(message: Message, _: Annotated[list[str], Depends(ui_basic_auth)]):
    try:
        res = httpx.post(
            f"{db_config['chat_history_api']}/conversation", json=message.model_dump()
        )
        if res in None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "success", "conversation": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_agent(
    agent: TigerGraphAgent,
    data: str,
    conversation_history: list[dict[str, str]],
    graphname,
) -> CoPilotResponse:
    resp = CoPilotResponse(
        natural_language_response="", answered_question=False, response_type="inquiryai"
    )
    try:
        # TODO: make num mesages in history configureable
        resp = agent.question_for_agent(data, conversation_history[-4:])
        pmetrics.llm_success_response_total.labels(embedding_service.model_name).inc()

    except MapQuestionToSchemaException:
        resp.natural_language_response = (
            "A schema mapping error occurred. Please try rephrasing your question."
        )
        resp.query_sources = {}
        resp.answered_question = False
        LogWriter.warning(
            f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to MapQuestionToSchemaException"
        )
        pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/{graphname}/query request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
    except Exception:
        resp.natural_language_response = "CoPilot had an issue answering your question. Please try again, or rephrase your prompt."

        resp.query_sources = {}
        resp.answered_question = False
        LogWriter.warning(
            f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception"
        )
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/{graphname}/query request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()

    return resp


async def write_message_to_history(message: Message, usr_auth: str):
    ch = db_config.get("chat_history_api")
    if ch is not None:
        headers = {"Authorization": f"Basic {usr_auth}"}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{ch}/conversation", headers=headers, json=message.model_dump()
                )
                res.raise_for_status()
        except Exception:
            exc = traceback.format_exc()
            logger.debug_pii(f"Error writing chat history Exception Trace:\n{exc}")

    else:
        LogWriter.info(f"chat-history not enabled. chat-history url: {ch}")


@router.websocket(route_prefix + "/{graphname}/chat")
async def chat(
    graphname: str,
    websocket: WebSocket,
):
    """
    TODO:
    the text received from the UI should be a Message().
        We need the conversation ID to
            initially retrieve the convo
            update the convo
    """
    await websocket.accept()

    # AUTH
    # this will error if auth does not pass. FastAPI will correctly respond depending on error
    usr_auth = await websocket.receive_text()
    _, conn = ws_basic_auth(usr_auth, graphname)

    # create convo_id
    conversation_history = []  # TODO: go get history instead of starting from 0
    convo_id = str(uuid.uuid4())
    agent = make_agent(graphname, conn, use_cypher)

    prev_id = None
    while True:
        data = await websocket.receive_text()

        # make message from data
        message = Message(
            conversation_id=convo_id,
            message_id=str(uuid.uuid4()),
            parent_id=prev_id,
            model=llm_config["model_name"],
            content=data,
            role=Role.user.name,
        )
        # save message
        await write_message_to_history(message, usr_auth)
        prev_id = message.message_id

        # generate response and keep track of response time
        start = time.monotonic()
        resp = run_agent(agent, data, conversation_history, graphname)
        elapsed = time.monotonic() - start

        # reply
        await websocket.send_text(resp.model_dump_json())

        # append message to history
        conversation_history.append(
            {"query": data, "response": resp.natural_language_response}
        )

        # save message
        message = Message(
            conversation_id=convo_id,
            message_id=str(uuid.uuid4()),
            parent_id=prev_id,
            model=llm_config["model_name"],
            content=resp.natural_language_response,
            role=Role.system.name,
            response_time=elapsed,
        )
        await write_message_to_history(message, usr_auth)
        prev_id = message.message_id
        print("**** convo_id:\n", message.conversation_id)
