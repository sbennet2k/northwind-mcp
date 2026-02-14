"""
Logging configuration for the Northwind MCP Server.

Sets up structured logging to stderr to prevent interference with
the MCP JSON-RPC protocol on stdout.
"""

import os
import sys
import logging.config
from typing import Any


log_level = os.getenv("LOG_LEVEL", "INFO").upper()


LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s.%(msecs)03d | "
                "%(levelname)-8s | "
                "%(name)-26s:%(lineno)-4d | "
                "%(funcName)-16s | "
                "%(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stderr,  # Must be stderr for MCP
        }
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["stderr"],
            "level": log_level,
        },
        "uvicorn.error": {
            "level": "INFO",
        },
        "uvicorn.access": {
            "level": "WARNING",
        },
    },
}


def setup_logging():
    """
    Applies the predefined logging configuration to the logging system.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
