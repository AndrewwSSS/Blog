"""store datetimes as timestamptz

Revision ID: d41c7e2a9f13
Revises: b5987d788c57
Create Date: 2026-11-19 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d41c7e2a9f13"
down_revision: Union[str, None] = "b5987d788c57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Existing values were written with datetime.utcnow(), so they are read as UTC.
COLUMNS = [
    ("posts", "date_posted", False),
    ("comments", "date_posted", False),
    ("outbox_events", "created_at", False),
    ("outbox_events", "published_at", True),
]


def upgrade() -> None:
    for table, column, nullable in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column, nullable in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
