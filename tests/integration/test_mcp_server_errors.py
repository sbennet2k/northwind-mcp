from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_execute_sql_security_block(mcp_session: ClientSession):
    """Verify that a destructive SQL command returns a protocol-level error."""

    # Attempt a forbidden DROP TABLE
    result = await mcp_session.call_tool(
        "execute_sql", arguments={"query": "DROP TABLE Customers", "params": {}}
    )

    # FastMCP should return isError=True, not raise a Python exception in the client
    assert result.isError is True
    assert "Security Violation" in result.content[0].text  # type: ignore


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_execute_sql_invalid_syntax(mcp_session: ClientSession):
    """Verify that malformed SQL returns a descriptive database error."""

    result = await mcp_session.call_tool(
        "execute_sql",
        arguments={"query": "SELECT * FROM NonExistentTable", "params": {}},
    )

    assert result.isError is True
    assert "no such table" in result.content[0].text.lower()  # type: ignore


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_execute_sql_missing_params(mcp_session: ClientSession):
    """Verify that missing required arguments return a validation error."""

    # Intentionally omit 'params'
    result = await mcp_session.call_tool("execute_sql", arguments={"query": "SELECT 1"})

    assert result.isError is True
    assert "validation error" in result.content[0].text.lower()  # type: ignore


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_server_connection_refused():
    """Verify the client handles a completely offline server."""

    # Use a port that definitely isn't running
    BAD_URL = "http://localhost:9999/mcp"

    with pytest.raises(Exception):
        async with streamable_http_client(BAD_URL) as (read, write):  # type: ignore
            pass


@pytest.mark.anyio
@pytest.mark.integration
async def test_validate_empty_query_fails_parse(mcp_session: ClientSession):
    """Verify that an empty or whitespace-only query fails the initial parse check."""

    # Empty string or just whitespace typically returns an empty list in sqlparse
    arguments: dict[str, Any] = {"query": "   ", "params": {}}

    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    # The tool should return valid: False and the specific parse error
    assert data["valid"] is False
    assert "Unable to parse SQL query" in data["errors"][0]


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_non_select_query(mcp_session: ClientSession):
    """Verify the 'SELECT only' guardrail triggers for UPDATE/DELETE."""

    arguments: dict[str, Any] = {
        "query": "UPDATE Customers SET ContactName = 'Hacker' WHERE CustomerID = 'ALFKI'",
        "params": {},
    }
    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    assert data["valid"] is False
    assert "Only SELECT queries are allowed" in data["errors"][0]


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_blacklist_keywords(mcp_session: ClientSession):
    """Verify the keyword blacklist catches dangerous commands inside strings."""
    # Even if hidden or concatenated, sqlparse flatten() should catch these

    arguments: dict[str, Any] = {
        "query": "SELECT * FROM (DROP TABLE Products)",
        "params": {},
    }
    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    assert data["valid"] is False
    assert "forbidden keyword" in data["errors"][0]


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_missing_parameters(mcp_session: ClientSession):
    """Verify error when named parameters (:) are used but params dict is empty."""

    arguments: dict[str, Any] = {
        "query": "SELECT * FROM Orders WHERE OrderID = :oid",
        "params": {},
    }
    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    assert data["valid"] is False
    assert "no params were provided" in data["errors"][0]


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_non_existent_table(mcp_session: ClientSession):
    """Verify the tool cross-references against the actual DB schema."""

    arguments: dict[str, Any] = {"query": "SELECT * FROM ImaginaryTable", "params": {}}
    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    assert data["valid"] is False
    assert "Table does not exist" in data["errors"][0]


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_syntax_error(mcp_session: ClientSession):
    """Verify SQLite EXPLAIN catches a syntax error via the tool."""

    arguments: dict[str, Any] = {
        "query": "SELECT * FORM Customers",  # Typos 'FORM'
        "params": {},
    }

    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    assert data["valid"] is False
    assert "SQL syntax/schema error" in data["errors"][0]


@pytest.mark.anyio
@pytest.mark.integration
async def test_integration_validate_sql_multiple_warnings(mcp_session: ClientSession):
    """Verify query with multiple JOINs and 'SELECT *' triggers warning."""

    complex_query = """
        SELECT *
        FROM CustomerCustomerDemo a
        JOIN CustomerDemographics b ON a.CustomerTypeID = b.CustomerTypeID
        JOIN Customers c ON a.CustomerID = c.CustomerID
        JOIN Orders d ON c.CustomerID = d.CustomerID
        JOIN 'Order Details' e ON d.OrderID = e.OrderID
    """

    arguments: dict[str, Any] = {"query": complex_query, "params": {}}

    result = await mcp_session.call_tool("validate_query", arguments=arguments)

    assert result.structuredContent is not None
    data = result.structuredContent

    assert data["valid"] is True
    assert data["errors"] == []
    assert "Query contains multiple JOINs" in data["warnings"][0]
    assert "Query uses SELECT *" in data["warnings"][1]
