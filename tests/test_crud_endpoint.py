import unittest
from fastapi.testclient import TestClient
from app.main import app
import json
import os
import pyTigerGraph as tg


class TestCRUDInquiryAI(unittest.TestCase):
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
        self.conn.graphname = "DigitalInfra"
        if self.use_token:
            self.conn.getToken()

    def test_register_custom_query_list(self):
        query_list = [
            {
                "function_header": "ms_dependency_chain",
                "description": "Finds dependents of a given microservice up to k hops.",
                "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
                "param_types": {"microservice": "str", "depth": "int"},
            },
            {
                "function_header": "getVertexCount",
                "description": "Get the count of a vertex type, optionally with a where filter",
                "docstring": "`getVertexCount(vertexType: Union[str, list] = '*', where: str = '')` → Union[int, dict]\nReturns the number of vertices of the specified type.\nParameters:\nvertexType (Union[str, list], optional): The name of the vertex type. If vertexType == '*', then count the instances of all vertex types (where cannot be specified in this case). Defaults to '*'.\nwhere (str, optional): A comma separated list of conditions that are all applied on each vertex’s attributes. The conditions are in logical conjunction (i.e. they are 'AND’ed' together). Defaults to ''.\nReturns:\nA dictionary of <vertex_type>: <vertex_count> pairs if vertexType is a list or '*'.\nAn integer of vertex count if vertexType is a single vertex type.\nUses:\nIf vertexType is specified only: count of the instances of the given vertex type(s).\nIf vertexType and where are specified: count of the instances of the given vertex type after being filtered by where condition(s).",
                "param_types": {"vertexType": "Union[str, List[str]]", "where": "str"},
            },
        ]

        response = self.client.post(
            "/DigitalInfra/register_docs",
            json=query_list,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_register_custom_query_single(self):
        single_query = {
            "function_header": "ms_dependency_chain",
            "description": "Finds dependents of a given microservice up to k hops.",
            "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
            "param_types": {"microservice": "str", "depth": "int"},
        }

        response = self.client.post(
            "/DigitalInfra/register_docs",
            json=single_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_delete_custom_query_expr(self):
        delete_query = {"ids": "", "expr": "function_header in ['ms_dependency_chain']"}

        response = self.client.post(
            "/DigitalInfra/delete_docs",
            json=delete_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_delete_custom_query_ids(self):
        delete_query = {"ids": "448543540718863740", "expr": ""}

        response = self.client.post(
            "/DigitalInfra/delete_docs",
            json=delete_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_delete_custom_query_idlist(self):
        delete_query = {"ids": ["448631022823408704", "448631022823408707"], "expr": ""}

        response = self.client.post(
            "/DigitalInfra/delete_docs",
            json=delete_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_delete_custom_query_noinput(self):
        delete_query = {"ids": "", "expr": ""}

        response = self.client.post(
            "/DigitalInfra/delete_docs",
            json=delete_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 500)

    def test_upsert_custom_query_ids(self):
        upsert_query = {
            "id": "448543540718863740",
            "query_info": {
                "function_header": "ms_dependency_chain_test_id",
                "description": "Finds dependents of a given microservice up to k hops.",
                "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
                "param_types": {"microservice": "str", "depth": "int"},
            },
        }

        response = self.client.post(
            "/DigitalInfra/upsert_docs",
            json=upsert_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_upsert_custom_query_docs(self):
        upsert_query = {
            "id": "",
            "expr": {
                "function_header": "ms_dependency_chain_test_docs",
                "description": "Finds dependents of a given microservice up to k hops.",
                "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
                "param_types": {"microservice": "str", "depth": "int"},
            },
        }

        response = self.client.post(
            "/DigitalInfra/upsert_docs",
            json=upsert_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

    def test_upsert_custom_query_noinput(self):
        upsert_query = {"ids": "", "expr": {}}

        response = self.client.post(
            "/DigitalInfra/upsert_docs",
            json=upsert_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 422)

    def test_upsert_new_existing_noid_docs(self):
        # ms_dependency_chain exists in milvus, find the id basded on function_header and update the description
        # ms_dependency_chain_11111 doesn't exist, no id found, insert directly
        # return two new ids after upserting
        upsert_query = [
            {
                "id": "",
                "query_info": {
                "function_header": "ms_dependency_chain",
                "description": "Testing Finds dependents of a given microservice up to k hops.",
                "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
                "param_types": {"microservice": "str", "depth": "int"},
                "graphname": "DigitalInfra"
                }
            },
            {
                "id": "",
                "query_info": {
                "function_header": "ms_dependency_chain_11111",
                "description": "Testing Finds dependents of a given microservice up to k hops.",
                "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
                "param_types": {"microservice": "str", "depth": "int"},
                "graphname": "DigitalInfra"
                }
            }
        ]

        response = self.client.post(
            "/DigitalInfra/upsert_docs",
            json=upsert_query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)


    def test_retrieve_custom_query(self):
        query = "how many microservices are there?"

        response = self.client.post(
            "/DigitalInfra/retrieve_docs",
            json=query,
            auth=(self.username, self.password),
        )
        print("-----------------------")
        print()
        print("response json")
        print(response.text)
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
