from typing import Any

import pytest
from mcp.client.session import ClientSession

from northwind_mcp.models.schema import DBSchema, SQLResult, TableColumn


@pytest.mark.anyio
@pytest.mark.integration
async def test_mcp_handshake_and_tools(mcp_session: ClientSession):
    """Verify the live MCP server is reachable and lists the correct tools."""

    result = await mcp_session.list_tools()
    tool_names = [t.name for t in result.tools]

    assert "get_db_schema" in tool_names
    assert "execute_sql" in tool_names
    assert "validate_query" in tool_names


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_get_db_schema(mcp_session: ClientSession):
    """Verify get_db_schema returns real Northwind schema info from the live DB."""

    # Call the tool
    result = await mcp_session.call_tool("get_db_schema", arguments={})
    assert not result.isError

    schema = DBSchema.model_validate(result.structuredContent)

    assert schema is not None
    assert "Customers" in schema.root
    assert "Products" in schema.root

    for table_name in schema.root.keys():
        table_columns = schema.root[table_name]

        for col in table_columns:
            assert isinstance(col, TableColumn)
            assert col.name is not None
            assert isinstance(col.pk, bool)


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_execute_sql_real_data(mcp_session: ClientSession):
    """Verify execute_sql successfully queries the real Northwind database."""

    # Test a real query
    arguments: dict[str, Any] = {
        "query": "SELECT ProductName FROM Products WHERE ProductID = :productId",
        "params": {"productId": 51},
    }

    result = await mcp_session.call_tool("execute_sql", arguments=arguments)

    # Check for success
    assert not result.isError
    assert result.structuredContent is not None

    raw_data = result.structuredContent
    query_results = SQLResult.model_validate(raw_data)

    assert "ProductName" in query_results.columns  # Column name
    assert "Manjimup Dried Apples" in query_results.rows[0]  # Column name


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_success(mcp_session: ClientSession):
    """Validate SQL query against the real Northwind database."""

    # Test a real query
    arguments: dict[str, Any] = {
        "query": "SELECT ProductName FROM Products WHERE ProductID = :productId",
        "params": {"productId": 51},
    }

    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    # Check for success
    assert not result.isError
    assert result.structuredContent is not None

    data = result.structuredContent

    assert data["valid"] is True
    assert data["errors"] == []
    assert isinstance(data["warnings"], list)


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_ping_tool(mcp_session: ClientSession):
    """
    Verify the ping tool is registered and returns a valid health status
    from the running Northwind MCP server.
    """
    result = await mcp_session.call_tool("ping", arguments={})

    # Check for success
    assert not result.isError
    assert result.structuredContent is not None

    data = result.structuredContent

    assert data["status"] == "ok"
    assert data["version"] is not None
    assert data["database"] == "healthy"
    assert data["timestamp"] is not None
    assert data["service"] == "NorthwindMCP"
