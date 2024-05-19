import time


class IngestionProgress:
    def __init__(self, num_docs, num_docs_ingested=0):
        self.num_docs = num_docs
        self.num_docs_ingested = num_docs_ingested
        self.num_chunks_in_doc = {}
        self.chunk_failures = {}
        self.doc_failures = {}

    def to_dict(self):
        return {
            "num_docs": self.num_docs,
            "num_docs_ingested": self.num_docs_ingested,
            "num_chunks_in_doc": self.num_chunks_in_doc,
            "chunk_failures": self.chunk_failures,
            "doc_failures": self.doc_failures,
        }


class Status:
    def __init__(
        self,
        status_id,
        user_id,
        graphname,
        progress_tracker=None,
        expiration=24 * 60 * 60,
    ):
        self.status_id = status_id
        self.user_id = user_id
        self.graphname = graphname
        self.progress = progress_tracker
        self.expiration = time.time() + expiration
        self.status = "in_progress"

    def to_dict(self):
        return {
            "status_id": self.status_id,
            "user_id": self.user_id,
            "graphname": self.graphname,
            "progress": self.progress.to_dict() if self.progress else None,
        }


class StatusManager:
    def __init__(self):
        self.statuses = {}

    def create_status(self, user_id, req_id, graphname, progress_tracker=None):
        status_id = req_id
        status = Status(status_id, user_id, graphname, progress_tracker)
        self.statuses[status_id] = status
        return status_id

    def get_status(self, status_id):
        return self.statuses.get(status_id)

    def delete_status(self, status_id):
        if status_id in self.statuses:
            del self.statuses[status_id]

    def clean_statuses(self):
        for status_id, status in self.statuses.items():
            if status.expiration < time.time():
                del self.statuses[status_id]
