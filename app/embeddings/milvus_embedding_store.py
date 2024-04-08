from datetime import datetime
from langchain_community.vectorstores import Milvus
from langchain_core.documents.base import Document
import logging
from pymilvus import connections, utility
from time import time
from typing import Iterable, Tuple, List, Optional, Union

from fastapi import HTTPException
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.base_embedding_store import EmbeddingStore
from app.metrics.prometheus_metrics import metrics
from app.log import req_id_cv
from app.tools.logwriter import LogWriter

logger = logging.getLogger(__name__)

class MilvusEmbeddingStore(EmbeddingStore):
    def __init__(self, embedding_service: EmbeddingModel, host: str, port: str, support_ai_instance: bool, collection_name: str = "tg_documents", vector_field: str = "vector_field", text_field: str = "text", vertex_field: str = "", username: str = "", password: str = "", alias: str = "alias"):
        self.embedding_service = embedding_service
        self.vector_field = vector_field
        self.vertex_field = vertex_field
        self.text_field = text_field
        self.support_ai_instance = support_ai_instance
        self.collection_name = collection_name
        self.milvus_alias = alias

        if host.startswith("http"):
            if host.endswith(str(port)):
                uri = host
            else:
                uri = f"{host}:{port}"
                
            self.milvus_connection = {
                "alias": self.milvus_alias,
                "uri": uri,
                "user": username,
                "password": password,
                "timeout": 30
            }
        else:
            self.milvus_connection = {
                "alias": self.milvus_alias,
                "host": host,
                "port": port,
                "user": username,
                "password": password,
                "timeout": 30
            }

        connections.connect(**self.milvus_connection)
        metrics.milvus_active_connections.labels(self.collection_name).inc
        LogWriter.info(f"Initializing Milvus with host={host}, port={port}, username={username}, collection={collection_name}")
        self.milvus = Milvus(
            embedding_function=embedding_service, 
            collection_name=collection_name, 
            connection_args=self.milvus_connection,
            auto_id = True,
            drop_old = False,
            text_field=text_field,
            vector_field=vector_field
        )

        if not self.support_ai_instance:
            self.load_documents()
    
    def check_collection_exists(self):
        connections.connect(**self.milvus_connection)
        return utility.has_collection(self.collection_name, using=self.milvus_alias)
    
    def load_documents(self):        
        if not self.check_collection_exists():
            from langchain.document_loaders import DirectoryLoader, JSONLoader

            def metadata_func(record: dict, metadata: dict) -> dict:
                metadata["function_header"] = record.get("function_header")
                metadata["description"] = record.get("description")
                metadata["param_types"] = record.get("param_types")
                metadata["custom_query"] = record.get("custom_query")

                return metadata

            LogWriter.info("Milvus add initial load documents init()")
            loader = DirectoryLoader("./app/pytg_documents/", 
                                    glob="*.json",
                                    loader_cls=JSONLoader,
                                    loader_kwargs = {'jq_schema':'.', 
                                                    'content_key': 'docstring',
                                                    'metadata_func': metadata_func})
            docs = loader.load()
            
            operation_type = "load_upsert"
            metrics.milvus_query_total.labels(self.collection_name, operation_type).inc()
            start_time = time()

            self.milvus.upsert(documents=docs)

            duration = time() - start_time
            metrics.milvus_query_duration_seconds.labels(self.collection_name, operation_type).observe(duration)
            LogWriter.info("Milvus finish initial load documents init()")

            LogWriter.info("Milvus initialized successfully")
        else:
            LogWriter.info("Milvus already initialized, skipping initial document load")

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
        try:
            if metadatas is None:
                    metadatas = []
                    
            # add fields required by Milvus if they do not exist
            if self.support_ai_instance:
                for metadata in metadatas:
                    if self.vertex_field not in metadata:
                        metadata[self.vertex_field] = ""
            else:
                for metadata in metadatas:
                    if "seq_num" not in metadata:
                        metadata["seq_num"] = 1
                    if "source" not in metadata:
                        metadata["source"] = ""

            LogWriter.info(f"request_id={req_id_cv.get()} Milvus ENTRY add_embeddings()")
            texts = [text for text, _ in embeddings]

            operation_type = "add_texts"
            metrics.milvus_query_total.labels(self.collection_name, operation_type).inc()
            start_time = time()

            added = self.milvus.add_texts(texts=texts, metadatas=metadatas)

            duration = time() - start_time
            metrics.milvus_query_duration_seconds.labels(self.collection_name, operation_type).observe(duration)

            LogWriter.info(f"request_id={req_id_cv.get()} Milvus EXIT add_embeddings()")

            # Check if registration was successful
            if added:
                success_message = f"Document registered with id: {added[0]}"
                LogWriter.info(success_message)
                return success_message
            else:
                error_message = f"Failed to register document {added}"
                LogWriter.error(error_message)
                raise Exception(error_message)
                    
        except Exception as e:
            error_message = f"An error occurred while registerin document: {str(e)}"
            LogWriter.error(error_message)
            raise e
        
    def upsert_embeddings(self, id: str, embeddings: Iterable[Tuple[str, List[float]]], metadatas: Optional[List[dict]] = None):
        try:
            LogWriter.info(f"request_id={req_id_cv.get()} Milvus ENTRY upsert_document()")

            if metadatas is None:
                    metadatas = []
                    
            # add fields required by Milvus if they do not exist
            if self.support_ai_instance:
                LogWriter.info(f"This is a SupportAI instance and needs vertex ids stored at {self.vertex_field}")
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
            operation_type = "upsert"
            if id is not None and id.strip():
                LogWriter.info(f"id: {id}")
                LogWriter.info(f"documents: {documents}")


                metrics.milvus_query_total.labels(self.collection_name, operation_type).inc()
                start_time = time()

                upserted = self.milvus.upsert(ids=[int(id)], documents=documents)

                duration = time() - start_time
                metrics.milvus_query_duration_seconds.labels(self.collection_name, operation_type).observe(duration)
            else:
                metrics.milvus_query_total.labels(self.collection_name, operation_type).inc()
                start_time = time()

                LogWriter.info(f"documents: {documents}")
                upserted = self.milvus.upsert(documents=documents)

                duration = time() - start_time
                metrics.milvus_query_duration_seconds.labels(self.collection_name, operation_type).observe(duration)

            LogWriter.info(f"request_id={req_id_cv.get()} Milvus EXIT upsert_document()")
            
            # Check if upsertion was successful
            if upserted:
                success_message = f"Document upserted with id: {upserted[0]}"
                LogWriter.info(success_message)
                return success_message
            else:
                error_message = f"Failed to upsert document {upserted}"
                LogWriter.error(error_message)
                raise Exception(error_message)
        
        except Exception as e:
            error_message = f"An error occurred while upserting document: {str(e)}"
            LogWriter.error(error_message)
            raise e
    
    def remove_embeddings(self, ids: Optional[List[str]] = None, expr: Optional[str] = None):
        try:
            LogWriter.info(f"request_id={req_id_cv.get()} Milvus ENTRY delete()")

            if not self.check_collection_exists():
                LogWriter.info(f"request_id={req_id_cv.get()} Milvus collection {self.collection_name} does not exist")
                LogWriter.info(f"request_id={req_id_cv.get()} Milvus EXIT delete()")
                return f"Milvus collection {self.collection_name} does not exist"
            
            # Check if ids or expr are provided
            if ids is None and expr is None:
                raise ValueError("Either id string or expr string must be provided.")

            # Perform deletion based on provided IDs or expression
            if expr:
                # Delete by expression
                start_time = time()
                metrics.milvus_query_total.labels(self.collection_name, "delete").inc()
                deleted = self.milvus.delete(expr=expr)
                end_time = time()
                metrics.milvus_query_duration_seconds.labels(self.collection_name, "delete").observe(end_time - start_time)
                deleted_message = f"deleted by expression: {expr} {deleted}"
            elif ids:
                ids = [int(x) for x in ids]
                # Delete by ids
                start_time = time()
                metrics.milvus_query_total.labels(self.collection_name, "delete").inc()
                deleted = self.milvus.delete(ids=ids)
                end_time = time()
                metrics.milvus_query_duration_seconds.labels(self.collection_name, "delete").observe(end_time - start_time)
                deleted_message = f"deleted by id(s): {ids} {deleted}"

            LogWriter.info(f"request_id={req_id_cv.get()} Milvus EXIT delete()")

            # Check if deletion was successful
            if deleted:
                success_message = f"Document(s) {deleted_message}."
                LogWriter.info(success_message)
                return success_message
            else:
                error_message = f"Failed to delete document(s). {deleted_message}"
                LogWriter.error(error_message)
                raise Exception(error_message)
        
        except Exception as e:
            error_message = f"An error occurred while deleting document(s): {str(e)}"
            LogWriter.error(error_message)
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
            LogWriter.info(f"request_id={req_id_cv.get()} Milvus ENTRY similarity_search_by_vector()")

            start_time = time()
            metrics.milvus_query_total.labels(self.collection_name, "similarity_search_by_vector").inc()
            similar = self.milvus.similarity_search_by_vector(embedding=query_embedding, k=top_k)
            end_time = time()
            metrics.milvus_query_duration_seconds.labels(self.collection_name, "similarity_search_by_vector").observe(end_time - start_time)

            sim_ids = [doc.metadata.get("function_header") for doc in similar]
            logger.debug(f"request_id={req_id_cv.get()} Milvus similarity_search_by_vector() retrieved={sim_ids}")
            # Convert pk from int to str for each document
            for doc in similar:
                doc.metadata['pk'] = str(doc.metadata['pk'])
            LogWriter.info(f"request_id={req_id_cv.get()} Milvus EXIT similarity_search_by_vector()")
            return similar
        except Exception as e:
            error_message = f"An error occurred while retrieving docuements: {str(e)}"
            LogWriter.error(error_message)
            raise e
        
    def add_connection_parameters(self, query_params: dict) -> dict:
        """ Add Connection Parameters.
            Add connection parameters to the query parameters.
            Args:
                query_params (dict):
                    Dictionary containing the parameters for the GSQL query.
            Returns:
                A dictionary containing the connection parameters.
        """
        if self.milvus_connection.get("uri", "") != "":
            if self.milvus_connection.get("user", "") != "":
                user = self.milvus_connection.get("user", "")
                pwd = self.milvus_connection.get("password", "")
                host = self.milvus_connection.get("uri", "")
                # build uri with user and password
                method = host.split(":")[0]
                host = host.split("://")[1]
                query_params["milvus_host"] = f"{method}://{user}:{pwd}@{host}"
            else:
                query_params["milvus_host"] = self.milvus_connection.get("uri", "")
            query_params["milvus_port"] = int(host.split(":")[-1])
        else:
            if self.milvus_connection.get("user", "") != "":
                user = self.milvus_connection.get("user", "")
                pwd = self.milvus_connection.get("password", "")
                host = self.milvus_connection.get("host", "")
                # build uri with user and password
                method = host.split(":")[0]
                host = host.split("://")[1]
                query_params["milvus_host"] = f"{method}://{user}:{pwd}@{host}"
            else:
                query_params["milvus_host"] = self.milvus_connection.get("host", "")
            query_params["milvus_port"] = int(self.milvus_connection.get("port", ""))
        query_params["vector_field_name"] = "document_vector"
        query_params["vertex_id_field_name"] = "vertex_id"
        return query_params

    def __del__(self):
        metrics.milvus_active_connections.labels(self.collection_name).dec
