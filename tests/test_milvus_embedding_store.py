import unittest
from unittest.mock import patch, MagicMock
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore 
from langchain_core.documents import Document

class TestMilvusEmbeddingStore(unittest.TestCase):

    @patch('app.embeddings.embedding_services.EmbeddingModel')
    @patch('langchain_community.vectorstores.milvus.Milvus.add_texts') 
    def test_add_embeddings(self, mock_milvus_function, mock_embedding_model):
        query = "What is the meaning of life?"
        embedded_query = [0.1,0.2,0.3]
        embedded_documents = [[0.1,0.2,0.3]]
        mock_embedding_model.embed_query.return_value = embedded_query
        mock_embedding_model.embed_documents.return_value = embedded_documents
        mock_milvus_function.return_value = None

        embedding_store = MilvusEmbeddingStore(embedding_service=mock_embedding_model, host="localhost", port=19530)
        embedding_store.add_embeddings(embeddings=[(query, embedded_documents)])

        mock_milvus_function.assert_called_once_with(texts=[query], metadatas=None)

    @patch('langchain_community.vectorstores.milvus.Milvus.similarity_search_by_vector') 
    def test_retrieve_embeddings(self, mock_milvus_function):
        embedded_query = [0.1,0.2,0.3]
        docs = [
            Document(
                page_content="A bunch of scientists bring back dinosaurs and mayhem breaks loose",
                metadata={"year": 1993, "rating": 7.7, "genre": "action"},
            ),
            Document(
                page_content="Leo DiCaprio gets lost in a dream within a dream within a dream within a ...",
                metadata={"year": 2010, "genre": "thriller", "rating": 8.2},
            )
        ]
        mock_milvus_function.return_value = docs

        embedding_store = MilvusEmbeddingStore(embedding_service=MagicMock(), host="localhost", port=19530)
        embedding_store.retrieve_similar(query_embedding=embedded_query, top_k=4)

        mock_milvus_function.assert_called_once_with(embedding=embedded_query, k=4)

if __name__ == "__main__":
    unittest.main()
