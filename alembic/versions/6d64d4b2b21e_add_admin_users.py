"""add admin users

Revision ID: 6d64d4b2b21e
Revises: 3f2c9a6b7d10
Create Date: 2026-09-29 22:52:13.913603
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6d64d4b2b21e"
down_revision: Union[str, Sequence[str], None] = "3f2c9a6b7d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_users",

        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "username",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "role",
            sa.String(length=20),
            server_default="staff",
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "username",
            name="uq_admin_users_username",
        ),
    )

    op.create_index(
        "ix_admin_users_username",
        "admin_users",
        ["username"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_users_username",
        table_name="admin_users",
    )

    op.drop_table("admin_users")