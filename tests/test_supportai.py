import unittest
from fastapi.testclient import TestClient
from app.main import app
import json
import os
import pyTigerGraph as tg


class TestSupportAI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        db_config = os.getenv("DB_CONFIG")
        with open(db_config, "r") as file:
            db_config = json.load(file)
        self.username = db_config["username"]
        self.password = db_config["password"]
        self.use_token = db_config["getToken"]
        self.conn = tg.TigerGraphConnection(
            db_config["hostname"], username=self.username, password=self.password
        )

    def test_initialize(self):
        self.conn.graphname = "SupportAI"
        if self.use_token:
            self.conn.getToken()
        # Test case 1: Verify that the endpoint returns a 200 status code
        response = self.client.post(
            "/SupportAI/supportai/initialize", auth=(self.username, self.password)
        )
        self.assertEqual(response.status_code, 200)

        concept_vertex = self.conn.getVertexType("Concept")
        print(concept_vertex)
        self.assertIsNotNone(concept_vertex)
        self.assertEqual(concept_vertex["Name"], "Concept")
        self.assertEqual(concept_vertex["PrimaryId"]["PrimaryIdAsAttribute"], True)


if __name__ == "__main__":
    unittest.main()
