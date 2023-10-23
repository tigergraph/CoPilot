import pandas as pd
import os
from fastapi.testclient import TestClient
import unittest


class CommonTests():
    def test_questions(self):
        for suite in ["OGB_MAG"]:
            questions = "./test_questions/"+suite+"/"+suite+"Questions.tsv"
            questions = pd.read_csv(questions, delimiter="\t")
            print(questions.head())