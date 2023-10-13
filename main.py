from typing import Union, Annotated, List, Dict
from fastapi import FastAPI, Header, Depends, HTTPException, status
from pydantic import BaseModel

from pyTigerGraph import TigerGraphConnection
import json

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from agent import TigerGraphAgent
from llm_services import OpenAI_Davinci, AzureOpenAI_GPT35_Turbo
from embedding_services import AzureOpenAI_Ada002, OpenAI_Embedding
from embedding_stores import FAISS_EmbeddingStore

from tools import MapQuestionToSchemaException

class NaturalLanguageQuery(BaseModel):
    query:str

class GSQLQueryInfo(BaseModel):
    query_name: str
    query_description: str
    heavy_runtime_warning: bool = False

class NaturalLanguageQueryResponse(BaseModel):
    natural_language_response: str
    query_sources: List[Dict] = None

with open("./openai_llm_config.json", "r") as f:
    llm_config = json.load(f)

app = FastAPI()

security = HTTPBasic()

if llm_config["llm_service"] == "OpenAI":
    embedding_service = OpenAI_Embedding(llm_config)
elif llm_config["llm_service"] == "Azure":
    embedding_service = AzureOpenAI_Ada002(llm_config)

'''
embedding_store = FAISS_EmbeddingStore()
'''

@app.get("/")
def read_root():
    return {"Hello": "World"}

'''
@app.post("/{graphname}/register-custom-query")
def register_query(graphname, query_info: GSQLQueryInfo, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    vec = embedding_service.embed_doc(query_info.query_description)[0]
    res = embedding_store.add_embeddings([(query_info.query_description, vec)], [{"name": query_info.query_name, "heavy_runtime": query_info.heavy_runtime_warning}])
    return res
'''

@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> NaturalLanguageQueryResponse:
    with open("./db_config.json", "r") as config_file:
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

    if llm_config["llm_service"] == "OpenAI":
        agent = TigerGraphAgent(OpenAI_Davinci(llm_config), conn)
    elif llm_config["llm_service"] == "Azure":
        agent = TigerGraphAgent(AzureOpenAI_GPT35_Turbo(llm_config), conn)

    resp = NaturalLanguageQueryResponse

    try:
        steps = agent.question_for_agent(query.query)

        query_sources = [{x[0].tool_input:x[-1]} for x in steps["intermediate_steps"] if x[0].tool=="ExecuteFunction"]

        resp.natural_language_response = steps["output"]
        resp.query_sources = query_sources
    except MapQuestionToSchemaException as e:
        resp.natural_language_response = str(e)

    return resp