import hashlib
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models.orders import (
    ConsentTextVersion,
    PrivacyPolicyVersion,
)


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
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def main():
    db = SessionLocal()

    try:
        existing_policy = db.scalar(
            select(PrivacyPolicyVersion).where(
                PrivacyPolicyVersion.version == PRIVACY_POLICY_VERSION
            )
        )

        if existing_policy is None:
            policy = PrivacyPolicyVersion(
                version=PRIVACY_POLICY_VERSION,
                title=PRIVACY_POLICY_TITLE,
                text=PRIVACY_POLICY_TEXT,
                content_sha256=sha256_text(PRIVACY_POLICY_TEXT),
                is_active=True,
                published_at=datetime.now(timezone.utc),
            )

            db.add(policy)

        existing_consent = db.scalar(
            select(ConsentTextVersion).where(
                ConsentTextVersion.version == CONSENT_VERSION
            )
        )

        if existing_consent is None:
            consent = ConsentTextVersion(
                version=CONSENT_VERSION,
                text=CONSENT_TEXT,
                content_sha256=sha256_text(CONSENT_TEXT),
                is_active=True,
                published_at=datetime.now(timezone.utc),
            )

            db.add(consent)

        db.commit()

        print("Готово.")

        policy = db.scalar(
            select(PrivacyPolicyVersion).where(
                PrivacyPolicyVersion.version == PRIVACY_POLICY_VERSION
            )
        )

        consent = db.scalar(
            select(ConsentTextVersion).where(
                ConsentTextVersion.version == CONSENT_VERSION
            )
        )

        print()
        print("Политика:")
        print("  версия:", policy.version)
        print("  hash:", policy.content_sha256)
        print("  активна:", policy.is_active)

        print()
        print("Согласие:")
        print("  версия:", consent.version)
        print("  hash:", consent.content_sha256)
        print("  активно:", consent.is_active)

    finally:
        db.close()


if __name__ == "__main__":
    main()