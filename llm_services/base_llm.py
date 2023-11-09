import os

class LLM_Model():
    def __init__(self, config):
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        self.llm = None
    
    def _read_prompt_file(self, path):
        with open(path) as f:
            prompt = f.read()
        return prompt
    
    @property
    def map_question_schema_prompt(self):
        raise("map_question_schema_prompt not supported in base class")

    @property
    def generate_function_prompt(self):
        raise("generate_function_prompt not supported in base class")

    @property
    def model(self):
        raise ("model not supported in base class")
