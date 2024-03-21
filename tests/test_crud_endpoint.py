import unittest
from fastapi.testclient import TestClient
from app.main import app
import json
import os
import pyTigerGraph as tg

class TestCRUDInquiryAI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # db_config = os.getenv("DB_CONFIG")
        db_config = "./configs/db_config.json"
        with open(db_config, "r") as file:
            db_config = json.load(file)
        self.username = db_config["username"]
        self.password = db_config["password"]
        self.use_token = db_config["getToken"]
        self.conn = tg.TigerGraphConnection(db_config["hostname"], username=self.username, password=self.password)

    def test_register_custom_query(self):
        self.conn.graphname="DigitalInfra"
        if self.use_token:
            self.conn.getToken()
        # Test case 1: Verify that the endpoint returns a 200 status code
        headers = {
            'accept': 'application/json',
            'Authorization': 'Basic dXNlcl8xOk15UGFzc3dvcmQxIQ==',
            'Content-Type': 'application/json'
        }

        query_list = [
            
            {
                "function_header": "ms_dependency_chain",
                "description": "Finds dependents of a given microservice up to k hops.",
                "docstring": "Finds dependents of a given microservice. Useful for determining effects of downtime for upgrades or bugs. Run the query with `runInstalledQuery('ms_dependency_chain', params={'microservice': 'INSERT_MICROSERVICE_ID_HERE', 'depth': INSERT_DEPTH_HERE})`. Depth defaults to 3.",
                "param_types": {"microservice": "str", "depth": "int"}
            },
            {
                "function_header": "getVertexCount",
                "description": "Get the count of a vertex type, optionally with a where filter",
                "docstring": "`getVertexCount(vertexType: Union[str, list] = '*', where: str = '')` → Union[int, dict]\nReturns the number of vertices of the specified type.\nParameters:\nvertexType (Union[str, list], optional): The name of the vertex type. If vertexType == '*', then count the instances of all vertex types (where cannot be specified in this case). Defaults to '*'.\nwhere (str, optional): A comma separated list of conditions that are all applied on each vertex’s attributes. The conditions are in logical conjunction (i.e. they are 'AND’ed' together). Defaults to ''.\nReturns:\nA dictionary of <vertex_type>: <vertex_count> pairs if vertexType is a list or '*'.\nAn integer of vertex count if vertexType is a single vertex type.\nUses:\nIf vertexType is specified only: count of the instances of the given vertex type(s).\nIf vertexType and where are specified: count of the instances of the given vertex type after being filtered by where condition(s).",
                "param_types": {
                    "vertexType": "Union[str, List[str]]",
                    "where": "str"
                }
            }
        ]

        response = self.client.post("/DigitalInfra/registercustomquery", headers=headers, json=query_list, auth=(self.username, self.password))
        print ("-----------------------")
        print ()
        print ("response json")
        print (response.text)

if __name__ == "__main__":
    unittest.main()