import logging
import os

if os.getenv("ECC"):
    from langchain_openai.chat_models import ChatOpenAI
else:
    from langchain_community.chat_models import ChatOpenAI

from common.llm_services import LLM_Model
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)


class OpenAI(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][
                auth_detail
            ]

        model_name = config["llm_model"]
        self.llm = ChatOpenAI(
            temperature=config["model_kwargs"]["temperature"], model_name=model_name
        )
        self.prompt_path = config["prompt_path"]
        LogWriter.info(
            f"request_id={req_id_cv.get()} instantiated OpenAI model_name={model_name}"
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
    def graphrag_scoring_prompt(self):
        filepath = self.prompt_path + "graphrag_scoring.txt"
        if os.path.exists(filepath):
            return self._read_prompt_file(filepath)
        else:
            return super().graphrag_scoring_prompt

    @property
    def question_expansion_prompt(self):
        filepath = self.prompt_path + "question_expansion.txt"
        if os.path.exists(filepath):
            return self._read_prompt_file(filepath)
        else:
            return super().question_expansion_prompt

    @property
    def supportai_response_prompt(self):
        filepath = self.prompt_path + "supportai_response.txt"
        if os.path.exists(filepath):
            return self._read_prompt_file(filepath)
        else:
            return super().supportai_response_prompt

    @property
    def hyde_prompt(self):
        filepath = self.prompt_path + "hyde.txt"
        if os.path.exists(filepath):
            return self._read_prompt_file(filepath)
        else:
            return super().hyde_prompt

    @property
    def model(self):
        return self.llm
