import os
from typing import List
from langchain.schema.embeddings import Embeddings

class EmbeddingModel(Embeddings):
    def __init__(self, config):
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        self.embeddings = None

    def embed_documents(self, texts: List[str]) -> List[float]:
        return self.embeddings.embed_documents(texts)

    def embed_query(self, question:str) -> List[float]:
        return self.embeddings.embed_query(question)


class AzureOpenAI_Ada002(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)
        from langchain.embeddings import AzureOpenAIEmbeddings
        self.embeddings = AzureOpenAIEmbeddings(deployment=config["azure_deployment"])


class OpenAI_Embedding(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)
        from langchain.embeddings import OpenAIEmbeddings
        self.embeddings = OpenAIEmbeddings()

class VertexAI_PaLM_Embedding(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)
        from langchain.embeddings import VertexAIEmbeddings
        self.embeddings = VertexAIEmbeddings()

class AWS_Bedrock_Embedding(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)
        from langchain.embeddings import BedrockEmbeddings
        self.embeddings = BedrockEmbeddings(credentials_profile_name = config["credentials_profile_name"],
                                            region_name = config["region_name"])