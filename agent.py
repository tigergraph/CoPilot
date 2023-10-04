from langchain.agents import AgentType, initialize_agent, load_tools

from langchain.llms import AzureOpenAI
from langchain.prompts import PromptTemplate
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from typing import Optional, Type

from tools import MapQuestionToSchema, GenerateFunction, ExecuteFunction

from llm_services import LLM_Model

class TigerGraphAgent():
    def __init__(self, llm_provider: LLM_Model, db_connection: "TigerGraphConnection"):
        self.conn = db_connection

        self.llm = llm_provider

        tools = [MapQuestionToSchema(self.conn, self.llm.model, self.llm.map_question_schema_prompt),
                 GenerateFunction(self.conn, self.llm.model, self.llm.generate_function_prompt),
                 ExecuteFunction(self.conn)]

        self.agent = initialize_agent(tools, self.llm.model, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True, return_intermediate_steps=True)

    def question_for_agent(self, question) -> str:
        return self.agent({"input": question})