import unittest

import pytest
from fastapi.testclient import TestClient
from app.main import app
import os
import pyTigerGraph as tg
import json


@pytest.mark.skip(reason="All tests in this class are currently skipped by the pipeline, coming back to it in the second iteration.")
class TestAppFunctions(unittest.TestCase):
    
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

    """TODO: Fix the ingest tests to be compatible with database operations
    def test_create_ingest_json_s3(self):
        # Test create_ingest with JSON file format
        ingest_config = {"file_format": "json", "loader_config": {}, "data_source": "s3", "data_source_config": {"aws_access_key": "test_key", "aws_secret_key": "test_secret"}}
        response = self.client.post("/SupportAI/supportai/create_ingest", json={"graphname": "SupportAI", "ingest_config": ingest_config}, auth=(self.username, self.password))
        print(response)
        self.assertEqual(response.status_code, 200)
        # Add more assertions as needed

    def test_create_ingest_csv_s3(self):
        # Test create_ingest with CSV file format
        ingest_config = {"file_format": "csv", "loader_config": {}, "data_source": "s3", "data_source_config": {"aws_access_key": "test_key", "aws_secret_key": "test_secret"}}
        response = self.client.post("/SupportAI/supportai/create_ingest", json={"graphname": "SupportAI", "ingest_config": ingest_config}, auth=(self.username, self.password))
        print(response)
        self.assertEqual(response.status_code, 200)
        # Add more assertions as needed
    """

    
    def test_create_ingest_json_no_data_source(self):
        # Test create_ingest with JSON file format
        ingest_config = {"file_format": "json", "loader_config": {}}
        response = self.client.post(
            "/SupportAI/supportai/create_ingest",
            json={"graphname": "SupportAI", "ingest_config": ingest_config},
            auth=(self.username, self.password),
        )
        self.assertEqual(response.status_code, 422)
        # Add more assertions as needed

    
    def test_create_ingest_csv_no_data_source(self):
        # Test create_ingest with CSV file format
        ingest_config = {"file_format": "csv", "loader_config": {}}
        response = self.client.post(
            "/SupportAI/supportai/create_ingest",
            json={"graphname": "SupportAI", "ingest_config": ingest_config},
            auth=(self.username, self.password),
        )
        self.assertEqual(response.status_code, 422)
        # Add more assertions as needed

    
    def test_create_ingest_invalid_data_source(self):
        # Test create_ingest with invalid data source
        ingest_config = {"file_format": "invalid", "loader_config": {}}
        response = self.client.post(
            "/SupportAI/supportai/create_ingest",
            json={"graphname": "SupportAI", "ingest_config": ingest_config},
            auth=(self.username, self.password),
        )
        self.assertEqual(
            response.status_code, 422
        )  # Assuming FastAPI returns 422 for validation errors
        # Add more assertions as needed

    """TODO: Fix the ingest tests to be compatible with database operations
    def test_ingest(self):
        # Test ingest function
        loader_info = {"file_path": "test_path", "load_job_id": "test_job_id", "data_source_id": "data_source_id"}
        response = self.client.post("/SupportAI/supportai/ingest", json=loader_info, auth=(self.username, self.password))
        print(response.json())
        self.assertEqual(response.status_code, 200)
        # Add more assertions as needed
    """

    
    def test_ingest_missing_file_path(self):
        # Test ingest with missing file path
        loader_info = {
            "load_job_id": "test_job_id",
            "data_source_id": "test_data_source_id",
        }
        response = self.client.post(
            "/SupportAI/supportai/ingest",
            json={"graphname": "SupportAI", "loader_info": loader_info},
            auth=(self.username, self.password),
        )
        self.assertEqual(
            response.status_code, 422
        )  # Assuming FastAPI returns 422 for validation errors
        # Add more assertions as needed

    
    def test_ingest_missing_load_job_id(self):
        # Test ingest with missing load job id
        loader_info = {"filePath": "test_path", "data_source_id": "test_data_source_id"}
        response = self.client.post(
            "/SupportAI/supportai/ingest",
            json={"graphname": "SupportAI", "loader_info": loader_info},
            auth=(self.username, self.password),
        )
        self.assertEqual(
            response.status_code, 422
        )  # Assuming FastAPI returns 422 for validation errors
        # Add more assertions as needed

    
    def test_ingest_missing_data_source_id(self):
        # Test ingest with missing data source id
        loader_info = {"filePath": "test_path", "load_job_id": "test_job_id"}
        response = self.client.post(
            "/SupportAI/supportai/ingest",
            json={"graphname": "SupportAI", "loader_info": loader_info},
            auth=(self.username, self.password),
        )
        self.assertEqual(
            response.status_code, 422
        )  # Assuming FastAPI returns 422 for validation errors
        # Add more assertions as needed


if __name__ == "__main__":
    unittest.main()
