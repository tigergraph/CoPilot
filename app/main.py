from typing import Union, Annotated, List, Dict
from fastapi import FastAPI, Header, Depends, HTTPException, status, Request, WebSocket
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import os
from pyTigerGraph import TigerGraphConnection
import json
import time
import uuid
import logging
from app.session import SessionHandler

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.agent import TigerGraphAgent
from app.llm_services import OpenAI, AzureOpenAI, AWS_SageMaker_Endpoint, GoogleVertexAI
from app.embedding_utils.embedding_services import AzureOpenAI_Ada002, OpenAI_Embedding, VertexAI_PaLM_Embedding
from app.embedding_utils.embedding_stores import FAISS_EmbeddingStore

from app.tools import MapQuestionToSchemaException
from app.py_schemas.schemas import NaturalLanguageQuery, NaturalLanguageQueryResponse, GSQLQueryInfo, BatchDocumentIngest, S3BatchDocumentIngest
from app.log import req_id_cv

LLM_SERVICE = os.getenv("LLM_CONFIG")
DB_CONFIG = os.getenv("DB_CONFIG")

with open(LLM_SERVICE, "r") as f:
    llm_config = json.load(f)

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

logger = logging.getLogger(__name__)

if llm_config["embedding_service"]["embedding_model_service"].lower() == "openai":
    embedding_service = OpenAI_Embedding(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "azure":
    embedding_service = AzureOpenAI_Ada002(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "vertexai":
    embedding_service = VertexAI_PaLM_Embedding(llm_config["embedding_service"])
else:
    raise Exception("Embedding service not implemented")


embedding_store = FAISS_EmbeddingStore(embedding_service)


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
    with open(DB_CONFIG, "r") as config_file:
        config = json.load(config_file)
        
    conn = TigerGraphConnection(
        host=config["hostname"],
        username = credentials.username,
        password = credentials.password,
        graphname = graphname,
    )

    if config["getToken"]:
        try:
            apiToken = conn._post(conn.restppUrl+"/requesttoken", authMode="pwd", data=str({"graph": conn.graphname}), resKey="results")["token"]
        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )

        conn = TigerGraphConnection(
            host=config["hostname"],
            username = credentials.username,
            password = credentials.password,
            graphname = graphname,
            apiToken = apiToken
        )

    return conn

@app.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@app.post("/{graphname}/registercustomquery")
def register_query(graphname, query_info: GSQLQueryInfo, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.debug(f"/{graphname}/registercustomquery request_id={req_id_cv.get()} registering {query_info.function_header}")
    vec = embedding_service.embed_query(query_info.docstring)
    res = embedding_store.add_embeddings([(query_info.docstring, vec)], [{"function_header": query_info.function_header, 
                                                                          "description": query_info.description,
                                                                          "param_types": query_info.param_types,
                                                                          "custom_query": True}])
    return res

# TODO: RUD of CRUD with custom queries

@app.post("/{graphname}/retrievedocs")
def retrieve_docs(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)], top_k:int = 3):
    # TODO: Better polishing of this response
    logger.debug_pii(f"/{graphname}/retrievedocs request_id={req_id_cv.get()} top_k={top_k} question={query.query}")
    tmp = str(embedding_store.retrieve_similar(embedding_service.embed_query(query.query), top_k=top_k))
    return tmp


@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, conn: TigerGraphConnection = Depends(get_db_connection)) -> NaturalLanguageQueryResponse:
    logger.debug_pii(f"/{graphname}/query request_id={req_id_cv.get()} question={query.query}")
    with open(DB_CONFIG, "r") as config_file:
        config = json.load(config_file)

    conn.customizeHeader(timeout=config["default_timeout"]*1000, responseSize=5000000)
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

    resp = NaturalLanguageQueryResponse

    try:
        steps = agent.question_for_agent(query.query)
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} agent executed")
        try:
            generate_func_output = steps["intermediate_steps"][-1][-1]
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
        logger.warn(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
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



@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('app/static/favicon.ico')

@app.get("/{graphname}/supportai/initialize")
def initialize(graphname, conn: TigerGraphConnection = Depends(get_db_connection)):
    with open("./gsql/supportai/SupportAI_Schema.gsql", "r") as f:
        schema = f.read()
    res = conn.gsql("""USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_schema""".format(graphname, schema))
    return {"status": res}

'''
@app.post("/{graphname}/supportai/batch_ingest")
def batch_ingest(graphname, doc_source:Union[S3BatchDocumentIngest, BatchDocumentIngest], conn: TigerGraphConnection = Depends(get_db_connection)):
    if doc_source.service.lower() == "s3":
        import boto3
        s3 = boto3.client('s3')
        # get the list of documents
        documents = []
        if doc_source.service_params["type"].lower() == "file":
            response = s3.get_object(Bucket=doc_source.service_params["bucket"], Key=doc_source.service_params["key"])
            documents = response['Body'].read().decode('utf-8').split("\n")
        elif doc_source.service_params["type"].lower() == "directory":
            response = s3.list_objects_v2(Bucket=doc_source.service_params["bucket"], Prefix=doc_source.service_params["key"])
            for obj in response.get('Contents', []):
                response = s3.get_object(Bucket=doc_source.service_params["bucket"], Key=obj['Key'])
                documents.append(response['Body'].read().decode('utf-8'))
    else:
        raise Exception("Document storage service not implemented")
    if doc_source.chunker.lower() == "regex":
        from app.chunkers.regex_chunker import RegexChunker
        chunker = RegexChunker(doc_source.chunker_params["pattern"])
    elif doc_source.chunker.lower() == "characters":
        from app.chunkers.character_chunker import CharacterChunker
        chunker = CharacterChunker(doc_source.chunker_params["chunk_size"], doc_source.chunker_params.get("overlap", 0))

    chunks = chunker(documents)
'''
