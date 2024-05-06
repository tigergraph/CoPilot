from abc import ABC, abstractmethod
from typing import Iterable, Tuple, List
import logging

logger = logging.getLogger(__name__)


class EmbeddingStore(ABC):
    """EmbeddingStore Base Class
    Used for connecting to various embedding stores.
    """

    @abstractmethod
    def add_embeddings(
        self,
        embeddings: Iterable[Tuple[str, List[float]]],
        metadatas: List[dict] = None,
    ) -> None:
        """Add Embeddings.
        Add embeddings to the Embedding store.
        Args:
            embeddings (Iterable[Tuple[str, List[float]]]):
                Iterable of content and embedding of the document.
            metadatas (List[dict]):
                List of dictionaries containing the metadata for each document.
                The embeddings and metadatas list need to have identical indexing.
        """
        pass

    @abstractmethod
    def remove_embeddings(self, ids: List[str]) -> None:
        """Remove Embeddings.
        Remove embeddings from the vector store.
        Args:
            ids (str):
                ID of the document to remove from the embedding store
        """
        pass

    @abstractmethod
    def retrieve_similar(
        self, query_embedding: List[float], top_k: int = 10, filter_expr: str = None
    ) -> List[Tuple[str, float]]:
        """Retrieve Similar.
        Retrieve similar embeddings from the vector store given a query embedding.
        Args:
            query_embedding (List[float]):
                The embedding to search with.
            top_k (int, optional):
                The number of documents to return. Defaults to 10.
            filter_expr (str, optional):
                Filter expression to apply to the query. Defaults to None.
        Returns:
            A list of Tuples containing vector id and vector embedding
        """
        pass

    @abstractmethod
    def add_connection_parameters(self, query_params: dict) -> dict:
        """Add Connection Parameters.
        Add connection parameters to the query parameters.
        Args:
            query_params (dict):
                Dictionary containing the parameters for the GSQL query.
        Returns:
            A dictionary containing the connection parameters.
        """
        pass
