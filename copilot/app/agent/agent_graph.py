import json
import logging
from typing import Optional

from agent.agent_generation import TigerGraphAgentGenerator
from agent.agent_hallucination_check import TigerGraphAgentHallucinationCheck
from agent.agent_rewrite import TigerGraphAgentRewriter
from agent.agent_router import TigerGraphAgentRouter
from agent.agent_usefulness_check import TigerGraphAgentUsefulnessCheck
from agent.Q import DONE, Q
from langgraph.graph import END, StateGraph
from pyTigerGraph.pyTigerGraphException import TigerGraphException
from supportai.retrievers import HNSWOverlapRetriever
from tools import MapQuestionToSchemaException
from typing_extensions import TypedDict

from common.logs.log import req_id_cv
from common.py_schemas import CoPilotResponse, MapQuestionToSchemaResponse

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
    def __init__(
        self,
        llm_provider,
        db_connection,
        embedding_model,
        embedding_store,
        mq2s_tool,
        gen_func_tool,
        cypher_gen_tool=None,
        enable_human_in_loop=False,
        q: Q = None,
    ):
        self.workflow = StateGraph(GraphState)
        self.llm_provider = llm_provider
        self.db_connection = db_connection
        self.embedding_model = embedding_model
        self.embedding_store = embedding_store
        self.mq2s = mq2s_tool
        self.gen_func = gen_func_tool
        self.cypher_gen = cypher_gen_tool
        self.enable_human_in_loop = enable_human_in_loop
        self.q = q

        self.supportai_enabled = True
        try:
            self.db_connection.getQueryMetadata("HNSW_Search_Sub")
        except TigerGraphException as e:
            logger.info("HNSW_Overlap not found in the graph. Disabling supportai.")
            self.supportai_enabled = False

    def emit_progress(self, msg):
        if self.q is not None:
            self.q.put(msg)

    def entry(self, state):
        if state.get("question_retry_count") is None:
            state["question_retry_count"] = 0
        else:
            state["question_retry_count"] += 1
        return state

    def route_question(self, state):
        """
        Run the agent router.
        """
        if state["question_retry_count"] > 2:
            return "apologize"
        self.emit_progress("Thinking")
        step = TigerGraphAgentRouter(self.llm_provider, self.db_connection)
        logger.debug_pii(
            f"request_id={req_id_cv.get()} Routing question: {state['question']}"
        )
        if self.supportai_enabled:
            source = step.route_question(state["question"])
            logger.debug_pii(
                f"request_id={req_id_cv.get()} Routing question to: {source}"
            )
            if source.datasource == "vectorstore":
                return "supportai_lookup"
            elif source.datasource == "functions":
                return "inquiryai_lookup"
        else:
            return "inquiryai_lookup"

    def apologize(self, state):
        """
        Apologize for not being able to answer the question.
        """
        self.emit_progress(DONE)
        state["answer"] = CoPilotResponse(
            natural_language_response="I'm sorry, I don't know the answer to that question. Please try rephrasing your question.",
            answered_question=False,
            response_type="error",
            query_sources={"error": "Question could not be routed to a datasource."},
        )
        return state

    def map_question_to_schema(self, state):
        """
        Run the agent schema mapping.
        """
        self.emit_progress("Mapping your question to the graph's schema")
        try:
            step = self.mq2s._run(state["question"])
            state["schema_mapping"] = step
            return state
        except MapQuestionToSchemaException:
            return "failure"

    def generate_function(self, state):
        """
        Run the agent function generator.
        """
        self.emit_progress("Generating the code to answer your question")
        try:
            step = self.gen_func._run(
                state["question"],
                state["schema_mapping"].target_vertex_types,
                state["schema_mapping"].target_vertex_attributes,
                state["schema_mapping"].target_vertex_ids,
                state["schema_mapping"].target_edge_types,
                state["schema_mapping"].target_edge_attributes,
            )
            state["context"] = step
        except Exception as e:
            state["context"] = {"error": str(e)}
        state["lookup_source"] = "inquiryai"
        return state

    def generate_cypher(self, state):
        """
        Run the agent cypher generator.
        """
        self.emit_progress("Generating the Cypher to answer your question")
        cypher = self.cypher_gen._run(state["question"])

        response = self.db_connection.gsql(cypher)
        response_lines = response.split("\n")
        try:
            json_str = "\n".join(response_lines[1:])
            response_json = json.loads(json_str)
            state["context"] = {
                "answer": response_json["results"][0],
                "cypher": cypher,
                "reasoning": "The following OpenCypher query was executed to answer the question. {}".format(
                    cypher
                ),
            }
        except:
            state["context"] = {
                "error": True,
                "error_message": response,
                "cypher": cypher,
            }

        state["lookup_source"] = "cypher"
        return state

    def hnsw_overlap_search(self, state):
        """
        Run the agent overlap search.
        """
        self.emit_progress("Searching the knowledge graph")
        retriever = HNSWOverlapRetriever(
            self.embedding_model,
            self.embedding_store,
            self.llm_provider.model,
            self.db_connection,
        )
        step = retriever.search(
            state["question"],
            indices=["Document", "DocumentChunk", "Entity", "Relationship"],
            top_k=5,
            num_seen_min=2,
            num_hops=2,
        )

        state["context"] = {
            "function_call": "HNSW_Overlap_Search",
            "result": step[0],
            "query_output_format": self.db_connection.getQueryMetadata(
                "HNSW_Overlap_Search"
            )["output"],
        }
        state["lookup_source"] = "supportai"
        return state

    def generate_answer(self, state):
        """
        Run the agent generator.
        """
        self.emit_progress("Connecting the pieces")
        step = TigerGraphAgentGenerator(self.llm_provider)
        logger.debug_pii(
            f"request_id={req_id_cv.get()} Generating answer for question: {state['question']}"
        )
        print("*****")
        print(state)
        print(state["lookup_source"])
        print("*****")
        if state["lookup_source"] == "supportai":
            answer = step.generate_answer(
                state["question"], state["context"]["result"]["@@final_retrieval"]
            )
        elif state["lookup_source"] == "inquiryai":
            answer = step.generate_answer(state["question"], state["context"]["result"])
        elif state["lookup_source"] == "cypher":
            answer = step.generate_answer(state["question"], state["context"]["answer"])
        logger.debug_pii(
            f"request_id={req_id_cv.get()} Generated answer: {answer.generated_answer}"
        )

        if state["lookup_source"] == "supportai":
            import re

            citations = [re.sub(r"_chunk_\d+", "", x) for x in answer.citation]
            state["context"]["reasoning"] = list(set(citations))
        try:
            resp = CoPilotResponse(
                natural_language_response=answer.generated_answer,
                answered_question=True,
                response_type=state["lookup_source"],
                query_sources=state["context"],
            )
        except Exception as e:
            resp = CoPilotResponse(
                natural_language_response="I'm sorry, I don't know the answer to that question.",
                answered_question=False,
                response_type=state["lookup_source"],
                query_sources={"error": str(e)},
            )
        state["answer"] = resp

        return state

    def rewrite_question(self, state):
        """
        Run the agent question rewriter.
        """
        self.emit_progress("Rephrasing the question")
        step = TigerGraphAgentRewriter(self.llm_provider)
        state["question"] = step.rewrite_question(state["question"])
        return state

    def check_answer_for_hallucinations(self, state):
        """
        Run the agent hallucination check.
        """
        self.emit_progress("Checking the response is relevant")
        step = TigerGraphAgentHallucinationCheck(self.llm_provider)
        hallucinations = step.check_hallucination(
            state["answer"].natural_language_response, state["context"]
        )
        if hallucinations.score == "yes":
            self.emit_progress(DONE)
            return "grounded"
        else:
            return "hallucination"

    def check_answer_for_usefulness(self, state):
        """
        Run the agent usefulness check.
        """
        step = TigerGraphAgentUsefulnessCheck(self.llm_provider)
        usefulness = step.check_usefulness(
            state["question"], state["answer"].natural_language_response
        )
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
                self.emit_progress(DONE)
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
        print("*****")
        print(state.get("context").get("error"))
        print("*****")
        if (
            isinstance(state.get("context"), Exception)
            and state.get("context") is not None
            and state["context"].get("error") is not None
        ):
            return "error"
        else:
            return "success"

    def create_graph(self):
        """
        Create a graph of the agent.
        """
        self.workflow.set_entry_point("entry")
        self.workflow.add_node("entry", self.entry)
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
                {"error": "generate_cypher", "success": "generate_answer"},
            )
            self.workflow.add_conditional_edges(
                "generate_cypher",
                self.check_state_for_generation_error,
                {"error": "apologize", "success": "generate_answer"},
            )
            if self.supportai_enabled:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                    {
                        "hallucination": "rewrite_question",
                        "grounded": END,
                        "inquiryai_not_useful": "generate_cypher",
                        "cypher_not_useful": "hnsw_overlap_search",
                        "supportai_not_useful": "map_question_to_schema",
                    },
                )
            else:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                    {
                        "hallucination": "rewrite_question",
                        "grounded": END,
                        "inquiryai_not_useful": "generate_cypher",
                        "cypher_not_useful": "apologize",
                    },
                )
        else:
            self.workflow.add_conditional_edges(
                "generate_function",
                self.check_state_for_generation_error,
                {"error": "rewrite_question", "success": "generate_answer"},
            )
            if self.supportai_enabled:
                self.workflow.add_conditional_edges(
                    "generate_answer",
                    self.check_answer_for_usefulness_and_hallucinations,
                    {
                        "hallucination": "rewrite_question",
                        "grounded": END,
                        "not_useful": "rewrite_question",
                        "inquiryai_not_useful": "hnsw_overlap_search",
                        "supportai_not_useful": "map_question_to_schema",
                    },
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
                        "supportai_not_useful": "map_question_to_schema",
                    },
                )

        if self.supportai_enabled:
            self.workflow.add_conditional_edges(
                "entry",
                self.route_question,
                {
                    "supportai_lookup": "hnsw_overlap_search",
                    "inquiryai_lookup": "map_question_to_schema",
                    "apologize": "apologize",
                },
            )
        else:
            self.workflow.add_conditional_edges(
                "entry",
                self.route_question,
                {
                    "inquiryai_lookup": "map_question_to_schema",
                    "apologize": "apologize",
                },
            )

        self.workflow.add_edge("map_question_to_schema", "generate_function")
        if self.supportai_enabled:
            self.workflow.add_edge("hnsw_overlap_search", "generate_answer")
        self.workflow.add_edge("rewrite_question", "entry")
        self.workflow.add_edge("apologize", END)

        app = self.workflow.compile()
        return app
