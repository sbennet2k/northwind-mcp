from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from northwind_mcp.server import ping


@pytest.mark.unit
def test_ping_healthy(mocker: MockerFixture, mock_db_conn: MagicMock):
    """Test ping returns 'ok' when database and version are available."""

    # Configure healthy DB response
    mock_db_conn.execute.return_value.fetchone.return_value = (1,)

    # Mock version
    mocker.patch("northwind_mcp.server.version", return_value="1.2.3")

    # Mock datetime
    mock_datetime = mocker.MagicMock()
    mock_datetime.now.return_value.astimezone.return_value.strftime.return_value = (
        "20-02-2026 17:05:15 EET"
    )
    mocker.patch("northwind_mcp.server.datetime", mock_datetime)

    result = ping(ctx=mocker.Mock())

    assert result["status"] == "ok"
    assert result["version"] == "1.2.3"
    assert result["database"] == "healthy"
    assert result["timestamp"] == "20-02-2026 17:05:15 EET"
    # Verify the ping actually checked the DB
    mock_db_conn.execute.assert_called_once_with("SELECT 1")


@pytest.mark.unit
def test_ping_degraded_db_failure(mocker: MockerFixture, mock_db_conn: MagicMock):
    """Test ping returns 'degraded' when the database check fails."""

    # Configure DB failure
    mock_db_conn.execute.side_effect = Exception("SQLite Error: Database locked")

    result = ping(ctx=mocker.Mock())

    assert result["status"] == "degraded"
    assert "unhealthy: SQLite Error: Database locked" in result["database"]


@pytest.mark.unit
def test_ping_version_not_found(mocker: MockerFixture, mock_db_conn: MagicMock):
    """Test ping handles missing package metadata gracefully."""

    # Simulate package not being installed
    mocker.patch("northwind_mcp.server.version", side_effect=PackageNotFoundError)

    result = ping(ctx=mocker.Mock())

    assert result["version"] == "unknown"
    assert result["status"] == "ok"  # DB is still healthy
    mock_db_conn.execute.assert_called_once_with("SELECT 1")
