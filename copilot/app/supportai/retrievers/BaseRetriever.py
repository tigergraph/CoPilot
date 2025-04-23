from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.base_embedding_store import EmbeddingStore
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.llm_services.base_llm import LLM_Model
from common.py_schemas import CandidateScore, CandidateGenerator
from common.config import embedding_store_type

from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain.output_parsers import OutputFixingParser

import re
import logging

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
        if embedding_store_type == "tigergraph":
            self.embedding_store.set_graphname(connection.graphname)
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

    def _question_to_keywords(self, question, top_k, verbose):
        keyword_parser = PydanticOutputParser(pydantic_object=CandidateGenerator)

        keyword_prompt = PromptTemplate(
            template = self.llm_service.keyword_extraction_prompt,
            input_variables=["question"],
            partial_variables={"format_instructions": keyword_parser.get_format_instructions()}
        )

        if verbose:
            self.logger.info("Prompt to LLM:\n" + keyword_prompt.invoke({"question": question}).to_string())

        model = self.llm_service.model

        chain = keyword_prompt | model | keyword_parser

        answer = chain.invoke({"question": question})

        if verbose:
            self.logger.info(f"Extracted keywords \"{answer}\" from question \"{question}\" by LLM")

        # sort list by quality score
        res = answer.candidates
        res.sort(key=lambda x: x.quality_score, reverse=True)

        keywords = [x.candidate for x in res[:top_k]]

        return keywords

    def _expand_question(self, question, top_k, verbose):
        question_parser = PydanticOutputParser(pydantic_object=CandidateGenerator)

        QUESTION_PROMPT = PromptTemplate(
            template = self.llm_service.question_expansion_prompt,
            input_variables=["question"],
            partial_variables={"format_instructions": question_parser.get_format_instructions()}
        )

        model = self.llm_service.model

        chain = QUESTION_PROMPT | model | question_parser
        #chain = QUESTION_PROMPT | model

        answer = chain.invoke({"question": question})

        if verbose:
            self.logger.info(f"Expanded question \"{question}\" from LLM: {answer}")

        # sort list by quality score
        res = answer.candidates
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

    def _generate_embedding(self, text, str_mode: bool = False) -> str:
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

    def _hyde_embedding(self, text, str_mode: bool = False) -> str:
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

    def _generate_start_set(self, questions, indices, top_k, similarity_threshold: float = 0.90, filter_expr: str = None, withHyDE: bool = False, verbose: bool = False):
        if not isinstance(questions, list):
            questions = [questions]

        candidate_set = []
        for question in questions:
            if withHyDE:
                query_embedding = self._hyde_embedding(question)
            else:
                query_embedding = self._generate_embedding(question)
            if embedding_store_type == "tigergraph":
                if filter_expr and "\"%" in filter_expr:
                    filter_expr = re.findall(r'"(%[^"]*)"', filter_expr)[0]
                res = self.embedding_store.retrieve_similar_with_score(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    vertex_types=indices,
                    filter_expr=filter_expr,
                )
                verbose and self.logger.info(f"Retrived topk similar for query \"{question}\": {res}")
                candidate_set += res
            else:
                #old_collection_name = self.embedding_store.collection_name
                for v_type in indices:
                    self.embedding_store.set_collection_name(self.conn.graphname+"_"+v_type)
                    res = self.embedding_store.retrieve_similar_with_score(
                        query_embedding=query_embedding,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold,
                        filter_expr=filter_expr,
                    )
                    for doc in res:
                        doc[0].metadata["vertex_type"] = v_type
                    verbose and self.logger.info(f"Retrived topk similar for query \"{question}\": {res}")
                    candidate_set += res
                #self.embedding_store.set_collection_name(old_collection_name)
        candidate_set.sort(key=lambda x: x[1], reverse=True)
        start_set = []
        for document, _ in candidate_set:
            start_set.append({"v": document.metadata["vertex_id"], "t": document.metadata["vertex_type"]})
        start_set = [dict(d) for d in {tuple(vt.items()) for vt in start_set}][:top_k]
        verbose and self.logger.info(f"Returning start_set: {str(start_set)}")
        return start_set

    def search(self, question):
        pass

    def retrieve_answer(self, question):
        pass
