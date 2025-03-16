import json
from supportai.retrievers import BaseRetriever
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.config import embedding_store_type

class HNSWOverlapRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)

    def search(self, question, indices, top_k=1, num_hops=2, num_seen_min=1, verbose=False):
        if embedding_store_type == "milvus":
            self._check_query_install("HNSW_Search_Sub")
            self._check_query_install("HNSW_Overlap_Search")

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
                        "verbose": verbose,
                    }
                ),
                usePost=True
            )
        else:
            self._check_query_install("HNSW_Overlap_Vector_Search")

            query_embedding = self._generate_embedding(question, False)

            res = self.conn.runInstalledQuery(
                "HNSW_Overlap_Vector_Search",
                params = {
                    "v_types": indices,
                    "query_vector": query_embedding,
                    "top_k": top_k,
                    "num_hops": num_hops,
                    "num_seen_min": num_seen_min,
                    "verbose": verbose,
                },
                usePost=True
            )            
        if "verbose" in res[0]:
            verbose_info = json.dumps(res[0]['verbose'])
            self.logger.info(f"Retrived HNSWOverlap query verbose info: {verbose_info}")
        return res

    def retrieve_answer(self, question, index, top_k=1, num_hops=2, num_seen_min=1, combine: bool = False, verbose: bool = False):
        retrieved = self.search(question, index, top_k, num_hops, num_seen_min, verbose)
        context = ["\n".join(retrieved[0]["final_retrieval"][x]) for x in retrieved[0]["final_retrieval"]]
        if combine:
            context = ["\n".join(context)]

        resp = self._generate_response(question, context)
        
        if verbose and "verbose" in retrieved[0]:
            resp["verbose"] = retrieved[0]["verbose"]
      
        return resp
