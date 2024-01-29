import os
import unittest
from fastapi.testclient import TestClient
from test_service import CommonTests
import wandb
import parse_test_config
import sys


class TestWithVertexAI(CommonTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from app.main import app
        cls.client = TestClient(app)
        cls.llm_service = "gcp-text-bison"
        if USE_WANDB:
            cls.table = wandb.Table(columns=columns)

    def test_config_read(self):
        resp = self.client.get("/")
        self.assertEqual(resp.json()["config"], "GCP-text-bison")

if __name__ == "__main__":
    parser = parse_test_config.create_parser()

    args = parser.parse_known_args()[0]

    USE_WANDB = args.wandb

    schema = args.schema

    if USE_WANDB:
        columns = ["LLM_Service", "Dataset", "Question Type", "Question Theme", "Question", "True Answer", "True Function Call",
                "Retrieved Natural Language Answer", "Retrieved Answer",
                "Answer Source", "Answer Correct", "Answered Question", "Response Time (seconds)"]
    CommonTests.setUpClass(schema)
    
    # clean up args before unittesting
    del sys.argv[1:]
    unittest.main()