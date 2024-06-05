import os
import unittest

import pytest
from fastapi.testclient import TestClient
from test_service import CommonTests
import wandb
import parse_test_config
import sys


@pytest.mark.skip(reason="All tests in this class are currently skipped by the pipeline, but used by the LLM regression tests.")
class TestWithOpenAI(CommonTests, unittest.TestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        from main import app

        cls.client = TestClient(app)
        cls.llm_service = "gpt-4o-2024-05-13"
        if USE_WANDB:
            cls.table = wandb.Table(columns=columns)

    
    def test_config_read(self):
        resp = self.client.get("/")
        self.assertEqual(resp.json()["config"], "GPT-4o")


if __name__ == "__main__":
    parser = parse_test_config.create_parser()

    args = parser.parse_known_args()[0]

    USE_WANDB = args.wandb

    schema = args.schema

    if USE_WANDB:
        columns = [
            "LLM_Service",
            "Dataset",
            "Question Type",
            "Question Theme",
            "Question",
            "True Answer",
            "True Function Call",
            "Retrieved Natural Language Answer",
            "Retrieved Answer",
            "Answer Source",
            "Answer Correct",
            "Answered Question",
            "Response Time (seconds)",
        ]
    CommonTests.setUpClass(schema)

    # clean up args before unittesting
    del sys.argv[1:]
    unittest.main()
