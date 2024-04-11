import json
import logging
import time
import uuid
from base64 import b64decode
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware

from app import routers
from app.config import PATH_PREFIX, PRODUCTION
from app.log import req_id_cv
from app.metrics.prometheus_metrics import metrics as pmetrics
from app.tools.logwriter import LogWriter


if PRODUCTION:
    app = FastAPI(title="TigerGraph CoPilot", docs_url=None, redoc_url=None, openapi_url=None)
else:
    app = FastAPI(title="TigerGraph CoPilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.root_router, prefix=PATH_PREFIX)
app.include_router(routers.inquiryai_router, prefix=PATH_PREFIX)
app.include_router(routers.supportai_router, prefix=PATH_PREFIX)


excluded_metrics_paths = ("/docs", "/openapi.json", "/metrics")

logger = logging.getLogger(__name__)


async def get_basic_auth_credentials(request: Request):
    auth_header = request.headers.get("Authorization")

    if auth_header is None:
        return ""

    try:
        auth_type, encoded_credentials = auth_header.split(" ", 1)
    except ValueError:
        return ""

    if auth_type.lower() != "basic":
        return ""

    try:
        decoded_credentials = b64decode(encoded_credentials).decode("utf-8")
        username, _ = decoded_credentials.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return username


# FIXME: this middle ware causes the API to hang if it raises an error
# @app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    LogWriter.info(f"{request.url.path} ENTRY request_id={req_id}")
    req_id_cv.set(req_id)
    start_time = time.time()
    response = await call_next(request)

    user_name = await get_basic_auth_credentials(request)
    client_host = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    action_name = request.url.path
    status = "SUCCESS"

    response = await call_next(request)
    if response.status_code != 200:
        status = "FAILURE"

    # set up the audit log entry structure and write it with the LogWriter
    if not any(request.url.path.endswith(path) for path in excluded_metrics_paths):
        audit_log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "userName": user_name,
            "clientHost": f"{client_host}:{request.url.port}",
            "userAgent": user_agent,
            "endpoint": request.url.path,
            "actionName": action_name,
            "status": status,
            "requestId": req_id,
        }
        LogWriter.audit_log(json.dumps(audit_log_entry), mask_pii=False)
        update_metrics(start_time=start_time, label=request.url.path)

    return response


def update_metrics(start_time, label):
    duration = time.time() - start_time
    pmetrics.copilot_endpoint_duration_seconds.labels(label).observe(duration)
    pmetrics.copilot_endpoint_total.labels(label).inc()
