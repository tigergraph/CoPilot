from app.llm_services import LLM_Model
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)
class GoogleVertexAI(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import VertexAI
        model_name = config["llm_model"]
        self.llm = VertexAI(
            model_name=model_name,
            max_output_tokens=1000,
            **config["model_kwargs"]
        )

        self.prompt_path = config["prompt_path"]
        logger.info(f"request_id={req_id_cv.get()} instantiated GoogleVertexAI model_name={model_name}")

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm