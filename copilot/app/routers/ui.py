import base64
import logging
import os
import re
import traceback
from typing import Annotated

import requests
from agent.agent import TigerGraphAgent, make_agent
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     WebSocket, status)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pyTigerGraph import TigerGraphConnection
from tools.validation_utils import MapQuestionToSchemaException

from common.config import db_config, embedding_service
from common.db.connections import get_db_connection_pwd_manual
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter
from common.metrics.prometheus_metrics import metrics as pmetrics
from common.py_schemas.schemas import (CoPilotResponse, GSQLQueryInfo,
                                       GSQLQueryList, NaturalLanguageQuery,
                                       QueryDeleteRequest, QueryUpsertRequest)

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
        resp = agent.question_for_agent(data, conversation_history[-3:])
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
    # create convo_id
    conversation_history = []  # TODO: go get history
    agent = make_agent(graphname, conn, use_cypher)

    while True:
        data = await websocket.receive_text()
        # TODO: send message to chat history
        # bg_tasks.add_task(write_message_to_history)

        message = run_agent(agent, data, conversation_history, graphname)
        await websocket.send_text(message.model_dump_json())

        # don't include CoPilot appologies for not being able to answer in the agent's known history
        # if message.answered_question:
        conversation_history.append(
            {"query": data, "response": message.natural_language_response}
        )

        # TODO: send response to chat history
        # bg_tasks.add_task(write_message_to_history)
