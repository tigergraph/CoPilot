import logging

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from app.config import llm_config, service_status

from pymilvus import connections, utility

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@router.get("/health")
async def health():
    try:
        # Check if Milvus is up and running and if the required collections exist
        connections.connect(host="milvus-standalone", port="19530")
        # Check if the required collections exist
        inquiry_collection_exists = utility.has_collection("tg_inquiry_documents")
        support_collection_exists = utility.has_collection("tg_support_documents")

        if inquiry_collection_exists or support_collection_exists:
            service_status["milvus"] = {"status": "ok", "error": None}
        else:
            service_status["milvus"] = {"status": "error", "error": "Milvus is up and running, but no collection exists"}
    except Exception as e:
        service_status["milvus"] = {"status": "error", "error": str(e)}
    
    status = {
        "status": "unhealthy" if any(v["error"] is not None for v in service_status.values()) else "healthy",
        "details": service_status
    }

    return status


@router.get("/metrics")
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")
