from app.supportai.retrievers import BaseRetriever
from pyTigerGraph import TigerGraphConnection

class HNSWOverlapRetriever(BaseRetriever):
    def __init__(self, embedding_service, llm_service, connection: TigerGraphConnection):
        super().__init__(embedding_service, llm_service)
        self.conn = connection

    def search(self, question, indices, top_k=1, num_hops=2, num_seen_min=1):
        query_embedding = self._generate_embedding(question)
        res = self.conn.runInstalledQuery("HNSW_Overlap_Search", 
                                            {"embedding": query_embedding,
                                             "embedding_indices": indices,
                                             "k": top_k,
                                             "num_hops": num_hops,
                                             "num_seen_min": num_seen_min})
        return res

    def retrieve_answer(self, question, index, top_k=1, num_hops=2, num_seen_min=1):
        retrieved = self.search(question, index, top_k, num_hops, num_seen_min)
        return self._generate_response(question, retrieved)