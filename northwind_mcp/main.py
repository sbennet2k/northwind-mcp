"""
Main entry point for the Northwind MCP Server.

Initializes the FastMCP server via Server-Sent Events (SSE),
configures global logging, and provides a Uvicorn-based runner.

Usage:
    python -m northwind_mcp.main
    OR
    uvicorn northwind_mcp.main:app --host 0.0.0.0 --port 9001
"""

from northwind_mcp.server import mcp_server
from northwind_mcp.logging_config import setup_logging
import logging

# FastMCP exposes an ASGI app
app = mcp_server.sse_app()

setup_logging()  # Setting up the logging config once
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn

    logger.debug("About to run uvicorn command...")

    uvicorn.run(
        "northwind_mcp.main:app",
        host="0.0.0.0",
        port=9001,
        log_level="info",
    )
