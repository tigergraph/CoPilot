from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.supportai.retrievers import BaseRetriever

class MilvusRetriever(BaseRetriever):
    def __init__(self, embedding_service, llm_service, milvus_embedding_store: MilvusEmbeddingStore):
        super().__init__(embedding_service, llm_service)
        self.milvus_embedding_store = milvus_embedding_store

    def search(self, question, top_k=1):
        query_embedding = self._generate_embedding(question)
        
        substrings = query_embedding.split(",")
        query_vector = [float(sub) for sub in substrings]
        res = self.milvus_embedding_store.retrieve_similar_ids(query_embedding=query_vector, top_k=top_k)
        return res

    def retrieve_answer(self, question, top_k=1):
        retrieved = self.search(question, top_k)
        return retrieved
        # return self._generate_response(question, retrieved)