from app.blob_stores.blob_store_interface import BlobStoreInterface
import boto3

class S3BlobStore(BlobStoreInterface):
    def __init__(self, aws_access_key_id, aws_secret_access_key):
        self.client = boto3.client('s3', aws_access_key_id=aws_access_key_id,
                               aws_secret_access_key=aws_secret_access_key)

    def list_documents(self, bucket: str, prefix: str):
        response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', [])]

    def read_document(self, bucket: str, key: str) -> str:
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8', errors="replace")