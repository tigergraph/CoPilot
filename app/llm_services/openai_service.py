from app.llm_services import LLM_Model
import os
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class OpenAI(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        for auth_detail in config["authentication_configuration"].keys():
            os.environ[auth_detail] = config["authentication_configuration"][auth_detail]
        
        from langchain.chat_models import ChatOpenAI
        model_name = config["llm_model"]
        self.llm = ChatOpenAI(temperature=config["model_kwargs"]["temperature"],
                              model_name=model_name)
        self.prompt_path = config["prompt_path"]
        logger.info(f"request_id={req_id_cv.get()} instantiated OpenAI model_name={model_name}")

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")
    
    @property
    def model(self):
        return self.llm