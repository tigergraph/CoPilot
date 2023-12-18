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
    """TigerGraph Agent Class
    
    The TigerGraph Agent Class combines the various dependencies needed for a AI Agent to reason with data in a TigerGraph database.

    Args:
        llm_provider (LLM_Model):
            a LLM_Model class that connects to an external LLM API service.
        db_connection (TigerGraphConnection):
            a PyTigerGraph TigerGraphConnection object instantiated to interact with the desired database/graph and authenticated with correct roles.
        embedding_model (EmbeddingModel):
            a EmbeddingModel class that connects to an external embedding API service.
        embedding_store (EmbeddingStore):
            a EmbeddingStore class that connects to an embedding store to retrieve pyTigerGraph and custom query documentation from.
    """
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

    def question_for_agent(self, question: str):
        """Question for Agent.

        Ask the agent a question to be answered by the database. Returns the agent resoposne or raises an exception.

        Args:
            question (str): 
                The question to ask the agent
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY question_for_agent")
        logger.debug_pii(f"request_id={req_id_cv.get()} question_for_agent question={question}")
        try:
            resp = self.agent({"input": question})
            logger.info(f"request_id={req_id_cv.get()} EXIT question_for_agent")
            return resp
        except Exception as e:
            logger.error(f"request_id={req_id_cv.get()} FAILURE question_for_agent")
            raise e