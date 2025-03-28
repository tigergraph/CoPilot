from supportai.retrievers import BaseRetriever

from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.config import embedding_store_type


class HNSWRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)

    def search(self, question, index, top_k=1, withHyDE=False, verbose=False):
        if embedding_store_type == "milvus":
            self._check_query_install("HNSW_Search_Sub")
            self._check_query_install("HNSW_Content_Search")

            if withHyDE:
                query_embedding = self._hyde_embedding(question)
            else:
                query_embedding = self._generate_embedding(question)
            params = self.embedding_store.add_connection_parameters(
                {
                    "v_type": index,
                    "query_vector_as_string": query_embedding,
                    "collection_name": self.conn.graphname + "_" + index,
                    "top_k": top_k,
                    "verbose": verbose,
                },
            )
            res = self.conn.runInstalledQuery("HNSW_Content_Search", params, usePost=True)
        else:
            self._check_query_install("HNSW_Content_Vector_Search")

            if withHyDE:
                query_embedding = self._hyde_embedding(question, False)
            else:
                query_embedding = self._generate_embedding(question, False)
            params = {
                "v_type": index,
                "query_vector": query_embedding,
                "top_k": top_k,
                "verbose": verbose,
            }
            res = self.conn.runInstalledQuery("HNSW_Content_Vector_Search", params, usePost=True)
        if len(res) > 1 and "verbose" in res[1]:
            verbose_info = json.dumps(res[1]['verbose'])
            self.logger.info(f"Retrived HNSW query verbose info: {verbose_info}")
        return res

    def retrieve_answer(self, question, index, top_k=1, withHyDE=False, combine: bool=False, verbose=False):
        retrieved = self.search(question, index, top_k, withHyDE, verbose)
        context = [retrieved[0]["final_retrieval"][x] for x in retrieved[0]["final_retrieval"]]
        if combine:
            context = ["\n".join(context)]

        resp = self._generate_response(question, context, verbose)

        if verbose and len(retrieved) > 1 and "verbose" in retrieved[1]:
            resp["verbose"] = retrieved[1]["verbose"]
            resp["verbose"]["final_retrieval"] = retrieved[0]["final_retrieval"]

        return resp
