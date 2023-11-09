from langchain.tools import BaseTool
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