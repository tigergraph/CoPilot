from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class TigerGraphAgentRouter:
    def __init__(self, llm_model):
        self.llm = llm_model

    def route_question(self, question: str) -> str:
        """Route a question to the appropriate datasource.

        Args:
            question (str): The question to route.

        Returns:
            str: The datasource to use for the question.
        """
        LogWriter.info(f"request_id={req_id_cv.get()} ENTRY route_question")
        prompt = PromptTemplate(
            template="""You are an expert at routing a user question to a vectorstore or graph database function calls. \n
            Use the vectorstore for questions on that would be best suited by text documents. \n
            Otherwise, use graph function calls. Give a binary choice 'graph_functions' or 'vectorstore' based on the question. \n
            Return the a JSON with a single key 'datasource' and no premable or explaination. \n
            Question to route: {question}""",
            input_variables=["question"],
        )

        question_router = prompt | self.llm.model | JsonOutputParser()
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT route_question")
        return question_router.invoke({"question": question})