from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.supportai.retrievers import BaseRetriever
from app.tools.logging_utils import hash_text
import logging
from pyTigerGraph import TigerGraphConnection

logger = logging.getLogger(__name__)

class MilvusRetriever(BaseRetriever):
    def __init__(self, embedding_service, llm_service, milvus_embedding_store: MilvusEmbeddingStore, connection: TigerGraphConnection):
        super().__init__(embedding_service, llm_service)
        self.milvus_embedding_store = milvus_embedding_store
        self.conn = connection

    def search(self, question, top_k=1):
        hashed_question = hash_text(question)
        
        logger.info(f"Generating embedding for question = {hashed_question}")
        query_embedding = self._generate_embedding(question)
        logger.info(f"Embedding generated for question = {hashed_question}")
        
        substrings = query_embedding.split(",")
        query_vector = [float(sub) for sub in substrings]
        
        logger.info(f"Retrieving similar queries for question = {hashed_question}")
        similar_ids = self.milvus_embedding_store.retrieve_similar_ids(query_embedding=query_vector, top_k=top_k)
        vertex_ids = [vertex_id for vertex_id, _ in similar_ids]
        logger.info(f"Retrieved similar queries for question = {hashed_question}, vertex_ids = {vertex_ids}")
        
        logger.info(f"Retrieving content TigerGraph for question {hashed_question} from vertex_ids = {vertex_ids}")
        res = self.conn.runInstalledQuery("Retrieve_Content_By_Vertex_IDs", {"vertex_ids": vertex_ids})
        print(res)
        logger.info(f"Content retrieved from TigerGraph for question {hashed_question} for vertex_ids = {vertex_ids}")
        return similar_ids

    def retrieve_answer(self, question, top_k=1):
        retrieved = self.search(question, top_k)
        return self._generate_response(question, retrieved)