from typing import Iterable, Tuple, List
from app.embedding_utils.embedding_services import EmbeddingModel
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class EmbeddingStore():
    """ EmbeddingStore Base Class
        Used for connecting to various embedding stores.
    """
    def __init__(self):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

    def add_embeddings(self, embeddings: Iterable[Tuple[str, List[float]]], metadatas: List[dict]):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

    def remove_embeddings(self, ids: List[str]):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

    def retrieve_similar(self, query_embedding, top_k=10):
        raise NotImplementedError("Cannot Instantiate Base Embedding Store Class")

class FAISS_EmbeddingStore(EmbeddingStore):
    """ FAISS_EmbeddingStore
    
        The EmbeddingStore implemented by FAISS. Runs locally to the InquiryAI service and does not have any database features.
        DO NOT USE IN PRODUCTION, there is no persistence/DR/HA/etc. only intended for development usage ONLY.
    """
    def __init__(self, embedding_service: EmbeddingModel):
        """ Initialize the FAISS_EmbeddingStore
            
            Reads the pyTigerGraph documentation and initializes the vector store with the embeddings generated.

            Args:
                embedding_service (EmbeddingModel): 
                    An EmbeddingModel instance that connects to an external embedding LLM service
        """
        from langchain.vectorstores import FAISS
        from langchain.document_loaders import DirectoryLoader, JSONLoader

        def metadata_func(record: dict, metadata: dict) -> dict:
            metadata["function_header"] = record.get("function_header")
            metadata["description"] = record.get("description")
            metadata["param_types"] = record.get("param_types")
            metadata["custom_query"] = record.get("custom_query")

            return metadata

        loader = DirectoryLoader("./app/pytg_documents/", 
                                 glob="*.json",
                                 loader_cls=JSONLoader,
                                 loader_kwargs = {'jq_schema':'.', 
                                                  'content_key': 'docstring',
                                                  'metadata_func': metadata_func})
        docs = loader.load()

        self.faiss = FAISS.from_documents(docs, embedding_service)

    def add_embeddings(self, embeddings: Iterable[Tuple[str, List[float]]], metadatas: List[dict]):
        """ Add Embeddings.
            Add embeddings to the Embedding store.
            Args:
                embeddings (Iterable[Tuple[str, List[float]]]):
                    Iterable of content and embedding of the document.
                metadatas (List[Dict]):
                    List of dictionaries containing the metadata for each document.
                    The embeddings and metadatas list need to have identical indexing.
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY add_embeddings()")
        added = self.faiss.add_embeddings(embeddings, metadatas)
        logger.info(f"request_id={req_id_cv.get()} EXIT add_embeddings()")
        return added

    def remove_embeddings(self, ids):
        """ Remove Embeddings.
            Remove embeddings from the vector store.
            Args:
                ids (str):
                    ID of the document to remove from the embedding store  
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY remove_embeddings()")
        deleted = self.faiss.delete(ids)
        logger.info(f"request_id={req_id_cv.get()} EXIT add_embeddings()")
        return deleted

    def retrieve_similar(self, query_embedding, top_k=10):
        """ Retireve Similar.
            Retrieve similar embeddings from the vector store given a query embedding.
            Args:
                query_embedding (List[float]):
                    The embedding to search with.
                top_k (int, optional):
                    The number of documents to return. Defaults to 10.
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY retrieve_similar()")
        similar = self.faiss.similarity_search_by_vector(query_embedding, top_k)
        sim_ids = [doc.metadata.get("function_header") for doc in similar]
        logger.debug(f"request_id={req_id_cv.get()} retrieve_similar() retrieved={sim_ids}")
        logger.info(f"request_id={req_id_cv.get()} EXIT retrieve_similar()")
        return similar

class TG_EmbeddingStore(EmbeddingStore):
    def __init__(self):
        raise NotImplementedError("TG Embedding Store not implemented")