"""add product display name

Revision ID: 8d4b7e2c1f90
Revises: 0fae9568989c
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d4b7e2c1f90"
down_revision: Union[str, None] = "0fae9568989c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("display_name", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "display_name")
