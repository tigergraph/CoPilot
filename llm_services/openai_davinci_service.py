from llm_services import LLM_Model
import os

class OpenAI_Davinci(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        from langchain.llms import OpenAI
        self.llm = OpenAI(temperature=0, model_name="text-davinci-003")
        self.prompt_path = "./prompts/open_ai_davinci-003/"

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")
    
    @property
    def model(self):
        return self.llm