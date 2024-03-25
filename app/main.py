from typing import Optional, Union, Annotated, List, Dict
from fastapi import FastAPI, BackgroundTasks, Header, Depends, HTTPException, status, Request, WebSocket
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import os
from pyTigerGraph import TigerGraphConnection
import json
import time
import uuid
import logging
from app.session import SessionHandler
from app.supportai.supportai_ingest import BatchIngestion

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.agent import TigerGraphAgent
from app.llm_services import OpenAI, AzureOpenAI, AWS_SageMaker_Endpoint, GoogleVertexAI
from app.embeddings.embedding_services import AzureOpenAI_Ada002, OpenAI_Embedding, VertexAI_PaLM_Embedding
from app.embeddings.faiss_embedding_store import FAISS_EmbeddingStore
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore

from app.status import StatusManager
from app.tools import MapQuestionToSchemaException
from app.py_schemas.schemas import *
from app.log import req_id_cv
from app.supportai.retrievers import *
from app.supportai.concept_management.create_concepts import *

LLM_SERVICE = os.getenv("LLM_CONFIG")
DB_CONFIG = os.getenv("DB_CONFIG")
MILVUS_CONFIG = os.getenv("MILVUS_CONFIG")

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



app = FastAPI()

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

logger = logging.getLogger(__name__)

if llm_config["embedding_service"]["embedding_model_service"].lower() == "openai":
    embedding_service = OpenAI_Embedding(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "azure":
    embedding_service = AzureOpenAI_Ada002(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "vertexai":
    embedding_service = VertexAI_PaLM_Embedding(llm_config["embedding_service"])
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
    else:
        raise Exception("LLM Completion Service Not Supported")


embedding_store = FAISS_EmbeddingStore(embedding_service)

if milvus_config.get("enabled") == "true":
    logger.info(f"Milvus enabled for host {milvus_config['host']} at port {milvus_config['port']}")

    logger.info(f"Setting up Milvus embedding store for InquiryAI")
    embedding_store = MilvusEmbeddingStore(
            embedding_service,
            host=milvus_config["host"],
            port=milvus_config["port"],
            collection_name="tg_inquiry_documents", 
            support_ai_instance=False,
            username=milvus_config.get("username", ""),
            password=milvus_config.get("password", "")
    )

    support_collection_name=milvus_config.get("collection_name", "tg_support_documents")
    logger.info(f"Setting up Milvus embedding store for SupportAI with collection_name: {support_collection_name}")
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
        vertex_field=milvus_config.get("vertex_field", "vertex_id")
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    logger.info(f"{request.url.path} ENTRY request_id={req_id}")
    req_id_cv.set(req_id)
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"{request.url.path} EXIT request_id={req_id} completed_in={formatted_process_time}ms status_code={response.status_code}")
    
    return response

def get_db_connection(graphname, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> TigerGraphConnection:
    conn = TigerGraphConnection(
        host=db_config["hostname"],
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
            username = credentials.username,
            password = credentials.password,
            graphname = graphname,
            apiToken = apiToken
        )
    conn.customizeHeader(timeout=db_config["default_timeout"]*1000, responseSize=5000000)
    return conn

@app.get("/")
def read_root():
    return {"config": llm_config["model_name"]}

@app.post("/{graphname}/getqueryembedding")
def get_query_embedding(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.debug(f"/{graphname}/getqueryembedding request_id={req_id_cv.get()} question={query.query}")
    return embedding_service.embed_query(query.query)

@app.post("/{graphname}/register_docs")
def register_query(graphname, query_list: Union[GSQLQueryInfo, List[GSQLQueryInfo]], credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.debug(f"Using embedding store: {embedding_store}")
    results = []

    if not isinstance(query_list, list):
        query_list = [query_list]

    for query_info in query_list:
        logger.debug(f"/{graphname}/registercustomquery request_id={req_id_cv.get()} registering {query_info.function_header}")

        vec = embedding_service.embed_query(query_info.docstring)
        res = embedding_store.add_embeddings([(query_info.docstring, vec)], [{"function_header": query_info.function_header, 
                                                                            "description": query_info.description,
                                                                            "param_types": query_info.param_types,
                                                                            "custom_query": True}])
        if res:
            results.append(res)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register document")

    return results

@app.post("/{graphname}/upsert_docs")
def upsert_query(graphname, request_data: Union[QueryUperstRequest, List[QueryUperstRequest]], credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    try:
        results = []

        if not isinstance(request_data, list):
            request_data = [request_data]

        for request_info in request_data:
            id = request_info.id
            query_info = request_info.query_info

            if not id and not query_info:
                raise HTTPException(status_code=400, detail="At least one of 'id' or 'query_info' is required")
            
            logger.debug(f"/{graphname}/upsertcustomquery request_id={req_id_cv.get()} upserting document")

            vec = embedding_service.embed_query(query_info.docstring)
            res = embedding_store.upsert_embeddings(id, [(query_info.docstring, vec)], [{"function_header": query_info.function_header, 
                                                                                        "description": query_info.description,
                                                                                        "param_types": query_info.param_types,
                                                                                        "custom_query": True}])
            if res:
                results.append(res)
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upsert document")
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while upserting query {str(e)}")
    
@app.post("/{graphname}/delete_docs")
def delete_query(graphname, request_data: QueryDeleteRequest, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    ids = request_data.ids
    expr = request_data.expr
    
    if ids and not isinstance(ids, list):
        try:
            ids = [ids]
        except ValueError:
            raise ValueError("Invalid ID format. IDs must be string or lists of strings.")

    logger.debug(f"/{graphname}/deletecustomquery request_id={req_id_cv.get()} deleting {ids}")
    
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
    # TODO: Better polishing of this response
    logger.debug_pii(f"/{graphname}/retrievedocs request_id={req_id_cv.get()} top_k={top_k} question={query.query}")
    tmp = str(embedding_store.retrieve_similar(embedding_service.embed_query(query.query), top_k=top_k))
    return tmp
@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, conn: TigerGraphConnection = Depends(get_db_connection)) -> CoPilotResponse:
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
    else:
        logger.error(f"/{graphname}/query request_id={req_id_cv.get()} agent creation failed due to invalid llm_service")
        raise Exception("LLM Completion Service Not Supported")

    resp = CoPilotResponse
    resp.response_type = "inquiryai"

    try:
        steps = agent.question_for_agent(query.query)
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} agent executed")
        try:
            generate_func_output = steps["intermediate_steps"][-1][-1]
            if "action_input" in steps["output"]:
                resp.natural_language_response = generate_func_output["action_input"]
            else:
                resp.natural_language_response = steps["output"]
            resp.natural_language_response = steps["output"]
            resp.query_sources = {"function_call": generate_func_output["function_call"],
                                "result": json.loads(generate_func_output["result"]),
                                "reasoning": generate_func_output["reasoning"]}
            resp.answered_question = True
        except Exception as e:
            resp.natural_language_response = steps["output"]
            resp.query_sources = {"agent_history": str(steps)}
            resp.answered_question = False
            logger.warning(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
    except MapQuestionToSchemaException as e:
        resp.natural_language_response = ""
        resp.query_sources = {}
        resp.answered_question = False
        logger.warning(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to MapQuestionToSchemaException")
    except Exception as e:
        resp.natural_language_response = ""
        resp.query_sources = {}
        resp.answered_question = False
        logger.warning(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
    return resp

@app.post("/{graphname}/login")
def login(graphname, conn: TigerGraphConnection = Depends(get_db_connection)):
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
        res = retrieve_answer(graphname, NaturalLanguageQuery(query=data), session.db_conn)
        await websocket.send_text(f"{res.natural_language_response}")

@app.get("/health")
def health():
    return {"status": "healthy",
            "llm_completion_model": llm_config["completion_service"]["llm_model"],
            "embedding_service": llm_config["embedding_service"]["embedding_model_service"]}


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('app/static/favicon.ico')

@app.post("/{graphname}/supportai/initialize")
def initialize(graphname, conn: TigerGraphConnection = Depends(get_db_connection)):
    # need to open the file using the absolute path
    abs_path = os.path.abspath(__file__)
    file_path = os.path.join(os.path.dirname(abs_path), "./gsql/supportai/SupportAI_Schema.gsql")
    with open(file_path, "r") as f:
        schema = f.read()
    res = conn.gsql("""USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_schema""".format(graphname, schema))
    return {"status": json.dumps(res)}

@app.post("/{graphname}/supportai/batch_ingest")
async def batch_ingest(graphname, doc_source:Union[S3BatchDocumentIngest, BatchDocumentIngest], background_tasks: BackgroundTasks, conn: TigerGraphConnection = Depends(get_db_connection)):
    req_id = req_id_cv.get()
    status_manager.create_status(conn.username, req_id, graphname)
    ingestion = BatchIngestion(embedding_service, get_llm_service(llm_config), conn, status_manager.get_status(req_id))
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
def create_vdb(graphname, config: CreateVectorIndexConfig, conn: TigerGraphConnection = Depends(get_db_connection)):
    if conn.getVertexCount("HNSWEntrypoint", where='id=="{}"'.format(config.index_name)) == 0:
        res = conn.runInstalledQuery("HNSW_CreateEntrypoint", {"index_name": config.index_name})
    res = conn.runInstalledQuery("HNSW_BuildIndex", {"index_name": config.index_name,
                                                     "v_types": config.vertex_types,
                                                     "M": config.M,
                                                     "ef_construction": config.ef_construction})
    return res

@app.get("/{graphname}/supportai/deletevdb/{index_name}")
def delete_vdb(graphname, index_name, conn: TigerGraphConnection = Depends(get_db_connection)):
    res = conn.runInstalledQuery("HNSW_DeleteIndex", {"index_name": index_name})
    return res
    
@app.post("/{graphname}/supportai/queryvdb/{index_name}")
def query_vdb(graphname, index_name, query: SupportAIQuestion, conn: TigerGraphConnection = Depends(get_db_connection)):
    retriever = HNSWRetriever(embedding_service, get_llm_service(llm_config), conn)
    res = retriever.search(query.question, index_name, query.method_params["top_k"], query.method_params["withHyDE"])
    return res

@app.post("/{graphname}/supportai/search")
def search(graphname, query: SupportAIQuestion, conn: TigerGraphConnection = Depends(get_db_connection)):
    if query.method.lower() == "hnswoverlap":
        retriever = HNSWOverlapRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.search(query.question,
                               query.method_params["indicies"],
                               query.method_params["top_k"],
                               query.method_params["num_hops"],
                               query.method_params["num_seen_min"])
    elif query.method.lower() == "vdb":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.search(query.question,
                               query.method_params["index"],
                               query.method_params["top_k"],
                               query.method_params["withHyDE"])
    elif query.method.lower() == "sibling":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWSiblingRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.search(query.question,
                               query.method_params["index"],
                               query.method_params["top_k"],
                               query.method_params["lookback"],
                               query.method_params["lookahead"],
                               query.method_params["withHyDE"])
    elif query.method.lower() == "entityrelationship":
        retriever = EntityRelationshipRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.search(query.question, query.method_params["top_k"])

    return res

@app.post("/{graphname}/supportai/answerquestion")
def answer_question(graphname, query: SupportAIQuestion, conn: TigerGraphConnection = Depends(get_db_connection)):
    resp = CoPilotResponse
    resp.response_type = "supportai"
    if query.method.lower() == "hnswoverlap":
        retriever = HNSWOverlapRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.retrieve_answer(query.question,
                                        query.method_params["indices"],
                                        query.method_params["top_k"],
                                        query.method_params["num_hops"],
                                        query.method_params["num_seen_min"])
    elif query.method.lower() == "vdb":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.retrieve_answer(query.question,
                                        query.method_params["index"],
                                        query.method_params["top_k"],
                                        query.method_params["withHyDE"])
    elif query.method.lower() == "sibling":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWSiblingRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.retrieve_answer(query.question,
                               query.method_params["index"],
                               query.method_params["top_k"],
                               query.method_params["lookback"],
                               query.method_params["lookahead"],
                               query.method_params["withHyDE"])
    elif query.method.lower() == "entityrelationship":
        retriever = EntityRelationshipRetriever(embedding_service, get_llm_service(llm_config), conn)
        res = retriever.retrieve_answer(query.question, query.method_params["top_k"])
    else:
        raise Exception("Method not implemented")
    
    resp.natural_language_response = res["response"]
    resp.query_sources = res["retrieved"]

    return res

@app.get("/{graphname}/supportai/buildconcepts")
def build_concepts(graphname, conn: TigerGraphConnection = Depends(get_db_connection)):
    rels_concepts = RelationshipConceptCreator(conn, llm_config, embedding_service)
    rels_concepts.create_concepts()
    ents_concepts = EntityConceptCreator(conn, llm_config, embedding_service)
    ents_concepts.create_concepts()
    comm_concepts = CommunityConceptCreator(conn, llm_config, embedding_service)
    comm_concepts.create_concepts()
    high_level_concepts = HigherLevelConceptCreator(conn, llm_config, embedding_service)
    high_level_concepts.create_concepts()
    return {"status": "success"}
