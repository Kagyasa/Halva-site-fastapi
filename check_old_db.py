import sqlite3

OLD_DB = r"C:\Users\kagyasa\Halva_project\backend\db.sqlite3"

connection = sqlite3.connect(OLD_DB)

tables = [
    "categories",
    "products",
    "pickup_locations",
    "showcase_items",
    "site_contacts",
]

for table in tables:
    print(f"\n--- {table} ---")

    columns = connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    for column in columns:
        print(column)

    count = connection.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"Записей: {count}")

connection.close()