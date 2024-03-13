from app.storage.base_blob_store import BlobStorage
from google.cloud import storage

class GoogleBlobStore(BlobStorage):
    def __init__(self, google_credentials_json):
        self.client = storage.Client.from_service_account_json(google_credentials_json)

    def list_documents(self, bucket_name: str, prefix: str):
        bucket = self.client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
        return [blob.name for blob in blobs]

    def read_document(self, bucket_name: str, blob_name: str) -> str:
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_text()