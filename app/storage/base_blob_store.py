from abc import abstractmethod, ABC


class BlobStorage(ABC):
    def __init__(self):
        self.client = None

    @abstractmethod
    def list_documents(self, bucket: str, prefix: str) -> list:
        """
        List documents in a specified bucket filtered by a prefix.

        Parameters:
        - bucket (str): The name of the bucket.
        - prefix (str): The prefix to filter documents by.

        Returns:
        - list: A list of document names matching the prefix in the specified bucket.
        """
        pass

    @abstractmethod
    def read_document(self, bucket: str, key: str) -> str:
        """
        Read a document from a specified bucket.

        Parameters:
        - bucket (str): The name of the bucket.
        - key (str): The key of the document to read.

        Returns:
        - str: The content of the document as a string.
        """
        pass
