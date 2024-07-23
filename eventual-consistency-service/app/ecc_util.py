from common.chunkers import character_chunker, regex_chunker, semantic_chunker
from common.config import doc_processing_config, embedding_service


def get_chunker():
    if doc_processing_config.get("chunker") == "semantic":
        chunker = semantic_chunker.SemanticChunker(
            embedding_service,
            doc_processing_config["chunker_config"].get("method", "percentile"),
            doc_processing_config["chunker_config"].get("threshold", 0.95),
        )
    elif doc_processing_config.get("chunker") == "regex":
        chunker = regex_chunker.RegexChunker(
            pattern=doc_processing_config["chunker_config"].get("pattern", "\\r?\\n")
        )
    elif doc_processing_config.get("chunker") == "character":
        chunker = character_chunker.CharacterChunker(
            chunk_size=doc_processing_config["chunker_config"].get("chunk_size", 1024),
            overlap_size=doc_processing_config["chunker_config"].get("overlap_size", 0),
        )
    else:
        raise ValueError("Invalid chunker type")

    return chunker
