import os
import unittest
from fastapi.testclient import TestClient
from test_service import CommonTests
import wandb

USE_WANDB = True

if USE_WANDB:
    columns = ["LLM_Service", "Dataset", "Question Theme", "Question", "True Answer", "True Function Call",
               "Retrieved Natural Language Answer", "Retrieved Answer",
               "Answer Source", "Answer Correct"]


class TestWithAzure(CommonTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["LLM_CONFIG"] = "./configs/azure_llm_config.json"
        from main import app
        cls.client = TestClient(app)
        if USE_WANDB:
            cls.wandbLogger = wandb.init(project="llm-eval-sweep")
            cls.llm_service = "azure_gpt3.5_turbo_instruct"
            cls.table = wandb.Table(columns=columns)

    def test_config_read(self):
        resp = self.client.get("/")
        self.assertEqual(resp.json()["llm_service"], "Azure")

    @classmethod
    def tearDownClass(cls):
        if USE_WANDB:
            cls.wandbLogger.log({"qa_results": cls.table})

if __name__ == "__main__":
    unittest.main()