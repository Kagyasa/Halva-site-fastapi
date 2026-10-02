"""add order staff notes

Revision ID: 3f2c9a6b7d10
Revises: 8d4b7e2c1f90
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3f2c9a6b7d10"
down_revision: Union[str, None] = "8d4b7e2c1f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("staff_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "staff_notes")
