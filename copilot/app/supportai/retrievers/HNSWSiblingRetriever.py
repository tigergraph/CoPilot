import json
from supportai.retrievers import BaseRetriever
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.config import embedding_store_type


class HNSWSiblingRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)

    def search(self, question, index, top_k=1, lookback=3, lookahead=3, expand=False, withHyDE=False, verbose=False):
        if expand:
            questions = self._expand_question(question, top_k, verbose)
        else:
            questions = [question]
        start_set = self._generate_start_set(questions, [index], top_k, withHyDE=withHyDE, verbose=verbose)

        self._check_query_install("HNSW_Chunk_Sibling_Search")
        res = self.conn.runInstalledQuery(
            "HNSW_Chunk_Sibling_Search",
            params = {
                "json_list_vts": str(start_set),
                "v_type": index,
                "lookback": lookback,
                "lookahead": lookahead,
                "verbose": verbose,
            },
            usePost=True
        )
        if len(res) > 1 and "verbose" in res[1]:
            verbose_info = json.dumps(res[1]['verbose'])
            self.logger.info(f"Retrived HNSWChunkSibling query verbose info: {verbose_info}")
            res[1]["verbose"]["expanded_questions"] = questions
        return res

    def retrieve_answer(
        self, question, index, top_k=1, lookback=3, lookahead=3, withHyDE=False, expand=False, combine=False, verbose=False
    ):
        retrieved = self.search(question, index, top_k, lookback, lookahead, withHyDE, expand, verbose)
        content = {}
        for x in retrieved[0]["final_retrieval"]:
            content[x] = [retrieved[0]["final_retrieval"][x][y]["content"] for y in retrieved[0]["final_retrieval"][x]]

        context = ["\n".join(content[x]) for x in content]
        if combine:
            context = ["\n ".join(context)]

        resp = self._generate_response(question, context, verbose)

        if verbose and len(retrieved) > 1 and "verbose" in retrieved[1]:
            resp["verbose"] = retrieved[1]["verbose"]
            resp["verbose"]["final_retrieval"] = retrieved[0]["final_retrieval"]

        return resp
