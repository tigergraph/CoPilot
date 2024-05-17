import json
import logging
import time
import uuid
from base64 import b64decode
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.security import HTTPBasicCredentials
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import routers
from common.config import PATH_PREFIX, PRODUCTION
from common.logs.log import req_id_cv
from common.metrics.prometheus_metrics import metrics as pmetrics
from common.logs.logwriter import LogWriter
from common.db.connections import get_db_connection_pwd, get_db_connection_id_token

if PRODUCTION:
    app = FastAPI(
        title="TigerGraph CoPilot", docs_url=None, redoc_url=None, openapi_url=None
    )
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


@app.middleware("http")
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


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    graphname = request.url.components.path.split("/")[1]
    if (
        graphname == ""
        or graphname == "docs"
        or graphname == "openapi.json"
        or graphname == "metrics"
        or graphname == "health"
    ):
        return await call_next(request)
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, credentials = authorization.split()
        if scheme.lower() == "basic":
            LogWriter.info("Authenticating with basic auth")
            username, password = b64decode(credentials).decode().split(":", 1)
            credentials = HTTPBasicCredentials(username=username, password=password)
            try:
                conn = get_db_connection_pwd(graphname, credentials)
            except HTTPException as e:
                LogWriter.error("Failed to connect to TigerGraph. Incorrect username or password.")
                return JSONResponse(status_code=401,
                                    content={"message": "Failed to connect to TigerGraph. Incorrect username or password."})
        else:
            LogWriter.info("Authenticating with id token")
            try:
                conn = get_db_connection_id_token(graphname, credentials)
            except HTTPException as e:
                LogWriter.error("Failed to connect to TigerGraph. Incorrect ID Token.")
                return JSONResponse(status_code=401,
                                    content={"message": "Failed to connect to TigerGraph. Incorrect ID Token."})
        request.state.conn = conn
    response = await call_next(request)
    return response


def update_metrics(start_time, label):
    duration = time.time() - start_time
    pmetrics.copilot_endpoint_duration_seconds.labels(label).observe(duration)
    pmetrics.copilot_endpoint_total.labels(label).inc()
