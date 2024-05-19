import contextvars
import json
import logging
import os
from datetime import datetime
from typing import Any


class UTCFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        utc_datetime = datetime.utcfromtimestamp(record.created)
        return utc_datetime.strftime("%m%d %H:%M:%S%f,")


def get_log_config() -> dict[str, Any]:
    LOG_CONFIG = os.getenv("LOG_CONFIG", "configs/log_config.json")

    if LOG_CONFIG is None or (
        LOG_CONFIG.endswith(".json") and not os.path.exists(LOG_CONFIG)
    ):
        log_config = {
            "log_file_path": "/tmp/logs",
            "log_max_size": 104857600,
            "log_backup_count": 0,
        }
    elif LOG_CONFIG.endswith(".json"):
        with open(LOG_CONFIG) as f:
            log_config = json.load(f)
    else:
        try:
            log_config = json.loads(str(LOG_CONFIG))
        except json.JSONDecodeError as e:
            raise Exception(
                "LOG_CONFIG must be a .json file or a JSON string, failed with error: "
                + str(e)
            )

    return log_config


def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


addLoggingLevel("DEBUG_PII", logging.DEBUG - 5)
log_config = get_log_config()
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()

log_directory = log_config.get("log_file_path", "/tmp/logs")
os.makedirs(log_directory, exist_ok=True)
# log file handlers
log_file_paths = {
    "info": (log_directory + "/log.INFO", logging.INFO),
    "debug": (log_directory + "/log.DEBUG", logging.DEBUG),
    "debug_pii": (log_directory + "/log.DEBUG", logging.DEBUG_PII),
    "warning": (log_directory + "/log.WARNING", logging.WARNING),
    "error": (log_directory + "/log.ERROR", logging.ERROR),
    "audit": (log_directory + "/log.AUDIT-COPILOT", logging.INFO),
}
formatter = UTCFormatter(
    "[%(levelname).1s%(asctime)s %(process)d %(filename)s:%(lineno)d] %(message)s"
)
audit_formatter = UTCFormatter("%(message)s")
handlers = []
# set logging level for handlers
for p in log_file_paths.values():
    h = logging.FileHandler(p[0])
    h.setLevel(p[1])
    h.setFormatter(formatter)
    handlers.append(h)


logging.basicConfig(level=LOGLEVEL, handlers=handlers)


req_id_cv = contextvars.ContextVar("req_id", default=None)
