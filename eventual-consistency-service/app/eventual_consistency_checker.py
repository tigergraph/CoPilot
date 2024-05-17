import logging
import time
from typing import List

from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)


class EventualConsistencyChecker:
    def __init__(
        self,
        interval_seconds,
        graphname,
        vertex_field,
        embedding_service,
        embedding_indices: List[str],
        embedding_stores,
        conn,
        chunker,
        extractor,
        batch_size = 10
    ):
        self.interval_seconds = interval_seconds
        self.graphname = graphname
        self.conn = conn
        self.is_initialized = False
        self.vertex_field = vertex_field
        self.embedding_service = embedding_service
        self.embedding_indices = embedding_indices
        self.embedding_stores = embedding_stores
        self.chunker = chunker
        self.extractor = extractor
        self.batch_size = batch_size

        self._check_query_install("Scan_For_Updates")
        self._check_query_install("Update_Vertices_Processing_Status")
        self._check_query_install("ECC_Status")

    def _install_query(self, query_name):
        LogWriter.info(f"Installing query {query_name}")
        with open(f"common/gsql/supportai/{query_name}.gsql", "r") as f:
            query = f.read()
        res = self.conn.gsql(
            "USE GRAPH "
            + self.conn.graphname
            + "\n"
            + query
            + "\n INSTALL QUERY "
            + query_name
        )
        return res

    def _check_query_install(self, query_name):
        LogWriter.info(f"Checking if query {query_name} is installed")
        endpoints = self.conn.getEndpoints(
            dynamic=True
        )  # installed queries in database
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
        self.conn.upsertVertex(
            "DocumentChunk",
            chunk_id,
            attributes={"epoch_added": date_added, "idx": int(chunk_id.split("_")[-1])},
        )
        self.conn.upsertVertex(
            "Content", chunk_id, attributes={"text": chunk, "epoch_added": date_added}
        )
        self.conn.upsertEdge(
            "DocumentChunk", chunk_id, "HAS_CONTENT", "Content", chunk_id
        )
        self.conn.upsertEdge("Document", doc_id, "HAS_CHILD", "DocumentChunk", chunk_id)
        if int(chunk_id.split("_")[-1]) > 0:
            self.conn.upsertEdge(
                "DocumentChunk",
                chunk_id,
                "IS_AFTER",
                "DocumentChunk",
                doc_id + "_chunk_" + str(int(chunk_id.split("_")[-1]) - 1),
            )

    # TODO: Change to loading job for all entities in document at once
    def _upsert_entities(self, src_id, src_type, entities):
        date_added = int(time.time())
        self.conn.upsertVertices(
            "Entity",
            [
                (x["id"], {"definition": x["definition"], "epoch_added": date_added})
                for x in entities
            ],
        )
        self.conn.upsertVertices(
            "Concept",
            [
                (
                    x["type"],
                    {
                        "description": "",
                        "concept_type": "EntityType",
                        "epoch_added": date_added,
                    },
                )
                for x in entities
            ],
        )
        self.conn.upsertEdges(
            "Concept",
            "DESCRIBES_ENTITY",
            "Entity",
            [(x["type"], x["id"], {}) for x in entities],
        )
        self.conn.upsertEdges(
            src_type,
            "CONTAINS_ENTITY",
            "Entity",
            [(src_id, x["id"], {}) for x in entities],
        )

    # TODO: Change to loading job for all relationships in document at once
    def _upsert_rels(self, src_id, src_type, relationships):
        date_added = int(time.time())
        self.conn.upsertVertices(
            "Relationship",
            [
                (
                    x["source"] + ":" + x["type"] + ":" + x["target"],
                    {
                        "definition": x["definition"],
                        "short_name": x["type"],
                        "epoch_added": date_added,
                    },
                )
                for x in relationships
            ],
        )
        self.conn.upsertEdges(
            "Entity",
            "IS_HEAD_OF",
            "Relationship",
            [
                (x["source"], x["source"] + ":" + x["type"] + ":" + x["target"], {})
                for x in relationships
            ],
        )
        self.conn.upsertEdges(
            "Relationship",
            "HAS_TAIL",
            "Entity",
            [
                (x["source"] + ":" + x["type"] + ":" + x["target"], x["target"], {})
                for x in relationships
            ],
        )
        self.conn.upsertEdges(
            src_type,
            "MENTIONS_RELATIONSHIP",
            "Relationship",
            [
                (src_id, x["source"] + ":" + x["type"] + ":" + x["target"], {})
                for x in relationships
            ],
        )

    def fetch_and_process_vertex(self):
        v_types_to_scan = self.embedding_indices
        vertex_ids_content_map: dict = {}
        for v_type in v_types_to_scan:
            LogWriter.info(f"Fetching vertex ids and content for vertex type: {v_type}")
            vertex_ids_content_map = self.conn.runInstalledQuery(
                "Scan_For_Updates", {"v_type": v_type, "num_samples": self.batch_size}
            )[0]["@@v_and_text"]

            vertex_ids = [vertex_id for vertex_id in vertex_ids_content_map.keys()]
            LogWriter.info(
                f"Remove existing entries from Milvus with vertex_ids in {str(vertex_ids)}"
            )
            self.embedding_stores[self.graphname + "_" + v_type].remove_embeddings(
                expr=f"{self.vertex_field} in {str(vertex_ids)}"
            )

            LogWriter.info(f"Embedding content from vertex type: {v_type}")
            for vertex_id, content in vertex_ids_content_map.items():
                if content != "":
                    vec = self.embedding_service.embed_query(content)
                    self.embedding_stores[self.graphname + "_" + v_type].add_embeddings(
                        [(content, vec)], [{self.vertex_field: vertex_id}]
                    )

            if v_type == "Document":
                LogWriter.info(f"Chunking the content from vertex type: {v_type}")
                for vertex_id, content in vertex_ids_content_map.items():
                    chunks = self._chunk_document(content)
                    for i, chunk in enumerate(chunks):
                        self._upsert_chunk(vertex_id, f"{vertex_id}_chunk_{i}", chunk)

            if v_type == "Document" or v_type == "DocumentChunk":
                LogWriter.info(
                    f"Extracting and upserting entities from the content from vertex type: {v_type}"
                )
                for vertex_id, content in vertex_ids_content_map.items():
                    extracted = self._extract_entities(content)
                    if len(extracted["nodes"]) > 0:
                        self._upsert_entities(vertex_id, v_type, extracted["nodes"])
                    if len(extracted["rels"]) > 0:
                        self._upsert_rels(vertex_id, v_type, extracted["rels"])

            LogWriter.info(
                f"Updating the TigerGraph vertex ids to confirm that processing was completed"
            )
            if vertex_ids:
                vertex_ids = [{"id": vertex_id, "type": v_type} for vertex_id in vertex_ids]
                self.conn.runInstalledQuery(
                    "Update_Vertices_Processing_Status",
                    {"processed_vertices": vertex_ids},
                    usePost=True
                )
            else:
                LogWriter.error(f"No changes detected for vertex type: {v_type}")

        return len(vertex_ids_content_map) != 0

    def initialize(self):
        LogWriter.info(
            f"Eventual Consistency Check running for graphname {self.graphname} "
        )
        self.is_initialized = True
        ok = True
        while ok:
            ok = self.fetch_and_process_vertex()
        LogWriter.info(
            f"Eventual Consistency Check finished for graphname {self.graphname}. Success={ok}"
        )

    def get_status(self):
        statuses = {}
        for v_type in self.embedding_indices:
            status = self.conn.runInstalledQuery(
                "ECC_Status", {"v_type": v_type}
            )[0]["results"]
            statuses[v_type] = status
        return self.is_initialized