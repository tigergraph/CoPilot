import json
import os

from fastapi.security import HTTPBasic

from app.embeddings.embedding_services import (AWS_Bedrock_Embedding,
                                               AzureOpenAI_Ada002,
                                               OpenAI_Embedding,
                                               VertexAI_PaLM_Embedding)
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.llm_services import (AWS_SageMaker_Endpoint, AWSBedrock, AzureOpenAI,
                              GoogleVertexAI, OpenAI)
from app.session import SessionHandler
from app.status import StatusManager
from app.tools.logwriter import LogWriter

security = HTTPBasic()
session_handler = SessionHandler()
status_manager = StatusManager()

# Configs
LLM_SERVICE = os.getenv("LLM_CONFIG", "configs/llm_config.json")
DB_CONFIG = os.getenv("DB_CONFIG", "configs/db_config.json")
MILVUS_CONFIG = os.getenv("MILVUS_CONFIG", "configs/milvus_config.json")
DOC_PROCESSING_CONFIG = os.getenv(
    "DOC_PROCESSING_CONFIG", "configs/doc_processing_config.json"
)
PATH_PREFIX = os.getenv("PATH_PREFIX", "")
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

if not PATH_PREFIX.startswith("/") and len(PATH_PREFIX) != 0:
    PATH_PREFIX = f"/{PATH_PREFIX}"
if PATH_PREFIX.endswith("/"):
    PATH_PREFIX = PATH_PREFIX[:-1]

if LLM_SERVICE is None:
    raise Exception("LLM_CONFIG environment variable not set")
if DB_CONFIG is None:
    raise Exception("DB_CONFIG environment variable not set")

if LLM_SERVICE[-5:] != ".json":
    try:
        llm_config = json.loads(LLM_SERVICE)
    except Exception as e:
        raise Exception(
            "LLM_CONFIG environment variable must be a .json file or a JSON string, failed with error: "
            + str(e)
        )
else:
    with open(LLM_SERVICE, "r") as f:
        llm_config = json.load(f)

if DB_CONFIG[-5:] != ".json":
    try:
        db_config = json.loads(str(DB_CONFIG))
    except Exception as e:
        raise Exception(
            "DB_CONFIG environment variable must be a .json file or a JSON string, failed with error: "
            + str(e)
        )
else:
    with open(DB_CONFIG, "r") as f:
        db_config = json.load(f)


if MILVUS_CONFIG is None or (
    MILVUS_CONFIG.endswith(".json") and not os.path.exists(MILVUS_CONFIG)
):
    milvus_config = {"host": "localhost", "port": "19530", "enabled": "false"}
elif MILVUS_CONFIG.endswith(".json"):
    with open(MILVUS_CONFIG, "r") as f:
        milvus_config = json.load(f)
else:
    try:
        milvus_config = json.loads(str(MILVUS_CONFIG))
    except json.JSONDecodeError as e:
        raise Exception(
            "MILVUS_CONFIG must be a .json file or a JSON string, failed with error: "
            + str(e)
        )


if llm_config["embedding_service"]["embedding_model_service"].lower() == "openai":
    embedding_service = OpenAI_Embedding(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "azure":
    embedding_service = AzureOpenAI_Ada002(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "vertexai":
    embedding_service = VertexAI_PaLM_Embedding(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "bedrock":
    embedding_service = AWS_Bedrock_Embedding(llm_config["embedding_service"])
else:
    raise Exception("Embedding service not implemented")


def get_llm_service(llm_config):
    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        return OpenAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        return AzureOpenAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        return AWS_SageMaker_Endpoint(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "vertexai":
        return GoogleVertexAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "bedrock":
        return AWSBedrock(llm_config["completion_service"])
    else:
        raise Exception("LLM Completion Service Not Supported")


LogWriter.info(
    f"Milvus enabled for host {milvus_config['host']} at port {milvus_config['port']}"
)

LogWriter.info(f"Setting up Milvus embedding store for InquiryAI")
embedding_store = MilvusEmbeddingStore(
    embedding_service,
    host=milvus_config["host"],
    port=milvus_config["port"],
    collection_name="tg_inquiry_documents",
    support_ai_instance=False,
    username=milvus_config.get("username", ""),
    password=milvus_config.get("password", ""),
    alias=milvus_config.get("alias", "default"),
)

support_collection_name = milvus_config.get("collection_name", "tg_support_documents")
LogWriter.info(
    f"Setting up Milvus embedding store for SupportAI with collection_name: {support_collection_name}"
)
vertex_field = milvus_config.get("vertex_field", "vertex_id")
support_ai_embedding_store = MilvusEmbeddingStore(
    embedding_service,
    host=milvus_config["host"],
    port=milvus_config["port"],
    support_ai_instance=True,
    collection_name=support_collection_name,
    username=milvus_config.get("username", ""),
    password=milvus_config.get("password", ""),
    vector_field=milvus_config.get("vector_field", "document_vector"),
    text_field=milvus_config.get("text_field", "document_content"),
    vertex_field=vertex_field,
    alias=milvus_config.get("alias", "default"),
)


if DOC_PROCESSING_CONFIG is None or (
    DOC_PROCESSING_CONFIG.endswith(".json")
    and not os.path.exists(DOC_PROCESSING_CONFIG)
):
    doc_processing_config = {
        "chunker": "semantic",
        "chunker_config": {"method": "percentile", "threshold": 0.95},
        "extractor": "llm",
        "extractor_config": {},
    }
elif DOC_PROCESSING_CONFIG.endswith(".json"):
    with open(DOC_PROCESSING_CONFIG, "r") as f:
        doc_processing_config = json.load(f)
else:
    doc_processing_config = json.loads(DOC_PROCESSING_CONFIG)
