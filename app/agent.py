from langchain.agents import AgentType, initialize_agent
from typing import List, Union

from tools import GenerateFunction, MapQuestionToSchema
from embedding_utils.embedding_services import EmbeddingModel
from embedding_utils.embedding_stores import EmbeddingStore

from llm_services.base_llm import LLM_Model

class TigerGraphAgent():
    def __init__(self, llm_provider: LLM_Model, db_connection: "TigerGraphConnection", embedding_model: EmbeddingModel, embedding_store:EmbeddingStore):
        self.conn = db_connection

        self.llm = llm_provider

        self.mq2s = MapQuestionToSchema(self.conn, self.llm.model, self.llm.map_question_schema_prompt)
        self.gen_func = GenerateFunction(self.conn, self.llm.model, self.llm.generate_function_prompt, embedding_model, embedding_store)

        tools = [self.mq2s, self.gen_func]
        
        
        self.agent = initialize_agent(tools,
                                      self.llm.model,
                                      agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                                      verbose=True,
                                      return_intermediate_steps=True,
                                      #max_iterations=7,
                                      early_stopping_method="generate",
                                      handle_parsing_errors=True,
                                      agent_kwargs={
                                        "prefix": """DIRECTLY TRANSFER THE OBSERVATION INTO ACTION INPUTS AS NECESSARY.
                                                     BE VERBOSE IN ACTION INPUTS AND THOUGHTS.
                                                     NEVER HALLUCINATE FUNCTION CALLS, MY JOB DEPENDS ON CORRECT ANSWERS.
                                                     ALWAYS USE THE MapQuestionToSchema TOOL BEFORE GenerateFunction.'"""
                                      })

    def question_for_agent(self, question):
        try:
            resp = self.agent({"input": question})
            return resp
        except Exception as e:
            raise e