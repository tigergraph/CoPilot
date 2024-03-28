import asyncio
import logging
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.supportai.chunkers import BaseChunker
from app.supportai.extractors import BaseExtractor
from pyTigerGraph import TigerGraphConnection
import time

logger = logging.getLogger(__name__)

class EventualConsistencyChecker:
    def __init__(self, interval_seconds, graphname, vertex_field,
                 embedding_service: EmbeddingModel, embedding_store: MilvusEmbeddingStore,
                 conn: TigerGraphConnection, chunker: BaseChunker, extractor: BaseExtractor):
        self.interval_seconds = interval_seconds
        self.graphname = graphname
        self.conn = conn
        self.is_initialized = False
        self.vertex_field = vertex_field
        self.embedding_service = embedding_service
        self.embedding_store = embedding_store
        self.chunker = chunker
        self.extractor = extractor

        self._check_query_install("Scan_For_Updates")
        self._check_query_install("Update_Vertices_Processing_Status")
        
    def _install_query(self, query_name):
        logger.info(f"Installing query {query_name}")
        with open(f"app/gsql/supportai/{query_name}.gsql", "r") as f:
            query = f.read()
        res = self.conn.gsql("USE GRAPH "+self.conn.graphname+"\n"+query+"\n INSTALL QUERY "+query_name)
        return res


    def _check_query_install(self, query_name):
        logger.info(f"Checking if query {query_name} is installed")
        endpoints = self.conn.getEndpoints(dynamic=True) # installed queries in database
        installed_queries = [q.split("/")[-1] for q in endpoints]

        if query_name not in installed_queries:
            return self._install_query(query_name)
        else:
            return True
        
    def _chunk_document(self, content):
        return self.chunker.chunk(content)
    
    def _extract_entities(self, content):
        return self.extractor.extract(content)
    
    # TODO: Change to loading job for all chunks in document at once
    def _upsert_chunk(self, doc_id, chunk_id, chunk):
        date_added = int(time.time())
        self.conn.upsertVertex("DocumentChunk", chunk_id, attributes={"epoch_added": date_added, "idx": int(chunk_id.split("_")[-1])})
        self.conn.upsertVertex("Content", chunk_id, attributes={"text": chunk, "epoch_added": date_added})
        self.conn.upsertEdge("DocumentChunk", chunk_id, "HAS_CONTENT", "Content", chunk_id)
        self.conn.upsertEdge("Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id)
        if int(chunk_id.split("_")[-1]) > 0:
            self.conn.upsertEdge("DocumentChunk", chunk_id, "IS_AFTER", "DocumentChunk", doc_id+"_chunk_"+str(int(chunk_id.split("_")[-1])-1))
    
    # TODO: Change to loading job for all entities in document at once
    def _upsert_entities(self, src_id, src_type, entities):
        date_added = int(time.time())
        self.conn.upsertVertices("Entity", [(x["id"], {"definition": x["definition"], "epoch_added": date_added, "embedding": self.embedding_service.embed_query(x["definition"])}) for x in entities])
        self.conn.upsertVertices("Concept", [(x["type"], {"description": "", "concept_type": "EntityType", "epoch_added": date_added, "embedding": []}) for x in entities])
        self.conn.upsertEdges("Concept", "DESCRIBES_ENTITY", "Entity", [(x["type"], x["id"], {}) for x in entities])
        self.conn.upsertEdges(src_type, "CONTAINS_ENTITY", "Entity", [(src_id, x["id"], {}) for x in entities])

    # TODO: Change to loading job for all relationships in document at once
    def _upsert_rels(self, src_id, src_type, relationships):
        date_added = int(time.time())
        self.conn.upsertVertices("Relationship", [(x["source"]+":"+x["type"]+":"+x["target"], {"definition": x["definition"], "short_name": x["type"], "epoch_added": date_added, "embedding": self.embedding_service.embed_query(x["definition"])}) for x in relationships])
        self.conn.upsertEdges("Entity", "IS_HEAD_OF", "Relationship", [(x["source"], x["source"]+":"+x["type"]+":"+x["target"], {}) for x in relationships])
        self.conn.upsertEdges("Relationship", "HAS_TAIL", "Entity", [(x["source"]+":"+x["type"]+":"+x["target"], x["target"], {}) for x in relationships])
        self.conn.upsertEdges(src_type, "MENTIONS_RELATIONSHIP", "Relationship", [(src_id, x["source"]+":"+x["type"]+":"+x["target"], {}) for x in relationships])

    async def fetch_and_process_vertex(self):
        v_types_to_scan = ["Document"]
        for v_type in v_types_to_scan:
            if v_type == "Document":
                vertex_ids_content_map = self.conn.runInstalledQuery("Scan_For_Updates")[0]["@@v_and_text"]

                vertex_ids = [vertex_id for vertex_id in vertex_ids_content_map.keys()]
                logger.info(f"Remove existing entries from Milvus with vertex_ids in {str(vertex_ids)}")
                self.embedding_store.remove_embeddings(expr=f"{self.vertex_field} in {str(vertex_ids)}")

                for vertex_id, content in vertex_ids_content_map.items():
                    vec = self.embedding_service.embed_query(content)
                    self.embedding_store.add_embeddings([(content, vec)], [{self.vertex_field: vertex_id}])

                logger.info(f"Chunking the content")
                for vertex_id, content in vertex_ids_content_map.items():
                    chunks = self._chunk_document(content)
                    for i, chunk in enumerate(chunks):
                        self._upsert_chunk(vertex_id, f"{vertex_id}_chunk_{i}", chunk)
                    

                logger.info(f"Extracting and upserting entities from the content")
                for vertex_id, content in vertex_ids_content_map.items():
                    extracted = self._extract_entities(content)
                    self._upsert_entities(vertex_id, "Document", extracted["nodes"])
                    self._upsert_rels(vertex_id, "Document", extracted["rels"])

                logger.info(f"Updating the TigerGraph vertex ids to confirm that processing was completed")
                if vertex_ids:
                    vertex_ids = [(vertex_id, "Document") for vertex_id in vertex_ids]
                    self.conn.runInstalledQuery("Update_Vertices_Processing_Status", {"processed_vertices": vertex_ids})
            else:
                logger.error(f"Unsupported vertex type {v_type}")

    async def run_periodic_task(self):
        while True:
            await self.fetch_and_process_vertex()
            await asyncio.sleep(self.interval_seconds)

    async def initialize(self):
        if not self.is_initialized:
            logger.info(f"Eventual Consistency Check initializing for graphname {self.graphname} with interval_seconds {self.interval_seconds}")
            asyncio.create_task(self.run_periodic_task())
            self.is_initialized = True