from supportai.retrievers import BaseRetriever
import asyncio
from concurrent.futures import ThreadPoolExecutor

from common.metrics.tg_proxy import TigerGraphConnectionProxy

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator

from common.llm_services import LLM_Model


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


class GraphRAG(BaseRetriever):
    def __init__(
        self,
        embedding_service,
        embedding_store,
        llm_service: LLM_Model,
        connection: TigerGraphConnectionProxy,
    ):
        super().__init__(embedding_service, embedding_store, llm_service, connection)
        self._check_query_install("GraphRAG_CommunityRetriever")

    def search(self, question, community_level: int):
        res = self.conn.runInstalledQuery("GraphRAG_CommunityRetriever", {"community_level": community_level}, usePost=True)
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
                        top_k_answer_candidates: int = 1):
        retrieved = self.search(question, community_level)
        context = [x["attributes"] for x in retrieved[0]["selected_comms"]]
        
        with ThreadPoolExecutor() as executor:
            res = executor.submit(self.gather_candidates, question, context).result()

        # sort list by quality score
        res.sort(key=lambda x: x.quality_score, reverse=True)

        new_context = [{"candidate_answer": x.answer,
                        "score": x.quality_score} for x in res[:top_k_answer_candidates]]
        
        return self._generate_response(question, new_context)
