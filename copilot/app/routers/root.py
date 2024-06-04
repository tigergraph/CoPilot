import logging

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from common.config import llm_config

from pymilvus import connections, utility

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@router.get("/health")
async def health():
    # Check if Milvus is up and running and if the required collections exist
    connections.connect(host="milvus-standalone", port="19530")

    try:
        # Check if the required collections exist
        inquiry_collection_exists = utility.has_collection("tg_inquiry_documents")
        support_collection_exists = utility.has_collection("tg_support_documents")

        if inquiry_collection_exists or support_collection_exists:
            return {
                "status": "healthy",
                "llm_completion_model": llm_config["completion_service"]["llm_model"],
                "embedding_service": llm_config["embedding_service"][
                    "embedding_model_service"
                ],
            }
        else:
            return {"status": "Milvus is up and running, but no collection exist yet"}
    except Exception as e:
        return {"status": "Error checking Milvus health", "error": str(e)}


@router.get("/metrics")
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
