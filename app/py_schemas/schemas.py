from pydantic import BaseModel
from typing import Optional, Union, Annotated, List, Dict


class NaturalLanguageQuery(BaseModel):
    query: str


class SupportAIQuestion(BaseModel):
    question: str
    method: str = "hybrid"
    method_params: dict = {}


class SupportAIInitConfig(BaseModel):
    chunker: str
    chunker_params: dict
    extractor: str
    extractor_params: dict


class GSQLQueryInfo(BaseModel):
    function_header: str
    description: str
    docstring: str
    param_types: dict = {}


class CoPilotResponse(BaseModel):
    natural_language_response: str
    answered_question: bool
    response_type: str
    query_sources: Dict = None


class BatchDocumentIngest(BaseModel):
    service: str
    service_params: dict
    chunker: str = None
    chunker_params: dict = None


class S3BatchDocumentIngest(BatchDocumentIngest):
    service: str = "s3"
    service_params: dict = {
        "bucket": str,
        "key": str,
        "type": str,
        "aws_access_key_id": str,
        "aws_secret_access_key": str,
    }


class GoogleBatchDocumentIngest(BatchDocumentIngest):
    service: str = "s3"
    service_params: dict = {
        "bucket": str,
        "key": str,
        "type": str,
        "google_credentials": str,
    }


class AzureBatchDocumentIngest(BatchDocumentIngest):
    service: str = "s3"
    service_params: dict = {
        "bucket": str,
        "key": str,
        "type": str,
        "azure_connection_string": str,
    }


class DocumentChunk(BaseModel):
    document_chunk_id: str
    text: str
    chunk_embedding: List[float] = None
    entities: List[Dict] = None
    relationships: List[Dict] = None


class Document(BaseModel):
    document_id: str
    text: str
    document_embedding: List[float] = None
    document_chunks: List[DocumentChunk] = None
    entities: List[Dict] = None
    relationships: List[Dict] = None
    document_collection: str = None


class CreateVectorIndexConfig(BaseModel):
    index_name: str
    vertex_types: List[str]
    M: int = 20
    ef_construction: int = 128


class CreateIngestConfig(BaseModel):
    data_source: str
    data_source_config: Dict
    loader_config: Dict = {"doc_id_field": str, "content_field": str}
    file_format: str = "json"


class LoadingInfo(BaseModel):
    load_job_id: str
    data_source_id: str
    file_path: str


class QueryDeleteRequest(BaseModel):
    ids: Optional[Union[str, List[str]]]
    expr: Optional[str]


class QueryUperstRequest(BaseModel):
    id: Optional[str]
    query_info: Optional[GSQLQueryInfo]
