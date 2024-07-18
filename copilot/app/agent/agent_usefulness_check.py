from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from common.logs.logwriter import LogWriter
import logging
from common.logs.log import req_id_cv
from langchain.pydantic_v1 import BaseModel, Field

logger = logging.getLogger(__name__)

class UsefulnessCheckResponse(BaseModel):
    score: str = Field(description="The score of the usefulness check. Either 'yes' or 'no', indicating if the answer is useful.")

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
        
        usefulness_parser = PydanticOutputParser(pydantic_object=UsefulnessCheckResponse)
        
        prompt = PromptTemplate(
            template="""You are a grader assessing whether the generated answer is useful to resolve the question. \n 
            Here is the answer:
            \n ------- \n
            {generation} 
            \n ------- \n
            Here is the question: {question}
            Give a binary score 'yes' or 'no' to indicate whether the answer is useful to resolve a question.
            An answer is considered useful if the answer mostly addresses the question reasonably.
            Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.
            Answer in the format: {format_instructions}""",
            input_variables=["generation", "question"],
            partial_variables={
                "format_instructions": usefulness_parser.get_format_instructions()
            }
        )

        # Chain
        rag_chain = prompt | self.llm.model | usefulness_parser

        prediction = rag_chain.invoke({"generation": answer, "question": question})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT check_usefulness")
        return prediction