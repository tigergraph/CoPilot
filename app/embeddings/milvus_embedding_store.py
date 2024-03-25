from datetime import datetime
import logging
from typing import Iterable, Tuple, List, Optional, Union

from fastapi import HTTPException
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.base_embedding_store import EmbeddingStore
from app.log import req_id_cv
from langchain_community.vectorstores import Milvus
from pymilvus import connections, utility
from langchain_core.documents.base import Document

logger = logging.getLogger(__name__)

class MilvusEmbeddingStore(EmbeddingStore):
    def __init__(self, embedding_service: EmbeddingModel, host: str, port: str, support_ai_instance: bool, collection_name: str = "tg_documents", vector_field: str = "vector_field", text_field: str = "text", vertex_field: str = "", username: str = "", password: str = ""):
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
        self.support_ai_instance = support_ai_instance

        if (not self.support_ai_instance):
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
        if metadatas is None:
                metadatas = []
                
        # add fields required by Milvus if they do not exist
        if self.support_ai_instance:
            logger.info(f"This is a SupportAI instance and needs vertex ids stored at {self.vertex_field}")
            for metadata in metadatas:
                if self.vertex_field not in metadata:
                    metadata[self.vertex_field] = ""
        else:
            for metadata in metadatas:
                if "seq_num" not in metadata:
                    metadata["seq_num"] = 1
                if "source" not in metadata:
                    metadata["source"] = ""

        logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY add_embeddings()")
        texts = [text for text, _ in embeddings]
        added = self.milvus.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"request_id={req_id_cv.get()} Milvus EXIT add_embeddings()")
        return added

    def upsert_embeddings(self, id: str, embeddings: Iterable[Tuple[str, List[float]]], metadatas: Optional[List[dict]] = None):
        try:
            logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY upsert_document()")

            if metadatas is None:
                    metadatas = []
                    
            # add fields required by Milvus if they do not exist
            if self.support_ai_instance:
                logger.info(f"This is a SupportAI instance and needs vertex ids stored at {self.vertex_field}")
                for metadata in metadatas:
                    if self.vertex_field not in metadata:
                        metadata[self.vertex_field] = ""
            else:
                for metadata in metadatas:
                    if "seq_num" not in metadata:
                        metadata["seq_num"] = 1
                    if "source" not in metadata:
                        metadata["source"] = ""

            documents = []

            # Iterate over embeddings and metadatas simultaneously
            for (text, embedding), metadata in zip(embeddings, metadatas or []):
                # Create a document with text as page content
                document = Document(page_content=text)

                # Add embedding to metadata
                if metadata is None:
                    metadata = {}
                # metadata["embedding"] = embedding

                # Add metadata to document
                document.metadata = metadata

                # Append document to the list
                documents.append(document)

            # Perform upsert operation
            if id is not None and id.strip():
                logger.info(f"id: {id}")
                logger.info(f"documents: {documents}")
                upserted = self.milvus.upsert(ids=[int(id)], documents=documents)
            else:
                logger.info(f"documents: {documents}")
                upserted = self.milvus.upsert(documents=documents)

            logger.info(f"request_id={req_id_cv.get()} Milvus EXIT upsert_document()")
            
            # Check if upsertion was successful
            if upserted:
                success_message = f"document upserted {upserted}"
                logger.info(success_message)
                return success_message
            else:
                error_message = f"Failed to upsert document {upserted}"
                logger.error(error_message)
                raise Exception(error_message)
        
        except Exception as e:
            error_message = f"An error occurred while upserting document: {str(e)}"
            logger.error(error_message)
            raise e
    
    def remove_embeddings(self, ids: Optional[List[str]] = None, expr: Optional[str] = None):
        try:
            logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY delete()")
            
            # Check if ids or expr are provided
            if ids is None and expr is None:
                raise ValueError("Either id list/string or expr string must be provided.")

            # Perform deletion based on provided IDs or expression
            if expr:
                # Delete by IDs
                deleted = self.milvus.delete(expr=expr)
                deleted_message = f"Deleted by expression: {expr} {deleted}"
            elif ids:
                # Delete by expression
                deleted = self.milvus.delete(ids=ids)
                deleted_message = f"Deleted by IDs: {ids} {deleted}"

            logger.info(f"request_id={req_id_cv.get()} Milvus EXIT delete()")

            # Check if deletion was successful
            if deleted:
                success_message = f"Embeddings {deleted_message}."
                logger.info(success_message)
                return success_message
            else:
                error_message = f"Failed to delete embeddings. {deleted_message}"
                logger.error(error_message)
                raise Exception(error_message)
        
        except Exception as e:
            error_message = f"An error occurred while deleting embeddings: {str(e)}"
            logger.error(error_message)
            raise e

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
        try:
            logger.info(f"request_id={req_id_cv.get()} Milvus ENTRY similarity_search_by_vector()")
            similar = self.milvus.similarity_search_by_vector(embedding=query_embedding, k=top_k)
            sim_ids = [doc.metadata.get("function_header") for doc in similar]
            logger.debug(f"request_id={req_id_cv.get()} Milvus similarity_search_by_vector() retrieved={sim_ids}")
            # Convert pk from int to str for each document
            for doc in similar:
                doc.metadata['pk'] = str(doc.metadata['pk'])
            logger.info(f"request_id={req_id_cv.get()} Milvus EXIT similarity_search_by_vector()")
            return similar
        except Exception as e:
            error_message = f"An error occurred while retrieving docuements: {str(e)}"
            logger.error(error_message)
            raise e