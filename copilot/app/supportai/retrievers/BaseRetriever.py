from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.base_embedding_store import EmbeddingStore
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.llm_services.base_llm import LLM_Model
from common.py_schemas import QuestionScore, QuestionGenerator

from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain.output_parsers import OutputFixingParser

import logging

question_parser = PydanticOutputParser(pydantic_object=QuestionGenerator)

QUESTION_PROMPT = PromptTemplate(template = """
You are a helpful assistant responsible for generating 10 new questions similar to the original question below to represent its meaning in a more clear way.
Include a quality score for the answer, based on how well it represents the meaning of the original question. The quality score should be between 0 (poor) and 100 (excellent).

Question: {question}

{format_instructions}
""",
input_variables=["question"],
partial_variables={"format_instructions": question_parser.get_format_instructions()}
)

class BaseRetriever:
    def __init__(
        self,
        embedding_service: EmbeddingModel,
        embedding_store: EmbeddingStore,
        llm_service: LLM_Model,
        connection: TigerGraphConnectionProxy = None,
    ):
        self.emb_service = embedding_service
        self.llm_service = llm_service
        self.conn = connection
        self.embedding_store = embedding_store
        self.logger = logging.getLogger(__name__)

    def _install_query(self, query_name):
        with open(f"common/gsql/supportai/retrievers/{query_name}.gsql", "r") as f:
            query = f.read()
        res = self.conn.gsql(
            "USE GRAPH "
            + self.conn.graphname
            + "\n"
            + query
            + "\n INSTALL QUERY "
            + query_name
        )
        return res

    def _check_query_install(self, query_name):
        endpoints = self.conn.getEndpoints(
            dynamic=True
        )  # installed queries in database
        installed_queries = [q.split("/")[-1] for q in endpoints if f"/{self.conn.graphname}/" in q]

        if query_name not in installed_queries:
            return self._install_query(query_name)
        else:
            return True

    def _generate_question(self, question, top_k, verbose):
        model = self.llm_service.model
        new_parser = OutputFixingParser.from_llm(parser=question_parser, llm=model)

        chain = QUESTION_PROMPT | model | question_parser

        answer = chain.invoke({"question": question})

        if verbose:
            self.logger.info(f"Answer from LLM: {answer}")

        # sort list by quality score
        res = answer.questions
        res.sort(key=lambda x: x.quality_score, reverse=True)

        questions = [x.candidate for x in res[:top_k]]

        return questions

    def _generate_response(self, question, retrieved, verbose):
        model = self.llm_service.llm
        prompt = self.llm_service.supportai_response_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        if verbose:
            self.logger.info("Prompt to LLM:\n" + prompt.invoke({"question": question, "sources": retrieved}).to_string())

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": question, "sources": retrieved})

        return {"response": generated, "retrieved": retrieved}

    def _generate_embedding(self, text, str_mode: bool = True) -> str:
        embedding = self.emb_service.embed_query(text)
        if str_mode:
            return (
                str(embedding)
                .strip("[")
                .strip("]")
                .replace(" ", "")
            )
        else:
            return embedding

    def _hyde_embedding(self, text, str_mode: bool = True) -> str:
        model = self.llm_service.llm
        prompt = self.llm_service.hyde_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": text})

        return self._generate_embedding(generated, str_mode)

    """    
    def _get_entities_relationships(self, text: str, extractor: BaseExtractor):
        return extractor.extract(text)
    """

    def search(self, question):
        pass

    def retrieve_answer(self, question):
        pass
