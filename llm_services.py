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


class OpenAI_Davinci(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
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


class AzureOpenAI_GPT35_Turbo(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import AzureOpenAI
        self.llm = AzureOpenAI(
            deployment_name=config["completion_service"]["deployment_name"],
            model_name=config["completion_service"]["model_name"],
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

class GoogleVertexAI(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import VertexAI
        self.llm = VertexAI(
            deployment_name=config["completion_service"]["deployment_name"],
            model_name=config["completion_service"]["model_name"],
            temperature=0
        )

        self.prompt_path = "./prompts/gcp_vertexai_palm/"

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm

class AWSBedrock_Titan(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import Bedrock
        self.llm = Bedrock(
            credentials_profile_name=config["completion_service"]["credentials_profile_name"],
            model_id=config["completion_service"]["model_id"],
            temperature=0
        )

        self.prompt_path = "./prompts/aws_bedrock_titan/"

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm