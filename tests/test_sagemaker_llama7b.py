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


class TestWithLlama(CommonTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from app.main import app
        cls.client = TestClient(app)
        cls.llm_service = "llama7B"
        if USE_WANDB:
            cls.table = wandb.Table(columns=columns)

    def test_config_read(self):
        resp = self.client.get("/")
        self.assertEqual(resp.json()["config"]["completion_service"]["llm_service"], "sagemaker")

if __name__ == "__main__":
    unittest.main()