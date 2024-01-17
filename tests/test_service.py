import pandas as pd
import os
from fastapi.testclient import TestClient
import json
import wandb
from langchain.evaluation import load_evaluator
from langchain.chat_models import ChatOpenAI
import time
from pygit2 import Repository, Commit

EPS = 0.001

class CommonTests():
    @classmethod
    def setUpClass(cls, schema="all", use_wandb=True):
        cls.USE_WANDB = use_wandb
        def question_test_generator(dataset, row, username, password):
            # Need to extract q/a pairs before test is generated,
            # as otherwise we look at the last question/answer pair is used
            question = row["Question"]
            true_answer = str(row["Answer"])
            function_call = row["Function Call"]
            question_theme = row["Question Theme"]
            question_type = row["Question Type"]

            test_name = "test_question_"+dataset+"_"+str(row.name)+question_theme.replace(" ", "_")

            def test(self):
                def json_are_equal(obj1, obj2, epsilon=EPS):
                    # Check if the types are the same
                    if type(obj1) != type(obj2):
                        return False
                    
                    # Check for lists
                    if isinstance(obj1, list):
                        if len(obj1) != len(obj2):
                            return False
                        for i in range(len(obj1)):
                            if not json_are_equal(obj1[i], obj2[i], epsilon):
                                return False
                        return True
                    
                    # Check for dictionaries
                    elif isinstance(obj1, dict):
                        if set(obj1.keys()) != set(obj2.keys()):
                            return False
                        for key in obj1:
                            if not json_are_equal(obj1[key], obj2[key], epsilon):
                                return False
                        return True
                    
                    # Check for floats with epsilon
                    elif isinstance(obj1, float):
                        return abs(obj1 - obj2) < epsilon
                    
                    # Check for other types
                    else:
                        return obj1 == obj2


                t1 = time.time()
                resp = self.client.post("/"+dataset+"/query", json={"query": question}, auth=(username, password))
                t2 = time.time()
                self.assertEqual(resp.status_code, 200)
                evaluator = load_evaluator("string_distance")
                try:
                    answer = resp.json()["query_sources"]["result"]
                    query_source = resp.json()["query_sources"]["function_call"]
                    question_answered = resp.json()["answered_question"]
                except:
                    answer = ""
                    query_source = str(resp.json()["query_sources"])
                    question_answered = resp.json()["answered_question"]
                correct = False
                if isinstance(answer, str):
                    string_dist = evaluator.evaluate_strings(prediction=answer, reference=true_answer)["score"]
                    if string_dist <= .2:
                        correct = True
                elif isinstance(answer, list):
                    json_form = json.loads(true_answer)
                    try:
                        correct = json_are_equal(answer, json_form)
                    except Exception as e:
                        correct = False
                elif isinstance(answer, dict):
                    json_form = json.loads(true_answer)
                    try:
                        correct = json_are_equal(answer, json_form)
                    except Exception as e:
                        correct = False
                elif isinstance(answer, int):
                    try:
                        if answer == int(true_answer):
                            correct = True
                    except ValueError:
                        correct = False
                elif isinstance(answer, float):
                    try:
                        if abs(answer - float(true_answer)) <= EPS:
                            correct = True
                    except ValueError:
                        correct = False

                if question_answered and not(correct): # final LLM evaluation
                    fp = open("../configs/test_evaluation_model_config.json")
                    test_llm_config = json.load(fp)
                    fp.close()
                    llm = ChatOpenAI(**test_llm_config)
                    
                    evaluator = load_evaluator("labeled_score_string", llm=llm)

                    eval_result = evaluator.evaluate_strings(
                        prediction=str(answer)+" answered by this function call: " +str(query_source),
                        reference=str(true_answer)+" answered by this function call: "+str(function_call),
                        input=question
                    )

                    if eval_result["score"] >= 7:
                        correct = True

                if self.USE_WANDB:
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
                            query_source,
                            correct,
                            question_answered,
                            t2-t1
                    )

                self.assertEqual(correct, True)
            return test_name, test


        def query_registration_test_generator(dataset, username, password, query_name, query_json):
            
            # Need to extract q/a pairs before test is generated,
            # as otherwise we look at the last question/answer pair is used

            test_name = "test_insert_"+dataset+"_"+query_name

            def test(self):
                resp = self.client.post("/"+dataset+"/registercustomquery",
                                        json=json.loads(query_json), 
                                        auth=(username, password))
                self.assertEqual(resp.status_code, 200)
                id = resp.json()[0]
                self.assertIsInstance(id, str)
            return test_name, test

        with open(os.environ["DB_CONFIG"], "r") as config_file:
            config = json.load(config_file)

        def get_query_and_prompt(suite, query):
            with open("./test_questions/"+suite+"/"+query+"/"+query+"_prompt.json") as f:
                query_desc = f.read()
            return query_desc


        if schema == "all":
            schemas = [x for x in os.listdir('./test_questions/') if not(os.path.isfile('./test_questions/'+x))]
        else:
            schemas = [schema]

        for suite in schemas:
            queries = [x for x in os.listdir('./test_questions/'+suite+"/") if not(os.path.isfile('./test_questions/'+suite+"/"+x)) and not(x == "tmp") and not(x == "gsql")]

            prompts = [(q, get_query_and_prompt(suite, q)) for q in queries]

            registration_tests = [query_registration_test_generator(suite, config["username"], config["password"], q[0], q[1]) for q in prompts]

            for rt in registration_tests:
                setattr(cls, rt[0], rt[1])

            questions = "./test_questions/"+suite+"/"+suite+"Questions.tsv"
            questions = pd.read_csv(questions, delimiter="\t")
            
            tests = list(questions.apply(lambda x: question_test_generator(suite, x, config["username"], config["password"]), axis = 1))
            for test in tests:
                setattr(cls, test[0], test[1])

    @classmethod
    def tearDownClass(cls):
        if cls.USE_WANDB:
            df = cls.table.get_dataframe()
            q_types = list(df["Question Type"].unique())
            for q_type in q_types:
                filtered_df = df[df["Question Type"] == q_type]
                unique_datasets = list(df["Dataset"].unique())
                for dataset in unique_datasets:
                    cls.config = {
                        "llm_service": cls.llm_service,
                        "question_type": q_type,
                        "dataset": dataset,
                        "branch": Repository('.').head.shorthand,
                        "commit_hash": Repository('.').head.peel(Commit).id.hex
                    }
                    final_df = filtered_df[filtered_df["Dataset"] == dataset]
                    if final_df.shape[0] > 0:
                        cls.wandbLogger = wandb.init(project="llm-eval-sweep", config=cls.config)
                        acc = (final_df["Answer Correct"].sum())/final_df["Answer Correct"].shape[0]
                        not_wrong_perc = (final_df["Answer Correct"].sum() + (final_df["Answered Question"] == False).sum())/final_df["Answer Correct"].shape[0]
                        avg_resp_time = final_df["Response Time (seconds)"].mean()
                        cls.wandbLogger.log({"LLM Service": cls.llm_service,
                                            "Question Type": q_type,
                                            "Dataset": dataset,
                                            "Accuracy": acc,
                                            "Not Wrong Percent": not_wrong_perc,
                                            "Average Response Time (seconds)": avg_resp_time,
                                            "Number of Questions": final_df["Answer Correct"].shape[0]}, commit=True)
                        tmp_table = wandb.Table(dataframe=final_df)
                        cls.wandbLogger.log({"qa_results": tmp_table})
                        wandb.finish()
