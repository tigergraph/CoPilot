from typing_extensions import TypedDict
import json
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

import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

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
                 cypher_gen_tool = None,
                 enable_human_in_loop=False):
        self.workflow = StateGraph(GraphState)
        self.llm_provider = llm_provider
        self.db_connection = db_connection
        self.embedding_model = embedding_model
        self.embedding_store = embedding_store
        self.mq2s = mq2s_tool
        self.gen_func = gen_func_tool
        self.cypher_gen = cypher_gen_tool
        self.enable_human_in_loop = enable_human_in_loop

        self.supportai_enabled = True
        if "'The query: HNSW_Overlap does not exists in graph" in self.db_connection.getQueryMetadata("HNSW_Overlap"):
            self.supportai_enabled = True

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
        logger.debug_pii(f"request_id={req_id_cv.get()} Routing question: {state['question']}")
        source = step.route_question(state['question'])
        logger.debug_pii(f"request_id={req_id_cv.get()} Routing question to: {source}")
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
        try:
            step = self.gen_func._run(state['question'],
                                    state["schema_mapping"].target_vertex_types,
                                    state["schema_mapping"].target_vertex_attributes,
                                    state["schema_mapping"].target_vertex_ids,
                                    state["schema_mapping"].target_edge_types,
                                    state["schema_mapping"].target_edge_attributes)
            state["context"] = step
        except Exception as e:
            state["context"] = {"error": str(e)}
        state["lookup_source"] = "inquiryai"
        return state
    
    def generate_cypher(self, state):
        """
        Run the agent cypher generator.
        """
        cypher = self.cypher_gen._run(state['question'])

        response = self.db_connection.gsql(cypher)
        response_lines = response.split('\n')
        try:
            json_str = '\n'.join(response_lines[1:])
            response_json = json.loads(json_str)
            state["context"] = {"answer": response_json["results"][0], "cypher": cypher}
        except:
            state["context"] = {"error": True, "error_message": response, "cypher": cypher}

        state["lookup_source"] = "cypher"
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
        logger.debug_pii(f"request_id={req_id_cv.get()} Generating answer for question: {state['question']}")
        if state["lookup_source"] == "supportai":
            answer = step.generate_answer(state['question'], state["context"])
        elif state["lookup_source"] == "inquiryai":
            answer = step.generate_answer(state['question'], state["context"]["result"])
        elif state["lookup_source"] == "cypher":
            answer = step.generate_answer(state['question'], state["context"]["answer"])
        logger.debug_pii(f"request_id={req_id_cv.get()} Generated answer: {answer.generated_answer}")

        try:
            resp = CoPilotResponse(natural_language_response=answer.generated_answer,
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
        hallucinations = step.check_hallucination(state["answer"].natural_language_response, state["context"])
        if hallucinations.score == "yes":
            return "grounded"
        else:
            return "hallucination"
        
    def check_answer_for_usefulness(self, state):
        """
        Run the agent usefulness check.
        """
        step = TigerGraphAgentUsefulnessCheck(self.llm_provider)
        usefulness = step.check_usefulness(state["question"], state["answer"].natural_language_response)
        if usefulness.score == "yes":
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
                if state["lookup_source"] == "supportai":
                    return "supportai_not_useful"
                elif state["lookup_source"] == "inquiryai":
                    return "inquiryai_not_useful"
                elif state["lookup_source"] == "cypher":
                    return "cypher_not_useful"
        
    def check_state_for_generation_error(self, state):
        """
        Check if the state has an error.
        """
        if state["context"].get("error") is not None:
            return "error"
        else:
            return "success"

    def create_graph(self):
        """
        Create a graph of the agent.
        """
        self.workflow.set_entry_point("entry")
        self.workflow.add_node("entry", lambda x: x)
        self.workflow.add_node("generate_answer", self.generate_answer)
        self.workflow.add_node("map_question_to_schema", self.map_question_to_schema)
        self.workflow.add_node("generate_function", self.generate_function)
        if self.supportai_enabled:
            self.workflow.add_node("hnsw_overlap_search", self.hnsw_overlap_search)
        self.workflow.add_node("rewrite_question", self.rewrite_question)
        self.workflow.add_node("apologize", self.apologize)

        if self.cypher_gen:
            self.workflow.add_node("generate_cypher", self.generate_cypher)
            self.workflow.add_conditional_edges(
                "generate_function",
                self.check_state_for_generation_error,
                {
                    "error": "generate_cypher",
                    "success": "generate_answer"
                }
            )
            self.workflow.add_conditional_edges("generate_cypher",
                                                self.check_state_for_generation_error,
                                                {
                                                    "error": "apologize",
                                                    "success": "generate_answer"
                                                })
            if self.supportai_enabled:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                        {
                            "hallucination": "rewrite_question",
                            "grounded": END,
                            "inquiryai_not_useful": "generate_cypher",
                            "cypher_not_useful": "hnsw_overlap_search",
                            "supportai_not_useful": "map_question_to_schema"
                        }
                    )
            else:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                        {
                            "hallucination": "rewrite_question",
                            "grounded": END,
                            "inquiryai_not_useful": "generate_cypher",
                            "cypher_not_useful": "apologize"
                        }
                    )
        else:
            self.workflow.add_edge("generate_function", "generate_answer")
            if self.supportai_enabled:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                        {
                            "hallucination": "rewrite_question",
                            "grounded": END,
                            "not_useful": "rewrite_question",
                            "inquiryai_not_useful": "hnsw_overlap_search",
                            "supportai_not_useful": "map_question_to_schema"
                        }
                )
            else:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                        {
                            "hallucination": "rewrite_question",
                            "grounded": END,
                            "not_useful": "rewrite_question",
                            "inquiryai_not_useful": "apologize",
                            "supportai_not_useful": "map_question_to_schema"
                        }
                )

        if self.supportai_enabled:
            self.workflow.add_conditional_edges(
                "entry",
                self.route_question,
                {
                    "supportai_lookup": "hnsw_overlap_search",
                    "inquiryai_lookup": "map_question_to_schema",
                    "apologize": "apologize"
                }
            )
        else:
            self.workflow.add_edge("entry", "map_question_to_schema")

        self.workflow.add_edge("map_question_to_schema", "generate_function")
        if self.supportai_enabled:
            self.workflow.add_edge("hnsw_overlap_search", "generate_answer")
        self.workflow.add_edge("rewrite_question", "entry")
        self.workflow.add_edge("apologize", END)
        

        app = self.workflow.compile()
        return app

                                            