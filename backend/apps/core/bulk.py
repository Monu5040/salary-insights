"""Saving many rows in one statement (design §10)."""

from collections.abc import Sequence
from typing import Any

from django.db import connection
from django.db.models import Field, Model


def update_many(rows: Sequence[Model], fields: Sequence[str]) -> None:
    """Save these fields of these rows with one UPDATE, whatever their number.

    Django's bulk_update builds a CASE with a branch per row for every field: for an import
    of 10,000 raises it spent about five seconds building them in Python and another second
    in Postgres evaluating them. Here each column travels as one array instead, and
    `unnest` turns the arrays back into rows to join on.
    """
    if not rows:
        return
    columns = _columns(type(rows[0]), fields)
    quote = connection.ops.quote_name
    names = ", ".join(quote(column) for column, _ in columns)
    arrays = ", ".join(f"%s::{field.db_type(connection)}[]" for _, field in columns)
    assignments = ", ".join(f"{quote(column)} = new.{quote(column)}" for column, _ in columns[1:])
    key = quote(columns[0][0])
    table = quote(type(rows[0])._meta.db_table)
    # Only the model's own table and column names are formatted in; every value is a parameter.
    sql = (
        f"UPDATE {table} AS old SET {assignments} "  # noqa: S608
        f"FROM unnest({arrays}) AS new({names}) WHERE old.{key} = new.{key}"
    )
    values = [
        [field.get_db_prep_save(getattr(row, field.attname), connection) for row in rows]
        for _, field in columns
    ]
    with connection.cursor() as cursor:
        cursor.execute(sql, values)


def _columns(model: type[Model], names: Sequence[str]) -> list[tuple[str, Field[Any, Any]]]:
    """The primary key, then the named fields, each with its column."""
    meta = model._meta
    found: list[tuple[str, Field[Any, Any]]] = []
    for field in [meta.pk, *(meta.get_field(name) for name in names)]:
        if not isinstance(field, Field) or field.column is None:
            raise ValueError(f"{model.__name__} has no column for {field}.")
        found.append((field.column, field))
    return found
