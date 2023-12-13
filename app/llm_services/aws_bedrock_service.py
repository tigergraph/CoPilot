from app.llm_services import LLM_Model
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

# TODO: Finish implementation

class AWSBedrock(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import Bedrock
        model_name = config["completion_service"]["llm_model"]
        self.llm = Bedrock(
            credentials_profile_name=config["completion_service"]["credentials_profile_name"],
            model_id=config["completion_service"]["llm_model"],
            temperature=0
        )

        self.prompt_path = "./prompts/aws_bedrock/"
        logger.info(f"request_id={req_id_cv.get()} instantiated AWSBedrock model_name={model_name}")

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm