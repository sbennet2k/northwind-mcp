"""
Northwind MCP Server Tool Definitions.

Implements a Model Context Protocol (MCP) server using the FastMCP framework.

Exposed Tools:
    - get_db_schema: Returns Northwind DB table and column metadata.
    - validate_query: Validation suite for checking SQL safety and syntax.
    - execute_sql: Executes SELECT queries and returns structured results.
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP, Context
from northwind_mcp.connection import get_db_connection
from northwind_mcp.models.schema import TableColumn, SQLResult, DBSchema

import re
import sqlparse
from sqlparse.tokens import Keyword # type: ignore

from northwind_mcp.utils.utils import extract_tables


mcp_server = FastMCP("NorthwindMCP")


logger = logging.getLogger(__name__)


@mcp_server.tool()
def get_db_schema(ctx: Context[Any, Any]) -> DBSchema:
    """Fetches the full database schema as a flat mapping of tables to columns."""

    logger.info("Fetching DB schema...")

    schema_dict: dict[str, list[TableColumn]] = {}

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get all user-defined tables
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [row[0] for row in cursor.fetchall()]

        # Iterate and build column metadata
        for table in tables:
            cursor.execute(f'PRAGMA table_info("{table}")')

            cols = [
                TableColumn(
                    name=row[1],
                    type=row[2],
                    notnull=bool(row[3]),
                    default_value=row[4],
                    pk=bool(row[5]),
                )
                for row in cursor.fetchall()
            ]
            schema_dict[table] = cols

    return DBSchema(schema_dict)


@mcp_server.tool()
def validate_query(query: str, params: dict[str, Any], ctx: Context[Any, Any]) -> dict[str, Any]:
    """
    Validates a SQL SELECT query using sqlparse with join-aware column validation.
    """

    logger.info("Validating SQL query '%s' with params '%s'", query, params)

    result: dict[str, Any] = {
        "valid": False,
        "errors": [],
        "warnings": []
    }

    # --- Guardrail: SELECT only ---
    parsed = sqlparse.parse(query)
    if not parsed:
        result["errors"].append("Unable to parse SQL query.")
        logger.error("Unable to parse SQL query.")
        return result

    statement = parsed[0]
    if statement.get_type() != "SELECT":
        result["errors"].append("Only SELECT queries are allowed.")
        logger.error("Only SELECT queries are allowed.")
        return result

    # --- Blacklist ---
    blacklist = {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "ATTACH", "DETACH", "PRAGMA", "VACUUM", "LOAD_EXTENSION"
    }

    query_words = re.findall(r'\b\w+\b', query.upper())
    for word in query_words:
        if word.upper() in blacklist:
            result["errors"].append(f"Query contains forbidden keyword: {word.upper()}")
            logger.error("Query contains forbidden keyword: %s", word)
            return result

    # --- Parameter sanity check ---
    if ":" in query and not params:
        result["errors"].append("Query uses parameters but no params were provided.")
        logger.error("Query uses parameters but no params were provided.")
        return result
    
    try:
        # --- Load schema ---
        schema: DBSchema = get_db_schema(ctx)

        schema_tables = {
            table.lower(): {col.name.lower() for col in cols}
            for table, cols in schema.root.items()
        }
        logger.debug("Tables in schema (lowercase): %s", schema_tables)

        # --- Extract tables ---
        tables = extract_tables(query)
        logger.debug("Tables extracted from query: %s", tables)
        tables_lower = [t.lower() for t in tables]
        logger.debug("Tables extracted from query (lowercase): %s", tables_lower)

        for table in tables_lower:
            if table not in schema_tables:
                result["errors"].append(f"Table does not exist: {table}")
                logger.error("Table does not exist in schema: %s", table)

        if result["errors"]:
            return result
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # --- SQLite syntax/schema validation ---
            try:
                cursor.execute(f"EXPLAIN {query}", params or {})
            except Exception as e:
                result["errors"].append(f"EXPLAIN failed. SQL syntax/schema error: {e}")
                logger.error("EXPLAIN failed. SQL syntax/schema error: %s", e)
                return result

        # --- Complexity warnings ---
        join_count = query.lower().count("join")
        if join_count > 3:
            result["warnings"].append(
                "Query contains multiple JOINs; may be complex."
            )
            logger.warning("Query contains multiple JOINs; may be complex.")

        if "*" in query:
            result["warnings"].append(
                "Query uses SELECT *; consider specifying columns."
            )
            logger.warning("Query uses SELECT *; consider specifying columns.")

    except Exception as e:
        result["errors"].append(f"Unexpected error during validation: {e}")

    result["valid"] = not result["errors"]
    return result


@mcp_server.tool()
def execute_sql(query: str, params: dict[str, Any], ctx: Context[Any, Any]) -> SQLResult:
    """Executes a read-only SELECT query against the Northwind database."""

    logger.info("Executing SQL query...")

    # Basic guardrail (assumed that validate_sql tool has been called earlier)
    if not query.strip().lower().startswith("select"):
        # Note: This will be reported as a tool error in FastMCP
        raise ValueError("Security Violation: Only SELECT queries are allowed.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description] if cursor.description else []
            return SQLResult(columns=columns, rows=rows)
        except Exception as e:
            logger.exception("SQL Execution Error")
            raise e # FastMCP handles this and sends the error to the LLM
