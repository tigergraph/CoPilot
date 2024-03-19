from datetime import datetime
import logging
from typing import Iterable, Tuple, List
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.base_embedding_store import EmbeddingStore
from app.log import req_id_cv
from langchain_community.vectorstores import Milvus
from pymilvus import connections, utility

logger = logging.getLogger(__name__)

class MilvusEmbeddingStore(EmbeddingStore):
    def __init__(self, embedding_service: EmbeddingModel, host: str, port: str, collection_name: str = "tg_documents", vector_field: str = "vector_field", text_field: str = "text", vertex_field: str = "vertex_id", username: str = "", password: str = ""):
        milvus_connection = {
            "host": host,
            "port": port,
            "user": username,
            "password": password
        }

        logger.info(f"Initializing Milvus with host={host}, port={port}, username={username}, collection={collection_name}")
        self.milvus = Milvus(
            embedding_function=embedding_service, 
            collection_name=collection_name, 
            connection_args=milvus_connection,
            auto_id = True,
            drop_old = False,
            text_field=text_field,
            vector_field=vector_field
        )
        self.embedding_service = embedding_service
        self.vector_field = vector_field
        self.vertex_field = vertex_field
        self.text_field = text_field

        self.load_documents(milvus_connection, collection_name)
    
    def load_documents(self, milvus_connection, collection_name):
        # manual connection to check if the collection exists the first time
        alias = "default"
        connections.connect(alias=alias, **milvus_connection)
        collection_not_exists = not utility.has_collection(collection_name, using=alias)
        
        if (collection_not_exists):
            from langchain.document_loaders import DirectoryLoader, JSONLoader

            def metadata_func(record: dict, metadata: dict) -> dict:
                metadata["function_header"] = record.get("function_header")
                metadata["description"] = record.get("description")
                metadata["param_types"] = record.get("param_types")
                metadata["custom_query"] = record.get("custom_query")

                return metadata

            logger.info("Milvus add initial load documents init()")
            loader = DirectoryLoader("./app/pytg_documents/", 
                                    glob="*.json",
                                    loader_cls=JSONLoader,
                                    loader_kwargs = {'jq_schema':'.', 
                                                    'content_key': 'docstring',
                                                    'metadata_func': metadata_func})
            docs = loader.load()
            self.milvus.upsert(documents=docs)
            logger.info("Milvus finish initial load documents init()")

            logger.info("Milvus initialized successfully")
        else:
            logger.info("Milvus already initialized, skipping initial document load")

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
        added = self.milvus.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"request_id={req_id_cv.get()} Milvus EXIT add_embeddings()")
        return added

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