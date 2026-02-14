import pytest
import os
import socket
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from pytest_mock import MockerFixture
from northwind_mcp.models.schema import DBSchema, TableColumn


TEST_HOST = os.getenv("TEST_HOST", "127.0.0.1")
TEST_PORT = int(os.getenv("TEST_PORT", 9001))

async def wait_for_port(host: str, port: int, timeout: int = 10):
    """Wait until a TCP port becomes available."""
    for _ in range(timeout):
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            await asyncio.sleep(1)
    raise RuntimeError("Server did not start in time")

@pytest.fixture(scope="session")
def anyio_backend():
    """Override the default anyio_backend to have session scope."""
    return "asyncio"

@pytest.fixture(scope="session")
async def mcp_server():
    """Start FastMCP server via uvicorn for integration tests."""

    process = await asyncio.create_subprocess_exec(
        "uvicorn",
        "northwind_mcp.main:app",
        "--host",
        TEST_HOST,
        "--port",
        str(TEST_PORT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await wait_for_port(TEST_HOST, TEST_PORT) # Ensure server is up
    yield
    process.terminate() # send terminate signal to child process
    await process.wait() # Ensure socket is closed, resources released

@pytest.fixture
async def mcp_session(mcp_server: None):
    """Provide initialized MCP ClientSession."""

    url = f"http://{TEST_HOST}:{TEST_PORT}/sse"

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

@pytest.fixture
def mock_schema():
    """Provides a standard Northwind-style schema for validation tests."""
    return DBSchema(root={
        "products": [TableColumn(name="ProductID", type="INT", notnull=True, pk=True)],
        "categories": [TableColumn(name="CategoryID", type="INT", notnull=True, pk=True)],
        "users": [], "orders": [], "items": [], "suppliers": []
    })

@pytest.fixture
def mock_db(mocker: MockerFixture):
    """Mocks the DB connection and cursor for EXPLAIN queries."""
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mocker.patch("northwind_mcp.server.get_db_connection", return_value=mock_conn)
    return mock_cursor # Returning the cursor makes assertions easier
