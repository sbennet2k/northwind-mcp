import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from northwind_mcp.server import execute_sql
from northwind_mcp.models.schema import SQLResult

@pytest.mark.unit
def test_execute_sql_success(mock_db: MagicMock):
    """Verify that execute_sql returns a valid SQLResult for a SELECT query."""
    
    # Setup Mock Data on the fixture-provided cursor
    mock_db.description = [("IDCol",), ("NameCol",)]
    mock_db.fetchall.return_value = [(1, "Name1"), (2, "Name2")]

    # Execute query
    query = "SELECT * FROM DummyTable WHERE IDCol = :id"
    params = {"id": 1}
    result = execute_sql(query=query, params=params, ctx=None)

    assert isinstance(result, SQLResult)
    assert result.columns == ["IDCol", "NameCol"]
    assert len(result.rows) == 2
    assert result.rows[0][1] == "Name1"

    # Verify the cursor was called correctly with params
    mock_db.execute.assert_called_once_with(query, params)

@pytest.mark.unit
def test_execute_sql_security_violation():
    """Verify that non-SELECT queries raise a ValueError."""
    
    # Use pytest.raises to verify the guardrail triggers correctly
    with pytest.raises(ValueError, match="Security Violation"):
        execute_sql(query="DROP TABLE Products", params={}, ctx=None)

@pytest.mark.unit
def test_execute_sql_database_error(mocker: MockerFixture, mock_db: MagicMock):
    """Verify execute_sql logs and re-raises exceptions during SQL execution."""

    # Setup Mock Cursor to raise an error
    mock_db.execute.side_effect = Exception("no such table: non_existent")

    # Patch the logger in the server module
    mock_logger = mocker.patch("northwind_mcp.server.logger")
    
    # Tool should re-raise the exception
    with pytest.raises(Exception, match="no such table"):
        execute_sql(
            query="SELECT * FROM non_existent", 
            params={}, 
            ctx=None
        )

    # Ensure the logger captured the error message
    mock_logger.exception.assert_called_once_with("SQL Execution Error")
