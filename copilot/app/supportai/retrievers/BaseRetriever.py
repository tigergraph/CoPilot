from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.base_embedding_store import EmbeddingStore
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.llm_services.base_llm import LLM_Model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


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

    def _install_query(self, query_name):
        with open(f"app/gsql/supportai/retrievers/{query_name}.gsql", "r") as f:
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
        installed_queries = [q.split("/")[-1] for q in endpoints]

        if query_name not in installed_queries:
            return self._install_query(query_name)
        else:
            return True

    def _generate_response(self, question, retrieved):
        model = self.llm_service.llm
        prompt = self.llm_service.supportai_response_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": question, "sources": retrieved})

        return {"response": generated, "retrieved": retrieved}

    def _generate_embedding(self, text) -> str:
        return (
            str(self.emb_service.embed_query(text))
            .strip("[")
            .strip("]")
            .replace(" ", "")
        )

    def _hyde_embedding(self, text) -> str:
        model = self.llm_service.llm
        prompt = self.llm_service.hyde_prompt

        prompt = ChatPromptTemplate.from_template(prompt)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        generated = chain.invoke({"question": text})

        return self._generate_embedding(generated)

    """    
    def _get_entities_relationships(self, text: str, extractor: BaseExtractor):
        return extractor.extract(text)
    """

    def search(self, question):
        pass

    def retrieve_answer(self, question):
        pass
