import time
import re
from pyTigerGraph import TigerGraphConnection
from app.metrics.prometheus_metrics import metrics
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv


logger = logging.getLogger(__name__)


class TigerGraphConnectionProxy:
    def __init__(self, tg_connection: TigerGraphConnection, auth_mode: str = "pwd"):
        self.original_req = tg_connection._req
        tg_connection._req = self._req
        self._tg_connection = tg_connection
        self.auth_mode = auth_mode
        metrics.tg_active_connections.inc()

    def __getattr__(self, name):
        original_attr = getattr(self._tg_connection, name)

        if callable(original_attr):

            def hooked(*args, **kwargs):
                if name == "runInstalledQuery":
                    return self._runInstalledQuery(*args, **kwargs)
                else:
                    return original_attr(*args, **kwargs)

            return hooked
        else:
            return original_attr

    def _req(self, method: str, url: str, authMode: str, *args, **kwargs):
        # we always use token auth
        # always use proxy endpoint in GUI for restpp and gsql
        if self.auth_mode == "pwd":
            return self.original_req(method, url, authMode, *args, **kwargs)
        else:
            url = re.sub(r"/gsqlserver/", "/api/gsql-server/", url)
            url = re.sub(r"/restpp/", "/api/restpp/", url)
            return self.original_req(method, url, "token", *args, **kwargs)

    def _runInstalledQuery(self, query_name, params, usePost=False):
        start_time = time.time()
        metrics.tg_inprogress_requests.labels(query_name=query_name).inc()
        try:
            restppid = self._tg_connection.runInstalledQuery(
                query_name, params, runAsync=True, usePost=usePost
            )
            LogWriter.info(
                f"request_id={req_id_cv.get()} query {query_name} started with RESTPP ID {restppid}"
            )
            result = None
            while not result:
                if (
                    self._tg_connection.checkQueryStatus(restppid)[0]["status"].lower()
                    == "success"
                ):
                    LogWriter.info(
                        f"request_id={req_id_cv.get()} query {query_name} completed successfully with RESTPP ID {restppid}"
                    )
                    result = self._tg_connection.getQueryResult(restppid)
                elif (
                    self._tg_connection.checkQueryStatus(restppid)[0]["status"].lower()
                    == "aborted"
                ):
                    LogWriter.error(
                        f"request_id={req_id_cv.get()} query {query_name} with RESTPP ID {restppid} aborted"
                    )
                    raise Exception(
                        f"Query {query_name} with restppid {restppid} aborted"
                    )
                elif (
                    self._tg_connection.checkQueryStatus(restppid)[0]["status"].lower()
                    == "timeout"
                ):
                    LogWriter.error(
                        f"request_id={req_id_cv.get()} query {query_name} with restppid {restppid} timed out"
                    )
                    raise Exception(
                        f"Query {query_name} with restppid {restppid} timed out"
                    )
                time.sleep(0.1)
            success = True
        except Exception as e:
            LogWriter.error(f"Error running query {query_name}: {str(e)}")
            success = False
            raise e
        finally:
            metrics.tg_inprogress_requests.labels(query_name=query_name).dec()
            duration = time.time() - start_time
            metrics.tg_query_duration_seconds.labels(query_name=query_name).observe(
                duration
            )
            metrics.tg_query_count.labels(query_name=query_name).inc()
            if not success:
                metrics.tg_query_error_total.labels(
                    query_name=query_name, error_type="error"
                ).inc()
            else:
                metrics.tg_query_success_total.labels(query_name=query_name).inc()
        return result

    def __del__(self):
        if self.auth_mode == "pwd":
            resp = self._tg_connection._delete(
                self._tg_connection.restppUrl + "/requesttoken",
                authMode="pwd",
                data=str({"token": self._tg_connection.apiToken}),
                resKey=None
            )
        metrics.tg_active_connections.dec()
