from llm_services import LLM_Model
import os

class AzureOpenAI_GPT35_Turbo(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        from langchain.llms import AzureOpenAI
        self.llm = AzureOpenAI(
            deployment_name=config["deployment_name"],
            model_name=config["model_name"],
            temperature=0
        )

        self.prompt_path = "./prompts/azure_open_ai_gpt35_turbo_instruct/"

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm