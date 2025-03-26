from common.chunkers import character_chunker, regex_chunker, semantic_chunker, markdown_chunker
from common.config import doc_processing_config, embedding_service, llm_config
from common.llm_services import (
    AWS_SageMaker_Endpoint,
    AWSBedrock,
    AzureOpenAI,
    GoogleVertexAI,
    Groq,
    HuggingFaceEndpoint,
    Ollama,
    OpenAI,
)

def get_chunker():
    chunker_type = doc_processing_config.get("chunker")
    if chunker_type == "semantic":
        chunker = semantic_chunker.SemanticChunker(
            embedding_service,
            doc_processing_config["chunker_config"].get("method", "percentile"),
            doc_processing_config["chunker_config"].get("threshold", 0.95),
        )
    elif chunker_type == "regex":
        chunker = regex_chunker.RegexChunker(
            pattern=doc_processing_config["chunker_config"].get("pattern", "\\r?\\n")
        )
    elif chunker_type == "character":
        chunker = character_chunker.CharacterChunker(
            chunk_size=doc_processing_config["chunker_config"].get("chunk_size", 1024),
            overlap_size=doc_processing_config["chunker_config"].get("overlap_size", 0),
        )
    elif chunker_type == "markdown":
        s_chunker = semantic_chunker.SemanticChunker(
            embedding_service,
            "percentile",
            0.90,
        )
        chunker = markdown_chunker.MarkdownChunker(
            s_chunker
        )
    else:
        raise ValueError(f"Invalid chunker type: {chunker_type}")

    return chunker


def get_llm_service():
    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        llm_provider = OpenAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        llm_provider = AzureOpenAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        llm_provider = AWS_SageMaker_Endpoint(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "vertexai":
        llm_provider = GoogleVertexAI(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "bedrock":
        llm_provider = AWSBedrock(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "groq":
        llm_provider = Groq(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "ollama":
        llm_provider = Ollama(llm_config["completion_service"])
    elif llm_config["completion_service"]["llm_service"].lower() == "huggingface":
        llm_provider = HuggingFaceEndpoint(llm_config["completion_service"])

    return llm_provider
