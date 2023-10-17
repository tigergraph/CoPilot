from typing import Iterable, Tuple, List
from embedding_services import EmbeddingModel

class EmbeddingStore():
    def __init__(self):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

    def add_embeddings(self, embeddings: Iterable[Tuple[str, List[float]]], metadatas: List[dict]):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

    def remove_embeddings(self, ids: List[str]):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

    def retrieve_similar(self, query_embedding, top_k=10):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

class FAISS_EmbeddingStore(EmbeddingStore):
    def __init__(self, embedding_service: EmbeddingModel):
        from langchain.vectorstores import FAISS
        from langchain.document_loaders import DirectoryLoader

        loader = DirectoryLoader("./pytg_documents/", glob="*.txt")
        docs = loader.load()

        self.faiss = FAISS.from_documents(docs, embedding_service)

    def add_embeddings(self, embeddings: Iterable[Tuple[str, List[float]]], metadatas: List[dict]):
        return self.faiss.add_embeddings(embeddings, metadatas)

    def remove_embeddings(self, ids):
        return self.faiss.delete(ids)

    def retrieve_similar(self, query_embedding, top_k=10):
        return self.faiss.similarity_search_by_vector(query_embedding, top_k)

class TG_EmbeddingStore(EmbeddingStore):
    def __init__(self):
        raise NotImplementedError("TG Embedding Store not implemented")