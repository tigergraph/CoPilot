import json
import os
import unittest
from unittest.mock import patch, MagicMock

from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from langchain_core.documents import Document

class TestMilvusEmbeddingStore(unittest.TestCase):

    @patch("app.embeddings.embedding_services.EmbeddingModel")
    @patch("app.embeddings.milvus_embedding_store.MilvusEmbeddingStore.connect_to_milvus")
    def test_add_embeddings(self, mock_connect, mock_embedding_model):
        query = "What is the meaning of life?"
        embedded_query = [0.1, 0.2, 0.3]
        embedded_documents = [[0.1, 0.2, 0.3]]
        mock_embedding_model.embed_query.return_value = embedded_query
        mock_embedding_model.embed_documents.return_value = embedded_documents
        mock_connect.return_value = None

        embedding_store = MilvusEmbeddingStore(
            embedding_service=mock_embedding_model,
            host="localhost",
            port=19530,
            support_ai_instance=True,
        )
        embedding_store.milvus = MagicMock()
        
        embedding_store.add_embeddings(embeddings=[(query, embedded_documents)])
        embedding_store.milvus.add_texts.assert_called_once_with(texts=[query], metadatas=[])

    @patch("app.embeddings.milvus_embedding_store.MilvusEmbeddingStore.connect_to_milvus")
    def test_retrieve_embeddings(self, mock_connect):
        mock_connect.return_value = None
        embedded_query = [0.1, 0.2, 0.3]
        docs = [
            Document(
                page_content="What is the meaning of life?",
                metadata={
                    "last_updated_at": 1710352745,
                    "vertex_id": "123",
                    "pk": 448308749969916221,
                },
            )
        ]

        embedding_store = MilvusEmbeddingStore(
            embedding_service=MagicMock(),
            host="localhost",
            port=19530,
            support_ai_instance=True,
        )
        embedding_store.milvus = MagicMock()
        embedding_store.milvus.similarity_search_by_vector.return_value = docs

        result = embedding_store.retrieve_similar(
            query_embedding=embedded_query, top_k=4
        )

        embedding_store.milvus.similarity_search_by_vector.assert_called_once_with(embedding=embedded_query, k=4, expr=None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].page_content, "What is the meaning of life?")
        self.assertEqual(result[0].metadata["vertex_id"], "123")


if __name__ == "__main__":
    unittest.main()
