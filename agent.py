from langchain.agents import AgentType, initialize_agent

from tools import ExecuteFunction, GenerateFunction, MapQuestionToSchema
from embedding_utils.embedding_services import EmbeddingModel
from embedding_utils.embedding_stores import EmbeddingStore

from llm_services.base_llm import LLM_Model

class TigerGraphAgent():
    def __init__(self, llm_provider: LLM_Model, db_connection: "TigerGraphConnection", embedding_model: EmbeddingModel, embedding_store:EmbeddingStore):
        self.conn = db_connection

        self.llm = llm_provider

        tools = [MapQuestionToSchema(self.conn, self.llm.model, self.llm.map_question_schema_prompt),
                 GenerateFunction(self.conn, self.llm.model, self.llm.generate_function_prompt, embedding_model, embedding_store),
                 ExecuteFunction(self.conn)]

        self.agent = initialize_agent(tools,
                                      self.llm.model,
                                      agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                                      verbose=True,
                                      return_intermediate_steps=True,
                                      max_iterations=4,
                                      early_stopping_method="generate",
                                      agent_kwargs={
                                        "prefix": """DIRECTLY TRANSFER THE OBSERVATION INTO ACTION INPUTS AS NECESSARY.
                                                     BE VERBOSE IN ACTION INPUTS AND THOUGHTS. NEVER CALL MULTIPLE FUNCTIONS.
                                                     ALWAYS DIRECTLY PASS THE OUTPUT OF GenerateFunction AS INPUT TO ExecuteFunction.
                                                     NEVER HALLUCINATE FUNCTION CALLS, MY JOB DEPENDS ON CORRECT ANSWERS."""
                                      })

    def question_for_agent(self, question) -> str:
        try:
            return self.agent({"input": question})
        except Exception as e:
            return "Error occured with message: "+str(type(e).__name__) + " - " + str(e)