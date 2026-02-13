"""
Database connection utilities for the Northwind SQLite store.

Provides centralized access to the Northwind database file, 
enforcing security through read-only (RO) URI connections to prevent 
accidental data modification by the MCP server.
"""

import sqlite3
from pathlib import Path


CURR_DIR = Path(__file__).resolve().parent
DB_PATH = CURR_DIR / "data" / "northwind.db"


def get_db_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database missing at: {DB_PATH}")
    
    # Return a secure, read-only connection
    return sqlite3.connect(
        f"{DB_PATH.as_uri()}?mode=ro",
        uri=True,
        check_same_thread=True
    )
