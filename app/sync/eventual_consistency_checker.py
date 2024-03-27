import asyncio
import logging
from app.embeddings.embedding_services import EmbeddingModel
from app.embeddings.milvus_embedding_store import MilvusEmbeddingStore
from pyTigerGraph import TigerGraphConnection

class EventualConsistencyChecker:
    def __init__(self, interval_seconds, graphname, vertex_field, embedding_service: EmbeddingModel, embedding_store: MilvusEmbeddingStore, conn: TigerGraphConnection):
        self.graphname = graphname
        self.conn = conn
        self.is_initialized = False
        self.vertex_field = vertex_field
        self.embedding_service = embedding_service
        self.embedding_store = embedding_store
        asyncio.create_task(self.run_periodic_task(interval_seconds))

    async def fetch_and_process_vertex(self):
        vertex_ids_content_map = self.conn.runInstalledQuery("Scan_For_Updates")
        vertex_ids_content_map = {1 : "Doc1", 2: "Doc2", 3: "Doc3"}

        if isinstance(vertex_ids_content_map, list):
            vertex_ids_content_map = vertex_ids_content_map[0]

        vertex_ids = [int(vertex_id) for vertex_id in vertex_ids_content_map.keys()]
        logging.info(f"Remove existing entries from Milvus with vertex_ids in {str(vertex_ids)}")
        self.embedding_store.remove_embeddings(expr=f"{self.vertex_field} in {str(vertex_ids)}")

        for vertex_id, content in vertex_ids_content_map.items():
            vec = self.embedding_service.embed_query(content)
            self.embedding_store.add_embeddings([(content, vec)], [{self.vertex_field: vertex_id}])

        logging.info(f"Updating the TigerGraph vertex ids to confirm that processing was completed")
        self.conn.runInstalledQuery("Update_Vertices_Processing_Status", {"vertex_ids": str(vertex_ids)})

    async def run_periodic_task(self, interval_seconds: int):
        while True:
            await asyncio.sleep(interval_seconds)
            await self.fetch_and_process_vertex()