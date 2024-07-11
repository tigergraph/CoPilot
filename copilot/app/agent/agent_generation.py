import logging
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from common.logs.logwriter import LogWriter
from common.logs.log import req_id_cv
from langchain.pydantic_v1 import BaseModel, Field

logger = logging.getLogger(__name__)

# # Define a function to calculate token length
# def calculate_token_length(text):
#     tokens = tokenizer.encode(text, add_special_tokens=False)
#     return len(tokens)

# Function to approximate token length by characters
def approximate_token_length(text):
    return len(text) // 4  # Assuming an average token length of 4 characters


class CoPilotAnswerOutput(BaseModel):
    generated_answer: str = Field(description="The generated answer to the question. Make sure maintain a professional tone.")
    citation: list[str] = Field(description="The citation for the answer. List the information used.")

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
            template="""Given the answer context in JSON format, rephrase it to answer the question. \n
                        Use only the provided information in context without adding any reasoning or additional logic. \n
                        Make sure all information in the answer are covered in the generated answer.\n
                        Question: {question} \n
                        Answer: {context} \n
                        Format: {format_instructions}""",
            # template="""Given the context, generate answer.\n
            #             Make sure all facts in the context are covered in the generated answer.\n
            #             Context: {context} \n
            #             Format: {format_instructions}""",
            input_variables=["question", "context"],
            partial_variables={
                "format_instructions": answer_parser.get_format_instructions()
            }
        )

        full_prompt = prompt.format(
            question=question,
            context=context,
            format_instructions=answer_parser.get_format_instructions()
        )

        logger.info(f"full_prompt: {full_prompt}")
        # Calculate token lengths
        context_token_length = approximate_token_length(context)
        # Render the prompt to get the full string for token length calculation
        prompt_token_length = approximate_token_length(full_prompt)
        # Log the token lengths
        logger.info(f"Context Token Length: {context_token_length}")
        # logger.info(f"Prompt Token Length: {prompt_token_length}")
        logger.info(f"Total Token Length: {prompt_token_length}")

        # Ensure the total token length does not exceed the model's token limit
        model_token_limit = 8192  # Replace with your model's token limit
        if prompt_token_length > model_token_limit:
            logger.warning("The combined length of context and prompt exceeds the model's token limit.")
            # Truncate or simplify the context to fit within the token limit
            # truncated_context = context[:model_token_limit - prompt_token_length - 1]
            # full_prompt = generate_full_prompt(question, truncated_context, format_instructions)
        else:
            logger.info("The combined length of context and prompt is within the model's token limit.")
        # logger.info(f"prompt: {prompt}")
        # logger.info(f"answer_parser get_format_instructions: {answer_parser.get_format_instructions()}")
        # Chain
        rag_chain = prompt | self.llm.model | answer_parser
        generation = rag_chain.invoke({"question": question, "context": context})

        logger.info(f"Generated Answer: {generation.generated_answer}")
        logger.info(f"Citations: {generation.citation}")

        LogWriter.info(f"request_id={req_id_cv.get()} EXIT generate_answer")

        return generation