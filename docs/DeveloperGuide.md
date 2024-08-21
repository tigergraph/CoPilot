# Developer Guide

## Introduction

Welcome to the developer guide for TigerGraph CoPilot. This guide provides information on how to add a new LangChain tool, embedding service, or LLM generation service to CoPilot.

## Table of Contents

- [Adding a New LangChain Tool](#adding-a-new-langchain-tool)
- [Adding a New Embedding Service](#embedding-a-service)
- [Adding a New LLM Generation Service](#adding-a-new-llm-generation-service)
- [Adding New Tests](#adding-a-new-test-suite)
  
## Adding a New LangChain Tool
If you want your agent to connect to other data sources or be able to perform custom logic, you can add a new LangChain tool to TigerGraph CoPilot. To add a new LangChain tool, follow these steps:
1. In the `app/tools` directory, create a new file for your tool. The file should be named `toolname.py` where `toolname` is the name of your tool.
2. Define your tool. The tool should a valid Python class that inherits from the LangChain `BaseTool` class. For more information refer to the [LangChain documentation](https://python.langchain.com/docs/modules/agents/tools/custom_tools#subclass-basetool).
3. Add your tool to the `app/tools/__init__.py` file. This file should contain an import statement for your tool. For example:
```python
from .generate_function import GenerateFunction
```
4. Enable your tool to be used by the agent. To do this, import and instantiate your tool in the `app/agent.py` file. For example:
```python
from tools import GenerateFunction
generate_function = GenerateFunction()
```

Then add the tool to the `tools` list in the `Agent` class. For example:
```python
tools = [mq2s, gen_func, new_tool]
```
5. Test your tool. Run the service and test your tool to ensure that it works as expected.

6. (Optional): Think that your tool could be useful for others? Consider contributing it! To contribute your tool, submit a pull request to the TigerGraph CoPilot repository and checkout our [contributing guidelines](./Contributing.md).

## Add a New Embedding Service
One might want to add a new embedding service to TigerGraph CoPilot to better fit their deployment environment. To do this, follow these steps:
1. In `app/embeddings/embedding_service.py` and create a new class that inherits from the `BaseEmbeddingService` class. For example:
```python
class MyEmbeddingService(BaseEmbeddingService):
    def __init__(self, config):
        super().__init__(config)
        # Add your custom initialization code here
```
2. Implement the needed methods for your service. If you utilize a LangChain-supported embedding service, you can use the `BaseEmbeddingService` class as a reference. If you are using a custom endpoint, you will need to implement the `embed_documents` and `embed_query` methods accordingly.
3. Import your service and dd your service to the `app/main.py` file where the `EmbeddingService` class is instantiated. For example:
```python
from common.embeddings.embedding_service import MyembeddingService

if llm_config["embedding_service"]["embedding_model_service"].lower() == "MyEmbeddingService":
    embedding_service = MyEmbeddingService(llm_config["embedding_service"])
```
4. Test your service. Run the service and test your service to ensure that it works as expected.
5. (Optional): Think that your service could be useful for others? Consider contributing it! To contribute your service, submit a pull request to the TigerGraph CoPilot repository and checkout our [contributing guidelines](./Contributing.md).

## Add a New LLM Generation Service

To add a new LLM generation service to TigerGraph CoPilot, follow these steps:

1. Create a new file in the `app/llm_services` directory. The file should be named `service_name.py` where `service_name` is the name of your service.
2. Define your service. The service should be a valid Python class that inherits from the `LLM_Model` class defined in the `app/llm_services/base_llm.py` file.
3. Add your service to the `app/llm_services/__init__.py` file. This file should contain an import statement for your service. For example:
```python
from .service_name import ServiceName
```
4. Import and instantiate your service in the `app/main.py` file. For example:
```python
from common.llm_services import ServiceName

# Within the instantiation of the Agent class elif block
elif llm_config["completion_service"]["llm_service"].lower() == "my_service":
    logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=my_service agent created")
    agent = TigerGraphAgent(AzureOpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
```
5. Test your service. Run the service and test your service to ensure that it works as expected.
6. (Optional): Think that your service could be useful for others? Consider contributing it! To contribute your service, submit a pull request to the TigerGraph CoPilot repository and checkout our [contributing guidelines](./Contributing.md).

## Adding a New Test Suite
To add a new InquiryAI test suite to TigerGraph CoPilot, follow these steps:

1. Download the InquiryAI test template from [here](https://docs.google.com/spreadsheets/d/1wyEgRhWjmgv0xkLQPOIWd00s0FQPgQy_prI5fnSrC5I/edit?usp=sharing) in `.tsv` format.

2. Create a new directory in the `tests/test_questions` directory. The directory should be named `suite_name` where `suite_name` is the name of your test suite.

3. Add the `.tsv` file to the new directory, populated with your example questions and expected answers.

4. (Optional): Add the necessary GSQL and setup script to the `tests/test_questions/suite_name` directory to support your test suite. The setup scripts are not run with the test suite, but help to set up the graph for the test suite. The tests assume that the graph is already set up.

5. Add necessary query descriptors to the `tests/test_questions/suite_name` directory. Within a directory named after the query, add a `.json` file with the query descriptor. Optionally add a `.gsql` file with the query itself.

6. Add the test suite to the `tests/test_questions/parse_test_config.py` file by adding an available schema to the `schema` argument list.

7. Test your test suite. Run the test suite and ensure that it works as expected. Run the tests with the following command (and add desired options described [here](../README.md#test-script-options)):
```bash
./run_tests.sh
```

8. (Optional): Think that your test suite could be useful for others? Consider contributing it! To contribute your test suite, submit a pull request to the TigerGraph CoPilot repository and checkout our [contributing guidelines](./Contributing.md).
