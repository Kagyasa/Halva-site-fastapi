import sqlite3
from pathlib import Path

from sqlalchemy import text

from app.database import engine


OLD_DB = Path(
    r"C:\Users\kagyasa\Halva_project\backend\db.sqlite3"
)

TABLES = [
    "categories",
    "products",
    "pickup_locations",
    "showcase_items",
    "site_contacts",
]


def get_rows(connection: sqlite3.Connection, table: str):
    connection.row_factory = sqlite3.Row

    return connection.execute(
        f"SELECT * FROM {table}"
    ).fetchall()


def main():
    if not OLD_DB.exists():
        raise FileNotFoundError(
            f"Старая база не найдена: {OLD_DB}"
        )

    old_connection = sqlite3.connect(OLD_DB)

    try:
        # Сначала только читаем данные из Django.
        data = {
            table: get_rows(old_connection, table)
            for table in TABLES
        }

        print("Найдено в старой Django-базе:")

        for table, rows in data.items():
            print(f"  {table}: {len(rows)}")

        # Проверяем, что новая база пустая.
        with engine.connect() as connection:
            for table in TABLES:
                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar_one()

                if count != 0:
                    raise RuntimeError(
                        f"Таблица {table} новой базы "
                        f"уже содержит {count} записей."
                    )

        # Переносим всё одной транзакцией.
        # Если что-нибудь упадёт, частичного импорта не останется.
        with engine.begin() as connection:

            # 1. Категории
            for row in data["categories"]:
                connection.execute(
                    text("""
                        INSERT INTO categories (
                            id,
                            name,
                            slug,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :id,
                            :name,
                            :slug,
                            :is_active,
                            :created_at,
                            :updated_at
                        )
                    """),
                    dict(row),
                )

            # 2. Точки самовывоза
            for row in data["pickup_locations"]:
                connection.execute(
                    text("""
                        INSERT INTO pickup_locations (
                            id,
                            name,
                            address,
                            phone,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :id,
                            :name,
                            :address,
                            :phone,
                            :is_active,
                            :created_at,
                            :updated_at
                        )
                    """),
                    dict(row),
                )

            # 3. Товары
            for row in data["products"]:
                connection.execute(
                    text("""
                        INSERT INTO products (
                            id,
                            name,
                            slug,
                            price,
                            weight_min_grams,
                            weight_max_grams,
                            portions_min,
                            portions_max,
                            diameter_cm,
                            height_min_cm,
                            height_max_cm,
                            image_url,
                            is_active,
                            created_at,
                            updated_at,
                            category_id,
                            size,
                            is_available_for_order,
                            vk_url
                        )
                        VALUES (
                            :id,
                            :name,
                            :slug,
                            :price,
                            :weight_min_grams,
                            :weight_max_grams,
                            :portions_min,
                            :portions_max,
                            :diameter_cm,
                            :height_min_cm,
                            :height_max_cm,
                            :image_url,
                            :is_active,
                            :created_at,
                            :updated_at,
                            :category_id,
                            :size,
                            :is_available_for_order,
                            :vk_url
                        )
                    """),
                    dict(row),
                )

            # 4. Витрины
            for row in data["showcase_items"]:
                connection.execute(
                    text("""
                        INSERT INTO showcase_items (
                            id,
                            created_at,
                            updated_at,
                            pickup_location_id,
                            product_id
                        )
                        VALUES (
                            :id,
                            :created_at,
                            :updated_at,
                            :pickup_location_id,
                            :product_id
                        )
                    """),
                    dict(row),
                )

            # 5. Контакты
            for row in data["site_contacts"]:
                connection.execute(
                    text("""
                        INSERT INTO site_contacts (
                            id,
                            type,
                            title,
                            value,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :id,
                            :type,
                            :title,
                            :value,
                            :is_active,
                            :created_at,
                            :updated_at
                        )
                    """),
                    dict(row),
                )

        print("\nПеренос завершён.")

        print("\nНовая FastAPI-база:")

        with engine.connect() as connection:
            for table in TABLES:
                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar_one()

                print(f"  {table}: {count}")

    finally:
        old_connection.close()


if __name__ == "__main__":
    main()