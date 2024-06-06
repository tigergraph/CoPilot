from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv
from langchain.pydantic_v1 import BaseModel, Field

logger = logging.getLogger(__name__)

class CoPilotAnswerOutput(BaseModel):
    generated_answer: str = Field(description="The generated answer to the question. Make sure maintain a professional tone and keep the answer consice.")

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

        answer_parser = PydanticOutputParser(pydantic_object=CoPilotAnswerOutput)

        prompt = PromptTemplate(
            template="""Given the question and the context, generate an answer. \n
                        Make sure to answer the question in a friendly and informative way. \n
                        Question: {question} \n
                        Context: {context}
                        Format: {format_instructions}""",
            input_variables=["question", "context"],
            partial_variables={
                "format_instructions": answer_parser.get_format_instructions()
            }
        )

        # Chain
        rag_chain = prompt | self.llm.model | answer_parser
        generation = rag_chain.invoke({"context": context, "question": question})
        LogWriter.info(f"request_id={req_id_cv.get()} EXIT generate_answer")
        return generation