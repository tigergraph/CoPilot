from base_llm import LLM_Model

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