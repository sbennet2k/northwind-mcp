import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from northwind_mcp.server import validate_query
from northwind_mcp.models.schema import DBSchema
from northwind_mcp.utils.utils import extract_tables

@pytest.mark.unit
def test_extract_tables_regex():
    """Verify regex correctly extracts tables from FROM and JOIN clauses."""

    query = "SELECT * FROM Orders JOIN Customers ON Orders.ID = Customers.ID"
    tables = extract_tables(query)
    assert set(t.lower() for t in tables) == {"orders", "customers"}

@pytest.mark.unit
def test_validate_query_parse_check():
    """Verify that an empty/whitespace-only query fails initial parse check."""

    # Empty string or whitespace typically returns an empty list in sqlparse
    query = "   "
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is False
    assert "Unable to parse SQL query" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_select_guardrail():
    """Verify the 'SELECT only' guardrail triggers."""

    query = "DROP TABLE Products"
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is False
    assert "Only SELECT queries are allowed" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_blacklist():
    """Verify the keyword blacklist catches dangerous commands ."""

    query = "SELECT * FROM (DROP TABLE Products)"
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is False
    assert "forbidden keyword" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_missing_params():
    """Verify error when query has placeholders but no params provided."""

    query = "SELECT * FROM Products WHERE id = :id"
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is False
    assert "no params were provided" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_table_not_found(
    mocker: MockerFixture, mock_schema: DBSchema
):
    """Verify error when a table is used that isn't in the schema."""

    mocker.patch(
        "northwind_mcp.server.get_db_schema", return_value=mock_schema
    )
    mocker.patch(
        "northwind_mcp.server.extract_tables", return_value=["UnknownTable"]
    )

    query = "SELECT * FROM UnknownTable"
    result = validate_query(query, {}, ctx=None)
    
    assert result["valid"] is False
    assert "Table does not exist: unknowntable" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_syntax_error(
    mocker: MockerFixture, mock_db: MagicMock, mock_schema: DBSchema
):
    """Verify SQLite EXPLAIN catches a syntax error."""

    # Update the mock schema to include 'form' as a valid table 
    # so the tool passes the "Table Existence" check.
    mock_schema.root["form"] = []

    # Set expected error
    mock_db.execute.side_effect = Exception("near 'FORM': syntax error")
    mocker.patch(
        "northwind_mcp.server.get_db_schema", return_value=mock_schema
    )
    mocker.patch(
        "northwind_mcp.server.extract_tables", return_value=["FORM"]
    )
    
    result = validate_query("SELECT * FORM Customers", {}, ctx=None)
    
    assert result["valid"] is False
    assert "SQL syntax/schema error" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_warnings(
    mocker: MockerFixture, mock_db: MagicMock, mock_schema: DBSchema
):
    """Verify that multiple JOINs and SELECT * trigger warnings."""
    
    # Mock all dependencies to return success
    mocker.patch(
        "northwind_mcp.server.get_db_schema", 
        return_value=mock_schema
    )
    mocker.patch(
        "northwind_mcp.server.extract_tables", 
        return_value=["users", "orders", "items", "products", "suppliers"]
    )
    
    # query with 4 JOINs and a '*'
    query = """
        SELECT * FROM users 
        JOIN orders ON users.id = orders.user_id 
        JOIN items ON orders.id = items.order_id 
        JOIN products ON items.prod_id = products.id
        JOIN suppliers ON products.supp_id = suppliers.id
    """
    
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is True
    mock_db.execute.assert_called()
    assert len(result["warnings"]) == 2
    assert "Query contains multiple JOINs" in result["warnings"][0]
    assert "Query uses SELECT *" in result["warnings"][1]

@pytest.mark.unit
def test_validate_query_unexpected_error(mocker: MockerFixture):
    """Verify the catch-all exception block handles unexpected logic failures."""
    
    # Force get_db_schema to blow up with a weird error
    mocker.patch(
        "northwind_mcp.server.get_db_schema", 
        side_effect=RuntimeError("Database file is corrupted or missing")
    )

    query = "SELECT * FROM Products"
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is False
    assert "Unexpected error during validation" in result["errors"][0]

@pytest.mark.unit
def test_validate_query_success(
    mocker: MockerFixture, mock_db: MagicMock, mock_schema: DBSchema
):
    """Verify that a standard, valid SELECT query passes validation."""

    mocker.patch(
        "northwind_mcp.server.get_db_schema", return_value=mock_schema
    )
    mocker.patch(
        "northwind_mcp.server.extract_tables", 
        return_value=["Products", "Categories"]
    )

    # Define a valid query (No '*' and only 1 JOIN to avoid warnings)
    query = """
    SELECT p.ProductName FROM Products p 
    JOIN Categories c ON p.CategoryID = c.CategoryID
    """
    result = validate_query(query, {}, ctx=None)

    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 0
    mock_db.execute.assert_called_once_with(f"EXPLAIN {query}", {})
