import logging
import time
from typing import Dict, List

import ecc_util
from common.logs.logwriter import LogWriter
from common.embeddings.embedding_services import EmbeddingModel
from common.embeddings.base_embedding_store import EmbeddingStore
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.chunkers import BaseChunker
from common.extractors import BaseExtractor
from common.config import embedding_store_type

logger = logging.getLogger(__name__)


class EventualConsistencyChecker:
    def __init__(
        self,
        process_interval_seconds,
        cleanup_interval_seconds,
        graphname,
        vertex_field,
        embedding_service: EmbeddingModel,
        embedding_indices: List[str],
        embedding_stores: Dict[str, EmbeddingStore],
        conn: TigerGraphConnectionProxy,
        extractor: BaseExtractor,
        batch_size = 10,
        run_forever = True
    ):
        self.process_interval_seconds = process_interval_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.graphname = graphname
        self.conn = conn
        self.is_initialized = False
        self.vertex_field = vertex_field
        self.embedding_service = embedding_service
        self.embedding_indices = embedding_indices
        self.embedding_stores = embedding_stores
        self.extractor = extractor
        self.batch_size = batch_size
        self.run_forever = run_forever

        self._check_query_install("Scan_For_Updates")
        self._check_query_install("Update_Vertices_Processing_Status")
        self._check_query_install("ECC_Status")
        self._check_query_install("Check_Nonexistent_Vertices")

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

        if "error" in str(res).lower():
            LogWriter.error(res)
            raise Exception(f"Eventual consistency checker failed to install query {query_name}")

        return res

    def _check_query_install(self, query_name):
        LogWriter.info(f"Checking if query {query_name} is installed")
        endpoints = self.conn.getEndpoints(
            dynamic=True
        )  # installed queries in database
        installed_queries = [q.split("/")[-1] for q in endpoints if f"/{conn.graphname}/" in q]

        if query_name not in installed_queries:
            return self._install_query(query_name)
        else:
            return True

    def _chunk_document(self, content):
        chunker = ecc_util.get_chunker(content["ctype"])
        return chunker.chunk(content["text"])

    def _extract_entities(self, content):
        return self.extractor.extract(content["text"])

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
            start_time = time.time()
            LogWriter.info(f"Fetching {self.batch_size} vertex ids and content for vertex type: {v_type}")

            vertex_ids_content_map = self._fetch_unprocessed_vertices(v_type)
            vertex_ids = [vertex_id for vertex_id in vertex_ids_content_map.keys()]

            if vertex_ids:
                self._remove_existing_entries(v_type, vertex_ids)
                self._process_content(v_type, vertex_ids_content_map)
                self._update_processing_status(v_type, vertex_ids)
                self._log_elapsed_time(start_time, v_type)
            else:
                LogWriter.error(f"No changes detected for vertex type: {v_type}")

        return len(vertex_ids_content_map) != 0

    def _fetch_unprocessed_vertices(self, v_type):
        return self.conn.runInstalledQuery(
            "Scan_For_Updates", {"v_type": v_type, "num_samples": self.batch_size}
        )[0]["@@v_and_text"]

    def _remove_existing_entries(self, v_type, vertex_ids):
        if embedding_store_type == "tigergraph":
            vector_index = "tigergraph"
        else:
            vector_index = self.graphname + "_" + v_type
        LogWriter.info(f"Remove existing entries with vertex_ids in {str(vertex_ids)}")
        self.embedding_stores[vector_index].remove_embeddings(
            expr=f"{self.vertex_field} in {str(vertex_ids)}"
        )

    def _process_content(self, v_type, vertex_ids_content_map):
        if embedding_store_type == "tigergraph":
            vector_index = "tigergraph"
        else:
            vector_index = self.graphname + "_" + v_type
        LogWriter.info(f"Embedding content from vertex type: {v_type}")
        for vertex_id, content in vertex_ids_content_map.items():
            if content:
                vec = self.embedding_service.embed_query(content["text"])
                self.embedding_stores[vector_index].add_embeddings(
                    [(text, vec)], [{self.vertex_field: vertex_id}]
                )

            if v_type == "Document":
                self._process_document_content(v_type, vertex_id, content)
            
            if v_type in ["Document", "DocumentChunk"]:
                self._extract_and_upsert_entities(v_type, vertex_id, content)

    def _process_document_content(self, v_type, vertex_id, content):
        LogWriter.info(f"Chunking the content from vertex type: {v_type}")
        chunks = self._chunk_document(content)
        for i, chunk in enumerate(chunks):
            self._upsert_chunk(vertex_id, f"{vertex_id}_chunk_{i}", chunk)

    def _extract_and_upsert_entities(self, v_type, vertex_id, content):
        LogWriter.info(f"Extracting and upserting entities from the content from vertex type: {v_type}")
        extracted = self._extract_entities(content)
        if extracted["nodes"]:
            self._upsert_entities(vertex_id, v_type, extracted["nodes"])
        if extracted["rels"]:
            self._upsert_rels(vertex_id, v_type, extracted["rels"])

    def _update_processing_status(self, v_type, vertex_ids):
        LogWriter.info(f"Updating the TigerGraph vertex ids for type {v_type} to confirm that processing was completed")
        processed_vertices = [{"id": vertex_id, "type": v_type} for vertex_id in vertex_ids]
        self.conn.runInstalledQuery(
            "Update_Vertices_Processing_Status",
            {"processed_vertices": processed_vertices},
            usePost=True
        )

    def _log_elapsed_time(self, start_time, v_type):
        end_time = time.time()
        elapsed_time = end_time - start_time
        LogWriter.info(f"Time elapsed for processing vertex_ids for type {v_type}: {elapsed_time:.2f} seconds")


    def verify_and_cleanup_embeddings(self, batch_size=10):
        if embedding_store_type == "tigergraph":
            vector_index = "tigergraph"
        else:
            vector_index = self.graphname + "_" + v_type
        for v_type in self.embedding_indices:
            LogWriter.info(f"Running cleanup for vertex type {v_type}")

            query_result = self.embedding_stores[vector_index].query("pk > 0", [self.vertex_field, 'pk'])
            if not query_result:
                LogWriter.info(f"No vertices to process for vertex type {v_type}")
                continue

            vertex_id_map, duplicates_to_remove = self._identify_duplicates(query_result)
            self._remove_duplicates(v_type, duplicates_to_remove)

            unique_vertex_ids = list(vertex_id_map.keys())
            self._process_vertex_batches(v_type, unique_vertex_ids, batch_size)

            LogWriter.info(f"Finished cleanup for vertex type {v_type}")

    def _identify_duplicates(self, query_result):
        vertex_id_map = {}
        duplicates_to_remove = []

        for item in query_result:
            vertex_id = item.get(self.vertex_field)
            pk = item.get('pk')
            if vertex_id not in vertex_id_map:
                vertex_id_map[vertex_id] = pk
            else:
                duplicates_to_remove.append(pk)
                LogWriter.info(f"Duplicate vertex id found with pk {pk} and will be removed")

        return vertex_id_map, duplicates_to_remove

    def _remove_duplicates(self, v_type, duplicates_to_remove):
        if embedding_store_type == "tigergraph":
            vector_index = "tigergraph"
        else:
            vector_index = self.graphname + "_" + v_type
        for pk in duplicates_to_remove:
            self.embedding_stores[vector_index].remove_embeddings(
                expr=f"pk == {pk}"
            )
            LogWriter.info(f"Removed duplicate with pk {pk} from Milvus")

    def _process_vertex_batches(self, v_type, unique_vertex_ids, batch_size):
        for i in range(0, len(unique_vertex_ids), batch_size):
            batch_vertex_ids = unique_vertex_ids[i:i + batch_size]

            non_existent_vertices = self.conn.runInstalledQuery(
                "Check_Nonexistent_Vertices",
                {"v_type": v_type, "vertex_ids": batch_vertex_ids}
            )[0]["@@missing_vertices"]

            if non_existent_vertices:
                self._cleanup_nonexistent_vertices(v_type, non_existent_vertices)
            else:
                LogWriter.info(f"No cleanup needed for current batch of vertex type {v_type}")

    def _cleanup_nonexistent_vertices(self, v_type, non_existent_vertices):
        if embedding_store_type == "tigergraph":
            vector_index = "tigergraph"
        else:
            vector_index = self.graphname + "_" + v_type
        for vertex_id in non_existent_vertices:
            self.embedding_stores[vector_index].remove_embeddings(
                expr=f"{self.vertex_field} == '{vertex_id}'"
            )

    def initialize(self):
        LogWriter.info(
            f"Eventual Consistency Check running for graphname {self.graphname} "
        )
        self.is_initialized = True
        while True:
            worked = self.fetch_and_process_vertex()

            if not self.run_forever:
                break
            elif not worked:
                LogWriter.info(
                    f"Eventual Consistency Check waiting to process for graphname {self.graphname} for {self.process_interval_seconds} seconds"
                )
                time.sleep(self.process_interval_seconds)

            
    def initialize_cleanup(self):
        LogWriter.info(
            f"Eventual Consistency Check running cleanup for graphname {self.graphname} "
        )
        self.is_initialized = True
        while True:
            self.verify_and_cleanup_embeddings()

            if not self.run_forever:
                break
            else:
                LogWriter.info(
                    f"Eventual Consistency Check waiting to cleanup for graphname {self.graphname} for {self.cleanup_interval_seconds} seconds"
                )
                time.sleep(self.cleanup_interval_seconds)

    def get_status(self):
        statuses = {}
        for v_type in self.embedding_indices:
            status = self.conn.runInstalledQuery(
                "ECC_Status", {"v_type": v_type}
            )[0]
            LogWriter.info(f"ECC_Status for graphname {self.graphname}: {status}")
            statuses[v_type] = status
        return statuses
