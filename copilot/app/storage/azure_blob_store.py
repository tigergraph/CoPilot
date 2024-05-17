from app.storage.base_blob_store import BlobStorage
from azure.storage.blob import BlobServiceClient


class AzureBlobStore(BlobStorage):
    def __init__(self, connection_string: str):
        self.client = BlobServiceClient.from_connection_string(connection_string)

    def list_documents(self, container_name: str, prefix: str):
        container_client = self.client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blob_list]

    def read_document(self, container_name: str, blob_name: str) -> str:
        blob_client = self.client.get_blob_client(
            container=container_name, blob=blob_name
        )
        return blob_client.download_blob().content_as_text()
