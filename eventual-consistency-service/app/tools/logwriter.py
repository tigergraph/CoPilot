import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler

from app.log import audit_formatter, formatter, get_log_config, log_file_paths

log_config = get_log_config()


class CorrectingLogger(logging.Logger):
    def findCaller(self, stack_info=False, stacklevel=1):
        """
        Override findCaller to look further back in the stack.
        This adjusts stacklevel to find the correct caller outside of LogWriter.
        """
        f = logging.currentframe()
        if f is not None:
            f = f.f_back
        orig_f = f
        while f and stacklevel > 0:
            f = f.f_back
            stacklevel -= 1
        if not f:
            f = orig_f
        rv = "(unknown file)", 0, "(unknown function)", None
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename == logging._srcfile or filename == os.path.normcase(__file__):
                f = f.f_back
                continue
            sinfo = None
            if stack_info:
                sinfo = self.find_stack_info(f)
            rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
            break
        return rv


class LogWriter:
    logger_initialized = False
    general_logger: logging.Logger = None
    error_logger: logging.Logger = None
    warning_logger: logging.Logger = None
    audit_logger: logging.Logger = None

    pii_patterns = [
        (
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "[EMAIL REDACTED]",
        ),
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN REDACTED]"),
        (re.compile(r"\b(?<!-)(?:\d{4}[ -]?){3}\d{4}(?!-)\b"), "[CREDIT CARD REDACTED]"),
        (re.compile(r"\b(?:\d{3}-)?\d{3}-\d{4}\b"), "[PHONE REDACTED]"),
        (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IPV4 REDACTED]"),
        (
            re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
            "[IPV6 REDACTED]",
        ),
        (re.compile(r"\bUser\d+\b"), "[USER ID REDACTED]"),
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
        max_size = log_config.get("log_max_size", 100 * 1024 * 1024)
        backup_count = log_config.get("log_max_size", 100)

        logger = logging.setLoggerClass(CorrectingLogger)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        handler = RotatingFileHandler(
            file_name, maxBytes=max_size, backupCount=backup_count
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    @staticmethod
    def initialize_logger():
        if not LogWriter.logger_initialized:
            # Set log directory, dependending on configuration
            log_directory = log_config.get("log_file_path", "/tmp/logs")
            os.makedirs(log_directory, exist_ok=True)

            # Logging for info, error and audit
            LogWriter.general_logger = LogWriter.setup_logger(
                "info", log_file_paths["info"][0], logging.INFO, formatter
            )

            LogWriter.warning_logger = LogWriter.setup_logger(
                "warning", log_file_paths["warning"][0], logging.WARNING, formatter
            )

            LogWriter.error_logger = LogWriter.setup_logger(
                "error", log_file_paths["error"][0], logging.ERROR, formatter
            )

            LogWriter.audit_logger = LogWriter.setup_logger(
                "audit",
                log_file_paths["audit"][0],
                logging.INFO,
                audit_formatter,
            )

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
            extra_info = " | " + " ".join(
                f"{key}={value}" for key, value in kwargs.items()
            )
            message += extra_info

        # getattr(LogWriter.general_logger, level.lower())(message)
        if level.upper() == "ERROR":
            LogWriter.error_logger.error(message)
        elif level.upper() == "WARNING":
            LogWriter.warning_logger.warning(message)
        elif level.upper() == "INFO":
            LogWriter.general_logger.info(message)

    @staticmethod
    def info(message, mask_pii=True, **kwargs):
        LogWriter.log("info", message, mask_pii, **kwargs)

    @staticmethod
    def warn(message, mask_pii=True, **kwargs):
        LogWriter.log("warning", message, mask_pii, **kwargs)

    @staticmethod
    def warning(message, mask_pii=True, **kwargs):
        LogWriter.log("warning", message, mask_pii, **kwargs)

    @staticmethod
    def error(message, mask_pii=True, **kwargs):
        LogWriter.log("error", message, mask_pii, **kwargs)

    @staticmethod
    def audit_log(message: dict, mask_pii=True):
        LogWriter.initialize_logger()

        if mask_pii:
            masked_message = {
                k: LogWriter.mask_pii(v) if isinstance(v, str) else v
                for k, v in message.items()
            }
        else:
            masked_message = message

        LogWriter.audit_logger.info(json.dumps(masked_message))
