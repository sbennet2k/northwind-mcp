import pytest
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from pytest_mock import MockerFixture
from northwind_mcp.models.schema import DBSchema, TableColumn


MCP_URL = "http://localhost:9001/sse"

@pytest.fixture
async def mcp_session():
    """
    Fixture to provide an initialized MCP ClientSession over SSE.
    Automatically handles setup and teardown.
    """
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
            # Session and SSE client close automatically here when the test finishes

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
