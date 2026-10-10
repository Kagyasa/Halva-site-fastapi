"""Read-only Django SQLite import; all target writes share one transaction."""

import argparse
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Numeric, func, insert, select

import app.models  # noqa: F401 -- register tables before inspecting metadata
from app.database import Base, engine

TABLES = ("categories", "pickup_locations", "products", "showcase_items", "site_contacts")


def convert_row(table, row):
    values = {}
    for column in table.columns:
        if column.name not in row.keys():
            continue  # New optional columns receive their defaults.
        value = row[column.name]
        if value is not None:
            if isinstance(column.type, Boolean):
                if value not in (0, 1, False, True):
                    raise ValueError(f"Invalid boolean: {table.name}.{column.name}")
                value = bool(value)
            elif isinstance(column.type, DateTime):
                value = datetime.fromisoformat(str(value))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=UTC)
            elif isinstance(column.type, Numeric):
                value = Decimal(str(value))
        values[column.name] = value
    return values


def import_catalog(source: Path) -> None:
    source = source.resolve(strict=True)
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as old:
        old.row_factory = sqlite3.Row
        data = {
            name: [
                convert_row(Base.metadata.tables[name], row)
                for row in old.execute(f"SELECT * FROM {name}")
            ]
            for name in TABLES
        }
    with engine.begin() as connection:
        for name in TABLES:
            table = Base.metadata.tables[name]
            if connection.scalar(select(func.count()).select_from(table)):
                raise ValueError(f"Таблица {name} уже заполнена. Импорт не выполнен.")
        for name in TABLES:
            if data[name]:
                connection.execute(insert(Base.metadata.tables[name]), data[name])
            print(f"{name}: {len(data[name])}")
    print("Перенос завершён")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Путь к старой Django db.sqlite3")
    args = parser.parse_args()
    import_catalog(args.source)


if __name__ == "__main__":
    main()
