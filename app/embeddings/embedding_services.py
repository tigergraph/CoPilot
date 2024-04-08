import os
from typing import List
from langchain.schema.embeddings import Embeddings
import logging
import time
from app.log import req_id_cv
from app.metrics.prometheus_metrics import metrics
from app.tools.logwriter import LogWriter

logger = logging.getLogger(__name__)

class EmbeddingModel(Embeddings):
    """ EmbeddingModel.
        Implements connections to the desired embedding API.
    """
    def __init__(self, config: dict, model_name: str):
        """ Initialize an EmbeddingModel
            Read JSON config file and export the details as environment variables.
        """
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        self.embeddings = None
        self.model_name = model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """ Embed Documents.
            Generate embeddings for a list of documents.
            
            Args:
                texts (List[str]):
                    List of documents to embed.
            Returns:
                Nested lists of floats that contain embeddings.
        """
        start_time = time.time()
        metrics.llm_inprogress_requests.labels(self.model_name).inc()

        try:
            LogWriter.info(f"request_id={req_id_cv.get()} ENTRY embed_documents()")
            docs = self.embeddings.embed_documents(texts)
            LogWriter.info(f"request_id={req_id_cv.get()} EXIT embed_documents()")
            metrics.llm_success_response_total.labels(self.model_name).inc()
            return docs
        except Exception as e:
            metrics.llm_query_error_total.labels(self.model_name).inc()
            raise e
        finally:
            metrics.llm_request_total.labels(self.model_name).inc()
            metrics.llm_inprogress_requests.labels(self.model_name).dec()
            duration = time.time() - start_time
            metrics.llm_request_duration_seconds.labels(self.model_name).observe(duration)

    def embed_query(self, question: str) -> List[float]:
        """ Embed Query.
            Embed a string.

            Args:
                question (str):
                    A string to embed.
        """
        start_time = time.time()
        metrics.llm_inprogress_requests.labels(self.model_name).inc()

        try:
            LogWriter.info(f"request_id={req_id_cv.get()} ENTRY embed_query()")
            logger.debug_pii(f"request_id={req_id_cv.get()} embed_query() embedding question={question}")
            query_embedding = self.embeddings.embed_query(question)
            LogWriter.info(f"request_id={req_id_cv.get()} EXIT embed_query()")
            metrics.llm_success_response_total.labels(self.model_name).inc()
            return query_embedding
        except Exception as e:
            metrics.llm_query_error_total.labels(self.model_name).inc()
            raise e
        finally:
            metrics.llm_request_total.labels(self.model_name).inc()
            metrics.llm_inprogress_requests.labels(self.model_name).dec()
            duration = time.time() - start_time
            metrics.llm_request_duration_seconds.labels(self.model_name).observe(duration)


class AzureOpenAI_Ada002(EmbeddingModel):
    """ Azure OpenAI Ada-002 Embedding Model
    """
    def __init__(self, config):
        super().__init__(config, model_name=config.get("model_name", "OpenAI ada-002"))
        from langchain.embeddings import AzureOpenAIEmbeddings
        self.embeddings = AzureOpenAIEmbeddings(deployment=config["azure_deployment"])


class OpenAI_Embedding(EmbeddingModel):
    """ OpenAI Embedding Model
    """
    def __init__(self, config):
        super().__init__(config, model_name=config.get("model_name", "OpenAI gpt-4-0613"))
        from langchain.embeddings import OpenAIEmbeddings
        self.embeddings = OpenAIEmbeddings()

class VertexAI_PaLM_Embedding(EmbeddingModel):
    """ VertexAI PaLM Embedding Model
    """
    def __init__(self, config):
        super().__init__(config, model_name=config.get("model_name", "VertexAI PaLM"))
        from langchain.embeddings import VertexAIEmbeddings
        self.embeddings = VertexAIEmbeddings()

class AWS_Bedrock_Embedding(EmbeddingModel):
    """AWS Bedrock Embedding Model"""

    def __init__(self, config):
        from langchain_community.embeddings import BedrockEmbeddings
        import boto3

        super().__init__(config=config, model_name=config["embedding_model"])

        client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",
            aws_access_key_id=config["authentication_configuration"][
                "AWS_ACCESS_KEY_ID"
            ],
            aws_secret_access_key=config["authentication_configuration"][
                "AWS_SECRET_ACCESS_KEY"
            ],
        )
        self.embeddings = BedrockEmbeddings(client=client)
