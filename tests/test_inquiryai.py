import unittest
from fastapi.testclient import TestClient
from app.main import app
import json
import os
import pyTigerGraph as tg


class TestInquiryAI(unittest.TestCase):
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
        self.conn.graphname = "DigitalInfra"
        if self.use_token:
            self.conn.getToken()
        # Test case 1: Verify that the endpoint returns a 200 status code
        headers = {
            "accept": "application/json",
            "Authorization": "Basic dXNlcl8xOk15UGFzc3dvcmQxIQ==",
            "Content-Type": "application/json",
        }

        data_1 = {
            "function_header": "ms_dependency_chain",
            "description": "Finds dependents of a given microservice up to k hops.",
            "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
            "param_types": {"microservice": "str", "depth": "int"},
        }

        response = self.client.post(
            "/DigitalInfra/registercustomquery",
            headers=headers,
            json=data_1,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)

        data_2 = {
            "query": "what services would be affected if the microservice MS_61242 is upgraded?"
        }

        response = self.client.post(
            "/DigitalInfra/query",
            headers=headers,
            json=data_2,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

        data_3 = {"query": "How many microservices are there?"}

        response = self.client.post(
            "/DigitalInfra/query",
            headers=headers,
            json=data_3,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

        data_4 = {"query": "How many calls have a response time greater than 5?"}

        response = self.client.post(
            "/DigitalInfra/query",
            headers=headers,
            json=data_4,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
