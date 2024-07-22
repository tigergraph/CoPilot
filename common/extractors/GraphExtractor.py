from langchain_community.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer

from common.config import get_llm_service, llm_config
from common.extractors.BaseExtractor import BaseExtractor


class GraphExtractor(BaseExtractor):
    def __init__(self):
        llm = get_llm_service(llm_config).llm
        self.transformer = LLMGraphTransformer(
            llm=llm,
            node_properties=["description"],
            relationship_properties=["description"],
        )

    def extract(self, text) -> list[GraphDocument]:
        doc = Document(page_content=text)
        graph_docs = self.transformer.convert_to_graph_documents([doc])
        return graph_docs
