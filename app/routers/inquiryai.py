import json
import logging
import traceback
from typing import Annotated, List, Union

from fastapi import (APIRouter, Depends, HTTPException, Request, WebSocket,
                     status)
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasicCredentials

from app.agent import TigerGraphAgent
from app.config import (embedding_service, embedding_store, llm_config,
                        security, session_handler)
from app.llm_services import (AWS_SageMaker_Endpoint, AWSBedrock, AzureOpenAI,
                              GoogleVertexAI, OpenAI)
from app.log import req_id_cv
from app.metrics.prometheus_metrics import metrics as pmetrics
from app.metrics.tg_proxy import TigerGraphConnectionProxy
from app.py_schemas.schemas import (CoPilotResponse, GSQLQueryInfo,
                                    NaturalLanguageQuery, QueryDeleteRequest,
                                    QueryUperstRequest)
from app.tools.logwriter import LogWriter
from app.tools.validation_utils import MapQuestionToSchemaException
from app.util import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["InquiryAI"])


@router.post("/{graphname}/query")
def retrieve_answer(
    graphname,
    query: NaturalLanguageQuery,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
) -> CoPilotResponse:
    logger.debug_pii(
        f"/{graphname}/query request_id={req_id_cv.get()} question={query.query}"
    )
    logger.debug(
        f"/{graphname}/query request_id={req_id_cv.get()} database connection created"
    )

    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=openai agent created"
        )
        agent = TigerGraphAgent(
            OpenAI(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=azure agent created"
        )
        agent = TigerGraphAgent(
            AzureOpenAI(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=sagemaker agent created"
        )
        agent = TigerGraphAgent(
            AWS_SageMaker_Endpoint(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "vertexai":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=vertexai agent created"
        )
        agent = TigerGraphAgent(
            GoogleVertexAI(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "bedrock":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=bedrock agent created"
        )
        agent = TigerGraphAgent(
            AWSBedrock(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
        )
    else:
        LogWriter.error(
            f"/{graphname}/query request_id={req_id_cv.get()} agent creation failed due to invalid llm_service"
        )
        raise Exception("LLM Completion Service Not Supported")

    resp = CoPilotResponse(
        natural_language_response="", answered_question=False, response_type="inquiryai"
    )
    steps = ""
    try:
        steps = agent.question_for_agent(query.query)
        # try again if there were no steps taken
        if len(steps["intermediate_steps"]) == 0:
            steps = agent.question_for_agent(query.query)

        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} agent executed")
        try:
            generate_func_output = steps["intermediate_steps"][-1][-1]
            resp.natural_language_response = steps["output"]
            resp.query_sources = {
                "function_call": generate_func_output["function_call"],
                "result": json.loads(generate_func_output["result"]),
                "reasoning": generate_func_output["reasoning"],
            }
            resp.answered_question = True
            pmetrics.llm_success_response_total.labels(
                embedding_service.model_name
            ).inc()
        except Exception:
            resp.natural_language_response = (
                # "An error occurred while processing the response. Please try again."
                str(steps["output"])
            )
            resp.query_sources = {"agent_history": str(steps)}
            resp.answered_question = False
            LogWriter.warning(
                f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception"
            )
            pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()
            exc = traceback.format_exc()
            logger.debug_pii(
                f"/{graphname}/query request_id={req_id_cv.get()} Exception Trace:\n{exc}"
            )
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
    except Exception as e:
        resp.natural_language_response = (
            # "An error occurred while processing the response. Please try again."
            str(steps["output"])
        )
        resp.query_sources = {} if len(steps) == 0 else {"agent_history": str(steps)}
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


@router.post("/{graphname}/getqueryembedding")
def get_query_embedding(
    graphname,
    query: NaturalLanguageQuery,
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
):
    logger.debug(
        f"/{graphname}/getqueryembedding request_id={req_id_cv.get()} question={query.query}"
    )

    return embedding_service.embed_query(query.query)


@router.post("/{graphname}/register_docs")
def register_docs(
    graphname,
    query_list: Union[GSQLQueryInfo, List[GSQLQueryInfo]],
):
    logger.debug(f"Using embedding store: {embedding_store}")
    results = []

    if not isinstance(query_list, list):
        query_list = [query_list]

    for query_info in query_list:
        logger.debug(
            f"/{graphname}/register_docs request_id={req_id_cv.get()} registering {query_info.function_header}"
        )

        vec = embedding_service.embed_query(query_info.docstring)
        res = embedding_store.add_embeddings(
            [(query_info.docstring, vec)],
            [
                {
                    "function_header": query_info.function_header,
                    "description": query_info.description,
                    "param_types": query_info.param_types,
                    "custom_query": True,
                }
            ],
        )
        if res:
            results.append(res)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register document(s)",
            )

    return results


@router.post("/{graphname}/upsert_docs")
def upsert_docs(
    graphname,
    request_data: Union[QueryUperstRequest, List[QueryUperstRequest]],
):
    try:
        results = []

        if not isinstance(request_data, list):
            request_data = [request_data]

        for request_info in request_data:
            id = request_info.id
            query_info = request_info.query_info

            if not id and not query_info:
                raise HTTPException(
                    status_code=400,
                    detail="At least one of 'id' or 'query_info' is required",
                )

            logger.debug(
                f"/{graphname}/upsert_docs request_id={req_id_cv.get()} upserting document(s)"
            )

            vec = embedding_service.embed_query(query_info.docstring)
            res = embedding_store.upsert_embeddings(
                id,
                [(query_info.docstring, vec)],
                [
                    {
                        "function_header": query_info.function_header,
                        "description": query_info.description,
                        "param_types": query_info.param_types,
                        "custom_query": True,
                    }
                ],
            )
            if res:
                results.append(res)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upsert document(s)",
                )
        return results

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred while upserting query {str(e)}"
        )


@router.post("/{graphname}/delete_docs")
def delete_docs(
    graphname,
    request_data: QueryDeleteRequest
):
    ids = request_data.ids
    expr = request_data.expr

    if ids and not isinstance(ids, list):
        try:
            ids = [ids]
        except ValueError:
            raise ValueError(
                "Invalid ID format. IDs must be string or lists of strings."
            )

    logger.debug(
        f"/{graphname}/delete_docs request_id={req_id_cv.get()} deleting document(s)"
    )

    # Call the remove_embeddings method based on provided IDs or expression
    try:
        if expr:
            res = embedding_store.remove_embeddings(expr=expr)
            return res
        elif ids:
            res = embedding_store.remove_embeddings(ids=ids)
            return res
        else:
            raise HTTPException(
                status_code=400, detail="Either IDs or an expression must be provided."
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{graphname}/retrieve_docs")
def retrieve_docs(
    graphname,
    query: NaturalLanguageQuery,
    top_k: int = 3,
):
    logger.debug_pii(
        f"/{graphname}/retrieve_docs request_id={req_id_cv.get()} top_k={top_k} question={query.query}"
    )
    return embedding_store.retrieve_similar(
        embedding_service.embed_query(query.query), top_k=top_k
    )


@router.post("/{graphname}/login")
def login(graphname, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    session_id = session_handler.create_session(conn.username, conn)
    return {"session_id": session_id}


@router.post("/{graphname}/logout")
def logout(graphname, session_id: str):
    session_handler.delete_session(session_id)
    return {"status": "success"}


@router.get("/{graphname}/chat")
def chat(request: Request):
    return HTMLResponse(open("app/static/chat.html").read())


@router.websocket("/{graphname}/ws")
async def websocket_endpoint(websocket: WebSocket, graphname: str, session_id: str):
    session = session_handler.get_session(session_id)
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        res = retrieve_answer(
            graphname, NaturalLanguageQuery(query=data), session.db_conn
        )
        await websocket.send_text(f"{res.natural_language_response}")
