from langchain.tools import BaseTool, StructuredTool, Tool, tool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from pyTigerGraph import TigerGraphConnection
import re

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

        for word in result1:
            if not(word.lower() in vertices):
                raise MapQuestionToSchemaException("No "+word+" vertex in the graph schema. Please rephrase your question.")

        word_list = ['edge', 'Edge', 'Edges', 'edges']

        edges = [x.lower() for x in self.conn.getEdgeTypes()]

        pattern = rf'(\w+)\s*(?:\b(?:{"|".join(word_list)})\b)'

        result1 = re.findall(pattern, restate_q)

        for word in result1:
            if not(word.lower() in edges):
                raise MapQuestionToSchemaException("No "+word+" edge in the graph schema. Please rephrase your question.")

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
    
    def __init__(self, conn, llm, prompt):
        super().__init__()
        self.conn = conn
        self.llm = llm
        self.prompt = prompt
    
    def _run(self, question: str) -> str:
        PROMPT = PromptTemplate(
            template=self.prompt, input_variables=["question", "vertices", "queries", "edges"]
        )
        queries = self.conn.getInstalledQueries()
        [queries[x]["parameters"].pop("read_committed") for x in queries] #remove read_committed
        inputs = [{"question": question, 
                    "vertices": self.conn.getVertexTypes(), 
                    "edges": self.conn.getEdgeTypes(), 
                    "queries": [{queries[x]["alternative_endpoint"].split("/")[-1]: queries[x]["parameters"]} for x in queries]
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