from prometheus_client import Gauge, Histogram, Counter


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class PrometheusMetrics(metaclass=SingletonMeta):
    def __init__(self):
        if not hasattr(self, "initialized"):
            # collect metrics for TigerGraph
            self.tg_active_connections = Gauge(
                "tg_active_connections", "Number of active connections to TigerGraph"
            )
            self.tg_inprogress_requests = Gauge(
                "tg_inprogress_requests",
                "Number of TG requests in progress",
                ["query_name"],
            )
            self.tg_query_duration_seconds = Histogram(
                "tg_query_duration_seconds",
                "Duration of TigerGraph queries",
                ["query_name"],
            )
            self.tg_query_count = Counter(
                "tg_query_total", "Number of TigerGraph queries called", ["query_name"]
            )
            self.tg_query_error_total = Counter(
                "tg_query_error_total",
                "Number of TigerGraph query errors",
                ["query_name", "error_type"],
            )
            self.tg_query_success_total = Counter(
                "tg_query_success_total",
                "Number of TigerGraph query successes",
                ["query_name"],
            )

            # collect metrics for LLMs
            self.llm_inprogress_requests = Gauge(
                "llm_inprogress_requests",
                "Number of LLM requests in progress",
                ["llm_model"],
            )
            self.llm_request_duration_seconds = Histogram(
                "llm_request_duration_seconds",
                "Duration of LLM requests",
                ["llm_model"],
            )
            self.llm_request_total = Counter(
                "llm_request_total",
                "Number of times a request to an LLM model is made",
                ["llm_model"],
            )
            self.llm_success_response_total = Counter(
                "llm_success_response_total",
                "Number of LLM responses that yielded a useful result",
                ["llm_model"],
            )
            self.llm_bad_response_total = Counter(
                "llm_bad_response_total",
                "Number of LLM responses that yielded a useless result",
                ["llm_model"],
            )
            self.llm_query_error_total = Counter(
                "llm_query_error_total",
                "Number of LLM responses that yielded an error result",
                ["llm_model"],
            )

            # collect metrics for Milvus
            self.milvus_active_connections = Gauge(
                "milvus_active_connections",
                "Number of active connections to Milvus",
                ["collection_name"],
            )
            self.milvus_query_duration_seconds = Histogram(
                "milvus_query_duration_seconds",
                "Duration of Milvus queries",
                ["collection_name", "method_name"],
            )
            self.milvus_query_total = Counter(
                "milvus_query_total",
                "Number of Milvus queries called",
                ["collection_name", "method_name"],
            )

            # collect metrics for CoPilot
            self.copilot_endpoint_duration_seconds = Histogram(
                "copilot_endpoint_duration_seconds",
                "Duration of the CoPilot endpoint execution",
                ["endpoint"],
            )
            self.copilot_endpoint_total = Counter(
                "copilot_endpoint_total",
                "Number of times the CoPilot endpoint is called",
                ["endpoint"],
            )

            self.initialized = True


metrics = PrometheusMetrics()
