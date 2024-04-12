import time
from pyTigerGraph import TigerGraphConnection
from app.metrics.prometheus_metrics import metrics
from app.tools.logwriter import LogWriter
import logging
from app.log import req_id_cv


logger = logging.getLogger(__name__)

class TigerGraphConnectionProxy:
    def __init__(self, tg_connection: TigerGraphConnection):
        self._tg_connection = tg_connection
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

    def _runInstalledQuery(self, query_name, params):
        start_time = time.time()
        metrics.tg_inprogress_requests.labels(query_name=query_name).inc()
        try:
            restppid = self._tg_connection.runInstalledQuery(query_name, params, runAsync=True)
            LogWriter.info(f"request_id={req_id_cv.get()} query {query_name} started with RESTPP ID {restppid}")
            result = None
            while not result:
                if self._tg_connection.checkQueryStatus(restppid)[0]["status"].lower() == "success":
                    LogWriter.info(f"request_id={req_id_cv.get()} query {query_name} completed successfully with RESTPP ID {restppid}")
                    result = self._tg_connection.getQueryResult(restppid)
                elif self._tg_connection.checkQueryStatus(restppid)[0]["status"].lower() == "aborted":
                    LogWriter.error(f"request_id={req_id_cv.get()} query {query_name} with RESTPP ID {restppid} aborted")
                    raise Exception(f"Query {query_name} with restppid {restppid} aborted")
                elif self._tg_connection.checkQueryStatus(restppid)[0]["status"].lower() == "timeout":
                    LogWriter.error(f"request_id={req_id_cv.get()} query {query_name} with restppid {restppid} timed out")
                    raise Exception(f"Query {query_name} with restppid {restppid} timed out")
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
        metrics.tg_active_connections.dec()
