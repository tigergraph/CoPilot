from langchain.tools import BaseTool
from langchain.llms.base import LLM
from langchain.tools.base import ToolException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from pyTigerGraph import TigerGraphConnection
from embedding_utils.embedding_services import EmbeddingModel
from embedding_utils.embedding_stores import EmbeddingStore

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