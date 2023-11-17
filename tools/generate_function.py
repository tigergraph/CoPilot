from langchain.tools import BaseTool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pyTigerGraph import TigerGraphConnection
from langchain.pydantic_v1 import BaseModel, Field, validator
from schemas import MapQuestionToSchemaResponse
from typing import List, Dict, Type, Optional
from embedding_utils.embedding_services import EmbeddingModel
from embedding_utils.embedding_stores import EmbeddingStore
from .validate_against_schema import validate_schema, MapQuestionToSchemaException
import json

class GenerateFunction(BaseTool):
    name = "GenerateFunction"
    description = "Generates and executes a function call on the database. Always use MapQuestionToSchema before this tool."
    conn: "TigerGraphConnection" = None
    llm: LLM = None
    prompt: str = None
    handle_tool_error: bool =True
    embedding_model: EmbeddingModel = None
    embedding_store: EmbeddingStore = None
    args_schema: Type[MapQuestionToSchemaResponse] = MapQuestionToSchemaResponse
    
    def __init__(self, conn, llm, prompt, embedding_model, embedding_store):
        super().__init__()
        self.conn = conn
        self.llm = llm
        self.prompt = prompt
        self.embedding_model = embedding_model
        self.embedding_store = embedding_store
    
    def _run(self, question: str,
                   target_vertex_types: List[str] = [],
                   target_vertex_attributes: Dict[str, List[str]] = {},
                   target_vertex_ids: Dict[str, List[str]] = {},
                   target_edge_types: List[str] = [],
                   target_edge_attributes: Dict[str, List[str]] = {}) -> str:

        PROMPT = PromptTemplate(
            template=self.prompt, input_variables=["question", "vertex_types", "edge_types", "vertex_attributes",
                                                   "vertex_ids", "edge_attributes", "doc1", "doc2", "doc3"]
        )

        try:
            validate_schema(self.conn,
                            target_vertex_types, 
                            target_edge_types,
                            target_vertex_attributes, 
                            target_edge_attributes)
        except MapQuestionToSchemaException as e:
            return e

        lookup_question = question + " "
        if target_vertex_types != []:
            lookup_question += "using vertices: "+str(target_vertex_types) + " "
        if target_edge_types != []:
            lookup_question += "using edges: "+str(target_edge_types)

        docs = self.embedding_store.retrieve_similar(self.embedding_model.embed_query(lookup_question), top_k=3)
        inputs = [{"question": question, 
                    "vertex_types": target_vertex_types, #self.conn.getVertexTypes(), 
                    "edge_types": target_edge_types, #self.conn.getEdgeTypes(), 
                    "vertex_attributes": target_vertex_attributes,
                    "vertex_ids": target_vertex_ids,
                    "edge_attributes": target_edge_attributes,
                    "doc1": docs[0].page_content,
                    "doc2": docs[1].page_content,
                    "doc3": docs[2].page_content
                  }]

        chain = LLMChain(llm=self.llm, prompt=PROMPT)
        generated = chain.apply(inputs)[0]["text"]

        #TODO: Check if the generated function is within the function/installed query library to prevent prompt injection hacking.


        try:
            loc = {}
            exec("res = conn."+generated, {"conn": self.conn}, loc)
            return "Function {} produced the result {}".format(generated, json.dumps(loc["res"]))
        except Exception as e:
            print(e)
            raise ToolException("The function {} did not execute correctly. Please rephrase your question and try again".format(generated))


    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    def _handle_error(error:ToolException) -> str:
        return  "The following errors occurred during tool execution:" + error.args[0]+ "Please make sure the question is mapped to the schema correctly"