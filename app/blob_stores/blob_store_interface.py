class BlobStoreInterface:
    def __init__(self):
        self.client = None

    def list_documents(self, bucket: str, prefix: str):
        raise NotImplementedError

    def read_document(self, bucket: str, key: str) -> str:
        raise NotImplementedError