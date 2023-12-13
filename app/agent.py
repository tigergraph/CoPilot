from langchain.agents import AgentType, initialize_agent
from typing import List, Union
import logging

from app.tools import GenerateFunction, MapQuestionToSchema
from app.embedding_utils.embedding_services import EmbeddingModel
from app.embedding_utils.embedding_stores import EmbeddingStore

from app.llm_services.base_llm import LLM_Model

from app.log import req_id_cv

logger = logging.getLogger(__name__)

class TigerGraphAgent():
    def __init__(self, llm_provider: LLM_Model, db_connection: "TigerGraphConnection", embedding_model: EmbeddingModel, embedding_store:EmbeddingStore):
        self.conn = db_connection

        self.llm = llm_provider

        self.mq2s = MapQuestionToSchema(self.conn, self.llm.model, self.llm.map_question_schema_prompt)
        self.gen_func = GenerateFunction(self.conn, self.llm.model, self.llm.generate_function_prompt, embedding_model, embedding_store)

        tools = [self.mq2s, self.gen_func]
        logger.debug(f"request_id={req_id_cv.get()} agent tools created")
        self.agent = initialize_agent(tools,
                                      self.llm.model,
                                      agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                                      verbose=False,
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
        logger.debug(f"request_id={req_id_cv.get()} agent initialized")

    def question_for_agent(self, question):
        logger.info(f"request_id={req_id_cv.get()} ENTRY question_for_agent")
        logger.debug_pii(f"request_id={req_id_cv.get()} question_for_agent question={question}")
        try:
            resp = self.agent({"input": question})
            logger.info(f"request_id={req_id_cv.get()} EXIT question_for_agent")
            return resp
        except Exception as e:
            logger.error(f"request_id={req_id_cv.get()} FAILURE question_for_agent")
            raise e