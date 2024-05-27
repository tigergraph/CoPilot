from langchain.prompts import PromptTemplate
from langchain import hub
from langchain_core.output_parsers import JsonOutputParser
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class TigerGraphAgentUsefulnessCheck:
    def __init__(self, llm_model):
        self.llm = llm_model

    def check_usefulness(self, question: str, answer: str) -> dict:
        """Check if the answer is useful based on the question, context, and answer.
        Args:
            question: str: The question to generate an answer for.
            answer: str: The answer to check for usefulness.
        Returns:
            dict: The answer to the question and a boolean indicating if the answer is useful.
        """
        LogWriter.info(f"request_id={req_id_cv.get()} ENTRY check_usefulness")
        prompt = PromptTemplate(
            template="""You are a grader assessing whether an answer is useful to resolve a question. \n 
            Here is the answer:
            \n ------- \n
            {generation} 
            \n ------- \n
            Here is the question: {question}
            Give a binary score 'yes' or 'no' to indicate whether the answer is useful to resolve a question. \n
            Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.""",
            input_variables=["generation", "question"],
        )

        # Chain
        rag_chain = prompt | self.llm.model | JsonOutputParser()

        prediction = rag_chain.invoke({"generation": answer, "question": question})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT check_usefulness")
        return prediction