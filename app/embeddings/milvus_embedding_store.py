from datetime import datetime
import logging
from typing import Iterable, Tuple, List
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.base_embedding_store import EmbeddingStore
from app.log import req_id_cv
from langchain_community.vectorstores import Milvus

logger = logging.getLogger(__name__)

class MilvusEmbeddingStore(EmbeddingStore):
    def __init__(self, embedding_service: EmbeddingModel, host: str, port: str, collection_name: str = "tg_documents", vector_field: str = "vector_field", text_field: str = "text", vertex_field: str = "vertex_id", username: str = "", password: str = ""):
        logger.info(f"Initializing Milvus with host={host}, port={port}, username={username}, collection={collection_name}")
        self.milvus = Milvus(
            embedding_function=embedding_service, 
            collection_name=collection_name, 
                connection_args=dict(
                host=host,
                port=port,
                username=username,
                password=password
            ),
            auto_id = True,
            drop_old = True,
            text_field=text_field,
            vector_field=vector_field
        )
        self.embedding_service = embedding_service
        self.vector_field = vector_field
        self.vertex_field = vertex_field
        self.text_field = text_field
        logger.info(f"Milvus initialized successfully")

    def add_embeddings(self, embeddings: Iterable[Tuple[str, List[float]]], metadatas: List[dict]=None):
        """ Add Embeddings.
            Add embeddings to the Embedding store.
            Args:
                embeddings (Iterable[Tuple[str, List[float]]]):
                    Iterable of content and embedding of the document.
                metadatas (List[Dict]):
                    List of dictionaries containing the metadata for each document.
                    The embeddings and metadatas list need to have identical indexing.
        """
        logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY add_embeddings()")
        texts = [text for text, _ in embeddings]
        self.milvus.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"request_id={req_id_cv.get()} Milvus EXIT add_embeddings()")

    def remove_embeddings(self, ids):
        """ Remove Embeddings.
            Remove embeddings from the vector store.
            Args:
                ids (str):
                    ID of the document to remove from the embedding store  
        """
        logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY delete()")
        self.milvus.delete(ids)
        logger.info(f"request_id={req_id_cv.get()} Milvus EXIT delete()")

    def retrieve_similar(self, query_embedding, top_k=10):
        """ Retireve Similar.
            Retrieve similar embeddings from the vector store given a query embedding.
            Args:
                query_embedding (List[float]):
                    The embedding to search with.
                top_k (int, optional):
                    The number of documents to return. Defaults to 10.
            Returns:
                https://api.python.langchain.com/en/latest/documents/langchain_core.documents.base.Document.html#langchain_core.documents.base.Document
                Document results for search.
        """
        logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY similarity_search_by_vector()")
        similar = self.milvus.similarity_search_by_vector(embedding=query_embedding, k=top_k)
        sim_ids = [doc.metadata.get("function_header") for doc in similar]
        logger.debug(f"request_id={req_id_cv.get()} Milvus similarity_search_by_vector() retrieved={sim_ids}")
        logger.info(f"request_id={req_id_cv.get()} Milvus EXIT similarity_search_by_vector()")
        return similar