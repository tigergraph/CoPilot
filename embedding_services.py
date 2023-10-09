import os

class EmbeddingModel():
    def __init__(self, config):
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        self.embeddings = None

    def embed_doc(self, doc):
        return self.embeddings.embed_documents([doc])

    def get_embedding(self, question):
        return self.embeddings.embed_query(question)

    def compute_hnsw(self):
        pass

    def upload_to_db(self):
        pass


class AzureOpenAI_Ada002(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)
        from langchain.embeddings import OpenAIEmbeddings
        self.embeddings = OpenAIEmbeddings(deployment=config["embedding_service"]["deployment"])


class OpenAI_Embedding(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)
        from langchain.embeddings import OpenAIEmbeddings
        self.embeddings = OpenAIEmbeddings()
