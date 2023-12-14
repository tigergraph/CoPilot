from app.llm_services import LLM_Model
from langchain.llms.sagemaker_endpoint import LLMContentHandler
import json
from typing import Dict
import boto3
import logging
from app.log import req_id_cv

logger = logging.getLogger(__name__)

class ContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict = None) -> bytes:
        # Ensure that 'prompt' is a string
        #if not isinstance(prompt, str):
        #    raise ValueError("'prompt' must be a string.")
        input_dict = {"inputs": prompt, "parameters": model_kwargs}
        #input_dict.update(model_kwargs)
        input_str = json.dumps(input_dict)
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes):
        response_json = json.loads(output.read().decode("utf-8"))
        # Ensure that 'generated_text' is a key in the response JSON
        if "generation" not in response_json[0]:
            raise ValueError("'generation' not found in the response.")
        return response_json[0]["generation"]

class AWS_SageMaker_Endpoint(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import SagemakerEndpoint

        client = boto3.client(
            "sagemaker-runtime",
            region_name=config["authentication_configuration"]["region_name"],
        )

        model_name = config["endpoint_name"]
        self.llm = SagemakerEndpoint(
            endpoint_name=config["endpoint_name"],
            client=client,
            model_kwargs=config["model_kwargs"],
            endpoint_kwargs={"CustomAttributes": 'accept_eula=true'},
            content_handler=ContentHandler()
        )

        self.prompt_path = config["prompt_path"]
        logger.info(f"request_id={req_id_cv.get()} instantiated AWS_SageMaker_Endpoint model_name={model_name}")

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm