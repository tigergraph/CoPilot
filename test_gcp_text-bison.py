import os
import unittest
from fastapi.testclient import TestClient
from test_service import CommonTests
import wandb

USE_WANDB = True

if USE_WANDB:
    columns = ["LLM_Service", "Dataset", "Question Type", "Question Theme", "Question", "True Answer", "True Function Call",
               "Retrieved Natural Language Answer", "Retrieved Answer",
               "Answer Source", "Answer Correct", "Answered Question", "Response Time (seconds)"]


class TestWithVertexAI(CommonTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["LLM_CONFIG"] = "./configs/gcp_palm_config.json"
        from app.main import app
        cls.client = TestClient(app)
        cls.llm_service = "gcp-text-bison"
        if USE_WANDB:
            cls.table = wandb.Table(columns=columns)

    def test_config_read(self):
        resp = self.client.get("/")
        self.assertEqual(resp.json()["config"], "GCP-text-bison")

if __name__ == "__main__":
    unittest.main()