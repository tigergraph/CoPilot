from app.storage.azure_blob_store import AzureBlobStore
from app.storage.google_blob_store import GoogleBlobStore
from app.storage.s3_blob_store import S3BlobStore
from app.py_schemas import BatchDocumentIngest, Document, DocumentChunk, KnowledgeGraph
from typing import List, Union
import json
from datetime import datetime
from app.status import Status, IngestionProgress
from app.supportai.extractors import LLMEntityRelationshipExtractor

from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pyTigerGraph import TigerGraphConnection


class BaseIngestion():
    def __init__(self, embedding_service, llm_service, conn: TigerGraphConnection, status: Status):
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.conn = conn
        self.status = status

    def chunk_documents(self, documents, chunker, chunker_params):
        for doc in documents:
            doc.document_chunks = self.chunk_document(doc, chunker, chunker_params)
    
    def chunk_document(self, document, chunker, chunker_params):
        if chunker.lower() == "regex":
            from app.supportai.chunkers.regex_chunker import RegexChunker
            chunker = RegexChunker(chunker_params["pattern"])
        elif chunker.lower() == "characters":
            from app.supportai.chunkers.character_chunker import CharacterChunker
            chunker = CharacterChunker(chunker_params["chunk_size"], chunker_params.get("overlap", 0))
        else:
            raise ValueError(f"Chunker {chunker} not supported")

        chunks = chunker(document.text)
        chunks = [DocumentChunk(document_chunk_id=f"{document.document_id}_chunk_{i}", text=chunk) for i, chunk in enumerate(chunks)]
        return chunks
    
    def embed_document(self, document: Document):
        document.document_embedding = self.embedding_service.embed_query(document.text)

    def embed_documents(self, documents: List[Document]):
        return self.embedding_service.embed_documents([doc.text for doc in documents])
    
        
    def document_er_extraction(self, document: Union[Document, DocumentChunk]):
        extractor = LLMEntityRelationshipExtractor(self.llm_service)
        return extractor.extract(document.text)
    
    def documents_er_extraction(self, documents: List[Document]):
        for doc in documents:
            self.document_er_extraction(doc)

    def upsert_documents(self, documents: List[Document]):
        for doc in documents:
            self.upsert_document(doc)

    def upsert_chunk(self, chunk: DocumentChunk):
        now = datetime.now()
        date_added = now.strftime("%Y-%m-%d %H:%M:%S")
        chunk_id = chunk.document_chunk_id
        doc_id = chunk.document_chunk_id.split("_")[0]
        self.status.progress.chunk_failures[chunk_id] = []
        try:
            self.conn.upsertVertex("DocumentChunk", chunk_id, attributes={"embedding": chunk.chunk_embedding, "date_added": date_added, "idx": int(chunk_id.split("_")[-1])})
            self.conn.upsertVertex("Content", chunk_id, attributes={"text": chunk.text, "date_added": date_added})
            self.conn.upsertEdge("DocumentChunk", chunk_id, "HAS_CONTENT", "Content", chunk_id)
            self.conn.upsertEdge("Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id)
            if int(chunk_id.split("_")[-1]) > 0:
                self.conn.upsertEdge("DocumentChunk", chunk_id, "IS_AFTER", "DocumentChunk", doc_id+"_chunk_"+str(int(chunk_id.split("_")[-1])-1))
        except Exception as e:
            self.status.progress.chunk_failures[chunk_id].append(e)
        
        if chunk.entities != []:
            try:
                self.conn.upsertVertices("Entity", [(x["id"], {"definition": x["definition"], "date_added": date_added, "embedding": self.embedding_service.embed_query(x["definition"])}) for x in chunk.entities])
                self.conn.upsertEdges("DocumentChunk", "CONTAINS_ENTITY", "Entity", [(chunk_id, x["id"], {}) for x in chunk.entities])
            except Exception as e:
                self.status.progress.chunk_failures[chunk_id].append(e)
        
        if chunk.relationships != []:
            try:
                self.conn.upsertVertices("Relationship", [(x["source"]+":"+x["type"]+":"+x["target"], {"definition": x["definition"], "short_name": x["type"], "date_added": date_added, "embedding": self.embedding_service.embed_query(x["definition"])}) for x in chunk.relationships])
                self.conn.upsertEdges("Entity", "IS_HEAD_OF", "Relationship", [(x["source"], x["source"]+":"+x["type"]+":"+x["target"], {}) for x in chunk.relationships])
                self.conn.upsertEdges("Relationship", "HAS_TAIL", "Entity", [(x["source"]+":"+x["type"]+":"+x["target"], x["target"], {}) for x in chunk.relationships])
                self.conn.upsertEdges("DocumentChunk", "MENTIONS_RELATIONSHIP", "Relationship", [(chunk_id, x["source"]+":"+x["type"]+":"+x["target"], {}) for x in chunk.relationships])
            except Exception as e:
                self.status.progress.chunk_failures[chunk_id].append(e)

    def upsert_document(self, document: Document):
        now = datetime.now()
        date_added = now.strftime("%Y-%m-%d %H:%M:%S")
        doc_id = document.document_id
        doc_collection = document.document_collection
        doc_emb = document.document_embedding
        self.status.progress.doc_failures[doc_id] = []
        try:
            self.conn.upsertVertex("Document", doc_id, attributes={"embedding": doc_emb, "date_added": date_added})
            if doc_collection:
                self.conn.upsertEdge("DocumentCollection", doc_collection, "CONTAINS_DOCUMENT", "Document", doc_id)
            self.conn.upsertVertex("Content", doc_id, attributes={"text": document.text, "date_added": date_added})
            self.conn.upsertEdge("Document", doc_id, "HAS_CONTENT", "Content", doc_id)
        except Exception as e:
            self.status.progress.doc_failures[doc_id].append(e)
        
        if document.entities != []:
            try:
                self.conn.upsertVertices("Entity", [(x["id"], {"definition": x["definition"], "date_added": date_added, "embedding": self.embedding_service.embed_query(x["definition"])}) for x in document.entities])
                self.conn.upsertEdges("Document", "CONTAINS_ENTITY", "Entity", [(doc_id, x["id"], {}) for x in document.entities])
            except Exception as e:
                self.status.progress.doc_failures[doc_id].append(e)
        
        if document.relationships != []:
            try:
                self.conn.upsertVertices("Relationship", [(x["source"]+":"+x["type"]+":"+x["target"], {"definition": x["definition"], "short_name": x["type"], "date_added": date_added, "embedding": self.embedding_service.embed_query(x["definition"])}) for x in document.relationships])
                self.conn.upsertEdges("Entity", "IS_HEAD_OF", "Relationship", [(x["source"], x["source"]+":"+x["type"]+":"+x["target"], {}) for x in document.relationships])
                self.conn.upsertEdges("Relationship", "HAS_TAIL", "Entity", [(x["source"]+":"+x["type"]+":"+x["target"], x["target"], {}) for x in document.relationships])
                self.conn.upsertEdges("Document", "MENTIONS_RELATIONSHIP", "Relationship", [(doc_id, x["source"]+":"+x["type"]+":"+x["target"], {}) for x in document.relationships])
            except Exception as e:
                self.status.progress.doc_failures[doc_id].append(e)



class BatchIngestion(BaseIngestion):
    def __init__(self, embedding_service, llm_service, conn: TigerGraphConnection, status: Status):
        super().__init__(embedding_service=embedding_service, llm_service=llm_service, conn=conn, status=status)

    def _ingest(self, documents: List[Document], chunker, chunker_params):
        self.chunk_documents(documents, chunker, chunker_params)
        self.status.progress.num_chunks_in_doc = {doc.document_id: len(doc.document_chunks) for doc in documents}
        for doc in documents:
            self.embed_document(doc)
            res = self.document_er_extraction(doc)
            doc.entities = res["nodes"]
            doc.relationships = res["rels"]
            if doc.document_chunks:
                for chunk in doc.document_chunks:
                    chunk.chunk_embedding = self.embedding_service.embed_query(chunk.text)
                    res = self.document_er_extraction(chunk)
                    chunk.entities = res["nodes"]
                    chunk.relationships = res["rels"]
                    self.upsert_chunk(chunk)
            self.upsert_document(doc)
            self.status.progress.num_docs_ingested += 1
        self.status.status = "complete"
        return self.status.to_dict()

    def ingest_blobs(self, doc_source: BatchDocumentIngest):
        if doc_source.service == "s3":
            blob_store = S3BlobStore(doc_source.service_params["aws_access_key_id"],
                                     doc_source.service_params["aws_secret_access_key"])
        elif doc_source.service == "google":
            blob_store = GoogleBlobStore(doc_source.service_params["google_credentials"])
        elif doc_source.service == "azure":
            blob_store = AzureBlobStore(doc_source.service_params["azure_connection_string"])
        else:
            raise ValueError(f"Service {doc_source.service} not supported")
            
        # get the list of documents
        documents = []
        if doc_source.service_params["type"].lower() == "file":
            content = blob_store.read_document(doc_source.service_params["bucket"], doc_source.service_params["key"])
            doc = Document(document_id=doc_source.service_params["key"], text=content)
            documents = [doc]
        elif doc_source.service_params["type"].lower() == "directory":
            keys = blob_store.list_documents(doc_source.service_params["bucket"], doc_source.service_params["key"])
            for key in keys:
                content = blob_store.read_document(doc_source.service_params["bucket"], key)
                doc = Document(document_id=key, text=content, document_collection=doc_source.service_params["bucket"] + "_" + doc_source.service_params["key"])
                documents.append(doc)
        else:
            raise ValueError(f"Type {doc_source.service_params['type']} not supported")

        self.status.progress = IngestionProgress(num_docs=len(documents))
        return self._ingest(documents, doc_source.chunker, doc_source.chunker_params)