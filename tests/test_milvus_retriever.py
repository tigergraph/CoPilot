import unittest
from unittest.mock import patch, MagicMock
from app.supportai.retrievers import MilvusRetriever 

class TestMilvusRetriever(unittest.TestCase):

    @patch('app.supportai.retrievers.BaseRetriever._generate_response')
    @patch('app.supportai.retrievers.BaseRetriever._generate_embedding')
    @patch('pymilvus.Milvus') 
    def test_retrieve_answer(self, mock_milvus, mock_generate_embedding, mock_generate_response):
        mock_embedding = [0.1, 0.2, 0.3]
        mock_generate_embedding.return_value = mock_embedding

        mock_milvus_instance = MagicMock()
        mock_milvus.return_value = mock_milvus_instance
        
        mock_search_result = MagicMock()
        mock_milvus_instance.search.return_value = mock_search_result
        mock_generate_response.return_value = "Mocked response"

        retriever = MilvusRetriever(embedding_service=MagicMock(), llm_service=MagicMock(), milvus_client=mock_milvus_instance)

        result = retriever.retrieve_answer(question="What is the meaning of life?", index="my_index", top_k=5)

        mock_milvus_instance.search.assert_called_once()
        mock_generate_response.assert_called_once_with("What is the meaning of life?", mock_search_result)
        self.assertEqual(result, "Mocked response")

if __name__ == "__main__":
    unittest.main()
