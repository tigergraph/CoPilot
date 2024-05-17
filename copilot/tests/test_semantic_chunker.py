import unittest
from unittest.mock import Mock, patch
from app.supportai.chunkers.semantic_chunker import SemanticChunker


class TestSemanticChunker(unittest.TestCase):
    @patch("common.embeddings.embedding_services.EmbeddingModel")
    @patch("langchain_experimental.text_splitter.SemanticChunker.create_documents")
    def test_chunk_single_string(self, create_documents, MockEmbeddingModel):
        mock_emb_service = MockEmbeddingModel()

        create_documents.return_value = [
            Mock(page_content="Chunk 1"),
            Mock(page_content="Chunk 2"),
        ]

        semantic_chunker = SemanticChunker(embedding_serivce=mock_emb_service)
        input_string = "Chunk 1, Chunk 2, Chunk Unrelated"
        expected_chunks = ["Chunk 1", "Chunk 2"]
        actual_chunks = semantic_chunker.chunk(input_string)

        create_documents.assert_called_once_with([input_string])
        self.assertEqual(actual_chunks, expected_chunks)


if __name__ == "__main__":
    unittest.main()
