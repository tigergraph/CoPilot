import time
import re
from pyTigerGraph import TigerGraphConnection
from app.metrics.prometheus_metrics import metrics

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
                if name == "_req":
                    return self._req(*args, **kwargs)
                else:
                    return original_attr(*args, **kwargs)

            return hooked
        else:
            return original_attr

    def _req(self, method: str, url: str, authMode: str, *args, **kwargs):
        # we always use token auth 
        # always use proxy endpoint in GUI for restpp and gsql
        url = re.sub(r'/gsqlserver/', '/api/gsql-server/', url)
        url = re.sub(r'/restpp/', '/api/restpp/', url)
        return self._tg_connection._req(method, url, "token", *args, **kwargs)

    def _runInstalledQuery(self, query_name, params):
        start_time = time.time()
        metrics.tg_inprogress_requests.labels(query_name=query_name).inc()
        try:
            result = self._tg_connection.runInstalledQuery(query_name, params)
            success = True
        except Exception as e:
            success = False
            raise e
        finally:
            metrics.tg_inprogress_requests.labels(query_name=query_name).dec()
            duration = time.time() - start_time
            metrics.tg_query_duration_seconds.labels(query_name=query_name).observe(duration)
            metrics.tg_query_count.labels(query_name=query_name).inc()
            if not success:
                metrics.tg_query_error_total.labels(query_name=query_name, error_type="error").inc()
            else:
                metrics.tg_query_success_total.labels(query_name=query_name).inc()
        return result

    def __del__(self):
        metrics.tg_active_connections.dec()