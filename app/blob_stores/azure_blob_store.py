from app.blob_stores.blob_store_interface import BlobStoreInterface
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

class AzureBlobStore(BlobStoreInterface):
    def __init__(self, connection_string: str):
        self.client = BlobServiceClient.from_connection_string(connection_string)

    def list_documents(self, container_name: str, prefix: str):
        container_client = self.client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blob_list]

    def read_document(self, container_name: str, blob_name: str) -> str:
        blob_client = self.client.get_blob_client(container=container_name, blob=blob_name)
        return blob_client.download_blob().content_as_text()