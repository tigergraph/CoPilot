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
        """
        returns a list of GraphDocument:
        Each doc is:
            nodes=[
                Node(
                    id='Marie Curie',
                    type='Person',
                    properties={
                        'description': 'A Polish and naturalised-French physicist and chemist who conducted pioneering research on radioactivity.'
                    }
                ),
                ...
            ],
            relationships=[
                Relationship(
                    source=Node(id='Marie Curie', type='Person'),
                    target=Node(id='Pierre Curie', type='Person'),
                    type='SPOUSE'
                ),
                ...
            ]
        """
        doc = Document(page_content=text)
        graph_docs = self.transformer.convert_to_graph_documents([doc])
        translated_docs = self.translate(graph_docs)
        return translated_docs

    async def aextract(self, text:str) -> list[GraphDocument]:
        """
        returns a list of GraphDocument:
        Each doc is:
            nodes=[
                Node(
                    id='Marie Curie',
                    type='Person',
                    properties={
                        'description': 'A Polish and naturalised-French physicist and chemist who conducted pioneering research on radioactivity.'
                    }
                ),
                ...
            ],
            relationships=[
                Relationship(
                    source=Node(id='Marie Curie', type='Person'),
                    target=Node(id='Pierre Curie', type='Person'),
                    type='SPOUSE'
                ),
                ...
            ]
        """
        doc = Document(page_content=text)
        graph_docs = await self.transformer.aconvert_to_graph_documents([doc])
        return graph_docs
