import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock
from app.sync.eventual_consistency_checker import EventualConsistencyChecker


class TestEventualConsistencyChecker(unittest.TestCase):
    @patch("app.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("app.embeddings.embedding_services.EmbeddingModel")
    @patch("app.util.get_db_connection_id_token", return_value=Mock())
    def test_initialization(
        self,
        mock_get_db_connection,
        mock_embedding_model,
        mock_embedding_store
    ):
        """Test the initialization and ensure it doesn't reinitialize."""
        graphname = "testGraph"
        mock_conn = MagicMock()
        mock_get_db_connection.return_value = mock_conn
        mock_conn.getEndpoints.return_value = ["Scan_For_Updates", "Update_Vertices_Processing_Status"]
        checker = EventualConsistencyChecker(
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            ["index1"],
            {"testGraph_index1": mock_embedding_store},
            mock_conn,
            Mock(),
            Mock()
        )

        self.assertFalse(checker.is_initialized)
        checker.initialize()
        self.assertTrue(checker.is_initialized)

    @patch("app.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("app.embeddings.embedding_services.EmbeddingModel")
    @patch("app.util.get_db_connection_id_token", return_value=Mock())
    def test_fetch_and_process_vertex(
        self, mock_get_db_connection, mock_embedding_model, mock_embedding_store
    ):
        """Test fetch_and_process_vertex functionality."""
        graphname = "testGraph"
        conn = mock_get_db_connection.return_value
        
        conn.getEndpoints.return_value = ["Scan_For_Updates", "Update_Vertices_Processing_Status"]
        mock_response = [{
            "@@v_and_text": {
                1: "Doc1", 2: "Doc2", 3: "Doc3"
            }
        }]
        conn.runInstalledQuery.side_effect = [mock_response, "true"]
        checker = EventualConsistencyChecker(
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            ["index1"],
            {"testGraph_index1": mock_embedding_store},
            conn,
            MagicMock(),
            MagicMock()
        )

        checker.fetch_and_process_vertex()

        # Verify the sequence of calls and check the outputs
        conn.runInstalledQuery.assert_any_call("Scan_For_Updates", {"v_type": "index1", "num_samples": 10})
        conn.runInstalledQuery.assert_any_call(
            "Update_Vertices_Processing_Status", {"processed_vertices": [(1, 'index1'), (2, 'index1'), (3, 'index1')]}
        )
        # Assertions to ensure the embedding service and store were interacted with correctly
        mock_embedding_store.remove_embeddings.assert_called_once()
        mock_embedding_model.embed_query.assert_called()
        mock_embedding_store.add_embeddings.assert_called()

if __name__ == "__main__":
    unittest.main()
