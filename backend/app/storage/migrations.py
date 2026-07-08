"""Additive-only schema migration: adds any column an ORM model declares
but that an existing SQLite table is missing, so a future field (like
Signal.created_at) never again requires deleting and recreating the whole
database.

`Base.metadata.create_all` only creates missing *tables* — it does not
alter an existing table's columns, which is what forced deleting the dev
DB earlier. This closes that specific, narrow gap without adopting a full
migration tool: every column is added as plain nullable, dropping any
model-declared NOT NULL / UNIQUE / DEFAULT / server_default on the new
column, since a pre-existing row genuinely has no value for a brand-new
column (NULL is the honest answer for it) — every row inserted from here
on provides a real value via the ORM as normal.

Deliberately out of scope: renames, type changes, constraint/default
changes on a *new* column, or any change to an *existing* column
(including its constraints), or column/table removal. A model that needs
a real default/constraint on a new column against existing rows, or that
changes an existing column, needs a real migration tool (Alembic) once
the schema stabilizes enough that "just add a decisions.md entry" stops
being the right answer — see [[additive-schema-migration]] in
decisions.md.

Table/column identifiers here always come from this codebase's own ORM
model definitions (app/storage/models.py via Base.metadata), never
request or otherwise external input — DDL identifiers can't be
parameterized, so interpolating them is the one sanctioned exception to
"parameterized queries only" (security.md). The isidentifier() check
below guards that invariant defensively rather than relying purely on
convention.
"""

import logging

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


async def add_missing_columns(conn: AsyncConnection, base: type[DeclarativeBase]) -> None:
    await conn.run_sync(_add_missing_columns_sync, base)


def _add_missing_columns_sync(sync_conn: Connection, base: type[DeclarativeBase]) -> None:
    inspector = sa_inspect(sync_conn)
    for table in base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # a brand-new table: create_all already created it in full

        existing_columns = {column_info["name"] for column_info in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue

            if not table.name.isidentifier() or not column.name.isidentifier():
                raise ValueError(f"Refusing to ALTER on non-identifier name: {table.name}.{column.name}")

            column_type = column.type.compile(dialect=sync_conn.dialect)
            sync_conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}'))
            logger.info("Added missing column %s.%s (%s)", table.name, column.name, column_type)
