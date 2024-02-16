from app.py_schemas import S3BatchDocumentIngest, Document, DocumentChunk, KnowledgeGraph
from typing import List, Union
import json
from datetime import datetime
from app.status import Status, IngestionProgress

from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pyTigerGraph import TigerGraphConnection


class BaseIngestion():
    def __init__(self, embedding_service, llm_service, conn: TigerGraphConnection, stauts: Status):
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.conn = conn
        self.status = stauts

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
    

    def _extract_kg_from_doc(self, doc, chain, parser):
        try:
            out = chain.invoke({"input": doc, "format_instructions": parser.get_format_instructions()})
        except Exception as e:
            print("Error: ", e)
            return {"nodes": [], "rels": []}
        try:
            if "```json" not in out.content:
                json_out = json.loads(out.content.strip("content="))
            else:
                json_out = json.loads(out.content.split("```")[1].strip("```").strip("json").strip())

            formatted_rels = []
            for rels in json_out["rels"]:
                if isinstance(rels["source"], str) and isinstance(rels["target"], str):
                    formatted_rels.append(rels)
                elif isinstance(rels["source"], dict) and isinstance(rels["target"], str):
                    formatted_rels.append({"source": rels["source"]["id"], "target": rels["target"], "type": rels["type"], "definition": rels["definition"]})
                elif isinstance(rels["source"], str) and isinstance(rels["target"], dict):
                    formatted_rels.append({"source": rels["source"], "target": rels["target"]["id"], "type": rels["type"], "definition": rels["definition"]})
                elif isinstance(rels["source"], dict) and isinstance(rels["target"], dict):
                    formatted_rels.append({"source": rels["source"]["id"], "target": rels["target"]["id"], "type": rels["type"], "definition": rels["definition"]})
                else:
                    raise Exception("Relationship parsing error")
            return {"nodes": json_out["nodes"], "rels": formatted_rels}
        except:
            print("Error Processing: ", out)
        return {"nodes": [], "rels": []}
        
    def document_er_extraction(self, document: Union[Document, DocumentChunk]):
        parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)
        prompt = ChatPromptTemplate.from_messages(
                            [(
                            "system",
                            f"""# Knowledge Graph Instructions for GPT-4
                        ## 1. Overview
                        You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph.
                        - **Nodes** represent entities, concepts, and properties of entities.
                        - The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.
                        ## 2. Labeling Nodes
                        - **Consistency**: Ensure you use basic or elementary types for node labels.
                        - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
                        - **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
                        ## 3. Handling Numerical Data and Dates
                        - Numerical data, like age or other related information, should be incorporated as attributes or properties of the respective nodes.
                        - **No Separate Nodes for Dates/Numbers**: Do not create separate nodes for dates or numerical values. Always attach them as attributes or properties of nodes.
                        - **Property Format**: Properties must be in a key-value format. Only use properties for dates and numbers, string properties should be new nodes.
                        - **Quotation Marks**: Never use escaped single or double quotes within property values.
                        - **Naming Convention**: Use camelCase for property keys, e.g., `birthDate`.
                        ## 4. Coreference Resolution
                        - **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
                        If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"), 
                        always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.  
                        Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial. 
                        ## 5. Strict Compliance
                        Adhere to the rules strictly. Non-compliance will result in termination, including poor formatting. """),
                                ("human", "Use the given format to extract information from the following input: {input}"),
                                ("human", "Mandatory: Make sure to answer in the correct format, specified here: {format_instructions}"),
                            ])
        chain = prompt | self.llm_service.model #| parser
        er =  self._extract_kg_from_doc(document.text, chain, parser)
        return (er["nodes"], er["rels"])
        
    
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
            self.conn.upsertVertex("DocumentChunk", chunk_id, attributes={"embedding": chunk.chunk_embedding, "date_added": date_added, "content": chunk.text})
            self.conn.upsertEdge("Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id)
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
                self.conn.upsertEdge("DocumentCollection", doc_collection, "DOCUMENT_IN_COLLECTION", "Document", doc_id)
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
        super().__init__(embedding_service=embedding_service, llm_service=llm_service, conn=conn, stauts=status)

    def _ingest(self, documents: List[Document], chunker, chunker_params):
        self.chunk_documents(documents, chunker, chunker_params)
        self.status.progress.num_chunks_in_doc = {doc.document_id: len(doc.document_chunks) for doc in documents}
        for doc in documents:
            self.embed_document(doc)
            doc.entities, doc.relationships = self.document_er_extraction(doc)
            if doc.document_chunks:
                for chunk in doc.document_chunks:
                    chunk.chunk_embedding = self.embedding_service.embed_query(chunk.text)
                    chunk.entities, chunk.relationships = self.document_er_extraction(chunk)
                    self.upsert_chunk(chunk)
            self.upsert_document(doc)
            self.status.progress.num_docs_ingested += 1
        self.status.status = "complete"
        return self.status.to_dict()

    def ingest_s3(self, doc_source: S3BatchDocumentIngest):
        import boto3
        s3 = boto3.client('s3', aws_access_key_id = doc_source.service_params["aws_access_key_id"],
                                aws_secret_access_key = doc_source.service_params["aws_secret_access_key"])
        # get the list of documents
        documents = []
        if doc_source.service_params["type"].lower() == "file":
            response = s3.get_object(Bucket=doc_source.service_params["bucket"], Key=doc_source.service_params["key"])
            doc = Document(document_id=doc_source.service_params["key"], document_text=response['Body'].read().decode('utf-8', errors="replace"))
            documents = [doc]
        elif doc_source.service_params["type"].lower() == "directory":
            response = s3.list_objects_v2(Bucket=doc_source.service_params["bucket"], Prefix=doc_source.service_params["key"])
            for obj in response.get('Contents', []):
                response = s3.get_object(Bucket=doc_source.service_params["bucket"], Key=obj['Key'])
                doc = Document(document_id=obj['Key'], text=response['Body'].read().decode('utf-8', errors="replace"), document_collection=doc_source.service_params["bucket"]+"_"+doc_source.service_params["key"])
                documents.append(doc)
        else:
            raise ValueError(f"Type {doc_source.service_params['type']} not supported")
        self.status.progress = IngestionProgress(num_docs=len(documents))
        return self._ingest(documents, doc_source.chunker, doc_source.chunker_params)