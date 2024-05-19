from typing_extensions import TypedDict
from typing import Optional
from langgraph.graph import END, StateGraph

from app.agent.agent_generation import TigerGraphAgentGenerator
from app.agent.agent_router import TigerGraphAgentRouter
from app.agent.agent_hallucination_check import TigerGraphAgentHallucinationCheck
from app.agent.agent_usefulness_check import TigerGraphAgentUsefulnessCheck
from app.agent.agent_rewrite import TigerGraphAgentRewriter

from app.tools import MapQuestionToSchemaException
from app.supportai.retrievers import HNSWOverlapRetriever

from app.py_schemas import (MapQuestionToSchemaResponse,
                            CoPilotResponse)
class GraphState(TypedDict):
    """
    Represents the state of the agent graph.
    
    """
    question: str
    generation: str
    context: str
    answer: Optional[CoPilotResponse]
    lookup_source: Optional[str]
    schema_mapping: Optional[MapQuestionToSchemaResponse]
    question_retry_count: int = 0


class TigerGraphAgentGraph:
    def __init__(self, llm_provider,
                 db_connection,
                 embedding_model,
                 embedding_store,
                 mq2s_tool,
                 gen_func_tool,
                 enable_human_in_loop=False):
        self.workflow = StateGraph(GraphState)
        self.llm_provider = llm_provider
        self.db_connection = db_connection
        self.embedding_model = embedding_model
        self.embedding_store = embedding_store
        self.mq2s = mq2s_tool
        self.gen_func = gen_func_tool
        self.enable_human_in_loop = enable_human_in_loop

    def route_question(self, state):
        """
        Run the agent router.
        """
        step = TigerGraphAgentRouter(self.llm_provider, self.db_connection)
        if state.get("question_retry_count") is None:
            state["question_retry_count"] = 0
        elif state["question_retry_count"] > 2:
            return "apologize"
        state["question_retry_count"] += 1
        source = step.route_question(state['question'])
        if source.datasource == "vectorstore":
            return "supportai_lookup"
        elif source.datasource == "functions":
            return "inquiryai_lookup"
        
    def apologize(self, state):
        """
        Apologize for not being able to answer the question.
        """
        state["answer"] = CoPilotResponse(natural_language_response="I'm sorry, I don't know the answer to that question. Please try rephrasing your question.",
                                answered_question=False,
                                response_type="error",
                                query_sources={"error": "Question could not be routed to a datasource."})
        return state
        
    def map_question_to_schema(self, state):
        """
        Run the agent schema mapping.
        """
        try:
            step = self.mq2s._run(state['question'])
            state["schema_mapping"] = step
            return state
        except MapQuestionToSchemaException:
            return "failure"
        
    
    def generate_function(self, state):
        """
        Run the agent function generator.
        """
        step = self.gen_func._run(state['question'],
                                  state["schema_mapping"].target_vertex_types,
                                  state["schema_mapping"].target_vertex_attributes,
                                  state["schema_mapping"].target_vertex_ids,
                                  state["schema_mapping"].target_edge_types,
                                  state["schema_mapping"].target_edge_attributes)
        state["context"] = step
        state["lookup_source"] = "inquiryai"
        return state
    
    def hnsw_overlap_search(self, state):
        """
        Run the agent overlap search.
        """
        retriever = HNSWOverlapRetriever(self.embedding_model,
                                         self.embedding_store,
                                         self.llm_provider.model,
                                         self.db_connection)
        step = retriever.search(state['question'],
                                indices=["Document", "DocumentChunk",
                                         "Entity", "Relationship"],
                                num_seen_min=2)

        state["context"] = step[0]
        state["lookup_source"] = "supportai"
        return state
        
    
    def generate_answer(self, state):
        """
        Run the agent generator.
        """
        step = TigerGraphAgentGenerator(self.llm_provider)
        answer = step.generate_answer(state['question'], state["context"])

        try:
            resp = CoPilotResponse(natural_language_response=answer,
                                answered_question=True,
                                response_type=state["lookup_source"],
                                query_sources=state["context"])
        except Exception as e:
            resp = CoPilotResponse(natural_language_response="I'm sorry, I don't know the answer to that question.",
                                answered_question=False,
                                response_type=state["lookup_source"],
                                query_sources={"error": str(e)})
        state["answer"] = resp
        
        return state
    
    def rewrite_question(self, state):
        """
        Run the agent question rewriter.
        """
        step = TigerGraphAgentRewriter(self.llm_provider)
        state["question"] = step.rewrite_question(state["question"])
        return state
    
    def check_answer_for_hallucinations(self, state):
        """
        Run the agent hallucination check.
        """
        step = TigerGraphAgentHallucinationCheck(self.llm_provider)
        hallucinations = step.check_hallucination(state["answer"], state["context"])
        if hallucinations["score"] == "yes":
            return "grounded"
        else:
            return "hallucination"
        
    def check_answer_for_usefulness(self, state):
        """
        Run the agent usefulness check.
        """
        step = TigerGraphAgentUsefulnessCheck(self.llm_provider)
        usefulness = step.check_usefulness(state["question"], state["answer"])
        if usefulness["score"] == "yes":
            return "useful"
        else:
            return "not_useful"
        
    def check_answer_for_usefulness_and_hallucinations(self, state):
        """
        Run the agent usefulness and hallucination check.
        """
        hallucinated = self.check_answer_for_hallucinations(state)
        if hallucinated == "hallucination":
            return "hallucination"
        else:
            useful = self.check_answer_for_usefulness(state)
            if useful == "useful":
                return "grounded"
            else:
                return "not_useful"

    def create_graph(self):
        """
        Create a graph of the agent.
        """
        self.workflow.set_entry_point("entry")
        self.workflow.add_node("entry", lambda x: x)
        self.workflow.add_node("generate_answer", self.generate_answer)
        self.workflow.add_node("map_question_to_schema", self.map_question_to_schema)
        self.workflow.add_node("generate_function", self.generate_function)
        self.workflow.add_node("hnsw_overlap_search", self.hnsw_overlap_search)
        self.workflow.add_node("rewrite_question", self.rewrite_question)
        self.workflow.add_node("apologize", self.apologize)

        self.workflow.add_conditional_edges(
            "entry",
            self.route_question,
            {
                "supportai_lookup": "hnsw_overlap_search",
                "inquiryai_lookup": "map_question_to_schema",
                "apologize": "apologize"
            }
        )

        self.workflow.add_edge("map_question_to_schema", "generate_function")
        self.workflow.add_edge("generate_function", "generate_answer")
        self.workflow.add_edge("hnsw_overlap_search", "generate_answer")
        self.workflow.add_edge("rewrite_question", "entry")
        self.workflow.add_edge("apologize", END)
        self.workflow.add_conditional_edges(
            "generate_answer",
            self.check_answer_for_usefulness_and_hallucinations,
            {
                "hallucination": "rewrite_question",
                "grounded": END,
                "not_useful": "rewrite_question"
            }
        )

        app = self.workflow.compile()
        return app

                                            