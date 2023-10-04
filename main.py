from typing import Union, Annotated, List, Dict
from fastapi import FastAPI, Header, Depends, HTTPException, status
from pydantic import BaseModel

from pyTigerGraph import TigerGraphConnection
import json

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from agent import TigerGraphAgent

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

with open("./azure_llm_config.json", "r") as f:
    llm_config = json.load(f)

app = FastAPI()

security = HTTPBasic()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/{graphname}/register-custom-query")
def register_query(graphname, query_info: GSQLQueryInfo, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    return query_info


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

    if llm_config["llm_service"] == "OpenAI_Davinci":
        from llm_services import OpenAI_Davinci
        agent = TigerGraphAgent(OpenAI_Davinci(llm_config), conn)
    elif llm_config["llm_service"] == "AzureOpenAI_GPT35_Turbo":
        from llm_services import AzureOpenAI_GPT35_Turbo
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