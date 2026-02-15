"""
Main entry point for the Northwind MCP Server.

Initializes the FastMCP server, configures global logging,
and provides a Uvicorn-based runner.

Usage:
    python -m northwind_mcp.main
    OR
    uvicorn northwind_mcp.main:app --host 127.0.0.0 --port 9001
"""

import logging
import os

from northwind_mcp.logging_config import setup_logging
from northwind_mcp.server import mcp_server

# FastMCP exposes an ASGI app
app = mcp_server.streamable_http_app()

setup_logging()  # Setting up the logging config once
logger = logging.getLogger(__name__)

HOST = os.getenv("MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_PORT", 9001))

if __name__ == "__main__":
    import uvicorn

    logger.debug("About to run uvicorn command...")

    uvicorn.run(
        "northwind_mcp.main:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )
