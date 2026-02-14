"""
Utility functions
"""

import re

TABLE_REGEX = re.compile(
    r"""
    \b(?:FROM|JOIN)\s+           # FROM or JOIN keyword
    ([a-zA-Z_][\w\.]*)           # table name (optionally schema.table)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_tables(query: str) -> list[str]:
    """Extract table names from a SQL query."""

    tables: list[str] = []

    for match in TABLE_REGEX.findall(query):
        # Strip schema if present (schema.table -> table)
        table = match.split(".")[-1]
        tables.append(table)

    tables = list(dict.fromkeys(tables))

    return tables
