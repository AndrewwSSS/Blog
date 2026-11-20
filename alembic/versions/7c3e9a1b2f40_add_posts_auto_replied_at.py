"""add posts.auto_replied_at

Revision ID: 7c3e9a1b2f40
Revises: d41c7e2a9f13
Create Date: 2026-11-20 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c3e9a1b2f40"
down_revision: Union[str, None] = "d41c7e2a9f13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("auto_replied_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("posts", "auto_replied_at")
