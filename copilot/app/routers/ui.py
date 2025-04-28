import asyncio
import base64
import logging
import os
import re
import time
import traceback
import uuid
from typing import Annotated

import asyncer
import httpx
import requests
from agent.agent import TigerGraphAgent, make_agent
from agent.Q import DONE
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pyTigerGraph import TigerGraphConnection
from tools.validation_utils import MapQuestionToSchemaException

from common.config import db_config, embedding_service, llm_config, service_status
from common.db.connections import get_db_connection_pwd_manual
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter
from common.metrics.prometheus_metrics import metrics as pmetrics
from common.py_schemas.schemas import (
    AgentProgess,
    CoPilotResponse,
    Message,
    ResponseType,
    Role,
)

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
    return graphs, creds


@router.post(f"{route_prefix}/ui-login")
def login(auth: Annotated[list[str], Depends(ui_basic_auth)]):
    graphs = auth[0]
    return {"graphs": graphs}


@router.post(f"{route_prefix}/feedback")
def add_feedback(
    message: Message,
    creds: Annotated[tuple[list[str], HTTPBasicCredentials], Depends(ui_basic_auth)],
):
    creds = creds[1]
    auth = base64.b64encode(f"{creds.username}:{creds.password}".encode()).decode()
    try:
        res = httpx.post(
            f"{db_config['chat_history_api']}/conversation",
            json=message.model_dump(),
            headers={"Authorization": f"Basic {auth}"},
        )
        res.raise_for_status()
    except Exception as e:
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/ui/feedback request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        raise e

    return {"message": "feedback saved", "message_id": message.message_id}


@router.get(route_prefix + "/user/{user_id}")
async def get_user_conversations(
    user_id: str,
    creds: Annotated[tuple[list[str], HTTPBasicCredentials], Depends(ui_basic_auth)],
):
    creds = creds[1]
    auth = base64.b64encode(f"{creds.username}:{creds.password}".encode()).decode()
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{db_config['chat_history_api']}/user/{user_id}",
                headers={"Authorization": f"Basic {auth}"},
            )
            res.raise_for_status()
    except Exception as e:
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/ui/user/{user_id} request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        raise e

    return res.json()


@router.get(route_prefix + "/conversation/{conversation_id}")
async def get_conversation_contents(
    conversation_id: str,
    creds: Annotated[tuple[list[str], HTTPBasicCredentials], Depends(ui_basic_auth)],
):
    creds = creds[1]
    auth = base64.b64encode(f"{creds.username}:{creds.password}".encode()).decode()
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{db_config['chat_history_api']}/conversation/{conversation_id}",
                headers={"Authorization": f"Basic {auth}"},
            )
            res.raise_for_status()
    except Exception as e:
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/conversation/{conversation_id} request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        raise e

    return res.json()

@router.get(route_prefix + "/get_feedback")
async def get_conversation_feedback(
    creds: Annotated[tuple[list[str], HTTPBasicCredentials], Depends(ui_basic_auth)],
):
    creds = creds[1]
    auth = base64.b64encode(f"{creds.username}:{creds.password}".encode()).decode()
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{db_config['chat_history_api']}/get_feedback",
                headers={"Authorization": f"Basic {auth}"},
            )
            res.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch feedback")
    except Exception as e:
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/get_feedback request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    return res.json()


async def emit_progress(agent: TigerGraphAgent, ws: WebSocket):
    # loop on q until done token emit events through ws
    msg = None
    pop = asyncer.asyncify(agent.q.pop)

    while msg != DONE:
        msg = await pop()
        if msg is not None and msg != DONE:
            message = AgentProgess(
                content=msg,
                response_type=ResponseType.PROGRESS,
            )
            if ws:
                await ws.send_text(message.model_dump_json())
            else:
                return message.model_dump_json()


async def run_agent(
    agent: TigerGraphAgent,
    data: str,
    conversation_history: list[dict[str, str]],
    graphname,
    ws: WebSocket,
) -> CoPilotResponse:
    resp = CoPilotResponse(
        natural_language_response="", answered_question=False, response_type="inquiryai"
    )
    a_question_for_agent = asyncer.asyncify(agent.question_for_agent)
    try:
        # start agent and sample from Q to emit progress

        async with asyncio.TaskGroup() as tg:
            # run agent
            a_resp = tg.create_task(
                # TODO: make num mesages in history configureable
                a_question_for_agent(data, conversation_history[-4:])
            )
            # sample Q and emit events
            if ws:
                tg.create_task(emit_progress(agent, ws))
            else:
                emit_progress(agent, ws)
        pmetrics.llm_success_response_total.labels(embedding_service.model_name).inc()
        resp = a_resp.result()
        if ws:
            agent.q.clear()

    except MapQuestionToSchemaException:
        resp.natural_language_response = (
            "A schema mapping error occurred. Please try rephrasing your question."
        )
        resp.query_sources = {}
        resp.answered_question = False
        LogWriter.warning(
            f"/{graphname}/ui/chat request_id={req_id_cv.get()} agent execution failed due to MapQuestionToSchemaException"
        )
        pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/{graphname}/ui/chat request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
    except Exception as e:
        resp.natural_language_response = "CoPilot had an issue answering your question. Please try again, or rephrase your prompt."

        resp.query_sources = {}
        resp.answered_question = False
        LogWriter.warning(
            f"/{graphname}/ui/chat request_id={req_id_cv.get()} agent execution failed due to unknown exception {e}"
        )
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/{graphname}/ui/chat request_id={req_id_cv.get()} Exception Trace:\n{exc}"
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
        except Exception:  # catch all exceptions to log them, but don't raise
            exc = traceback.format_exc()
            logger.debug_pii(f"Error writing chat history\nException Trace:\n{exc}")

    else:
        LogWriter.info(f"chat-history not enabled. chat-history url: {ch}")

@router.get(route_prefix + "/{graphname}/query")
async def graph_query(
    graphname: str,
    creds: Annotated[tuple[list[str], HTTPBasicCredentials], Depends(ui_basic_auth)],
    q: str | None = None,
):
    creds = creds[1]
    auth = base64.b64encode(f"{creds.username}:{creds.password}".encode()).decode()
    _, conn = ws_basic_auth(auth, graphname)
    try:
        # create convo_id
        conversation_history = []  # TODO: go get history instead of starting from 0
        convo_id = str(uuid.uuid4())
    
        # create agent
        # get retrieval pattern to use
        rag_pattern = "hnsw_overlap"
        agent = make_agent(graphname, conn, use_cypher, supportai_retriever=rag_pattern)
    
        prev_id = None
        while True:
            data = q
            logger.info(f"Retrieving answer for chat \"{data}\"")

            # make message from data
            message = Message(
                conversation_id=convo_id,
                message_id=str(uuid.uuid4()),
                parent_id=prev_id,
                model=llm_config["model_name"],
                content=data,
                role=Role.USER,
            )
            # save message
            prev_id = message.message_id

            # generate response and keep track of response time
            start = time.monotonic()
            resp = await run_agent(
                agent, data, conversation_history, graphname, None
            )
            elapsed = time.monotonic() - start

            # save message
            message = Message(
               conversation_id=convo_id,
                message_id=str(uuid.uuid4()),
                parent_id=prev_id,
                model=llm_config["model_name"],
                content=resp.natural_language_response,
                role=Role.SYSTEM,
                response_time=elapsed,
                answered_question=resp.answered_question,
                response_type=resp.response_type,
                query_sources=resp.query_sources,
            )
            prev_id = message.message_id

            # reply
            return message.model_dump_json()
    except Exception as e:
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/ui/{graphname}/query request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        raise e

    return res.json()

@router.websocket(route_prefix + "/{graphname}/chat")
async def chat(
    graphname: str,
    websocket: WebSocket
):
    """
    TODO:
    the text received from the UI should be a Message().
        We need the conversation ID to
            initially retrieve the convo
            update the convo
    """
    if service_status["embedding_store"]["error"]:
        return HTTPException(
            status_code=503,
            detail=service_status["embedding_store"]["error"]
        )
    
    await websocket.accept()

    # AUTH
    # this will error if auth does not pass. FastAPI will correctly respond depending on error
    usr_auth = await websocket.receive_text()
    _, conn = ws_basic_auth(usr_auth, graphname)

    # create convo_id
    conversation_history = []  # TODO: go get history instead of starting from 0
    convo_id = str(uuid.uuid4())

    # create agent
    # get retrieval pattern to use
    rag_pattern = await websocket.receive_text()
    agent = make_agent(graphname, conn, use_cypher, ws=websocket, supportai_retriever=rag_pattern)

    prev_id = None
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Retrieving answer for chat \"{data}\"")

            # make message from data
            message = Message(
                conversation_id=convo_id,
                message_id=str(uuid.uuid4()),
                parent_id=prev_id,
                model=llm_config["model_name"],
                content=data,
                role=Role.USER,
            )
            # save message
            await write_message_to_history(message, usr_auth)
            prev_id = message.message_id

            # generate response and keep track of response time
            start = time.monotonic()
            resp = await run_agent(
                agent, data, conversation_history, graphname, websocket
            )
            elapsed = time.monotonic() - start

            # save message
            message = Message(
                conversation_id=convo_id,
                message_id=str(uuid.uuid4()),
                parent_id=prev_id,
                model=llm_config["model_name"],
                content=resp.natural_language_response,
                role=Role.SYSTEM,
                response_time=elapsed,
                answered_question=resp.answered_question,
                response_type=resp.response_type,
                query_sources=resp.query_sources,
            )
            await write_message_to_history(message, usr_auth)
            prev_id = message.message_id

            # reply
            await websocket.send_text(message.model_dump_json())

            # append message to history
            conversation_history.append(
                {"query": data, "response": resp.natural_language_response}
            )
    except WebSocketDisconnect as e:
        logger.info(f"Websocket disconnected: {str(e)}")
    except:
        await websocket.close()

