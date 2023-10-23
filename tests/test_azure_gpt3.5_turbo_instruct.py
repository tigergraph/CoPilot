import os
import unittest
from fastapi.testclient import TestClient
from test_service import CommonTests


class TestWithAzure(CommonTests, unittest.TestCase):
    def setUp(self):
        os.environ["LLM_CONFIG"] = "azure_llm_config.json"
        from main import app
        self.client = TestClient(app)
    
    def test_config_read(self):
        resp = self.client.get("/")
        self.assertEqual(resp.json()["llm_service"], "Azure")

if __name__ == "__main__":
    unittest.main()