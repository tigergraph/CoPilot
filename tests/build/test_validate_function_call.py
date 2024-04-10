from typing import Any
import unittest
from unittest.mock import patch
import os
import json
import app
from fastapi.testclient import TestClient
from app.py_schemas.schemas import Document
from app.tools.validation_utils import validate_function_call, InvalidFunctionCallException
import pyTigerGraph as tg
from pyTigerGraph import TigerGraphConnection
from pydantic import BaseModel
from typing import Dict

class Document(BaseModel):
    page_content: str
    metadata: Dict

class TestValidateFunctionCall(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        db_config = os.getenv("DB_CONFIG")
        with open(db_config, "r") as file:
            db_config = json.load(file)
        self.username = db_config["username"]
        self.password = db_config["password"]
        self.use_token = db_config["getToken"]
        self.conn = tg.TigerGraphConnection(db_config["hostname"], username=self.username, password=self.password)
        self.conn.graphname="DigitalInfra"
        self.conn.getToken(self.conn.createSecret())
    
    def test_valid_dynamic_function_call(self):
        # Assume retrived_docs and conn objects are properly set up
        generated_call = "runInstalledQuery('ms_dependency_chain', params={'microservice': 'MS_61242', 'depth': 3})" # Example generated call
        doc1 = Document(page_content="Finds dependents of a given microservice...", metadata={'function_header': 'ms_dependency_chain', 'description': 'Finds dependents of a given microservice up to k hops.', 'param_types': {'microservice': 'str', 'depth': 'int'}, 'custom_query': True})
        doc2 = Document(page_content="`getVertices(vertexType: str, where: str = '', limit: Union[int, str] = None, sort: str = '')` → dict\nRetrieves vertices of the given vertex type...", metadata={'source': './app/pytg_documents/get_vertices.json', 'seq_num': 1, 'function_header': 'getVertices', 'description': 'Get a sample of vertices', 'param_types': {'vertexType': 'str', 'where': 'str', 'limit': 'Union[int, str]', 'sort': 'str'}, 'custom_query': False})
        doc3 = Document(page_content='`getVerticesById(vertexType: str, vertexIds: Union[int, str, list])` → Union[list, str, pd.DataFrame]\nRetrieves vertices of the given vertex type, identified by their ID...', metadata={'source': './app/pytg_documents/get_vertices_by_id.json', 'seq_num': 1, 'function_header': 'getVerticesById', 'description': 'Get vertex information by vertex ID', 'param_types': {'vertexType': 'str', 'vertexIds': 'Union[int, str, List[Union[int, str]]'}, 'custom_query': False})
        retrieved_docs = [doc1, doc2, doc3]

        with patch('app.tools.validation_utils.logger') as mock_logger:
            result = validate_function_call(self.conn, generated_call, retrieved_docs)
            self.assertEqual(result, generated_call)

    def test_invalid_dynamic_function_call(self):
        # Assume retrived_docs and conn objects are properly set up
        generated_call = "runInstalledQuery('invalid_query')" # Example generated call
        doc1 = Document(page_content="Finds dependents of a given microservice...", metadata={'function_header': 'ms_dependency_chain', 'description': 'Finds dependents of a given microservice up to k hops.', 'param_types': {'microservice': 'str', 'depth': 'int'}, 'custom_query': True})
        doc2 = Document(page_content="`getVertices(vertexType: str, where: str = '', limit: Union[int, str] = None, sort: str = '')` → dict\nRetrieves vertices of the given vertex type...", metadata={'source': './app/pytg_documents/get_vertices.json', 'seq_num': 1, 'function_header': 'getVertices', 'description': 'Get a sample of vertices', 'param_types': {'vertexType': 'str', 'where': 'str', 'limit': 'Union[int, str]', 'sort': 'str'}, 'custom_query': False})
        doc3 = Document(page_content='`getVerticesById(vertexType: str, vertexIds: Union[int, str, list])` → Union[list, str, pd.DataFrame]\nRetrieves vertices of the given vertex type, identified by their ID...', metadata={'source': './app/pytg_documents/get_vertices_by_id.json', 'seq_num': 1, 'function_header': 'getVerticesById', 'description': 'Get vertex information by vertex ID', 'param_types': {'vertexType': 'str', 'vertexIds': 'Union[int, str, List[Union[int, str]]'}, 'custom_query': False})
        retrieved_docs = [doc1, doc2, doc3]

        with patch('app.tools.validation_utils.logger') as mock_logger:
            with self.assertRaises(InvalidFunctionCallException):
                validate_function_call(self.conn, generated_call, retrieved_docs)

    def test_valid_buildin_function_call(self):
        # Assume retrived_docs and conn objects are properly set up
        generated_call = "getVertexCount('Microservice')" # Example generated call
        doc1 = Document(page_content="`getVertices(vertexType: str, where: str = '', limit: Union[int, str] = None, sort: str = '')` → dict\nRetrieves vertices of the given vertex type...", metadata={'source': './app/pytg_documents/get_vertices.json', 'seq_num': 1, 'function_header': 'getVertices', 'description': 'Get a sample of vertices', 'param_types': {'vertexType': 'str', 'where': 'str', 'limit': 'Union[int, str]', 'sort': 'str'}, 'custom_query': False})
        doc2 = Document(page_content='`getVerticesById(vertexType: str, vertexIds: Union[int, str, list])` → Union[list, str, pd.DataFrame]\nRetrieves vertices of the given vertex type, identified by their ID.', metadata={'source': './app/pytg_documents/get_vertices_by_id.json', 'seq_num': 1, 'function_header': 'getVerticesById', 'description': 'Get vertex information by vertex ID', 'param_types': {'vertexType': 'str', 'vertexIds': 'Union[int, str, List[Union[int, str]]'}, 'custom_query': False})
        doc3 = Document(page_content="`getVertexCount(vertexType: Union[str, list] = '*', where: str = '')` → Union[int, dict]\nReturns the number of vertices of the specified type...", metadata={'source': './app/pytg_documents/get_vertex_count.json', 'seq_num': 1, 'function_header': 'getVertexCount', 'description': 'Get the count of a vertex type, optionally with a where filter', 'param_types': {'vertexType': 'Union[str, List[str]]', 'where': 'str'}, 'custom_query': False})
        retrieved_docs = [doc1, doc2, doc3]

        with patch('app.tools.validation_utils.logger') as mock_logger:
            result = validate_function_call(self.conn, generated_call, retrieved_docs)
            self.assertEqual(result, generated_call)

    def test_invalid_buildin_function_call(self):
        # Assume retrived_docs and conn objects are properly set up
        generated_call = "getVertexCount('Invalid')" # Example generated call
        doc1 = Document(page_content="Finds dependents of a given microservice...", metadata={'function_header': 'ms_dependency_chain', 'description': 'Finds dependents of a given microservice up to k hops.', 'param_types': {'microservice': 'str', 'depth': 'int'}, 'custom_query': True})
        doc2 = Document(page_content="`getVertices(vertexType: str, where: str = '', limit: Union[int, str] = None, sort: str = '')` → dict\nRetrieves vertices of the given vertex type...", metadata={'source': './app/pytg_documents/get_vertices.json', 'seq_num': 1, 'function_header': 'getVertices', 'description': 'Get a sample of vertices', 'param_types': {'vertexType': 'str', 'where': 'str', 'limit': 'Union[int, str]', 'sort': 'str'}, 'custom_query': False})
        doc3 = Document(page_content='`getVerticesById(vertexType: str, vertexIds: Union[int, str, list])` → Union[list, str, pd.DataFrame]\nRetrieves vertices of the given vertex type, identified by their ID...', metadata={'source': './app/pytg_documents/get_vertices_by_id.json', 'seq_num': 1, 'function_header': 'getVerticesById', 'description': 'Get vertex information by vertex ID', 'param_types': {'vertexType': 'str', 'vertexIds': 'Union[int, str, List[Union[int, str]]'}, 'custom_query': False})
        retrieved_docs = [doc1, doc2, doc3]

        with patch('app.tools.validation_utils.logger') as mock_logger:
            with self.assertRaises(InvalidFunctionCallException):
                validate_function_call(self.conn, generated_call, retrieved_docs)

if __name__ == '__main__':
    unittest.main()
    