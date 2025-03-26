import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator

from supportai.retrievers import BaseRetriever
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.llm_services import LLM_Model
from common.config import embedding_store_type

class CommunityAnswer(BaseModel):
    answer: str = Field(description="The answer to the question, based off of the context provided.")
    quality_score: int = Field(description="The quality of the answer, based on how well it answers the question. Rate the answer from 0 (poor) to 100 (excellent).")

output_parser = PydanticOutputParser(pydantic_object=CommunityAnswer)

ANSWER_PROMPT = PromptTemplate(template = """
You are a helpful assistant responsible for generating an answer to the question below using the data provided.
Include a quality score for the answer, based on how well it answers the question. The quality score should be between 0 (poor) and 100 (excellent).
                                                
Question: {question}
Context: {context}

{format_instructions}
""",
input_variables=["question", "context"],
partial_variables={"format_instructions": output_parser.get_format_instructions()}
)


class GraphRAGRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service: LLM_Model,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)

    def search(self, question, community_level: int, top_k: int = 5, with_chunk: bool = True, verbose: bool = False):
        if embedding_store_type == "milvus":
            self._check_query_install("GraphRAG_Community_Search")

            query_embedding = self._generate_embedding(question)

            res = self.conn.runInstalledQuery(
                "GraphRAG_Community_Search",
                self.embedding_store.add_connection_parameters(
                    {
                        "collection_prefix": self.conn.graphname,
                        "query_vector_as_string": query_embedding,
                        "community_level": community_level,
                        "top_k": top_k,
                        "with_chunk": with_chunk,
                        "verbose": verbose,
                    }
                ),
                usePost=True
            )
        else:
            self._check_query_install("GraphRAG_Community_Vector_Search")

            query_embedding = self._generate_embedding(question, False)

            res = self.conn.runInstalledQuery(
                "GraphRAG_Community_Vector_Search",
                params = {
                    "community_level": community_level,
                    "query_vector": query_embedding,
                    "top_k": top_k,
                    "with_chunk": with_chunk,
                    "verbose": verbose,
                },
                usePost=True
            )
        if len(res) > 1 and "verbose" in res[1]:
            verbose_info = json.dumps(res[1]['verbose'])
            self.logger.info(f"Retrived GraphRAG query verbose info: {verbose_info}")
        return res
    
    async def _generate_candidate(self, question, context):
        model = self.llm_service.model

        chain = ANSWER_PROMPT | model | output_parser

        answer = await chain.ainvoke(
            {
                "question": question,
                "context": context,
            }
        )
        return answer
    
    def gather_candidates(self, question, context):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [self._generate_candidate(question, c) for c in context]
        res = loop.run_until_complete(asyncio.gather(*tasks))
        loop.close()
        return res
    
    def retrieve_answer(self,
                        question: str,
                        community_level: int,
                        top_k: int = 1,
                        with_chunk: bool = False,
                        combine: bool = False,
                        verbose: bool = False):
        retrieved = self.search(question, community_level, top_k, with_chunk, verbose)
        
        context = []
        if combine:
            for x in retrieved[0]["final_retrieval"]:
                context += retrieved[0]["final_retrieval"][x]
            context = ["\n".join(set(context))]
        else:
            context = ["\n".join(retrieved[0]["final_retrieval"][x]) for x in retrieved[0]["final_retrieval"]]

        with ThreadPoolExecutor() as executor:
            res = executor.submit(self.gather_candidates, question, context).result()

        # sort list by quality score
        res.sort(key=lambda x: x.quality_score, reverse=True)

        new_context = [{"candidate_answer": x.answer,
                        "score": x.quality_score} for x in res[:top_k]]
        
        resp = self._generate_response(question, new_context, verbose)

        if verbose and len(retrieved) > 1 and "verbose" in retrieved[1]:
            resp["verbose"] = retrieved[1]["verbose"]
            resp["verbose"]["final_retrieval"] = retrieved[0]["final_retrieval"]

        return resp
