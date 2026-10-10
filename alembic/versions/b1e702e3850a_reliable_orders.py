"""Durable notifications, idempotency, catalog validation and UTC timestamps.

No existing orders or consent evidence are removed. Invalid legacy catalog
values must be corrected before upgrading; the preflight reports their IDs.
"""

import sqlalchemy as sa

from alembic import context, op

revision = "b1e702e3850a"
down_revision = "6d64d4b2b21e"
branch_labels = depends_on = None

CHECKS = {
    "products": [
        ("ck_products_portions_min", "portions_min IS NULL OR portions_min > 0"),
        ("ck_products_portions_max", "portions_max IS NULL OR portions_max > 0"),
        ("ck_products_height_min_cm", "height_min_cm IS NULL OR height_min_cm > 0"),
        (
            "ck_products_portions_range",
            "portions_min IS NULL OR portions_max IS NULL OR portions_min <= portions_max",
        ),
        ("ck_products_diameter_cm", "diameter_cm IS NULL OR diameter_cm > 0"),
        ("ck_products_weight_max_grams", "weight_max_grams IS NULL OR weight_max_grams > 0"),
        (
            "ck_products_height_range",
            "height_min_cm IS NULL OR height_max_cm IS NULL OR height_min_cm <= height_max_cm",
        ),
        ("ck_products_weight_min_grams", "weight_min_grams IS NULL OR weight_min_grams > 0"),
        ("ck_products_height_max_cm", "height_max_cm IS NULL OR height_max_cm > 0"),
        ("ck_products_price", "price >= 0"),
        (
            "ck_products_weight_range",
            "weight_min_grams IS NULL OR weight_max_grams IS NULL OR weight_min_grams <= weight_max_grams",
        ),
    ],
    "orders": [
        ("ck_orders_delivery_type", "delivery_type IN ('pickup', 'delivery')"),
        ("ck_orders_status", "status IN ('new', 'confirmed', 'completed', 'cancelled')"),
        (
            "ck_orders_amounts",
            "subtotal >= 0 AND delivery_fee >= 0 AND total = subtotal + delivery_fee",
        ),
    ],
    "order_items": [
        ("ck_order_items_price", "price >= 0"),
        ("ck_order_items_quantity", "quantity >= 1 AND quantity <= 50"),
    ],
    "admin_users": [("ck_admin_users_role", "role IN ('admin', 'staff')")],
}
UNIQUES = {
    "categories": [("uq_categories_slug", ("slug",))],
    "products": [("uq_products_slug", ("slug",))],
    "showcase_items": [("uq_showcase_location_product", ("pickup_location_id", "product_id"))],
}


def preflight():
    connection = op.get_bind()
    for table, checks in CHECKS.items():
        for name, expression in checks:
            invalid = (
                connection.execute(
                    sa.text(f"SELECT id FROM {table} WHERE NOT ({expression}) LIMIT 5")
                )
                .scalars()
                .all()
            )
            if invalid:
                raise RuntimeError(f"Correct {name} before upgrading: {table} IDs {invalid}")
    for table, constraints in UNIQUES.items():
        for name, columns in constraints:
            fields = ", ".join(columns)
            duplicate = connection.execute(
                sa.text(
                    f"SELECT {fields} FROM {table} GROUP BY {fields} HAVING COUNT(*) > 1 LIMIT 1"
                )
            ).first()
            if duplicate:
                raise RuntimeError(f"Correct duplicate {name} before upgrading: {duplicate}")


def upgrade():
    if not context.is_offline_mode():
        preflight()
    for table in set(CHECKS) | set(UNIQUES):
        with op.batch_alter_table(table) as batch:
            for name, expression in CHECKS.get(table, []):
                batch.create_check_constraint(name, expression)
            for name, columns in UNIQUES.get(table, []):
                batch.create_unique_constraint(name, list(columns))
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(64), nullable=True))
        batch.add_column(sa.Column("request_sha256", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_orders_idempotency_key", ["idempotency_key"])
        for column in ("created_at", "status", "requested_date"):
            batch.create_index(f"ix_orders_{column}", [column])
    op.add_column(
        "pickup_locations",
        sa.Column("weekday_hours", sa.String(100), server_default="08:00–21:00", nullable=False),
    )
    op.add_column(
        "pickup_locations",
        sa.Column("weekend_hours", sa.String(100), server_default="09:00–21:00", nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "categories",
            "products",
            "pickup_locations",
            "showcase_items",
            "site_contacts",
        ):
            for column in ("created_at", "updated_at"):
                op.alter_column(
                    table,
                    column,
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using=f"{column} AT TIME ZONE 'UTC'",
                )
    op.create_table(
        "email_notifications",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "order_id", sa.String(32), sa.ForeignKey("orders.id"), unique=True, nullable=False
        ),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("leased_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.String(32)),
        sa.Column("last_error", sa.String(200)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent')", name="ck_email_notifications_status"
        ),
    )
    op.create_index(
        "ix_email_notifications_next_attempt_at", "email_notifications", ["next_attempt_at"]
    )


def downgrade():
    op.drop_index("ix_email_notifications_next_attempt_at", table_name="email_notifications")
    op.drop_table("email_notifications")
    with op.batch_alter_table("pickup_locations") as batch:
        batch.drop_column("weekday_hours")
        batch.drop_column("weekend_hours")
    with op.batch_alter_table("orders") as batch:
        for column in ("created_at", "status", "requested_date"):
            batch.drop_index(f"ix_orders_{column}")
        batch.drop_constraint("uq_orders_idempotency_key", type_="unique")
        batch.drop_column("idempotency_key")
        batch.drop_column("request_sha256")
    for table in set(CHECKS) | set(UNIQUES):
        with op.batch_alter_table(table) as batch:
            for name, _ in CHECKS.get(table, []):
                batch.drop_constraint(name, type_="check")
            for name, _ in UNIQUES.get(table, []):
                batch.drop_constraint(name, type_="unique")
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "categories",
            "products",
            "pickup_locations",
            "showcase_items",
            "site_contacts",
        ):
            for column in ("created_at", "updated_at"):
                op.alter_column(
                    table,
                    column,
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    postgresql_using=f"{column} AT TIME ZONE 'UTC'",
                )
