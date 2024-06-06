from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from common.logs.logwriter import LogWriter
from pyTigerGraph.pyTigerGraph import TigerGraphConnection
import logging
from common.logs.log import req_id_cv

from langchain.pydantic_v1 import BaseModel, Field

logger = logging.getLogger(__name__)

class RouterResponse(BaseModel):
    datasource: str = Field(description="The datasource to use for the question")

class TigerGraphAgentRouter:
    def __init__(self, llm_model, db_conn: TigerGraphConnection):
        self.llm = llm_model
        self.db_conn = db_conn

    def route_question(self, question: str) -> str:
        """Route a question to the appropriate datasource.

        Args:
            question (str): The question to route.

        Returns:
            str: The datasource to use for the question.
        """
        LogWriter.info(f"request_id={req_id_cv.get()} ENTRY route_question")
        v_types = self.db_conn.getVertexTypes()
        e_types = self.db_conn.getEdgeTypes()

        router_parser = PydanticOutputParser(pydantic_object=RouterResponse)

        prompt = PromptTemplate(
            template="""You are an expert at routing a user question to a vectorstore or function calls. \n
            Use the vectorstore for questions on that would be best suited by text documents. \n
            Use the function calls for questions that ask about structured data, or operations on structured data. \n
            Keep in mind that some questions about documents such as "how many documents are there?" can be answered by function calls. \n
            The function calls can be used to answer questions about these entities: {v_types} and relationships: {e_types}. \n
            Otherwise, use function calls. Give a binary choice 'functions' or 'vectorstore' based on the question. \n
            Return the a JSON with a single key 'datasource' and no premable or explaination. \n
            Question to route: {question}
            Format: {format_instructions}""",
            input_variables=["question", "v_types", "e_types"],
            partial_variables={
                "format_instructions": router_parser.get_format_instructions()
            }
        )

        question_router = prompt | self.llm.model | router_parser
        res = question_router.invoke({"question": question, "v_types": v_types, "e_types": e_types})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT route_question")
        return res