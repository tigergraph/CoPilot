from langchain.prompts import PromptTemplate
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from common.logs.logwriter import LogWriter
import logging
from common.logs.log import req_id_cv

logger = logging.getLogger(__name__)

class TigerGraphAgentRewriter:
    def __init__(self, llm_model):
        self.llm = llm_model

    def rewrite_question(self, question: str) -> str:
        """Rewrite a new verison of the question.
        Args:
            question: str: The question to generate an answer for.
        Returns:
            str: The rewritten question.
        """
        LogWriter.info(f"request_id={req_id_cv.get()} ENTRY generate_answer")
        re_write_prompt = PromptTemplate(
            template="""You a question re-writer that converts an input question to a better version that is optimized \n 
            for vectorstore retrieval. Look at the initial and formulate an improved question. \n
            Here is the initial question: \n\n {question}. Improved question with no preamble: \n """,
            input_variables=["question"],
        )


        # Chain
        question_rewriter = re_write_prompt | self.llm.model | StrOutputParser()

        generation = question_rewriter.invoke({"question": question})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT generate_answer")
        return generation