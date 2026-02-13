import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from northwind_mcp.server import get_db_schema
from northwind_mcp.models.schema import TableColumn, DBSchema

@pytest.mark.unit
def test_get_db_schema_mocked(mock_db: MagicMock):
    """Verify that get_db_schema returns a valid schema."""

    # Setup results the cursor should return
    mock_db.fetchall.side_effect = [
        [("DummyTable1",)],  # Tables
        [(0, "DummyID", "INTEGER", 1, None, 1)] # Columns for DummyTable1
    ]

    schema = get_db_schema(ctx=None)

    assert isinstance(schema, DBSchema)
    assert "DummyTable1" in schema.root

    col = schema.root["DummyTable1"][0]
    assert isinstance(col, TableColumn)
    assert col.name == "DummyID"
    assert col.pk is True

@pytest.mark.unit
def test_get_db_schema_database_error(mocker: MockerFixture, mock_db: MagicMock):
    """Verify get_db_schema handles database exceptions gracefully."""
    
    # Force the cursor to fail during the first query
    mock_db.execute.side_effect = Exception("SQLite connection failed")

    # Verify that the exception is raised (to be caught by FastMCP/A2A)
    with pytest.raises(Exception, match="SQLite connection failed"):
        get_db_schema(ctx=None) # type: ignore
