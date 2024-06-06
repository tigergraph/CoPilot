import json
import os
import logging
import traceback
from typing import List, Union, Annotated

from fastapi import APIRouter, HTTPException, Request, WebSocket, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.security.http import HTTPBase

from app.agent import TigerGraphAgent
from app.config import embedding_service, embedding_store, llm_config, session_handler
from app.llm_services import (
    AWS_SageMaker_Endpoint,
    AWSBedrock,
    AzureOpenAI,
    GoogleVertexAI,
    OpenAI,
    Groq,
    Ollama,
    HuggingFaceEndpoint
)
from app.log import req_id_cv
from app.metrics.prometheus_metrics import metrics as pmetrics
from app.py_schemas.schemas import (
    CoPilotResponse,
    GSQLQueryInfo,
    GSQLQueryList,
    NaturalLanguageQuery,
    QueryDeleteRequest,
    QueryUpsertRequest,
)
from app.tools.logwriter import LogWriter
from app.tools.validation_utils import MapQuestionToSchemaException

logger = logging.getLogger(__name__)
router = APIRouter(tags=["InquiryAI"])
security = HTTPBase(scheme="basic", auto_error=False)


@router.post("/{graphname}/query")
def retrieve_answer(
    graphname,
    query: NaturalLanguageQuery,
    conn: Request,
    credentials: Annotated[HTTPBase, Depends(security)]
) -> CoPilotResponse:
    conn = conn.state.conn
    logger.debug_pii(
        f"/{graphname}/query request_id={req_id_cv.get()} question={query.query}"
    )
    logger.debug(
        f"/{graphname}/query request_id={req_id_cv.get()} database connection created"
    )
    use_cypher = os.getenv("USE_CYPHER", "false").lower() == "true"

    # TODO: This needs to be refactored just to use config.py
    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=openai agent created"
        )
        agent = TigerGraphAgent(
            OpenAI(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
            use_cypher=use_cypher
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
            use_cypher=use_cypher
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
            use_cypher=use_cypher
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
            use_cypher=use_cypher
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
            use_cypher=use_cypher
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "groq":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=groq agent created"
        )
        agent = TigerGraphAgent(
            Groq(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
            use_cypher=use_cypher
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "ollama":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=ollama agent created"
        )
        agent = TigerGraphAgent(
            Ollama(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
            use_cypher=use_cypher
        )
    elif llm_config["completion_service"]["llm_service"].lower() == "huggingface":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=huggingface agent created"
        )
        agent = TigerGraphAgent(
            HuggingFaceEndpoint(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
            use_cypher=use_cypher
        )
    else:
        LogWriter.error(
            f"/{graphname}/query request_id={req_id_cv.get()} agent creation failed due to invalid llm_service"
        )
        raise Exception("LLM Completion Service Not Supported")

    resp = CoPilotResponse(
        natural_language_response="", answered_question=False, response_type="inquiryai"
    )
    try:
        resp = agent.question_for_agent(query.query)
        '''
        # try again if there were no steps taken
        if len(steps["intermediate_steps"]) == 0:
            steps = agent.question_for_agent(query.query)

        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} agent executed")
        
        generate_func_output = steps["intermediate_steps"][-1][-1]
        resp.natural_language_response = steps["output"]
        resp.query_sources = {
            "function_call": generate_func_output["function_call"],
            "result": json.loads(generate_func_output["result"]),
            "reasoning": generate_func_output["reasoning"],
        }
        resp.answered_question = True
        '''
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
        try:
            # if the output is json, it's intermediate agent output
            #json.loads(str(steps))  # TODO: don't use errors as control flow
            resp.natural_language_response = (
                # "An error occurred while processing the response. Please try again."
                "CoPilot had an issue answering your question. Please try again, or rephrase your prompt."
            )
        except:
            # the output wasn't json. It was likely a message from the agent to the user
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


@router.get("/{graphname}/list_registered_queries")
def list_registered_queries(graphname, conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    conn = conn.state.conn
    if conn.getVer().split(".")[0] <= "3":
        query_descs = embedding_store.list_registered_documents(
            graphname=graphname,
            only_custom=True,
            output_fields=["function_header", "text"],
        )
    else:
        queries = embedding_store.list_registered_documents(
            graphname=graphname, only_custom=True, output_fields=["function_header"]
        )
        if not queries:
            return {"queries": []}
        query_descs = conn.getQueryDescription([x["function_header"] for x in queries])

    return query_descs


@router.post("/{graphname}/getqueryembedding")
def get_query_embedding(graphname, query: NaturalLanguageQuery):
    logger.debug(
        f"/{graphname}/getqueryembedding request_id={req_id_cv.get()} question={query.query}"
    )

    return embedding_service.embed_query(query.query)


@router.post("/{graphname}/register_docs")
def register_docs(
    graphname, query_list: Union[GSQLQueryInfo, List[GSQLQueryInfo]], conn: Request, credentials: Annotated[HTTPBase, Depends(security)]
):
    conn = conn.state.conn
    # auth check
    try:
        conn.echo()
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
                    "graphname": query_info.graphname,
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


@router.post("/{graphname}/upsert_from_gsql")
def upsert_from_gsql(graphname, query_list: GSQLQueryList, conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    req = conn
    conn = conn.state.conn

    query_names = query_list.queries
    query_descs = conn.getQueryDescription(query_names)
    logger.debug("retrieved query descriptions from GSQL"+str(query_descs))
    query_info_list = []
    for query_desc in query_descs:
        logger.debug("processing query description: "+str(query_desc))
        if query_desc.get("description", None) is None:
            logger.warning(f"Query may not perform well {query_desc['queryName']} because it has no description")
        params = query_desc["parameters"]
        if params == []:
            params = {}
        else:
            tmp_params = {}
            for param in params:
                tmp_params[param["paramName"]] = (
                    "INSERT " + param.get("description", "VALUE") + " HERE"
                )
            params = tmp_params
        param_types = conn.getQueryMetadata(query_desc["queryName"])["input"]
        q_info = GSQLQueryInfo(
            function_header=query_desc["queryName"],
            description=query_desc.get("description", ""),
            docstring=query_desc.get("description", "")
            + ".\nRun with runInstalledQuery('"
            + query_desc["queryName"]
            + "', params={})".format(json.dumps(params)),
            param_types={list(x.keys())[0]: x[list(x.keys())[0]] for x in param_types},
            graphname=graphname,
        )

        query_info_list.append(QueryUpsertRequest(id=None, query_info=q_info))
    return upsert_docs(graphname, query_info_list, req, credentials)


@router.post("/{graphname}/delete_from_gsql")
def delete_from_gsql(graphname, query_list: GSQLQueryList, conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    req = conn
    conn = conn.state.conn

    query_names = query_list.queries
    query_descs = conn.getQueryDescription(query_names)

    func_counter = 0

    for query_desc in query_descs:
        delete_docs(
            graphname,
            QueryDeleteRequest(
                ids=None,
                expr=f"function_header=='{query_desc['queryName']}' and graphname=='{graphname}'",
            ),
            req,
            credentials
        )
        func_counter += 1

    return {"deleted_functions": query_descs, "deleted_count": func_counter}


@router.post("/{graphname}/upsert_docs")
def upsert_docs(
    graphname,
    request_data: Union[QueryUpsertRequest, List[QueryUpsertRequest]],
    conn: Request,
    credentials: Annotated[HTTPBase, Depends(security)]
):
    conn = conn.state.conn
    # auth check
    try:
        conn.echo()
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
            elif not id and query_info:
                try: 
                    # expr = f"function_header in ['{query_info.function_header}']"
                    expr = f"function_header == '{query_info.function_header}'"
                    id = embedding_store.get_pks(expr)
                    if id:
                        id = str(id[0])
                        logger.info(f"Found document id {id} based on expression {expr}")
                    else:
                        id = ""
                        logger.info(f"No document found based on expression {expr}, inserting as a new document")
                except Exception as e:
                    error_message = f"An error occurred while getting pks of document: {str(e)}"
                    raise e

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
                        "graphname": query_info.graphname,
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
def delete_docs(graphname, request_data: QueryDeleteRequest, conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    conn = conn.state.conn
    # auth check
    try:
        conn.echo()
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
    credentials: Annotated[HTTPBase, Depends(security)],
    top_k: int = 3
):
    logger.debug_pii(
        f"/{graphname}/retrieve_docs request_id={req_id_cv.get()} top_k={top_k} question={query.query}"
    )
    return embedding_store.retrieve_similar(
        embedding_service.embed_query(query.query), top_k=top_k
    )


@router.post("/{graphname}/login")
def login(graphname, conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    session_id = session_handler.create_session(conn.state.conn.username, conn)
    return {"session_id": session_id}


@router.post("/{graphname}/logout")
def logout(graphname, session_id: str, credentials: Annotated[HTTPBase, Depends(security)]):
    session_handler.delete_session(session_id)
    return {"status": "success"}


@router.get("/{graphname}/chat")
def chat(request: Request):
    return HTMLResponse(open("app/static/chat.html").read())


@router.websocket("/{graphname}/ws")
async def websocket_endpoint(websocket: WebSocket, graphname: str, session_id: str, credentials: Annotated[HTTPBase, Depends(security)]):
    session = session_handler.get_session(session_id)
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        res = retrieve_answer(
            graphname, NaturalLanguageQuery(query=data), session.db_conn
        )
        await websocket.send_text(f"{res.natural_language_response}")
