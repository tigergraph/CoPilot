from pydantic import BaseModel
from typing import Union, Annotated, List, Dict

class NaturalLanguageQuery(BaseModel):
    query:str

class SupportAIQuestion(BaseModel):
    question:str
    method: str = "hybrid"
    method_params: dict = {}

class GSQLQueryInfo(BaseModel):
    function_header: str
    description: str
    docstring: str
    param_types: dict = {}

class NaturalLanguageQueryResponse(BaseModel):
    natural_language_response: str
    answered_question: bool
    query_sources: Dict = None

class BatchDocumentIngest(BaseModel):
    service: str
    service_params: dict
    chunker: str = None
    chunker_params: dict = None

class S3BatchDocumentIngest(BatchDocumentIngest):
    service: str = "s3"
    service_params: dict = {"bucket": str, 
                            "key": str,
                            "type": str,
                            "aws_access_key_id": str,
                            "aws_secret_access_key": str}

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