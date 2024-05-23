import json
import logging
import traceback
from typing import List, Union, Annotated

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.security.http import HTTPBase

from app.agent import TigerGraphAgent
from app.config import embedding_service, embedding_store, llm_config, session_handler
from app.tools import GenerateCypher
from app.log import req_id_cv
from app.metrics.prometheus_metrics import metrics as pmetrics
from app.py_schemas.schemas import (
    CoPilotResponse,
    NaturalLanguageQuery
)

from app.config import get_llm_service
from app.tools.logwriter import LogWriter

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
        f"/{graphname}/generate_cypher request_id={req_id_cv.get()} question={query.query}"
    )
    logger.debug(
        f"/{graphname}/generate_cypher request_id={req_id_cv.get()} database connection created"
    )

    llm = get_llm_service(llm_config)

    cypher_gen_tool = GenerateCypher(conn, llm)

    try:
        generated = cypher_gen_tool._run(query.query)
    except Exception as e:
        LogWriter.warning(
            f"/{graphname}/generate_cypher request_id={req_id_cv.get()} generation execution failed due to exception."
        )
        exc = traceback.format_exc()
        logger.debug_pii(
            f"/{graphname}/generate_cypher request_id={req_id_cv.get()} Exception Trace:\n{exc}"
        )
        return CoPilotResponse(
            natural_language_response="Failed to generate Cypher", answered_question=False, response_type="queryai"
        )

    resp = CoPilotResponse(
        natural_language_response=generated, 
        answered_question=True, 
        response_type="queryai",
        query_sources={"graphname": graphname, "query": query.query}
    )

    return resp

