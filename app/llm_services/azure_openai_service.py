from app.llm_services import LLM_Model
import os

class AzureOpenAI(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        from langchain.llms import AzureOpenAI
        self.llm = AzureOpenAI(
            deployment_name=config["deployment_name"],
            model_name=config["llm_model"],
            temperature=config["model_kwargs"]["temperature"]
        )

        self.prompt_path = config["prompt_path"]

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm