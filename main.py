from typing import Union, Annotated, List, Dict
from fastapi import FastAPI, Header, Depends, HTTPException, status
import os
from pyTigerGraph import TigerGraphConnection
import json

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from agent import TigerGraphAgent
from llm_services import OpenAI, AzureOpenAI, AWS_SageMaker_Endpoint
from embedding_utils.embedding_services import AzureOpenAI_Ada002, OpenAI_Embedding
from embedding_utils.embedding_stores import FAISS_EmbeddingStore

from tools import MapQuestionToSchemaException
from schemas.schemas import NaturalLanguageQuery, NaturalLanguageQueryResponse, GSQLQueryInfo

LLM_SERVICE = os.getenv("LLM_CONFIG")

with open(LLM_SERVICE, "r") as f:
    llm_config = json.load(f)

app = FastAPI()

security = HTTPBasic()

if llm_config["embedding_service"]["embedding_model_service"].lower() == "openai":
    embedding_service = OpenAI_Embedding(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "azure":
    embedding_service = AzureOpenAI_Ada002(llm_config["embedding_service"])


embedding_store = FAISS_EmbeddingStore(embedding_service)


@app.get("/")
def read_root():
    return {"config": llm_config}


@app.post("/{graphname}/register-custom-query")
def register_query(graphname, query_info: GSQLQueryInfo, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    vec = embedding_service.embed_documents(query_info.query_description)[0]
    res = embedding_store.add_embeddings([(query_info.query_description, vec)], [{"name": query_info.query_name, "heavy_runtime": query_info.heavy_runtime_warning}])
    return res

@app.post("/{graphname}/retrieve-docs")
def retrieve_docs(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    return str(embedding_store.retrieve_similar(embedding_service.embed_query(query.query), top_k=2))


@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> NaturalLanguageQueryResponse:
    with open("./configs/db_config.json", "r") as config_file:
        config = json.load(config_file)
        
    conn = TigerGraphConnection(
        host=config["hostname"],
        username = credentials.username,
        password = credentials.password,
        graphname = graphname,
    )

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

    conn.customizeHeader(timeout=config["default_timeout"]*1000)

    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        agent = TigerGraphAgent(OpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        agent = TigerGraphAgent(AzureOpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        agent = TigerGraphAgent(AWS_SageMaker_Endpoint(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    else:
        raise Exception("LLM Completion Service Not Supported")

    resp = NaturalLanguageQueryResponse

    try:
        steps = agent.question_for_agent(query.query)

        query_sources = [{x[0].tool_input:x[-1]} for x in steps["intermediate_steps"] if x[0].tool=="ExecuteFunction"]

        resp.natural_language_response = steps["output"]
        resp.query_sources = query_sources
    except MapQuestionToSchemaException as e:
        resp.natural_language_response = str(e)
        resp.query_sources = None
    except Exception as e:
        resp.natural_language_response = str(e)
        resp.query_sources = None
    return resp