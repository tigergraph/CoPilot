from typing import Union
from fastapi import FastAPI, Header
from pydantic import BaseModel

from pyTigerGraph import TigerGraphConnection
import json

from agent import TigerGraphAgent

from llm_services import OpenAI_Davinci, AzureOpenAI_GPT35_Turbo

class NaturalLanguageQuery(BaseModel):
    query:str


with open("./openai_llm_config.json", "r") as f:
    llm_config = json.load(f)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, token: str = Header(default=None)):
    with open("./db_config.json", "r") as config_file:
        config = json.load(config_file)
        
    conn = TigerGraphConnection(
        host=config["hostname"],
        graphname = graphname
    )

    if token:
        conn.apiToken = token

    agent = TigerGraphAgent(OpenAI_Davinci(llm_config), conn)

    return agent.question_for_agent(query.query)