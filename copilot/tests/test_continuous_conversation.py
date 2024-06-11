import unittest
import pytest
from fastapi.testclient import TestClient
from copilot.tests.app.main import app
import json
import os
import pyTigerGraph as tg

@pytest.mark.skip(reason="All tests in this class are currently skipped by the pipeline, coming back to it in the second iteration.")
class TestContinousConversationInquiryAI(unittest.TestCase):
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
        self.conn.graphname = "DemoGraph1"
        if self.use_token:
            self.conn.getToken()

    @pytest.mark.skip(reason="Does not work with automatic runs for some reason, coming back to it in second iteration")
    def test_case1(self):
        query1 = "What is William Torres's ID?"

        response = self.client.post(
            "/Demo_Graph1/query_with_history",
            json=query1,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)

        query2 = "What is his email?"
        response = self.client.post(
            "/Demo_Graph1/query_with_history",
            json=query2,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertIn("charles72@hotmail.com", response.text)
        self.assertEqual(response.status_code, 200)

    def test_case2(self):
        query3 = "Homy people are there in the graph?"
        response = self.client.post(
            "/Demo_Graph1/query_with_history",
            json=query3,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)

        query4 = "What are the names of these people?"
        response = self.client.post(
            "/Demo_Graph1/query_with_history",
            json=query4,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertIn("William Torres", response.text)
        self.assertEqual(response.status_code, 200)

    def test_case3(self):
        query3 = "Who does he know?"
        response = self.client.post(
            "/Demo_Graph1/query_with_history",
            json=query3,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertTrue("Lisa" in response.text or "497-63-0132" in response.text)
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
