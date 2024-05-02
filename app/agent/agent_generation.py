from langchain.prompts import PromptTemplate
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class TigerGraphAgentGenerator:
    def __init__(self, llm_model):
        self.llm = llm_model

    def generate_answer(self, question: str, context: str) -> str:
        """Generate an answer based on the question and context.
        Args:
            question: str: The question to generate an answer for.
            context: str: The context to generate an answer from.
        Returns:
            str: The answer to the question.
        """
        LogWriter.info(f"request_id={req_id_cv.get()} ENTRY generate_answer")
        prompt = PromptTemplate(
            template="""Given the question and the context, generate an answer. \n
                        Use the context to generate the answer. \n
                        Return the answer as a string. \n
                        Question: {question} \n
                        Context: {context}""",
            input_variables=["generation", "context"]
        )

        # Chain
        rag_chain = prompt | self.llm.model | StrOutputParser()

        generation = rag_chain.invoke({"context": context, "question": question})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT generate_answer")
        return generation