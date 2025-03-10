import logging
import traceback
import json
from time import sleep, time
from collections import defaultdict
from typing import Iterable, List, Optional, Tuple

import Levenshtein as lev
from asyncer import asyncify
from langchain_core.documents.base import Document

from common.embeddings.base_embedding_store import EmbeddingStore
from common.embeddings.embedding_services import EmbeddingModel
from common.logs.log import req_id_cv
from common.logs.logwriter import LogWriter
from common.metrics.prometheus_metrics import metrics

from pyTigerGraph import TigerGraphConnection

logger = logging.getLogger(__name__)


class TigerGraphEmbeddingStore(EmbeddingStore):
    def __init__(
        self,
        conn: TigerGraphConnection,
        embedding_service: EmbeddingModel,
        support_ai_instance: bool = False
    ):
        self.embedding_service = embedding_service
        self.support_ai_instance = support_ai_instance
        self.conn = TigerGraphConnection(
                host=conn.host,
                username=conn.username,
                password=conn.password,
                graphname=conn.graphname,
                restppPort=conn.restppPort,
                gsPort=conn.gsPort,
            )

        tg_version = self.conn.getVer()
        ver = tg_version.split(".")
        if int(ver[0]) >= 4 and int(ver[1]) >= 2:
            vector_queries = [
                "check_embedding_exists",
                "get_topk_similar",
                "get_topk_closest",
            ]
           
            logger.info(f"Installing GDS library")
            q_res = self.conn.gsql(
                """USE GLOBAL\nimport package gds\ninstall function gds.**"""
            )
            logger.info(f"Done installing GDS library with status {q_res}")

            installed_queries = [q.split("/")[-1] for q in self.conn.getEndpoints(dynamic=True) if f"{self.conn.graphname}/" in q]
            for q_name in vector_queries:
                if q_name not in installed_queries:
                    with open(f"common/gsql/vector/{q_name}.gsql", "r") as f:
                        q_body = f.read()
                    q_res = self.conn.gsql(
                        """USE GRAPH {}\n{}\ninstall query {}""".format(
                            self.conn.graphname, q_body, q_name
                        )
                    )
                    logger.info(f"Done installing vector query {q_name} with status {q_res}")
        else:
            raise Exception(f"Current TigerGraph version {ver} does not support vector feature!")

    def map_attrs(self, attributes: Iterable[Tuple[str, List[float]]]):
        # map attrs
        attrs = {}
        for (k, v) in attributes:
            attrs[k] = {"value": v}
        return attrs

    def add_embeddings(
        self,
        embeddings: Iterable[Tuple[Tuple[str, str], List[float]]],
        metadatas: List[dict] = None,
    ):
        """Add Embeddings.
        Add embeddings to the Embedding store.
        Args:
            embeddings (Iterable[Tuple[str, List[float]]]):
                Iterable of content and embedding of the document.
        """
        try:
            LogWriter.info(
                f"request_id={req_id_cv.get()} TigerGraph ENTRY add_embeddings()"
            )

            start_time = time()
            batch = {
                "vertices": defaultdict(dict[str, any]),
            }

            for i, (_, embedding) in enumerate(embeddings):
                (v_id, v_type) = metadatas[i].get("vertex_id")
                attr = self.map_attrs([("embedding", embedding)])
                batch["vertices"][v_type][v_id] = attr
            data = json.dumps(batch)
            added = self.conn.upsertData(data)

            duration = time() - start_time

            LogWriter.info(f"request_id={req_id_cv.get()} TigerGraph EXIT add_embeddings()")

            # Check if registration was successful
            if added:
                success_message = f"Document registered with id: {added[0]}"
                LogWriter.info(success_message)
                return success_message
            else:
                error_message = f"Failed to register document {added}"
                LogWriter.error(error_message)
                raise Exception(error_message)

        except Exception as e:
            error_message = f"An error occurred while registering document: {str(e)}"
            LogWriter.error(error_message)

    async def aadd_embeddings(
        self,
        embeddings: Iterable[Tuple[str, List[float]]],
        metadatas: List[dict] = None,
    ):
        """Add Embeddings.
        Add embeddings to the Embedding store.
        Args:
            embeddings (Iterable[Tuple[str, List[float]]]):
                Iterable of content and embedding of the document.
        """
        try:
            LogWriter.info(
                f"request_id={req_id_cv.get()} TigerGraph ENTRY aadd_embeddings()"
            )

            start_time = time()
            batch = {
                "vertices": defaultdict(dict[str, any]),
            }

            for i, (_, embedding) in enumerate(embeddings):
                (v_id, v_type) = metadatas[i].get("vertex_id")
                attr = self.map_attrs([("embedding", embedding)])
                batch["vertices"][v_type][v_id] = attr
            data = json.dumps(batch)
            added = self.conn.upsertData(data)

            duration = time() - start_time

            LogWriter.info(f"request_id={req_id_cv.get()} TigerGraph EXIT aadd_embeddings()")

            # Check if registration was successful
            if added:
                success_message = f"Document {metadatas} registered with status: {added}"
                LogWriter.info(success_message)
                return success_message
            else:
                error_message = f"Failed to register document {metadatas} with status {added}"
                LogWriter.error(error_message)
                raise Exception(error_message)

        except Exception as e:
            error_message = f"An error occurred while registering document: {str(e)}"
            LogWriter.error(error_message)

    def has_embeddings(
        self,
        v_ids: Iterable[Tuple[str, str]]
    ):
        ret = True
        try:
            for (v_id, v_type) in v_ids:
                res = self.conn.runInstalledQuery(
                    "check_embedding_exists",
                    params={
                        "vertex_type": v_type,
                        "vertex_id": v_id,
                    }
                )
                logger.info(f"Return result {res} for has_embeddings({v_ids})")
                ret = ret and ("result" in res and len(res["result"]) > 0)
        except Exception as e:
            logger.info(f"Exception {str(e)} when running has_embeddings({v_type}, {v_id}), return False")
            ret = False
        return ret

    def remove_embeddings(
        self, ids: Optional[List[str]] = None, expr: Optional[str] = None
    ):
        #TBD
        return

    def retrieve_similar(self, query_embedding, top_k=10, filter_expr: str = None):
        """Retireve Similar.
        Retrieve similar embeddings from the vector store given a query embedding.
        Args:
            query_embedding (List[float]):
                The embedding to search with.
            top_k (int, optional):
                The number of documents to return. Defaults to 10.
        Returns:
            https://api.python.langchain.com/en/latest/documents/langchain_core.documents.base.Document.html#langchain_core.documents.base.Document
            Document results for search.
        """
        try:
            LogWriter.info(
                f"request_id={req_id_cv.get()} Milvus ENTRY similarity_search_by_vector()"
            )

            start_time = time()
            end_time = time()
            return similar
        except Exception as e:
            error_message = f"An error occurred while retrieving docuements: {str(e)}"
            LogWriter.error(error_message)
            raise e

    def add_connection_parameters(self, query_params: dict) -> dict:
        """Add Connection Parameters.
        Add connection parameters to the query parameters.
        Args:
            query_params (dict):
                Dictionary containing the parameters for the GSQL query.
        Returns:
            A dictionary containing the connection parameters.
        """
        # Nothing needed for TG
        return query_params

    async def aget_k_closest(
        self, vertex: Tuple[str, str], k=10, threshold_similarity=0.90, edit_dist_threshold_pct=0.75
    ) -> list[Document]:
        threshold_dist = 1 - threshold_similarity

        logger.info(f"Fetch {k} closest entries for {vertex} with threshold {threshold_similarity}")
        # Get all vectors with this ID
        (v_id, v_type) = vertex
        verts = self.conn.runInstalledQuery(
            "get_topk_closest",
            params={
                "vertex_id": v_id,
                "vertex_id.type": v_type,
                "k": k,
                "threshold": threshold_similarity,
            }
        )
        logger.info(f"Got k closest entries for {vertex}: {verts}")
        result = []
        for r in verts:
            if "result" in r:
                for v in r.result:
                    result.append(v.v_id)
        logger.info(f"Returning {result}")
        return set(result)

    def check_embedding_rebuilt(
        self,
    ):
        

    def query(self, expr: str, output_fields: List[str]):
        """Get output fields with expression

        Args:
            expr: Expression - E.g: "pk > 0"

        Returns:
            List of output fields' contents
        """

        return []

    def __del__(self):
        logger.info("TigerGraphEmbeddingStore destructed.")
