from app.supportai.retrievers import BaseRetriever
from app.metrics.tg_proxy import TigerGraphConnectionProxy


class HNSWRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)
        self._check_query_install("HNSW_Search_Sub")
        self._check_query_install("HNSW_Search_Content")

    def search(self, question, index, top_k=1, withHyDE=False):
        if withHyDE:
            query_embedding = self._hyde_embedding(question)
        else:
            query_embedding = self._generate_embedding(question)
        params = self.embedding_store.add_connection_parameters(
            {
                "v_type": index,
                "query_vector_as_string": query_embedding,
                "collection_name": self.conn.graphname + "_" + index,
                "top_k": top_k,
            },
            usePost=True
        )
        res = self.conn.runInstalledQuery("HNSW_Search_Content", params)
        return res

    def retrieve_answer(self, question, index, top_k=1, withHyDE=False):
        retrieved = self.search(question, index, top_k, withHyDE)
        return self._generate_response(question, retrieved)
