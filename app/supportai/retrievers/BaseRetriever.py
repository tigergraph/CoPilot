from app.embeddings.embedding_services import EmbeddingModel
from app.llm_services.base_llm import LLM_Model
#from app.supportai.entity_relationship_extraction import BaseExtractor
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

class BaseRetriever():
    def __init__(self, embedding_service: EmbeddingModel, llm_service: LLM_Model):
        self.emb_service = embedding_service
        self.llm_service = llm_service

    def _generate_response(self, question, retrieved):
        model = self.llm_service.llm
        prompt = self.llm_service.supportai_response_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": question, "sources": retrieved})

        return {"response": generated, "retrieved": retrieved}

    def _generate_embedding(self, text) -> str:
        return str(self.emb_service.embed_query(text)).strip("[").strip("]").replace(" ", "")

    def _hyde_embedding(self, text) -> str:
        model = self.llm_service.llm
        prompt = self.llm_service.hyde_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": text})

        return self._generate_embedding(generated)
    

    '''    
    def _get_entities_relationships(self, text: str, extractor: BaseExtractor):
        return extractor.extract(text)
    '''
    def search(self, question):
        pass
    
    def retrieve_answer(self, question):
        pass

