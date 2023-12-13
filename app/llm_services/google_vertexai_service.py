from app.llm_services import LLM_Model

class GoogleVertexAI(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import VertexAI
        self.llm = VertexAI(
            model_name=config["llm_model"],
            max_output_tokens=1000,
            **config["model_kwargs"]
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