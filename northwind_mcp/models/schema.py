"""
Schema models
"""

from pydantic import BaseModel, RootModel
from typing import Any


class TableColumn(BaseModel):
    name: str
    type: str
    notnull: bool
    default_value: Any = None
    pk: bool


# Use RootModel to allow the dictionary to be the top-level object
class DBSchema(RootModel[dict[str, list[TableColumn]]]):
    """A flat mapping of table names to their column metadata."""

    pass


class SQLResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
