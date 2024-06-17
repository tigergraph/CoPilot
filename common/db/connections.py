import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials, HTTPAuthorizationCredentials
from pyTigerGraph import TigerGraphConnection
from pyTigerGraph.pyTigerGraphException import TigerGraphException
from requests import HTTPError

from common.config import (
    db_config,
    security,
)
from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.logs.logwriter import LogWriter

logger = logging.getLogger(__name__)
consistency_checkers = {}


def get_db_connection_id_token(
    graphname: str,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TigerGraphConnectionProxy:
    conn = TigerGraphConnection(
        host=db_config["hostname"],
        graphname=graphname,
        apiToken=credentials,
        tgCloud=True,
        sslPort=14240,
    )
    conn.customizeHeader(
        timeout=db_config["default_timeout"] * 1000, responseSize=5000000
    )
    conn = TigerGraphConnectionProxy(conn, auth_mode="id_token")

    try:
        conn.gsql("USE GRAPH " + graphname)
    except HTTPError:
        LogWriter.error("Failed to connect to TigerGraph. Incorrect ID Token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TigerGraphException as e:
        LogWriter.error(f"Failed to get token: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to get token - is the database running?"
        )

    LogWriter.info("Connected to TigerGraph with ID Token")
    return conn


def get_db_connection_pwd(
    graphname, credentials: Annotated[HTTPBasicCredentials, Depends(security)]
) -> TigerGraphConnectionProxy:
    conn = elevate_db_connection_to_token(db_config["hostname"], credentials.username, credentials.password, graphname)

    conn.customizeHeader(
        timeout=db_config["default_timeout"] * 1000, responseSize=5000000
    )
    conn = TigerGraphConnectionProxy(conn)
    LogWriter.info("Connected to TigerGraph with password")
    return conn



def get_db_connection_pwd_manual(
    graphname, username: str, password: str,
) -> TigerGraphConnectionProxy:
    """
    Manual auth - pass in user/pass not from basic auth
    """
    conn = elevate_db_connection_to_token(
            db_config["hostname"], username, password, graphname
        )

    conn.customizeHeader(
        timeout=db_config["default_timeout"] * 1000, responseSize=5000000
    )
    conn = TigerGraphConnectionProxy(conn)
    LogWriter.info("Connected to TigerGraph with password")
    return conn

def elevate_db_connection_to_token(host, username, password, graphname) -> TigerGraphConnectionProxy:
    conn = TigerGraphConnection(
        host=host,
        username=username,
        password=password,
        graphname=graphname
    )
    
    if db_config["getToken"]:
        try:
            apiToken = conn._post(
                conn.restppUrl + "/requesttoken",
                authMode="pwd",
                data=str({"graph": conn.graphname}),
                resKey="results",
            )["token"]
        except HTTPError:
            LogWriter.error("Failed to get token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        except TigerGraphException as e:
            LogWriter.error(f"Failed to get token: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to get token - is the database running?"
            )


        conn = TigerGraphConnection(
            host=db_config["hostname"],
            username=username,
            password=password,
            graphname=graphname,
            apiToken=apiToken
        )
    
    return conn
