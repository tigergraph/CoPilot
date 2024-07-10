import logging
import time
from typing import Dict, List

from agent.agent_graph import TigerGraphAgentGraph
from agent.Q import Q
from fastapi import WebSocket
from tools import GenerateCypher, GenerateFunction, MapQuestionToSchema

from common.config import embedding_service, embedding_store, llm_config
from common.embeddings.base_embedding_store import EmbeddingStore
from common.embeddings.embedding_services import EmbeddingModel
from common.llm_services import (
    AWS_SageMaker_Endpoint,
    AWSBedrock,
    AzureOpenAI,
    GoogleVertexAI,
    Groq,
    HuggingFaceEndpoint,
    Ollama,
    OpenAI,
)
from common.llm_services.base_llm import LLM_Model
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter
from common.metrics.prometheus_metrics import metrics
from common.metrics.tg_proxy import TigerGraphConnectionProxy

logger = logging.getLogger(__name__)


class TigerGraphAgent:
    """TigerGraph Agent Class

    The TigerGraph Agent Class combines the various dependencies needed for a AI Agent to reason with data in a TigerGraph database.

    Args:
        llm_provider (LLM_Model):
            a LLM_Model class that connects to an external LLM API service.
        db_connection (TigerGraphConnection):
            a PyTigerGraph TigerGraphConnection object instantiated to interact with the desired database/graph and authenticated with correct roles.
        embedding_model (EmbeddingModel):
            a EmbeddingModel class that connects to an external embedding API service.
        embedding_store (EmbeddingStore):
            a EmbeddingStore class that connects to an embedding store to retrieve pyTigerGraph and custom query documentation from.
    """

    def __init__(
        self,
        llm_provider: LLM_Model,
        db_connection: TigerGraphConnectionProxy,
        embedding_model: EmbeddingModel,
        embedding_store: EmbeddingStore,
        use_cypher: bool = False,
        ws=None,
        supportai_retriever="hnsw_overlap"
    ):
        self.conn = db_connection

        self.llm = llm_provider
        self.model_name = embedding_model.model_name
        self.embedding_model = embedding_model
        self.embedding_store = embedding_store

        self.mq2s = MapQuestionToSchema(
            self.conn, self.llm.model, self.llm.map_question_schema_prompt
        )
        self.gen_func = GenerateFunction(
            self.conn,
            self.llm.model,
            self.llm.generate_function_prompt,
            embedding_model,
            embedding_store,
        )

        self.cypher_tool = None
        if use_cypher:
            self.cypher_tool = GenerateCypher(self.conn, self.llm)

        self.q = None
        if ws is not None:
            self.q = Q()
        else:
            self.q = None

        self.agent = TigerGraphAgentGraph(
            self.llm,
            self.conn,
            self.embedding_model,
            self.embedding_store,
            self.mq2s,
            self.gen_func,
            cypher_gen_tool=self.cypher_tool,
            q=self.q,
            supportai_retriever=supportai_retriever
        ).create_graph()

        logger.debug(f"request_id={req_id_cv.get()} agent initialized")

    def question_for_agent(
        self, question: str, conversation: List[Dict[str, str]] = None
    ):
        """Question for Agent.

        Ask the agent a question to be answered by the database. Returns the agent response or raises an exception.

        Args:
            question (str):
                The question to ask the agent
        """
        start_time = time.time()
        metrics.llm_inprogress_requests.labels(self.model_name).inc()

        try:
            LogWriter.info(f"request_id={req_id_cv.get()} ENTRY question_for_agent")
            logger.debug_pii(
                f"request_id={req_id_cv.get()} question_for_agent question={question}"
            )

            input_data = {}
            input_data["input"] = question
            logger.info(f"conversation: {conversation}")

            if conversation is not None:
                input_data["conversation"] = [
                    {"query": chat["query"], "response": chat["response"]}
                    for chat in conversation
                ]
            else:
                # Handle the case where conversation is None or empty
                input_data["conversation"] = []
            logger.info(f"input_data: {input_data}")

            for output in self.agent.stream({"question": str(input_data)}):
                for key, value in output.items():
                    LogWriter.info(f"request_id={req_id_cv.get()} executed node {key}")

            LogWriter.info(f"request_id={req_id_cv.get()} EXIT question_for_agent")
            return value["answer"]
        except Exception as e:
            metrics.llm_query_error_total.labels(self.model_name).inc()
            LogWriter.error(f"request_id={req_id_cv.get()} FAILURE question_for_agent")
            import traceback

            traceback.print_exc()
            raise e
        finally:
            metrics.llm_request_total.labels(self.model_name).inc()
            metrics.llm_inprogress_requests.labels(self.model_name).dec()
            duration = time.time() - start_time
            metrics.llm_request_duration_seconds.labels(self.model_name).observe(
                duration
            )


def make_agent(graphname, conn, use_cypher, ws: WebSocket = None, supportai_retriever="hnsw_overlap") -> TigerGraphAgent:
    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        llm_service_name = "openai"
        llm_provider = OpenAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        llm_service_name = "azure"
        llm_provider = AzureOpenAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        llm_service_name = "sagemaker"
        llm_provider = AWS_SageMaker_Endpoint(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "vertexai":
        llm_service_name = "vertexai"
        llm_provider = GoogleVertexAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "bedrock":
        llm_service_name = "bedrock"
        llm_provider = AWSBedrock(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "groq":
        llm_service_name = "groq"
        llm_provider = Groq(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "ollama":
        llm_service_name = "ollama"
        llm_provider = Ollama(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "huggingface":
        llm_service_name = "huggingface"
        llm_provider = HuggingFaceEndpoint(llm_config["completion_service"])
    else:
        LogWriter.error(
            f"/{graphname}/query_with_history request_id={req_id_cv.get()} agent creation failed due to invalid llm_service"
        )
        raise Exception("LLM Completion Service Not Supported")

    logger.debug(
        f"/{graphname}/query_with_history request_id={req_id_cv.get()} llm_service={llm_service_name} agent created"
    )

    agent = TigerGraphAgent(
        llm_provider,
        conn,
        embedding_service,
        embedding_store,
        use_cypher=use_cypher,
        ws=ws,
        supportai_retriever=supportai_retriever
    )
    return agent
