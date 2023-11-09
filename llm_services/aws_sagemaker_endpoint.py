from llm_services import LLM_Model
import boto3

# TODO: Finish implementation

class AWS_SageMaker_Endpoint(LLM_Model):
    def __init__(self, config):
        super().__init__(config)
        from langchain.llms import SagemakerEndpoint

        roleARN = "arn:aws:iam::123456789:role/cross-account-role"
        sts_client = boto3.client("sts")
        response = sts_client.assume_role(
            RoleArn=roleARN, RoleSessionName="CrossAccountSession"
        )

        client = boto3.client(
            "sagemaker-runtime",
            region_name="us-west-2",
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
        )

        self.llm = SagemakerEndpoint(
            endpoint_name="endpoint-name",
            client=client,
            model_kwargs={"temperature": 1e-10}
        )

        self.prompt_path = "./prompts/aws_bedrock_titan/"

    @property
    def map_question_schema_prompt(self):
        return self._read_prompt_file(self.prompt_path+"map_question_to_schema.txt")

    @property
    def generate_function_prompt(self):
        return self._read_prompt_file(self.prompt_path+"generate_function.txt")

    @property
    def model(self):
        return self.llm