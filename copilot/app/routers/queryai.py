import json
import logging
import traceback
from typing import List, Union, Annotated

from fastapi import APIRouter, HTTPException, Request, WebSocket, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.security.http import HTTPBase

from app.agent import TigerGraphAgent
from common.config import embedding_service, embedding_store, llm_config, session_handler
from common.llm_services import (
    AWS_SageMaker_Endpoint,
    AWSBedrock,
    AzureOpenAI,
    GoogleVertexAI,
    OpenAI,
    Groq,
    Ollama,
    HuggingFaceEndpoint
)
from common.logs.log import req_id_cv
from common.metrics.prometheus_metrics import metrics as pmetrics
from common.py_schemas.schemas import (
    CoPilotResponse,
    GSQLQueryInfo,
    GSQLQueryList,
    NaturalLanguageQuery,
    QueryDeleteRequest,
    QueryUpsertRequest,
)
from common.logs.logwriter import LogWriter
from app.tools.validation_utils import MapQuestionToSchemaException

logger = logging.getLogger(__name__)
router = APIRouter(tags=["QueryAI"])
security = HTTPBase(scheme="basic", auto_error=False)


@router.post("/{graphname}/generate_cypher")
def generate_cypher(
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
    elif llm_config["completion_service"]["llm_service"].lower() == "groq":
        logger.debug(
            f"/{graphname}/query request_id={req_id_cv.get()} llm_service=groq agent created"
        )
        agent = TigerGraphAgent(
            Groq(llm_config["completion_service"]),
            conn,
            embedding_service,
            embedding_store,
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
        )
    else:
        LogWriter.error(
            f"/{graphname}/query request_id={req_id_cv.get()} agent creation failed due to invalid llm_service"
        )
        raise Exception("LLM Completion Service Not Supported")

    resp = CoPilotResponse(
        natural_language_response="", answered_question=False, response_type="inquiryai"
    )

    LogWriter.warning(
        f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception"
    )
    exc = traceback.format_exc()
    logger.debug_pii(
        f"/{graphname}/query request_id={req_id_cv.get()} Exception Trace:\n{exc}"
    )
    pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()

    return resp

