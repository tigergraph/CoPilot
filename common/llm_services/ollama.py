from common.llm_services import LLM_Model
import os
import logging
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)


class Ollama(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain_community.llms import Ollama as lc_Ollama

        model_name = config["llm_model"]
        self.llm = lc_Ollama(model=model_name, temperature=config["model_kwargs"]["temperature"], base_url=config.get("base_url", "http://localhost:11434"))
        self.prompt_path = config["prompt_path"]
        LogWriter.info(
            f"request_id={req_id_cv.get()} instantiated Ollama model_name={model_name}"
        )

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path + "map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path + "generate_function.txt")

    @property
    def entity_relationship_extraction_prompt(self):
        return self._read_prompt_file(
            self.prompt_path + "entity_relationship_extraction.txt"
        )

    @property
    def model(self):
        return self.llm
