from langchain.tools import BaseTool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains.graph_qa.cypher import GraphCypherQAChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pyTigerGraph import TigerGraphConnection
from langchain.pydantic_v1 import BaseModel, Field, validator
from app.schemas import MapQuestionToSchemaResponse
from typing import List, Dict, Type, Optional, Union
from app.embedding_utils.embedding_services import EmbeddingModel
from app.embedding_utils.embedding_stores import EmbeddingStore
from .validation_utils import validate_schema, validate_function_call, MapQuestionToSchemaException, InvalidFunctionCallException
import json
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class GenerateFunction(BaseTool):
    """ GenerateCypher Tool.
        Tool to generate and execute Cypher pattern matching queries against the database. Only use if GenerateFunction has failed.
    """
    name = "GenerateCypher"
    description = "Tool to generate and execute Cypher pattern matching queries against the database. Only use if GenerateFunction has failed."
    conn: "TigerGraphConnection" = None
    llm: LLM = None
    prompt: str = None
    handle_tool_error: bool =True
    embedding_model: EmbeddingModel = None
    embedding_store: EmbeddingStore = None
    args_schema: Type[MapQuestionToSchemaResponse] = MapQuestionToSchemaResponse
    
    def __init__(self, conn, llm, prompt):
        """ Initialize GenerateFunction.
            Args:
                conn (TigerGraphConnection):
                    pyTigerGraph TigerGraphConnection connection to the appropriate database/graph with correct permissions
                llm (LLM_Model):
                    LLM_Model class to interact with an external LLM API.
                prompt (str):
                    prompt to use with the LLM_Model. Varies depending on LLM service.
        """
        super().__init__()
        logger.debug(f"request_id={req_id_cv.get()} GenerateCypher instantiated")
        self.conn = conn
        self.llm = llm
        self.prompt = prompt
    
    def _run(self, question: str,
                   target_vertex_types: List[str] = [],
                   target_vertex_attributes: Dict[str, List[str]] = {},
                   target_vertex_ids: Dict[str, List[str]] = {},
                   target_edge_types: List[str] = [],
                   target_edge_attributes: Dict[str, List[str]] = {}) -> str:
        """ Run the tool.
            Args:
                question (str):
                    The question to answer with the database.
                target_vertex_types (List[str]):
                    The list of vertex types the question mentions.
                target_vertex_attributes (Dict[str, List[str]]):
                    The dictionary of vertex attributes the question mentions, in the form {"vertex_type": ["attr1", "attr2"]}
                target_vertex_ids (Dict[str, List[str]):
                    The dictionary of vertex ids the question mentions, in the form of {"vertex_type": ["v_id1", "v_id2"]}
                target_edge_types (List[str]):
                    The list of edge types the question mentions.
                target_edge_attributes (Dict[str, List[str]]):
                    The dictionary of edge attributes the question mentions, in the form {"edge_type": ["attr1", "attr2"]}
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY GenerateCypher._run()")
        PROMPT = PromptTemplate(
            template=self.prompt, input_variables=["question", "vertex_types", "edge_types", "vertex_attributes",
                                                   "vertex_ids", "edge_attributes", "doc1", "doc2", "doc3"]
        )

        if target_vertex_types == [] and target_edge_types == []:
            return "No vertex or edge types recognized. MapQuestionToSchema and then try again."

        try:
            validate_schema(self.conn,
                            target_vertex_types, 
                            target_edge_types,
                            target_vertex_attributes, 
                            target_edge_attributes)
        except MapQuestionToSchemaException as e:
            logger.warn(f"request_id={req_id_cv.get()} WARN input schema not valid")
            return e

        inputs = [{"question": question, 
                    "vertex_types": target_vertex_types, #self.conn.getVertexTypes(), 
                    "edge_types": target_edge_types, #self.conn.getEdgeTypes(), 
                    "vertex_attributes": target_vertex_attributes,
                    "vertex_ids": target_vertex_ids,
                    "edge_attributes": target_edge_attributes,
                  }]

        chain = GraphCypherQAChain(llm=self.llm, prompt=PROMPT)
        generated = chain.apply(inputs)[0]["text"]
        logger.debug(f"request_id={req_id_cv.get()} generated Cypher Call")

        try:
            generated = generated # TODO: Replace with validate_cypher call
        except InvalidFunctionCallException as e: # TODO: Replace with valid exception
            logger.warn(f"request_id={req_id_cv.get()} EXIT GenerateCypher._run() with exception={e}")
            return e

        generated = """runInterpretedQuery('INTERPRET OPENCYPHER QUERY () FOR GRAPH """+self.conn.graphname+"""{"""+generated+"""}')"""

        try:
            loc = {}
            exec("res = conn."+generated, {"conn": self.conn}, loc)
            logger.info(f"request_id={req_id_cv.get()} EXIT GenerateCypher._run()")
            return "Function {} produced the result {}".format(generated, json.dumps(loc["res"]))
        except Exception as e:
            logger.warn(f"request_id={req_id_cv.get()} EXIT GenerateCypher._run() with exception={e}")
            raise ToolException("The function {} did not execute correctly. Please rephrase your question and try again".format(generated))


    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    #def _handle_error(error:Union[ToolException, MapQuestionToSchemaException]) -> str:
    #    return  "The following errors occurred during tool execution:" + error.args[0]+ "Please make sure the question is mapped to the schema correctly"