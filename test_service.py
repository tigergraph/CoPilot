import pandas as pd
import os
from fastapi.testclient import TestClient
import unittest

class CommonTests():
    pass


def test_generator(dataset, row):
    test_name = "test_"+dataset+"_"+str(row.name)
    # Need to extract q/a pairs before test is generated,
    # as otherwise we look at the last question/answer pair is used
    question = row["Question"]
    true_answer = row["Answer"]

    def test(self):
        print(question)
        resp = self.client.post("/"+dataset+"/query", json={"query": question}, auth=("user_1", "MyPassword1!"))
        self.assertEqual(resp.status_code, 200)
        answer = list(resp.json()["query_sources"][0].values())[0]
        self.assertEqual(true_answer, str(answer))
    
    return test_name, test

for suite in ["OGB_MAG"]:
    questions = "./test_questions/"+suite+"/"+suite+"Questions.tsv"
    questions = pd.read_csv(questions, delimiter="\t")
    
    tests = list(questions.apply(lambda x: test_generator(suite, x), axis = 1))
    for test in tests:
        setattr(CommonTests, test[0], test[1])