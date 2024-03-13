from datetime import datetime
import logging
from typing import Iterable, Tuple, List
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.base_embedding_store import EmbeddingStore
from app.log import req_id_cv
from pymilvus import CollectionSchema, FieldSchema, DataType, connections, Collection, utility

logger = logging.getLogger(__name__)

class MilvusEmbeddingStore(EmbeddingStore):
    def __init__(self, host: str, port: str, collection_name: str, vector_field: str, vertex_field: str, shard_num: int = 2, consistency_level: str = "Eventually"):
        connections.connect(host=host, port=port)
        self.vector_field = vector_field
        self.vertex_field = vertex_field
        self.collection_name = collection_name

        if not utility.has_collection(collection_name):
            logger.debug(f"creating Milvus collection = {collection_name}")
            vector_id = FieldSchema(
                name="vector_id", 
                dtype=DataType.INT64, 
                is_primary=True,
                auto_id=True
            )
            document_content = FieldSchema(
                name=self.vector_field, 
                dtype=DataType.FLOAT_VECTOR, 
                dim=1536
            )
            vertex_id = FieldSchema(
                name=self.vertex_field, 
                dtype=DataType.VARCHAR,
                max_length=48
            )
            last_updated_at = FieldSchema(
                name="last_updated_at", 
                dtype=DataType.INT64  
            )
            schema = CollectionSchema(
                fields=[vector_id, document_content, vertex_id, last_updated_at], 
                description="Document content search"
            )
            
            self.collection = Collection(
                name=collection_name, 
                schema=schema, 
                using='default', 
                shards_num=shard_num,
                consistency_level=consistency_level
            )
            # TODO: Ahmed update
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 100},
            }
            self.collection.create_index(field_name=self.vector_field, index_params=index_params)
        else:
            logger.debug(f"Loading existing Milvus collection = {collection_name}")
            self.collection = Collection(name=collection_name)
        
        self.collection.load()

    def add_embeddings(self, embeddings: Iterable[Tuple[str, List[float], int]], metadatas: List[dict] = None):
        """ Add Embeddings.
            Add embeddings to the Embedding store.
            Args:
                embeddings (Iterable[Tuple[str, List[float], int]]):
                    Iterable of vertex id, embedding of the document, and the last_updated_time as int.
                metadatas (List[Dict]):
                    List of dictionaries containing the metadata for each document.
                    The embeddings and metadatas list need to have identical indexing.
        """
        vertex_ids = [id_ for id_, _, _ in embeddings]
        vectors = [vec for _, vec, _ in embeddings]
        last_updated_times = [lut for _, _, lut in embeddings]
        data = [vectors, vertex_ids, last_updated_times]
        self.collection = Collection(name=self.collection_name)
        insert_result = self.collection.insert(data)
        if insert_result is not None:
            logger.info(f"Successfully inserted data into the collection '{self.collection_name}'.")
            logger.info(f"Insert result IDs:{insert_result.primary_keys}")
            self.collection.load()
        else:
            logger.error(f"Failed to insert data into the collection '{self.collection_name}'.")

    def remove_embeddings(self, ids):
        """ Remove Embeddings.
            Remove embeddings from the vector store.
            Args:
                ids (str):
                    ID of the document to remove from the embedding store  
        """
        int_ids = [int(id_) for id_ in ids]
        self.collection.delete(expr=f"id in {int_ids}")
        self.collection.load()

    def retrieve_similar(self, query_embedding, top_k=10):
        """ Retireve Similar.
            Retrieve similar embeddings from the vector store given a query embedding.
            Args:
                query_embedding (List[float]):
                    The embedding to search with.
                top_k (int, optional):
                    The number of documents to return. Defaults to 10.
        """
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = self.collection.search(data=[query_embedding], anns_field="embedding", param=search_params, limit=top_k, output_fields=[self.vector_field, self.vertex_field])

        results = []
        for hit in results:
            tuple = Tuple(hit.entity.get(self.vector_field), hit.entity.get(self.vertex_field))
            results.append(tuple)
        return results

    def retrieve_similar_ids(self, query_embedding, top_k=10):
        """ Retireve the ids for the similar embeddings.
            Retrieve similar embeddings from the vector store given a query embedding.
            Args:
                query_embedding (List[float]):
                    The embedding to search with.
                top_k (int, optional):
                    The number of documents to return. Defaults to 10.
        """
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        print(query_embedding)
        self.collection.load()
        results = self.collection.search(data=[query_embedding], anns_field=self.vector_field, param=search_params, limit=top_k, output_fields=[self.vertex_field])

        results = []
        for hit in results:
            tuple = Tuple(hit.id, hit.entity.get(self.vertex_field))
            results.append(tuple)
        return results