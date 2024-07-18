import logging
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from common.logs.logwriter import LogWriter
from common.logs.log import req_id_cv
from langchain.pydantic_v1 import BaseModel, Field

logger = logging.getLogger(__name__)

class HallucinationCheckResponse(BaseModel):
    score: str = Field(description="The score of the hallucination check. Either 'yes' or 'no', indicating if the answer is hallucinated.")

class TigerGraphAgentHallucinationCheck:
    def __init__(self, llm_model):
        self.llm = llm_model

    def check_hallucination(self, generation: str, context: str) -> dict:
        """Check if the answer is hallucinated based on the question and context.
        Args:
            question: str: The question to generate an answer for.
            context: str: The context to generate an answer from.
        Returns:
            dict: The answer to the question and a boolean indicating if the answer is hallucinated.
        """
        LogWriter.info(f"request_id={req_id_cv.get()} ENTRY check_hallucination")
        
        hallucination_parser = PydanticOutputParser(pydantic_object=HallucinationCheckResponse)        

        prompt = PromptTemplate(
            template="""You are a grader assessing whether an answer is grounded in / supported by a set of facts. \n
            Here are the facts:
            \n ------- \n
            {context} 
            \n ------- \n
            Here is the answer: {generation}
            Provide a binary score 'yes' or 'no' score to indicate whether the answer is grounded in / supported by a set of facts.
            The score should be 'yes' if the information in the answer is found in the context. otherwise, the score should be 'no'. 
            Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.
            Format: {format_instructions}""",
            input_variables=["generation", "context"],
            partial_variables={
                "format_instructions": hallucination_parser.get_format_instructions()
            }
        )

        # Chain
        rag_chain = prompt | self.llm.model | hallucination_parser

        prediction = rag_chain.invoke({"context": context, "generation": generation})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT check_hallucination")
        return prediction