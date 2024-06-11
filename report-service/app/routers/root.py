import logging

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from common.config import llm_config

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/metrics")
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
