import unittest
from unittest.mock import patch, MagicMock
from app.supportai.retrievers import MilvusRetriever 

class TestMilvusRetriever(unittest.TestCase):

    @patch('app.supportai.retrievers.BaseRetriever._generate_response')
    @patch('app.supportai.retrievers.BaseRetriever._generate_embedding')
    @patch('app.embeddings.milvus_embedding_store.MilvusEmbeddingStore') 
    def test_retrieve_answer(self, mock_milvus_embedding, mock_generate_embedding, mock_generate_response):
        mock_embedding = "0.1,0.2,0.3"
        mock_generate_embedding.return_value = mock_embedding

        mock_milvus_embedding_store = MagicMock()
        mock_milvus_embedding.return_value = mock_milvus_embedding_store
        
        mock_search_result = MagicMock()
        mock_milvus_embedding_store.retrieve_similar_ids.return_value = mock_search_result
        mock_generate_response.return_value = "Mocked response"

        retriever = MilvusRetriever(embedding_service=MagicMock(), llm_service=MagicMock(), milvus_embedding_store=mock_milvus_embedding_store, connection=MagicMock())

        result = retriever.retrieve_answer(question="What is the meaning of life?", top_k=5)

        mock_milvus_embedding_store.retrieve_similar_ids.assert_called_once()
        mock_generate_response.assert_called_once_with("What is the meaning of life?", mock_search_result)
        self.assertEqual(result, "Mocked response")

if __name__ == "__main__":
    unittest.main()
