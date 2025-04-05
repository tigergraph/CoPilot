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

    def search(self, question, indices, top_k=1, num_hops=2, num_seen_min=1, expand = False, chunk_only=False, verbose=False):
        if expand:
            questions = self._expand_question(question, top_k, verbose)
        else:
            questions = [question]
        start_set = self._generate_start_set(questions, indices, top_k, verbose=verbose)

        self._check_query_install("HNSW_Overlap_Search")
        res = self.conn.runInstalledQuery(
            "HNSW_Overlap_Search",
            params = {
                "json_list_vts": str(start_set),
                "num_hops": num_hops,
                "num_seen_min": num_seen_min,
                "chunk_only": chunk_only,
                "verbose": verbose,
            },
            usePost=True
        )            
        if len(res) > 1 and "verbose" in res[1]:
            verbose_info = json.dumps(res[1]['verbose'])
            self.logger.info(f"Retrived HNSWOverlap query verbose info: {verbose_info}")
        return res

    def retrieve_answer(self, question, index, top_k=1, num_hops=2, num_seen_min=1, expand: bool = False, chunk_only: bool = False, combine: bool = False, verbose: bool = False):
        retrieved = self.search(question, index, top_k, num_hops, num_seen_min, expand, chunk_only, verbose)

        context = []
        if combine:
            for x in retrieved[0]["final_retrieval"]:
                context += retrieved[0]["final_retrieval"][x]
            context = ["\n".join(set(context))]
        else:
            context = ["\n".join(retrieved[0]["final_retrieval"][x]) for x in retrieved[0]["final_retrieval"]]

        resp = self._generate_response(question, context, verbose)
        
        if verbose and len(retrieved) > 1 and "verbose" in retrieved[1]:
            resp["verbose"] = retrieved[1]["verbose"]
            resp["verbose"]["final_retrieval"] = retrieved[0]["final_retrieval"]
      
        return resp
