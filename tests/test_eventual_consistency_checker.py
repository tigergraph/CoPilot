import asyncio
import unittest
from unittest.mock import Mock, patch

import pytest

from app.sync.eventual_consistency_checker import EventualConsistencyChecker


class TestEventualConsistencyChecker(unittest.TestCase):
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    
    def run_async(self, coro):
        """Utility function to run coroutine in the event loop."""
        return self.loop.run_until_complete(coro)

    @patch("app.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("app.embeddings.embedding_services.EmbeddingModel")
    @patch("app.main.get_db_connection", return_value=Mock())
    def test_initialization(
        self,
        mock_get_db_connection,
        mock_embedding_model,
        mock_embedding_store,
        mock_embedding_service,
    ):
        """Test the initialization and ensure it doesn't reinitialize."""
        graphname = "testGraph"
        conn = mock_get_db_connection.return_value
        checker = EventualConsistencyChecker(
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            mock_embedding_store,
            conn,
        )

        self.assertFalse(checker.is_initialized)
        self.run_async(checker.initialize())
        self.assertTrue(checker.is_initialized)

        initial_task_count = len(asyncio.all_tasks(loop=self.loop))
        self.run_async(checker.initialize())
        self.assertEqual(len(asyncio.all_tasks(loop=self.loop)), initial_task_count)

    @patch("app.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("app.embeddings.embedding_services.EmbeddingModel")
    @patch("app.main.get_db_connection", return_value=Mock())
    def test_fetch_and_process_vertex(
        self, mock_get_db_connection, mock_embedding_model, mock_embedding_store
    ):
        """Test fetch_and_process_vertex functionality."""
        graphname = "testGraph"
        conn = mock_get_db_connection.return_value
        checker = EventualConsistencyChecker(
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            mock_embedding_store,
            conn,
        )

        conn.runInstalledQuery.side_effect = [{1: "Doc1", 2: "Doc2", 3: "Doc3"}, "true"]

        self.run_async(checker.fetch_and_process_vertex())

        # Verify the sequence of calls
        conn.runInstalledQuery.assert_any_call("Scan_For_Updates")
        conn.runInstalledQuery.assert_any_call(
            "Update_Vertices_Processing_Status", {"vertex_ids": [1, 2, 3]}
        )

        # Assertions to ensure the embedding service and store were called correctly
        mock_embedding_store.remove_embeddings.assert_called_once()
        mock_embedding_model.embed_query.assert_called()
        mock_embedding_store.add_embeddings.assert_called()


if __name__ == "__main__":
    unittest.main()
