"""cascade delete post comments

Revision ID: 56e0016d6b9f
Revises: 454277925d92
Create Date: 2026-11-18 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "56e0016d6b9f"
down_revision: Union[str, None] = "454277925d92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "comments_post_id_fkey"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "comments", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT_NAME,
        "comments",
        "posts",
        ["post_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "comments", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT_NAME,
        "comments",
        "posts",
        ["post_id"],
        ["id"],
    )
