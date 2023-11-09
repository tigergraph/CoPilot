from llm_services import LLM_Model

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