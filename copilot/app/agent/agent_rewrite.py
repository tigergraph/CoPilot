
import logging
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter
from langchain.pydantic_v1 import BaseModel, Field


logger = logging.getLogger(__name__)

class QuestionRewriteResponse(BaseModel):
    rewritten_question: str = Field(description="The rewritten question.")

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

        rewrite_parser = PydanticOutputParser(pydantic_object=QuestionRewriteResponse)

        re_write_prompt = PromptTemplate(
            template="""You a question re-writer that converts an input question to a better version that is optimized \n 
            for AI agent question answering. Look at the initial and formulate an improved question. \n
            Here is the initial question: \n\n {question}. 
            Format your response in the following manner {format_instructions}""",
            input_variables=["question"],
            partial_variables={
                "format_instructions": rewrite_parser.get_format_instructions()
            }
        )


        # Chain
        question_rewriter = re_write_prompt | self.llm.model | rewrite_parser

        generation = question_rewriter.invoke({"question": question})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT generate_answer")
        return generation