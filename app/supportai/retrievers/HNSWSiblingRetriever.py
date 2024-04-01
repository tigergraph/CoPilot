from app.metrics.tg_proxy import TigerGraphConnectionProxy
from app.supportai.retrievers import BaseRetriever

class HNSWSiblingRetriever(BaseRetriever):
    def __init__(self, embedding_service, llm_service, connection: TigerGraphConnectionProxy):
        super().__init__(embedding_service, llm_service, connection)
        self._check_query_install("HNSW_Search_Sub")
        self._check_query_install("Chunk_Sibling_Retrieval")

    def search(self, question, index, top_k=1, lookback=3, lookahead=3, withHyDE=False):
        if withHyDE:
            query_embedding = self._hyde_embedding(question)
        else:
            query_embedding = self._generate_embedding(question)
        res = self.conn.runInstalledQuery("Chunk_Sibling_Retrieval", 
                                          {"embedding": query_embedding,
                                           "index_name": index, 
                                           "lookback": lookback,
                                           "lookahead": lookahead,
                                           "k": top_k})
        return res

    def retrieve_answer(self, question, index, top_k=1, lookback=3, lookahead=3, withHyDE=False):
        retrieved = self.search(question, index, top_k, lookback, lookahead, withHyDE)
        return self._generate_response(question, retrieved)