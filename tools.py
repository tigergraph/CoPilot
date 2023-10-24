from langchain.tools import BaseTool, StructuredTool, Tool, tool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from pyTigerGraph import TigerGraphConnection
from embedding_utils.embedding_services import EmbeddingModel
from embedding_utils.embedding_stores import EmbeddingStore
import re
import json

class MapQuestionToSchemaException(Exception):
    pass


class MapQuestionToSchema(BaseTool):
    name = "MapQuestionToSchema"
    description = "Always run first to map the query to the graph's schema"
    conn: "TigerGraphConnection" = None
    llm: LLM = None
    prompt: str = None
    handle_tool_error: bool = True
    
    def __init__(self, conn, llm, prompt):
        super().__init__()
        self.conn = conn
        self.llm = llm
        self.prompt = prompt
        
    def _run(self, query: str) -> str:
        """Use the tool."""

        RESTATE_QUESTION_PROMPT = PromptTemplate(
            template=self.prompt, input_variables=["question", "vertices", "edges"]
        )
        
        restate_chain = LLMChain(llm=self.llm, prompt=RESTATE_QUESTION_PROMPT)
        
        restate_q = restate_chain.apply([{"vertices": [x + " Vertex" for x in self.conn.getVertexTypes()], # + [x + " Edge" for x in conn.getEdgeTypes()],
                                          "question": query,
                                          "edges": [x + " Edge" for x in self.conn.getEdgeTypes()]}])[0]["text"]

        word_list = ['vertex', 'Vertex', 'Vertexes', 'vertexes', 'vertices', 'Vertices']

        vertices = [x.lower() for x in self.conn.getVertexTypes()]

        pattern = rf'(\w+)\s*(?:\b(?:{"|".join(word_list)})\b)'

        result1 = re.findall(pattern, restate_q)

        found = False
        for word in result1:
            if word.lower() in vertices:
                found = True
        '''
        if not(found):
            raise MapQuestionToSchemaException("No "+word+" vertex in the graph schema. Please rephrase your question.")
        '''
        word_list = ['edge', 'Edge', 'Edges', 'edges']

        edges = [x.lower() for x in self.conn.getEdgeTypes()]

        pattern2 = rf'(\w+)\s*(?:\b(?:{"|".join(word_list)})\b)'

        result2 = re.findall(pattern2, restate_q)

        if len(result2) > 0:
            found2 = False
            for word in result2:
                if word.lower() in edges:
                    found2 = True
            '''
            if not(found2):
                raise MapQuestionToSchemaException("No "+word+" edge in the graph schema. Please rephrase your question.")
            '''
        return restate_q
    
    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    def _handle_error(self, error:ToolException) -> str:
        return  "The following errors occurred during tool execution:" + error.args[0]+ "Please ask for human input if they asked their question correctly."

class GenerateFunction(BaseTool):
    name = "GenerateFunction"
    description = "Generate a pyTigerGraph function call"
    conn: "TigerGraphConnection" = None
    llm: LLM = None
    prompt: str = None
    handle_tool_error: bool =True
    embedding_model: EmbeddingModel = None
    embedding_store: EmbeddingStore = None
    
    def __init__(self, conn, llm, prompt, embedding_model, embedding_store):
        super().__init__()
        self.conn = conn
        self.llm = llm
        self.prompt = prompt
        self.embedding_model = embedding_model
        self.embedding_store = embedding_store
    
    def _run(self, question: str) -> str:
        PROMPT = PromptTemplate(
            template=self.prompt, input_variables=["question", "vertices", "edges", "doc1", "doc2", "doc3"]
        )
        queries = self.conn.getInstalledQueries()
        for query in queries:
            queries[query]["parameters"].pop("read_committed")
            try:
                queries[query]["parameters"].pop("result_attribute")
            except:
                pass
        docs = self.embedding_store.retrieve_similar(self.embedding_model.embed_query(question), top_k=3)
        #"queries": [{queries[x]["alternative_endpoint"].split("/")[-1]: queries[x]["parameters"]} for x in queries],
        inputs = [{"question": question, 
                    "vertices": self.conn.getVertexTypes(), 
                    "edges": self.conn.getEdgeTypes(), 
                    "doc1": docs[0].page_content,
                    "doc2": docs[1].page_content,
                    "doc3": docs[2].page_content
                  }]

        chain = LLMChain(llm=self.llm, prompt=PROMPT)
        generated = chain.apply(inputs)[0]["text"]
        return generated

    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    def _handle_error(error:ToolException) -> str:
        return  "The following errors occurred during tool execution:" + error.args[0]+ "Please ask for human input if they asked their question correctly."

class ExecuteFunction(BaseTool):
    name = "ExecuteFunction"
    description = "Execute a pyTigerGraph function"
    conn: "TigerGraphConnection" = None
    handle_tool_error: bool =True
    
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        
    def _run(self, function: str) -> str:
        try:
            loc = {}
            exec("res = conn."+function, {"conn": self.conn}, loc)
            return loc["res"]
        except:
            raise ToolException("The function {} did not execute directly. Please rephrase your question and try again".format(function))
    
    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
        
    def _handle_error(error:ToolException) -> str:
        return  "The following errors occurred during tool execution:" + error.args[0]+ "Please ask for human input if they asked their question correctly."