import pandas as pd
import os
from fastapi.testclient import TestClient
import json
import wandb
import time

with open("./configs/testing_config.json") as f:
    config = json.load(f)

USE_WANDB = config["use_wandb"]

class CommonTests():
    @classmethod
    def tearDownClass(cls):
        if USE_WANDB:
            df = cls.table.get_dataframe()
            q_types = list(df["Question Type"].unique())
            for q_type in q_types:
                filtered_df = df[df["Question Type"] == q_type]
                unique_datasets = list(df["Dataset"].unique())
                for dataset in unique_datasets:
                    cls.config = {
                        "llm_service": cls.llm_service,
                        "question_type": q_type,
                        "dataset": dataset
                    }
                    cls.wandbLogger = wandb.init(project="llm-eval-sweep", config=cls.config)
                    final_df = filtered_df[filtered_df["Dataset"] == dataset]
                    acc = (final_df["Answer Correct"].sum())/final_df["Answer Correct"].shape[0]
                    avg_resp_time = final_df["Response Time (seconds)"].mean()
                    cls.wandbLogger.log({"LLM Service": cls.llm_service,
                                        "Question Type": q_type,
                                        "Dataset": dataset,
                                        "Accuracy": acc,
                                        "Average Response Time (seconds)": avg_resp_time,
                                        "Number of Questions": final_df["Answer Correct"].shape[0]}, commit=True)
                    tmp_table = wandb.Table(dataframe=final_df)
                    cls.wandbLogger.log({"qa_results": tmp_table})
                    wandb.finish()

def test_generator(dataset, row, username, password):
    test_name = "test_"+dataset+"_"+str(row.name)
    # Need to extract q/a pairs before test is generated,
    # as otherwise we look at the last question/answer pair is used
    question = row["Question"]
    true_answer = row["Answer"]
    function_call = row["Function Call"]
    question_theme = row["Question Theme"]
    question_type = row["Question Type"]

    def test(self):
        t1 = time.time()
        resp = self.client.post("/"+dataset+"/query", json={"query": question}, auth=(username, password))
        t2 = time.time()
        self.assertEqual(resp.status_code, 200)
        answer = list(resp.json()["query_sources"][0].values())[-1]
        if USE_WANDB:
            self.table.add_data(
                    self.llm_service,
                    dataset,
                    question_type,
                    question_theme,
                    question,
                    true_answer,
                    function_call,
                    resp.json()["natural_language_response"], 
                    str(answer),
                    list(resp.json()["query_sources"][0].keys())[-1],
                    (true_answer == str(answer)),
                    t2-t1
            )
        self.assertEqual(true_answer, str(answer))
    return test_name, test

with open("./configs/db_config.json", "r") as config_file:
    config = json.load(config_file)

for suite in ["OGB_MAG"]:
    questions = "./test_questions/"+suite+"/"+suite+"Questions.tsv"
    questions = pd.read_csv(questions, delimiter="\t")
    
    tests = list(questions.apply(lambda x: test_generator(suite, x, config["username"], config["password"]), axis = 1))
    for test in tests:
        setattr(CommonTests, test[0], test[1])