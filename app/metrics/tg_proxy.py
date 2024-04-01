import time
from pyTigerGraph import TigerGraphConnection
from app.metrics.prometheus_metrics import metrics

class TigerGraphConnectionProxy:
    def __init__(self, tg_connection: TigerGraphConnection):
        self._tg_connection = tg_connection
        metrics.tg_active_connections.inc()

    def runInstalledQuery(self, query_name, params):
        start_time = time.time()
        try:
            with metrics.tg_inprogress_requests.labels(query_name):
                result = self._tg_connection.runInstalledQuery(query_name, params)
            success = True
        except Exception as e:
            success = False
            raise e
        finally:
            duration = time.time() - start_time
            metrics.tg_query_duration_seconds.labels(query_name).observe(duration)
            metrics.tg_query_count.labels(query_name).inc()
            if not success:
                metrics.tg_query_error_total.labels(query_name, "error_type").inc()
            else:
                metrics.tg_query_success_total.labels(query_name).inc()
        return result

    def __del__(self):
        metrics.tg_active_connections.dec()