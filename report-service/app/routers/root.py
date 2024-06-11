import logging

from fastapi.responses import FileResponse
from fastapi.security.http import HTTPBase
from fastapi import APIRouter, Request, Depends, Response
from typing import Annotated

from common.config import llm_config
from common.py_schemas import ReportCreationRequest

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBase(scheme="basic", auto_error=False)


@router.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "llm_completion_model": llm_config["completion_service"]["llm_model"],
        "embedding_service": llm_config["embedding_service"][
            "embedding_model_service"
        ],
    }

@router.post("/{graphname}/create_report")
def create_report(graphname: str,
                  create_report_request: ReportCreationRequest, 
                  conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    return create_report_request.model_dump_json()


@router.get("/metrics")
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
