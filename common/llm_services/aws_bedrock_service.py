from common.llm_services import LLM_Model
from langchain_community.chat_models import BedrockChat
import logging
from common.logs.log import req_id_cv
import boto3
from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)


class AWSBedrock(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        model_name = config["llm_model"]
        client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",
            aws_access_key_id=config["authentication_configuration"][
                "AWS_ACCESS_KEY_ID"
            ],
            aws_secret_access_key=config["authentication_configuration"][
                "AWS_SECRET_ACCESS_KEY"
            ],
        )
        self.llm = BedrockChat(
            client=client,
            model_id=model_name,
            model_kwargs={"temperature": 0},
        )

        self.prompt_path = config["prompt_path"]
        LogWriter.info(
            f"request_id={req_id_cv.get()} instantiated AWSBedrock model_name={model_name}"
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
