from typing import Union, Annotated
from fastapi import FastAPI, Header, Depends, HTTPException, status
from pydantic import BaseModel

from pyTigerGraph import TigerGraphConnection
import json

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from agent import TigerGraphAgent

from llm_services import OpenAI_Davinci, AzureOpenAI_GPT35_Turbo

class NaturalLanguageQuery(BaseModel):
    query:str


with open("./openai_llm_config.json", "r") as f:
    llm_config = json.load(f)

app = FastAPI()

security = HTTPBasic()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
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

    agent = TigerGraphAgent(OpenAI_Davinci(llm_config), conn)

    return agent.question_for_agent(query.query)