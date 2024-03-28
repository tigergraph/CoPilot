import asyncio
import logging
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from app.supportai.chunkers import BaseChunker
from app.supportai.extractors import BaseExtractor
from pyTigerGraph import TigerGraphConnection

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

    async def fetch_and_process_vertex(self):
        vertex_ids_content_map = self.conn.runInstalledQuery("Scan_For_Updates")[0]["@@v_and_text"]

        vertex_ids = [vertex_id for vertex_id in vertex_ids_content_map.keys()]
        logger.info(f"Remove existing entries from Milvus with vertex_ids in {str(vertex_ids)}")
        self.embedding_store.remove_embeddings(expr=f"{self.vertex_field} in {str(vertex_ids)}")

        for vertex_id, content in vertex_ids_content_map.items():
            vec = self.embedding_service.embed_query(content)
            self.embedding_store.add_embeddings([(content, vec)], [{self.vertex_field: vertex_id}])

        logger.info(f"Updating the TigerGraph vertex ids to confirm that processing was completed")
        if vertex_ids:
            vertex_ids = [(vertex_id, "Document") for vertex_id in vertex_ids]
            self.conn.runInstalledQuery("Update_Vertices_Processing_Status", {"processed_vertices": vertex_ids})

    async def run_periodic_task(self):
        while True:
            await self.fetch_and_process_vertex()
            await asyncio.sleep(self.interval_seconds)

    async def initialize(self):
        if not self.is_initialized:
            logger.info(f"Eventual Consistency Check initializing for graphname {self.graphname} with interval_seconds {self.interval_seconds}")
            asyncio.create_task(self.run_periodic_task())
            self.is_initialized = True