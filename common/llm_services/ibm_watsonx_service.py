import logging
import os

from common.llm_services import LLM_Model
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)


class IBMWatsonX(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][
                auth_detail
            ]

        from langchain_ibm import ChatWatsonx

        model_name = config["llm_model"]
        self.llm = ChatWatsonx(
            params={"temperature": config["model_kwargs"]["temperature"], "max_new_tokens": config["model_kwargs"]["max_new_tokens"]},
            url=config["authentication_configuration"]["WATSONX_URL"],
            apikey=config["authentication_configuration"]["WATSONX_APIKEY"],
            model_id=model_name,
            project_id=config["model_kwargs"]["project_id"]
        )
        self.prompt_path = config["prompt_path"]
        LogWriter.info(
            f"request_id={req_id_cv.get()} instantiated WatsonX model_name={model_name}"
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
