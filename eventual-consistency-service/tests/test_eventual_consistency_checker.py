import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.eventual_consistency_checker import EventualConsistencyChecker


class TestEventualConsistencyChecker(unittest.TestCase):
    @patch("common.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("common.embeddings.embedding_services.EmbeddingModel")
    @patch("common.db.connections.get_db_connection_id_token", return_value=Mock())
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
        mock_conn.getEndpoints.return_value = ["Scan_For_Updates", "Update_Vertices_Processing_Status", "ECC_Status", "Check_Nonexistent_Vertices"]
        checker = EventualConsistencyChecker(
            6000,
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            ["index1"],
            {"testGraph_index1": mock_embedding_store},
            mock_conn,
            Mock(),
            Mock(),
            run_forever=False
        )

        self.assertFalse(checker.is_initialized)
        checker.initialize()
        self.assertTrue(checker.is_initialized)

    @patch("common.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("common.embeddings.embedding_services.EmbeddingModel")
    @patch("common.db.connections.get_db_connection_id_token", return_value=Mock())
    def test_fetch_and_process_vertex(
        self, mock_get_db_connection, mock_embedding_model, mock_embedding_store
    ):
        """Test fetch_and_process_vertex functionality."""
        graphname = "testGraph"
        conn = mock_get_db_connection.return_value
        
        conn.getEndpoints.return_value = ["Scan_For_Updates", "Update_Vertices_Processing_Status", "ECC_Status", "Check_Nonexistent_Vertices"]
        mock_response = [{
            "@@v_and_text": {
                1: "Doc1", 2: "Doc2", 3: "Doc3"
            }
        }]
        conn.runInstalledQuery.side_effect = [mock_response, "true"]
        checker = EventualConsistencyChecker(
            6000,
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            ["index1"],
            {"testGraph_index1": mock_embedding_store},
            conn,
            MagicMock(),
            MagicMock(),
            run_forever=False
        )

        checker.fetch_and_process_vertex()

        # Verify the sequence of calls and check the outputs
        conn.runInstalledQuery.assert_any_call("Scan_For_Updates", {"v_type": "index1", "num_samples": 10})
        conn.runInstalledQuery.assert_any_call(
            "Update_Vertices_Processing_Status", {'processed_vertices': [{'id': 1, 'type': 'index1'}, {'id': 2, 'type': 'index1'}, {'id': 3, 'type': 'index1'}]}, usePost=True
        )
        # Assertions to ensure the embedding service and store were interacted with correctly
        mock_embedding_store.remove_embeddings.assert_called_once()
        mock_embedding_model.embed_query.assert_called()
        mock_embedding_store.add_embeddings.assert_called()
        
    @patch("common.embeddings.milvus_embedding_store.MilvusEmbeddingStore")
    @patch("common.embeddings.embedding_services.EmbeddingModel")
    @patch("common.db.connections.get_db_connection_id_token", return_value=Mock())
    def test_verify_and_cleanup_embeddings(
        self, mock_get_db_connection, mock_embedding_model, mock_embedding_store
    ):
        """Test fetch_and_process_vertex functionality."""
        graphname = "testGraph"
        conn = mock_get_db_connection.return_value

        conn.getEndpoints.return_value = ["Scan_For_Updates", "Update_Vertices_Processing_Status", "ECC_Status", "Check_Nonexistent_Vertices"]
        mock_response = [{
            "@@v_and_text": {
                1: "Doc1", 2: "Doc2", 3: "Doc3"
            }
        }]
        conn.runInstalledQuery.side_effect = [mock_response, "true"]

        checker = EventualConsistencyChecker(
            6000,
            6000,
            graphname,
            "vertex_id",
            mock_embedding_model,
            ["index1"],
            {"testGraph_index1": mock_embedding_store},
            conn,
            MagicMock(),
            MagicMock(),
            run_forever=False
        )

        checker.embedding_stores['testGraph_index1'].query.return_value = [
            {checker.vertex_field: 'v1'},
            {checker.vertex_field: 'v2'}
        ]

        checker.conn.runInstalledQuery.return_value = [
            {"@@missing_vertices": ['v1']}
        ]

        checker.verify_and_cleanup_embeddings()

        # Verify the sequence of calls and check the outputs
        checker.embedding_stores['testGraph_index1'].query.assert_called_once_with(
            "pk > 0", [checker.vertex_field]
        )

        checker.conn.runInstalledQuery.assert_called_with(
            "Check_Nonexistent_Vertices",
            {"v_type": 'index1', "vertex_ids": ['v1', 'v2']}
        )

        # Ensure the call to remove the non-existent vertex is made
        checker.embedding_stores['testGraph_index1'].remove_embeddings.assert_called_once_with(
            expr=f"{checker.vertex_field} == 'v1'"
        )

if __name__ == "__main__":
    unittest.main()
