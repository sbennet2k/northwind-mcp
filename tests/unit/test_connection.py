import pytest
from pathlib import Path
from pytest_mock import MockerFixture
from northwind_mcp.connection import DB_PATH, get_db_connection

@pytest.mark.unit
def test_db_path_calculation():
    """Verify the database path is correctly resolved relative to the file location."""
    assert DB_PATH.name == "northwind.db"
    assert "data" in DB_PATH.parts
    assert isinstance(DB_PATH, Path)

@pytest.mark.unit
def test_get_db_connection_raises_file_not_found(mocker: MockerFixture):
    """Verify FileNotFoundError is raised if the database file does not exist."""

    # Patch the class method to return False
    mocker.patch("northwind_mcp.connection.Path.exists", return_value=False)
    
    with pytest.raises(FileNotFoundError, match="Database missing at"):
        get_db_connection()

@pytest.mark.unit
def test_get_db_connection_is_readonly(mocker: MockerFixture):
    """Verify that the connection is initialized with the URI read-only flag."""

    # Ensure the code thinks the file exists so it doesn't raise FileNotFoundError
    mocker.patch("northwind_mcp.connection.Path.exists", return_value=True)
    
    # Mock the sqlite3.connect call
    mock_connect = mocker.patch("sqlite3.connect")

    get_db_connection()
    
    # Check the first argument of the call (the URI string)
    args, kwargs = mock_connect.call_args
    assert "mode=ro" in args[0]
    assert kwargs["uri"] is True
    assert kwargs["check_same_thread"] is True
