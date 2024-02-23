from app.embedding_utils import EmbeddingService
from app.llm_services import LLMService
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

class BaseRetriever():
    def __init__(self, embedding_service: EmbeddingService, llm_service: LLMService):
        self.emb_service = embedding_service
        self.llm_service = llm_service

    def generate_response(self, question, retrieved):
        model = self.llm_service.llm
        prompt = self.llm_service.supportai_response_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": question, "sources": retrieved})

        return {"response": generated, "retrieved": retrieved}

    def _generate_embedding(self, text) -> str:
        return self.emb_service.embed_query(text).strip("[").strip("]").replace(" ", "")

    def _hyde
    
    def retrieve(self, question):
        pass

