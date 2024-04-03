from langchain.tools import BaseTool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.pydantic_v1 import BaseModel, Field, validator
from app.metrics.tg_proxy import TigerGraphConnectionProxy
from app.py_schemas import MapQuestionToSchemaResponse, MapAttributeToAttributeResponse
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
    description = "Always run first to map the query to the graph's schema. GenerateFunction before using MapQuestionToSchema"
    conn: "TigerGraphConnectionProxy" = None
    llm: LLM = None
    prompt: str = None
    handle_tool_error: bool = True
    
    def __init__(self, conn, llm, prompt):
        """ Initialize MapQuestionToSchema.
            Args:
                conn (TigerGraphConnectionProxy):
                    pyTigerGraph TigerGraphConnection connection to the database; this is a proxy which includes metrics gathering.
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
            input_variables=["question", "vertices", "verticesAttrs", "edges", "edgesInfo"],
            partial_variables = {"format_instructions": parser.get_format_instructions()}
        )

        restate_chain = LLMChain(llm=self.llm, prompt=RESTATE_QUESTION_PROMPT)

        vertices = self.conn.getVertexTypes()
        edges = self.conn.getEdgeTypes()
        
        vertices_info = []
        for vertex in vertices: 
            vertex_attrs = self.conn.getVertexAttrs(vertex)
            vertex_info = {"vertex": vertex,
                           "attributes": vertex_attrs}
            vertices_info.append(vertex_info)
        
        edges_info = []
        for edge in edges:
            source_vertex = self.conn.getEdgeSourceVertexType(edge)
            target_vertex = self.conn.getEdgeTargetVertexType(edge)
            edge_info = {"edge": edge,
                         "source": source_vertex,
                         "target": target_vertex}
            edges_info.append(edge_info)

        restate_q = restate_chain.apply([{"vertices": vertices,
                                          "verticesAttrs": vertices_info,
                                          "edges": edges,
                                          "edgesInfo": edges_info,
                                          "question": query}])[0]["text"]

        logger.debug(f"request_id={req_id_cv.get()} MapQuestionToSchema applied")
        
        parsed_q = parser.invoke(restate_q)

        logger.debug_pii(f"request_id={req_id_cv.get()} MapQuestionToSchema parsed for question={query} into normalized_form={parsed_q}")

        attr_prompt = """For the following source attributes: {parsed_attrs}, map them to the corresponding output attribute in this list: {real_attrs}.
                         Format the response way explained below:
                        {format_instructions}"""

        attr_parser = PydanticOutputParser(pydantic_object=MapAttributeToAttributeResponse)

        ATTR_MAP_PROMPT = PromptTemplate(
            template = attr_prompt,
            input_variables=["parsed_attrs", "real_attrs"],
            partial_variables = {"format_instructions": attr_parser.get_format_instructions()}
        )

        attr_map_chain = LLMChain(llm=self.llm, prompt=ATTR_MAP_PROMPT)
        for vertex in parsed_q.target_vertex_attributes.keys():
            map_attr = attr_map_chain.apply([{"parsed_attrs": parsed_q.target_vertex_attributes[vertex], "real_attrs": self.conn.getVertexAttrs(vertex)}])[0]["text"]
            parsed_map = attr_parser.invoke(map_attr).attr_map
            parsed_q.target_vertex_attributes[vertex] = [parsed_map[x] for x in list(parsed_q.target_vertex_attributes[vertex])]

        logger.debug(f"request_id={req_id_cv.get()} MapVertexAttributes applied")

        for edge in parsed_q.target_edge_attributes.keys():
            map_attr = attr_map_chain.apply([{"parsed_attrs": parsed_q.target_edge_attributes[edge], "real_attrs": self.conn.getEdgeAttrs(edge)}])[0]["text"]
            parsed_map = attr_parser.invoke(map_attr).attr_map
            parsed_q.target_edge_attributes[edge] = [parsed_map[x] for x in list(parsed_q.target_edge_attributes[edge])]

        logger.debug(f"request_id={req_id_cv.get()} MapEdgeAttributes applied")

        try:
            validate_schema(self.conn,
                            parsed_q.target_vertex_types, 
                            parsed_q.target_edge_types,
                            parsed_q.target_vertex_attributes, 
                            parsed_q.target_edge_attributes)
        except MapQuestionToSchemaException as e:
            logger.warning(f"request_id={req_id_cv.get()} WARN MapQuestionToSchema to validate schema")
            raise e
        logger.info(f"request_id={req_id_cv.get()} EXIT MapQuestionToSchema._run()")
        return parsed_q
    
    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    #def _handle_error(self, error:MapQuestionToSchemaException) -> str:
    #    return  "The following errors occurred during tool execution:" + error.args[0]+ "Please make sure to map the question to the schema"