from langchain.tools import BaseTool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pyTigerGraph import TigerGraphConnection
from langchain.pydantic_v1 import BaseModel, Field, validator
from app.schemas import MapQuestionToSchemaResponse
from typing import List, Dict
from .validation_utils import validate_schema, MapQuestionToSchemaException
import re
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)


class MapQuestionToSchema(BaseTool):
    """ MapQuestionToSchema Tool.
        Tool to map questions to their datatypes in the database. Should be exectued before GenerateFunction.
    """
    name = "MapQuestionToSchema"
    description = "Always run first to map the query to the graph's schema. NEVER EXECUTE GenerateFunction before using MapQuestionToSchema"
    conn: "TigerGraphConnection" = None
    llm: LLM = None
    prompt: str = None
    handle_tool_error: bool = True
    
    def __init__(self, conn, llm, prompt):
        """ Initialize MapQuestionToSchema.
            Args:
                conn (TigerGraphConnection):
                    pyTigerGraph TigerGraphConnection connection to the database.
                llm (LLM_Model):
                    LLM_Model class to interact with an external LLM API.
                prompt (str):
                    prompt to use with the LLM_Model. Varies depending on LLM service.
        """
        super().__init__()
        logger.debug(f"request_id={req_id_cv.get()} MapQuestionToSchema instantiated")
        self.conn = conn
        self.llm = llm
        self.prompt = prompt
        
    def _run(self, query: str) -> str:
        """ Run the tool.
            Args:
                query (str):
                    The user's question.
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY MapQuestionToSchema._run()")
        parser = PydanticOutputParser(pydantic_object=MapQuestionToSchemaResponse)

        RESTATE_QUESTION_PROMPT = PromptTemplate(
            template=self.prompt,
            input_variables=["question", "vertices", "edges"],
            partial_variables = {"format_instructions": parser.get_format_instructions()}
        )
        restate_chain = LLMChain(llm=self.llm, prompt=RESTATE_QUESTION_PROMPT)
        
        restate_q = restate_chain.apply([{"vertices": self.conn.getVertexTypes(),
                                          "question": query,
                                          "edges": self.conn.getEdgeTypes()}])[0]["text"]

        logger.debug(f"request_id={req_id_cv.get()} MapQuestionToSchema applied")
        
        parsed_q = parser.invoke(restate_q)

        logger.debug_pii(f"request_id={req_id_cv.get()} MapQuestionToSchema parsed for question={query} into normalized_form={parsed_q}")

        try:
            validate_schema(self.conn,
                            parsed_q.target_vertex_types, 
                            parsed_q.target_edge_types,
                            parsed_q.target_vertex_attributes, 
                            parsed_q.target_edge_attributes)
        except MapQuestionToSchemaException as e:
            logger.warn(f"request_id={req_id_cv.get()} WARN MapQuestionToSchema to validate schema")
            raise e
        logger.info(f"request_id={req_id_cv.get()} EXIT MapQuestionToSchema._run()")
        return parsed_q
    
    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    #def _handle_error(self, error:MapQuestionToSchemaException) -> str:
    #    return  "The following errors occurred during tool execution:" + error.args[0]+ "Please make sure to map the question to the schema"