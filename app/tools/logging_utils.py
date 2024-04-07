import logging
import os
import json
from logging.handlers import RotatingFileHandler
import re

LOG_CONFIG = os.getenv("LOG_CONFIG")

if LOG_CONFIG is None or (LOG_CONFIG.endswith(".json") and not os.path.exists(LOG_CONFIG)):
    log_config =  {
        "log_file_path": "logs",
        "log_max_size": 104857600,
        "log_backup_count": 100
    }
elif LOG_CONFIG.endswith(".json"):
    with open(LOG_CONFIG, "r") as f:
        log_config = json.load(f)
else:
    try:
        log_config = json.loads(str(LOG_CONFIG))
    except json.JSONDecodeError as e:
        raise Exception("LOG_CONFIG must be a .json file or a JSON string, failed with error: " + str(e))

class LogWriter:
    logger_initialized = False
    general_logger: logging.Logger = None
    error_logger: logging.Logger = None
    audit_logger: logging.Logger = None

    pii_patterns = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL REDACTED]'),
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN REDACTED]'),
        (re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b'), '[CREDIT CARD REDACTED]'),
        (re.compile(r'\b(?:\d{3}-)?\d{3}-\d{4}\b'), '[PHONE REDACTED]'),
        (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), '[IPV4 REDACTED]'),
        (re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'), '[IPV6 REDACTED]'),
        (re.compile(r'\bUser\d+\b'), '[USER ID REDACTED]'),
    ]

    @staticmethod
    def mask_pii(message):
        """Mask PII data in the message based on predefined patterns."""
        for pattern, mask in LogWriter.pii_patterns:
            message = pattern.sub(mask, message)
        return message

    @staticmethod
    def setup_logger(name, file_name, level, formatter):
        """Generalized logger setup."""
        # Set log configuration defaults
        max_size = log_config.get("log_max_size", 100*1024*1024)
        backup_count = log_config.get("log_max_size", 100)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        handler = RotatingFileHandler(file_name, maxBytes=max_size, backupCount=backup_count)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    @staticmethod
    def initialize_logger():
        if not LogWriter.logger_initialized:
            # Set log directory, dependending on configuration
            log_directory = os.path.dirname(log_config["log_file_path"], "logs")            
            os.makedirs(log_directory, exist_ok=True)

            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # Logging for info, error and audit
            LogWriter.general_logger = LogWriter.setup_logger(
                "general", "logs/log.INFO", logging.DEBUG, formatter)

            LogWriter.error_logger = LogWriter.setup_logger(
                "error", "logs/log.ERROR", logging.ERROR, formatter)

            LogWriter.audit_logger = LogWriter.setup_logger(
                "audit", "log.AUDIT-COPILOT", logging.INFO, formatter)

            # logging for log.out
            stdout_handler = logging.StreamHandler()
            stdout_handler.setLevel(logging.DEBUG)
            stdout_handler.setFormatter(formatter)
            logging.getLogger().addHandler(stdout_handler)

            LogWriter.logger_initialized = True

    @staticmethod
    def log(level, message, mask_pii=True, **kwargs):
        LogWriter.initialize_logger()
        
        if mask_pii:
            message = LogWriter.mask_pii(message)
        
        if kwargs:
            extra_info = ' | ' + ' '.join(f'{key}={value}' for key, value in kwargs.items())
            message += extra_info

        getattr(LogWriter.general_logger, level.lower())(message)
        if level.upper() == "ERROR":
            LogWriter.error_logger.error(message)

    @staticmethod
    def audit_log(message: dict, mask_pii=True):
        LogWriter.initialize_logger()

        if mask_pii:
            masked_message = {k: LogWriter.mask_pii(v) if isinstance(v, str) else v for k, v in message.items()}
        else:
            masked_message = message

        LogWriter.audit_logger.info(json.dumps(masked_message))
