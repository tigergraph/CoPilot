from abc import ABC, abstractmethod

from langchain_community.graphs.graph_document import GraphDocument


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text:str):
        pass

    @abstractmethod
    async def aextract(self, text:str) -> list[GraphDocument]:
        pass
