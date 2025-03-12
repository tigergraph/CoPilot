from supportai.retrievers import BaseRetriever
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.config import embed_store_type
import logging

logger = logging.getLogger(__name__)

class HNSWOverlapRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)
        self._check_query_install("HNSW_Search_Sub")
        self._check_query_install("HNSW_Overlap_Search")

    def search(self, question, indices, top_k=1, num_hops=2, num_seen_min=1):
        if embed_store_type == "miluvs":
            query_embedding = self._generate_embedding(question)

            res = self.conn.runInstalledQuery(
                "HNSW_Overlap_Search",
                self.embedding_store.add_connection_parameters(
                    {
                        "query_vector_as_string": query_embedding,
                        "v_types": indices,
                        "collection_prefix": self.conn.graphname,
                        "top_k": top_k,
                        "num_hops": num_hops,
                        "num_seen_min": num_seen_min,
                    }
                ),
                usePost=True
            )
        else:
            query_embedding = self._generate_embedding(question, "list")
            logger.info(f"Use embedding {query_embedding} with dimension {len(query_embedding)}")

            res = self.conn.runInstalledQuery(
                "HNSW_Overlap_Search",
                params = {
                    "v_types": indices,
                    "query_vector": query_embedding,
                    "top_k": top_k,
                    "num_hops": num_hops,
                    "num_seen_min": num_seen_min,
                },
                usePost=True
            )            
        return res

    def retrieve_answer(self, question, index, top_k=1, num_hops=2, num_seen_min=1):
        retrieved = self.search(question, index, top_k, num_hops, num_seen_min)
        return self._generate_response(question, retrieved)
