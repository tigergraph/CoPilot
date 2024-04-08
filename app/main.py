from datetime import datetime
from typing import Optional, Union, Annotated, List, Dict
import traceback
from fastapi import FastAPI, BackgroundTasks, Header, Depends, HTTPException, status, Request, WebSocket
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from starlette.responses import Response
from base64 import b64decode
import os
import json
import time
import uuid
import logging
from pyTigerGraph import TigerGraphConnection
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.agent import TigerGraphAgent
from app.llm_services import OpenAI, AzureOpenAI, AWS_SageMaker_Endpoint, GoogleVertexAI, AWSBedrock
from app.embeddings.embedding_services import AWS_Bedrock_Embedding, AzureOpenAI_Ada002, OpenAI_Embedding, VertexAI_PaLM_Embedding
from app.embeddings.faiss_embedding_store import FAISS_EmbeddingStore
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.supportai.supportai_ingest import BatchIngestion

from app.session import SessionHandler
from app.status import StatusManager
from app.tools import MapQuestionToSchemaException
from app.py_schemas.schemas import *
from app.log import req_id_cv
from app.supportai.retrievers import *
from app.supportai.concept_management.create_concepts import *
from app.sync.eventual_consistency_checker import EventualConsistencyChecker
from app.tools.logwriter import LogWriter
from app.metrics.prometheus_metrics import metrics as pmetrics
from app.metrics.tg_proxy import TigerGraphConnectionProxy

# Configs
LLM_SERVICE = os.getenv("LLM_CONFIG", "configs/llm_config.json")
DB_CONFIG = os.getenv("DB_CONFIG", "configs/db_config.json")
MILVUS_CONFIG = os.getenv("MILVUS_CONFIG", "configs/milvus_config.json")
PATH_PREFIX = os.getenv("PATH_PREFIX", "")

if LLM_SERVICE is None:
    raise Exception("LLM_CONFIG environment variable not set")
if DB_CONFIG is None:
    raise Exception("DB_CONFIG environment variable not set")

if LLM_SERVICE[-5:] != ".json":
    try:
        llm_config = json.loads(LLM_SERVICE)
    except Exception as e:
        raise Exception("LLM_CONFIG environment variable must be a .json file or a JSON string, failed with error: " + str(e))
else:
    with open(LLM_SERVICE, "r") as f:
        llm_config = json.load(f)

if DB_CONFIG[-5:] != ".json":
    try:
        db_config = json.loads(str(DB_CONFIG))
    except Exception as e:
        raise Exception("DB_CONFIG environment variable must be a .json file or a JSON string, failed with error: " + str(e))
else:
    with open(DB_CONFIG, "r") as f:
        db_config = json.load(f)


if MILVUS_CONFIG is None or (MILVUS_CONFIG.endswith(".json") and not os.path.exists(MILVUS_CONFIG)):
    milvus_config = {
        "host": "localhost",
        "port": "19530",
        "enabled": "false"
    }
elif MILVUS_CONFIG.endswith(".json"):
    with open(MILVUS_CONFIG, "r") as f:
        milvus_config = json.load(f)
else:
    try:
        milvus_config = json.loads(str(MILVUS_CONFIG))
    except json.JSONDecodeError as e:
        raise Exception("MILVUS_CONFIG must be a .json file or a JSON string, failed with error: " + str(e))


app = FastAPI(root_path=PATH_PREFIX)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBasic()
session_handler = SessionHandler()
status_manager = StatusManager()

consistency_checkers = {}
excluded_metrics_paths = ("/docs", "/openapi.json", "/metrics")

logger = logging.getLogger(__name__)

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


embedding_store = FAISS_EmbeddingStore(embedding_service)

if milvus_config.get("enabled") == "true":
    LogWriter.info(f"Milvus enabled for host {milvus_config['host']} at port {milvus_config['port']}")

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

    support_collection_name=milvus_config.get("collection_name", "tg_support_documents")
    LogWriter.info(f"Setting up Milvus embedding store for SupportAI with collection_name: {support_collection_name}")
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

async def get_basic_auth_credentials(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if auth_header is None:
        return ""

    try:
        auth_type, encoded_credentials = auth_header.split(' ', 1)
    except ValueError:
        return ""

    if auth_type.lower() != 'basic':
        return ""
    
    try:
        decoded_credentials = b64decode(encoded_credentials).decode('utf-8')
        username, _ = decoded_credentials.split(':', 1)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return username

@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    LogWriter.info(f"{request.url.path} ENTRY request_id={req_id}")
    req_id_cv.set(req_id)
    start_time = time.time()
    response = await call_next(request)
       
    user_name = await get_basic_auth_credentials(request)
    client_host = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    action_name = request.url.path
    status = "SUCCESS"
    
    response = await call_next(request)
    if response.status_code != 200:
        status = "FAILURE"

    # set up the audit log entry structure and write it with the LogWriter
    if not any(request.url.path.endswith(path) for path in excluded_metrics_paths):
        audit_log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "userName": user_name,
            "clientHost": f"{client_host}:{request.url.port}",
            "userAgent": user_agent,
            "endpoint": request.url.path,
            "actionName": action_name,
            "status": status,
            "requestId": req_id
        }    
        LogWriter.audit_log(json.dumps(audit_log_entry), mask_pii=False)
        update_metrics(start_time=start_time, label=request.url.path)
    
    return response


def get_db_connection(graphname, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> TigerGraphConnectionProxy:
    conn = TigerGraphConnection(
        host = db_config["hostname"],
        username = credentials.username,
        password = credentials.password,
        graphname = graphname,
    )

    if db_config["getToken"]:
        try:
            apiToken = conn._post(conn.restppUrl+"/requesttoken", authMode="pwd", data=str({"graph": conn.graphname}), resKey="results")["token"]
        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )

        conn = TigerGraphConnection(
            host=db_config["hostname"],
            username=credentials.username,
            password=credentials.password,
            graphname=graphname,
            apiToken=apiToken,
        )

    conn.customizeHeader(timeout=db_config["default_timeout"] * 1000, responseSize=5000000)
    conn = TigerGraphConnectionProxy(conn)

    return conn


async def get_eventual_consistency_checker(graphname: str):
    if not db_config.get("enable_consistency_checker", True):
        logger.debug("Eventual consistency checker disabled")
        return

    check_interval_seconds = milvus_config.get("sync_interval_seconds", 30 * 60)
    credentials = HTTPBasicCredentials(username=db_config["username"], password=db_config["password"])
    conn=get_db_connection(graphname, credentials)

    if graphname not in consistency_checkers:
        vector_indices = {}
        if milvus_config.get("enabled") == "true":
            vertex_field = milvus_config.get("vertex_field", "vertex_id")
            index_names = milvus_config.get("indexes", ["Document", "DocumentChunk", "Entity", "Relationship", "Concept"])
            for index_name in index_names:
                vector_indices[graphname + "_" + index_name] = MilvusEmbeddingStore(
                    embedding_service,
                    host=milvus_config["host"],
                    port=milvus_config["port"],
                    support_ai_instance=True,
                    collection_name=graphname + "_" + index_name,
                    username=milvus_config.get("username", ""),
                    password=milvus_config.get("password", ""),
                    vector_field=milvus_config.get("vector_field", "document_vector"),
                    text_field=milvus_config.get("text_field", "document_content"),
                    vertex_field=vertex_field,
                )

        # TODO: chunker and extractor needs to be configurable
        from app.supportai.chunkers.semantic_chunker import SemanticChunker
        from app.supportai.extractors import LLMEntityRelationshipExtractor

        chunker = SemanticChunker(embedding_service, "percentile", 0.95)
        extractor = LLMEntityRelationshipExtractor(get_llm_service(llm_config))
        checker = EventualConsistencyChecker(check_interval_seconds,
                                             graphname, vertex_field,
                                             embedding_service, 
                                             index_names,
                                             vector_indices, 
                                             conn, chunker, extractor)
        await checker.initialize()
        consistency_checkers[graphname] = checker
    return consistency_checkers[graphname]


def update_metrics(start_time, label):
    duration = time.time() - start_time
    pmetrics.copilot_endpoint_duration_seconds.labels(label).observe(duration)
    pmetrics.copilot_endpoint_total.labels(label).inc()

@app.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@app.post("/{graphname}/getqueryembedding")
def get_query_embedding(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.debug(f"/{graphname}/getqueryembedding request_id={req_id_cv.get()} question={query.query}")

    return embedding_service.embed_query(query.query)

@app.post("/{graphname}/register_docs")
def register_docs(graphname, query_list: Union[GSQLQueryInfo, List[GSQLQueryInfo]], credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.debug(f"Using embedding store: {embedding_store}")
    results = []

    if not isinstance(query_list, list):
        query_list = [query_list]

    for query_info in query_list:
        logger.debug(f"/{graphname}/register_docs request_id={req_id_cv.get()} registering {query_info.function_header}")

        vec = embedding_service.embed_query(query_info.docstring)
        res = embedding_store.add_embeddings([(query_info.docstring, vec)], [{"function_header": query_info.function_header, 
                                                                            "description": query_info.description,
                                                                            "param_types": query_info.param_types,
                                                                            "custom_query": True}])
        if res:
            results.append(res)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register document(s)")

    return results


@app.post("/{graphname}/upsert_docs")
def upsert_docs(graphname, request_data: Union[QueryUperstRequest, List[QueryUperstRequest]], credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    try:
        results = []

        if not isinstance(request_data, list):
            request_data = [request_data]

        for request_info in request_data:
            id = request_info.id
            query_info = request_info.query_info

            if not id and not query_info:
                raise HTTPException(status_code=400, detail="At least one of 'id' or 'query_info' is required")

            logger.debug(f"/{graphname}/upsert_docs request_id={req_id_cv.get()} upserting document(s)")

            vec = embedding_service.embed_query(query_info.docstring)
            res = embedding_store.upsert_embeddings(id, [(query_info.docstring, vec)], [{"function_header": query_info.function_header, 
                                                                                        "description": query_info.description,
                                                                                        "param_types": query_info.param_types,
                                                                                        "custom_query": True}])
            if res:
                results.append(res)
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upsert document(s)")
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while upserting query {str(e)}")
    
@app.post("/{graphname}/delete_docs")
def delete_docs(graphname, request_data: QueryDeleteRequest, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    ids = request_data.ids
    expr = request_data.expr

    if ids and not isinstance(ids, list):
        try:
            ids = [ids]
        except ValueError:
            raise ValueError("Invalid ID format. IDs must be string or lists of strings.")

    logger.debug(f"/{graphname}/delete_docs request_id={req_id_cv.get()} deleting document(s)")

    # Call the remove_embeddings method based on provided IDs or expression
    try:
        if expr:
            res = embedding_store.remove_embeddings(expr=expr)
            return res
        elif ids:
            res = embedding_store.remove_embeddings(ids=ids)
            return res
        else:
            raise HTTPException(status_code=400, detail="Either IDs or an expression must be provided.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/{graphname}/retrieve_docs")
def retrieve_docs(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)], top_k:int = 3):
    logger.debug_pii(f"/{graphname}/retrieve_docs request_id={req_id_cv.get()} top_k={top_k} question={query.query}")
    return embedding_store.retrieve_similar(embedding_service.embed_query(query.query), top_k=top_k)


@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, conn: TigerGraphConnectionProxy = Depends(get_db_connection)) -> CoPilotResponse:
    logger.debug_pii(f"/{graphname}/query request_id={req_id_cv.get()} question={query.query}")
    logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} database connection created")

    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=openai agent created")
        agent = TigerGraphAgent(OpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=azure agent created")
        agent = TigerGraphAgent(AzureOpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=sagemaker agent created")
        agent = TigerGraphAgent(AWS_SageMaker_Endpoint(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "vertexai":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=vertexai agent created")
        agent = TigerGraphAgent(GoogleVertexAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "bedrock":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=bedrock agent created")
        agent = TigerGraphAgent(AWSBedrock(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    else:
        LogWriter.error(f"/{graphname}/query request_id={req_id_cv.get()} agent creation failed due to invalid llm_service")
        raise Exception("LLM Completion Service Not Supported")

    resp = CoPilotResponse
    resp.response_type = "inquiryai"

    try:
        steps = agent.question_for_agent(query.query)
        # LogWriter.info(f"steps: {steps}")
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} agent executed")
        try:
            # try again if there were no steps taken
            if len(steps["intermediate_steps"]) == 0:
                steps = agent.question_for_agent(query.query)

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
                "An error occurred while processing the response. Please try again."
            )
            resp.query_sources = {"agent_history": str(steps)}
            resp.answered_question = False
            LogWriter.warning(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
            pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()
            traceback.print_exc()
    except MapQuestionToSchemaException:
        resp.natural_language_response = (
            "A schema mapping error occurred. Please try rephrasing your question."
        )
        resp.query_sources = {}
        resp.answered_question = False
        LogWriter.warning(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to MapQuestionToSchemaException")
        pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()
        traceback.print_exc()
    except Exception:
        resp.natural_language_response = (
            "An error occurred while processing the response. Please try again."
        )
        resp.query_sources = {}
        resp.answered_question = False
        LogWriter.warning(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
        traceback.print_exc()
        pmetrics.llm_query_error_total.labels(embedding_service.model_name).inc()
    
    return resp


@app.post("/{graphname}/login")
def login(graphname, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    session_id = session_handler.create_session(conn.username, conn)
    return {"session_id": session_id}


@app.post("/{graphname}/logout")
def logout(graphname, session_id: str):
    session_handler.delete_session(session_id)
    return {"status": "success"}


@app.get("/{graphname}/chat")
def chat(request: Request):
    return HTMLResponse(open("app/static/chat.html").read())


@app.websocket("/{graphname}/ws")
async def websocket_endpoint(websocket: WebSocket, graphname: str, session_id: str):
    session = session_handler.get_session(session_id)
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        res = retrieve_answer(
            graphname, NaturalLanguageQuery(query=data), session.db_conn
        )
        await websocket.send_text(f"{res.natural_language_response}")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "llm_completion_model": llm_config["completion_service"]["llm_model"],
        "embedding_service": llm_config["embedding_service"]["embedding_model_service"],
    }


@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")


@app.post("/{graphname}/supportai/initialize")
def initialize(graphname, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    # need to open the file using the absolute path
    abs_path = os.path.abspath(__file__)
    file_path = os.path.join(
        os.path.dirname(abs_path), "./gsql/supportai/SupportAI_Schema.gsql"
    )
    with open(file_path, "r") as f:
        schema = f.read()
    schema_res = conn.gsql(
        """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_schema""".format(
            graphname, schema
        )
    )

    file_path = os.path.join(
        os.path.dirname(abs_path), "./gsql/supportai/SupportAI_IndexCreation.gsql"
    )
    with open(file_path, "r") as f:
        index = f.read()
    index_res = conn.gsql(
        """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_indexes""".format(
            graphname, index
        )
    )

    file_path = os.path.join(
        os.path.dirname(abs_path), "./gsql/supportai/Scan_For_Updates.gsql"
    )
    with open(file_path, "r") as f:
        scan_for_updates = f.read()
    res = conn.gsql(
        "USE GRAPH "
        + conn.graphname
        + "\n"
        + scan_for_updates
        + "\n INSTALL QUERY Scan_For_Updates"
    )

    file_path = os.path.join(
        os.path.dirname(abs_path),
        "./gsql/supportai/Update_Vertices_Processing_Status.gsql",
    )
    with open(file_path, "r") as f:
        update_vertices = f.read()
    res = conn.gsql("USE GRAPH "+conn.graphname+"\n"+update_vertices+"\n INSTALL QUERY Update_Vertices_Processing_Status")
    
    return {"schema_creation_status": json.dumps(schema_res), "index_creation_status": json.dumps(index_res)}


@app.post("/{graphname}/supportai/create_ingest")
async def create_ingest(graphname, ingest_config: CreateIngestConfig, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    if ingest_config.file_format.lower() == "json":
        abs_path = os.path.abspath(__file__)
        file_path = os.path.join(
            os.path.dirname(abs_path), "gsql/supportai/SupportAI_InitialLoadJSON.gsql"
        )
        with open(file_path, "r") as f:
            ingest_template = f.read()
        ingest_template = ingest_template.replace("@uuid@", str(uuid.uuid4().hex))
        doc_id = ingest_config.loader_config.get("doc_id_field", "doc_id")
        doc_text = ingest_config.loader_config.get("content_field", "content")
        ingest_template = ingest_template.replace('"doc_id"', '"{}"'.format(doc_id))
        ingest_template = ingest_template.replace('"content"', '"{}"'.format(doc_text))

    if ingest_config.file_format.lower() == "csv":
        abs_path = os.path.abspath(__file__)
        file_path = os.path.join(
            os.path.dirname(abs_path), "gsql/supportai/SupportAI_InitialLoadCSV.gsql"
        )
        with open(file_path, "r") as f:
            ingest_template = f.read()
        ingest_template = ingest_template.replace("@uuid@", str(uuid.uuid4().hex))
        separator = ingest_config.get("separator", "|")
        header = ingest_config.get("header", "true")
        eol = ingest_config.get("eol", "\n")
        quote = ingest_config.get("quote", "double")
        ingest_template = ingest_template.replace('"|"', '"{}"'.format(separator))
        ingest_template = ingest_template.replace('"true"', '"{}"'.format(header))
        ingest_template = ingest_template.replace('"\\n"', '"{}"'.format(eol))
        ingest_template = ingest_template.replace('"double"', '"{}"'.format(quote))

    abs_path = os.path.abspath(__file__)
    file_path = os.path.join(
        os.path.dirname(abs_path), "gsql/supportai/SupportAI_DataSourceCreation.gsql"
    )
    with open(file_path, "r") as f:
        data_stream_conn = f.read()

    # assign unique identifier to the data stream connection

    data_stream_conn = data_stream_conn.replace(
        "@source_name@", "SupportAI_" + graphname + "_" + str(uuid.uuid4().hex)
    )

    # check the data source and create the appropriate connection
    if ingest_config.data_source.lower() == "s3":
        data_conn = ingest_config.data_source_config
        if (
            data_conn.get("aws_access_key") is None
            or data_conn.get("aws_secret_key") is None
        ):
            raise Exception("AWS credentials not provided")
        connector = {
            "type": "s3",
            "access.key": data_conn["aws_access_key"],
            "secret.key": data_conn["aws_secret_key"],
        }

        data_stream_conn = data_stream_conn.replace(
            "@source_config@", json.dumps(connector)
        )

    elif ingest_config.data_source.lower() == "azure":
        if ingest_config.data_source_config.get("account_key") is not None:
            connector = {
                "type": "abs",
                "account.key": ingest_config.data_source_config["account_key"],
            }
        elif ingest_config.data_source_config.get("client_id") is not None:
            # verify that the client secret is also provided
            if ingest_config.data_source_config.get("client_secret") is None:
                raise Exception("Client secret not provided")
            # verify that the tenant id is also provided
            if ingest_config.data_source_config.get("tenant_id") is None:
                raise Exception("Tenant id not provided")
            connector = {
                "type": "abs",
                "client.id": ingest_config.data_source_config["client_id"],
                "client.secret": ingest_config.data_source_config["client_secret"],
                "tenant.id": ingest_config.data_source_config["tenant_id"],
            }
        else:
            raise Exception("Azure credentials not provided")
        data_stream_conn = data_stream_conn.replace(
            "@source_config@", json.dumps(connector)
        )
    elif ingest_config.data_source.lower() == "gcs":
        # verify that the correct fields are provided
        if ingest_config.data_source_config.get("project_id") is None:
            raise Exception("Project id not provided")
        if ingest_config.data_source_config.get("private_key_id") is None:
            raise Exception("Private key id not provided")
        if ingest_config.data_source_config.get("private_key") is None:
            raise Exception("Private key not provided")
        if ingest_config.data_source_config.get("client_email") is None:
            raise Exception("Client email not provided")
        connector = {
            "type": "gcs",
            "project_id": ingest_config.data_source_config["project_id"],
            "private_key_id": ingest_config.data_source_config["private_key_id"],
            "private_key": ingest_config.data_source_config["private_key"],
            "client_email": ingest_config.data_source_config["client_email"],
        }
        data_stream_conn = data_stream_conn.replace(
            "@source_config@", json.dumps(connector)
        )
    else:
        raise Exception("Data source not implemented")

    load_job_created = conn.gsql("USE GRAPH {}\n".format(graphname) + ingest_template)
    
    data_source_created = conn.gsql("USE GRAPH {}\n".format(graphname) + data_stream_conn)
    
    return {"load_job_id": load_job_created.split(":")[1].strip(" [").strip(" ").strip(".").strip("]"),
            "data_source_id": data_source_created.split(":")[1].strip(" [").strip(" ").strip(".").strip("]")}

@app.post("/{graphname}/supportai/ingest")
async def ingest(graphname, loader_info: LoadingInfo, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    if loader_info.file_path is None:
        raise Exception("File path not provided")
    if loader_info.load_job_id is None:
        raise Exception("Load job id not provided")
    if loader_info.data_source_id is None:
        raise Exception("Data source id not provided")

    try:
        res = conn.gsql(
            'USE GRAPH {}\nRUN LOADING JOB -noprint {} USING {}="{}"'.format(
                graphname,
                loader_info.load_job_id,
                "DocumentContent",
                "$" + loader_info.data_source_id + ":" + loader_info.file_path,
            )
        )
    except Exception as e:
        if (
            "Running the following loading job in background with '-noprint' option:"
            in str(e)
        ):
            res = str(e)
        else:
            raise e
    return {"job_name": loader_info.load_job_id,
            "job_id": res.split("Running the following loading job in background with '-noprint' option:")[1].split("Jobid: ")[1].split("\n")[0],
            "log_location": res.split("Running the following loading job in background with '-noprint' option:")[1].split("Log directory: ")[1].split("\n")[0]}
        
@app.post("/{graphname}/supportai/batch_ingest")
async def batch_ingest(graphname, doc_source:Union[S3BatchDocumentIngest, BatchDocumentIngest], background_tasks: BackgroundTasks, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    req_id = req_id_cv.get()
    status_manager.create_status(conn.username, req_id, graphname)
    ingestion = BatchIngestion(
        embedding_service,
        get_llm_service(llm_config),
        conn,
        status_manager.get_status(req_id),
    )
    if doc_source.service.lower() == "s3":
        background_tasks.add_task(ingestion.ingest_blobs, doc_source)
    else:
        raise Exception("Document storage service not implemented")
    
    return {"status": "request accepted", "request_id": req_id}


@app.get("/{graphname}/supportai/ingestion_status")
def ingestion_status(graphname, status_id: str):
    status = status_manager.get_status(status_id)

    if status:
        return {"status": status.to_dict()}
    else:
        return {"status": "not found"}


@app.post("/{graphname}/supportai/createvdb")
def create_vdb(graphname, config: CreateVectorIndexConfig, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    if conn.getVertexCount("HNSWEntrypoint", where='id=="{}"'.format(config.index_name)) == 0:
        res = conn.runInstalledQuery("HNSW_CreateEntrypoint", {"index_name": config.index_name})

    res = conn.runInstalledQuery(
        "HNSW_BuildIndex",
        {
            "index_name": config.index_name,
            "v_types": config.vertex_types,
            "M": config.M,
            "ef_construction": config.ef_construction,
        },
    )

    return res


@app.get("/{graphname}/supportai/deletevdb/{index_name}")
def delete_vdb(graphname, index_name, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    return conn.runInstalledQuery("HNSW_DeleteIndex", {"index_name": index_name})
    
@app.post("/{graphname}/supportai/queryvdb/{index_name}")
async def query_vdb(graphname, index_name, query: SupportAIQuestion, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    retriever = HNSWRetriever(embedding_service, get_llm_service(llm_config), conn)
    return retriever.search(query.question, index_name, query.method_params["top_k"], query.method_params["withHyDE"])


@app.post("/{graphname}/supportai/search")
async def search(graphname, query: SupportAIQuestion, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    if query.method.lower() == "hnswoverlap":
        retriever = HNSWOverlapRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(
            query.question,
            query.method_params["indicies"],
            query.method_params["top_k"],
            query.method_params["num_hops"],
            query.method_params["num_seen_min"],
        )
    elif query.method.lower() == "vdb":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "sibling":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWSiblingRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["lookback"],
            query.method_params["lookahead"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "entityrelationship":
        retriever = EntityRelationshipRetriever(embedding_service, embedding_store, get_llm_service(llm_config), conn)
        res = retriever.search(query.question, query.method_params["top_k"])

    return res


@app.post("/{graphname}/supportai/answerquestion")
async def answer_question(graphname, query: SupportAIQuestion, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    resp = CoPilotResponse
    resp.response_type = "supportai"
    if query.method.lower() == "hnswoverlap":
        retriever = HNSWOverlapRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(
            query.question,
            query.method_params["indices"],
            query.method_params["top_k"],
            query.method_params["num_hops"],
            query.method_params["num_seen_min"],
        )
    elif query.method.lower() == "vdb":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "sibling":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWSiblingRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["lookback"],
            query.method_params["lookahead"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "entityrelationship":
        retriever = EntityRelationshipRetriever(embedding_service, embedding_store, get_llm_service(llm_config), conn)
        res = retriever.retrieve_answer(query.question, query.method_params["top_k"])
    else:
        raise Exception("Method not implemented")

    resp.natural_language_response = res["response"]
    resp.query_sources = res["retrieved"]

    return res


@app.get("/{graphname}/supportai/buildconcepts")
async def build_concepts(graphname, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    rels_concepts = RelationshipConceptCreator(conn, llm_config, embedding_service)
    rels_concepts.create_concepts()
    ents_concepts = EntityConceptCreator(conn, llm_config, embedding_service)
    ents_concepts.create_concepts()
    comm_concepts = CommunityConceptCreator(conn, llm_config, embedding_service)
    comm_concepts.create_concepts()
    high_level_concepts = HigherLevelConceptCreator(conn, llm_config, embedding_service)
    high_level_concepts.create_concepts()

    return {"status": "success"}


@app.get("/{graphname}/supportai/forceupdate")
async def force_update(graphname: str, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    get_eventual_consistency_checker(graphname)
    return {"status": "success"}
