import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import SessionLocal
from app.models.orders import (
    ConsentTextVersion,
    PrivacyPolicyVersion,
)


# ВАЖНО:
# Опубликованную версию НЕ редактируем.
# Если меняется текст документа — меняем VERSION и создаём новую запись.

PRIVACY_POLICY_VERSION = "1.0"
PRIVACY_POLICY_TITLE = "Политика обработки персональных данных"
PRIVACY_POLICY_TEXT = """
Здесь будет полный текст Политики обработки персональных данных.

Перед запуском сайта этот текст нужно заменить на финальную юридическую версию.
""".strip()


CONSENT_VERSION = "1.0"
CONSENT_TEXT = """
Я даю согласие на обработку моих персональных данных в объёме,
необходимом для оформления, обработки и исполнения моей заявки на заказ.

Я подтверждаю, что ознакомился(ась) с действующей Политикой обработки
персональных данных.
""".strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def publish_policy(db) -> PrivacyPolicyVersion:
    expected_hash = sha256_text(PRIVACY_POLICY_TEXT)

    existing = db.scalar(
        select(PrivacyPolicyVersion).where(
            PrivacyPolicyVersion.version == PRIVACY_POLICY_VERSION
        )
    )

    if existing is not None:
        if (
            existing.title != PRIVACY_POLICY_TITLE
            or existing.text != PRIVACY_POLICY_TEXT
            or existing.content_sha256 != expected_hash
        ):
            raise RuntimeError(
                "Версия политики "
                f"{PRIVACY_POLICY_VERSION!r} уже опубликована с другим содержимым. "
                "Не изменяйте опубликованную версию: задайте новый "
                "PRIVACY_POLICY_VERSION."
            )

        db.execute(
            update(PrivacyPolicyVersion)
            .where(PrivacyPolicyVersion.id != existing.id)
            .values(is_active=False)
        )

        existing.is_active = True
        return existing

    db.execute(
        update(PrivacyPolicyVersion)
        .values(is_active=False)
    )

    policy = PrivacyPolicyVersion(
        version=PRIVACY_POLICY_VERSION,
        title=PRIVACY_POLICY_TITLE,
        text=PRIVACY_POLICY_TEXT,
        content_sha256=expected_hash,
        is_active=True,
        published_at=datetime.now(timezone.utc),
    )

    db.add(policy)
    return policy


def publish_consent(db) -> ConsentTextVersion:
    expected_hash = sha256_text(CONSENT_TEXT)

    existing = db.scalar(
        select(ConsentTextVersion).where(
            ConsentTextVersion.version == CONSENT_VERSION
        )
    )

    if existing is not None:
        if (
            existing.text != CONSENT_TEXT
            or existing.content_sha256 != expected_hash
        ):
            raise RuntimeError(
                "Версия согласия "
                f"{CONSENT_VERSION!r} уже опубликована с другим содержимым. "
                "Не изменяйте опубликованную версию: задайте новый "
                "CONSENT_VERSION."
            )

        db.execute(
            update(ConsentTextVersion)
            .where(ConsentTextVersion.id != existing.id)
            .values(is_active=False)
        )

        existing.is_active = True
        return existing

    db.execute(
        update(ConsentTextVersion)
        .values(is_active=False)
    )

    consent = ConsentTextVersion(
        version=CONSENT_VERSION,
        text=CONSENT_TEXT,
        content_sha256=expected_hash,
        is_active=True,
        published_at=datetime.now(timezone.utc),
    )

    db.add(consent)
    return consent


def main():
    with SessionLocal() as db:
        try:
            policy = publish_policy(db)
            consent = publish_consent(db)
            db.commit()
        except Exception:
            db.rollback()
            raise

        print("Готово.")
        print()
        print("Активная политика:")
        print("  версия:", policy.version)
        print("  hash:", policy.content_sha256)
        print("  опубликована:", policy.published_at)
        print()
        print("Активное согласие:")
        print("  версия:", consent.version)
        print("  hash:", consent.content_sha256)
        print("  опубликовано:", consent.published_at)


if __name__ == "__main__":
    main()
