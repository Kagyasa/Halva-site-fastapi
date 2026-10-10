from sqlalchemy import select

from app.database import SessionLocal
from app.models.catalog import SiteContact

SOCIAL_CONTACTS = [
    {
        "type": "vk",
        "title": "VK",
        "value": "https://vk.ru/halva_tort_snz",
    },
    {
        "type": "telegram",
        "title": "TG",
        "value": "https://vk.ru/halva_tort_snz",
    },
    {
        "type": "max",
        "title": "MAX",
        "value": "https://vk.ru/halva_tort_snz",
    },
]


def main():
    created = 0
    preserved = 0

    with SessionLocal() as db:
        for data in SOCIAL_CONTACTS:
            contact = db.scalar(
                select(SiteContact)
                .where(SiteContact.type == data["type"])
                .order_by(SiteContact.created_at.asc())
                .limit(1)
            )

            if contact is None:
                contact = SiteContact(
                    type=data["type"],
                    title=data["title"],
                    value=data["value"],
                    is_active=True,
                )
                db.add(contact)
                created += 1
            else:
                # Preserve admin edits, including the current TG and MAX links.
                preserved += 1

        db.commit()

    print(f"Готово. Создано записей: {created}")
    print(f"Сохранено существующих записей без изменений: {preserved}")


if __name__ == "__main__":
    main()
