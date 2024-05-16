from langchain.prompts import PromptTemplate
from langchain import hub
from langchain_core.output_parsers import JsonOutputParser
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

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
        prompt = PromptTemplate(
            template="""You are a grader assessing whether an answer is grounded in / supported by a set of facts. \n 
            Here are the facts:
            \n ------- \n
            {context} 
            \n ------- \n
            Here is the answer: {generation}
            Give a binary score 'yes' or 'no' score to indicate whether the answer is grounded in / supported by a set of facts. \n
            Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.""",
            input_variables=["generation", "context"]
        )

        # Chain
        rag_chain = prompt | self.llm.model | JsonOutputParser()

        prediction = rag_chain.invoke({"context": context, "generation": generation})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT check_hallucination")
        return prediction