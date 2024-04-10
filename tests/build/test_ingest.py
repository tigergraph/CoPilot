import unittest
from unittest.mock import patch, MagicMock

import pytest

from app.supportai.supportai_ingest import BatchIngestion
from app.status import IngestionProgress

class TestBatchIngestion(unittest.TestCase):

    def setUp(self):
        self.embedding_service_mock = MagicMock()
        self.llm_service_mock = MagicMock()
        self.conn_mock = MagicMock()
        self.status_mock = MagicMock()
        self.status_mock.progress = IngestionProgress(num_docs_ingested=0, num_docs=0)
        self.batch_ingestion = BatchIngestion(embedding_service=self.embedding_service_mock, llm_service=self.llm_service_mock, conn=self.conn_mock, status=self.status_mock)

    @patch('app.supportai.supportai_ingest.BatchIngestion._ingest')
    @patch('boto3.client')
    def test_ingest_blobs_s3_file_success(self, mock_boto3_client, mock_ingest):
        mock_blob = mock_boto3_client.return_value
        mock_get_object = mock_blob.get_object
        mock_get_object.return_value = {'Body': MagicMock(read=lambda: b'Fake document content')}
        
        mock_ingest.return_value = None

        doc_source = MagicMock()
        doc_source.service = "s3"
        doc_source.chunker = "characters"
        doc_source.chunker_params = { "chunk_size" : 11 }
        doc_source.service_params = {
            "type": "file", 
            "bucket": "test-bucket", 
            "key": "directory/", 
            "aws_access_key_id": "id", 
            "aws_secret_access_key": "key"
        }
        
        self.batch_ingestion.ingest_blobs(doc_source)        
        mock_ingest.assert_called_once()
        mock_blob.get_object.assert_called_once_with(Bucket="test-bucket", Key="directory/")

    @patch('app.supportai.supportai_ingest.BatchIngestion._ingest')
    @patch('azure.storage.blob.BlobServiceClient.from_connection_string')
    def test_ingest_blobs_azure_file_success(self, mock_from_connection_string, mock_ingest):
        mock_blob_service_client = MagicMock()
        mock_from_connection_string.return_value = mock_blob_service_client
        mock_blob_client = MagicMock()
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.return_value.content_as_text.return_value = 'Fake document content'

        mock_ingest.return_value = None

        container_name = "test-bucket"
        blob_name = "directory/file.txt"
        doc_source = MagicMock()
        doc_source.service = "azure"
        doc_source.chunker = "characters"
        doc_source.chunker_params = { "chunk_size": 11 }
        doc_source.service_params = {
            "type": "file",
            "bucket": container_name,
            "key": blob_name,
            "azure_connection_string": "connection_string"
        }

        batch_ingestion = BatchIngestion(embedding_service=MagicMock(), llm_service=MagicMock(), conn=MagicMock(), status=MagicMock())
        batch_ingestion.ingest_blobs(doc_source)

        mock_ingest.assert_called_once()
        mock_blob_service_client.get_blob_client.assert_called_once()
        mock_blob_client.download_blob.assert_called_once()
        mock_blob_client.download_blob.return_value.content_as_text.assert_called_once()

    @patch('app.supportai.supportai_ingest.BatchIngestion._ingest')
    @patch('google.cloud.storage.Client.from_service_account_json')
    def test_ingest_blobs_google_file_success(self, mock_from_service_account_json, mock_ingest):
        mock_blob_service_client = MagicMock()
        mock_from_service_account_json.return_value = mock_blob_service_client
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_blob_service_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        document_content = "Fake document content"
        mock_blob.download_as_text.return_value = document_content

        mock_ingest.return_value = None

        container_name = "test-bucket"
        blob_name = "directory/file.txt"
        doc_source = MagicMock()
        doc_source.service = "google"
        doc_source.chunker = "characters"
        doc_source.chunker_params = { "chunk_size": 11 }
        doc_source.service_params = {
            "type": "file",
            "bucket": container_name,
            "key": blob_name,
            "google_credentials": "credentials"
        }

        batch_ingestion = BatchIngestion(embedding_service=MagicMock(), llm_service=MagicMock(), conn=MagicMock(), status=MagicMock())
        batch_ingestion.ingest_blobs(doc_source)

        mock_blob_service_client.bucket.assert_called_once_with(container_name)
        mock_bucket.blob.assert_called_once_with(blob_name)
        mock_blob.download_as_text.assert_called_once()

    @patch('boto3.client')
    def test_ingest_blobs_unsupported_type(self, mock_boto3_client):
        # Test to ensure ValueError is raised for unsupported types without mocking blob stores, as the method should fail before any blob store interaction 
        mock_s3 = mock_boto3_client.return_value
        mock_get_object = mock_s3.get_object
        mock_get_object.return_value = {'Body': MagicMock(read=lambda: b'Fake document content')}
        
        doc_source = MagicMock()
        doc_source.service = "unsupported"
        doc_source.service_params = {"type": "file", "bucket": "test-bucket", "key": "directory/", "aws_access_key_id": "id", "aws_secret_access_key": "key"}

        ingestion = BatchIngestion(embedding_service=MagicMock(), llm_service=MagicMock(), conn=MagicMock(), status=MagicMock())
        
        with self.assertRaises(ValueError) as context:
            ingestion.ingest_blobs(doc_source)
        
        self.assertTrue("Service unsupported not supported" in str(context.exception))

if __name__ == '__main__':
    unittest.main()