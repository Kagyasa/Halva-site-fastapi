import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.orders import ConsentTextVersion, PrivacyPolicyVersion
from app.services.common import utc_now

DEMO_VERSION_PREFIX = "halva-demo-"
DEMO_ORDER_NOTE = "Демонстрационная заявка — создана для проверки и показа сайта."
DEMO_POLICY_TEXT = """ДЕМОНСТРАЦИОННЫЙ ДОКУМЕНТ

Эта страница показывает, как посетитель сможет ознакомиться с политикой перед
отправкой заявки. Итоговая политика обработки персональных данных пока не подготовлена.
Этот текст не является готовой политикой для приёма реальных заказов.

Для показа сайта используйте вымышленные контактные данные. Введённые имя, телефон,
состав заявки, дата, время и способ получения сохраняются в базе и показываются
сотрудникам в админке. Если настроена почта, уведомление отправляется на адрес
получателя заявок. Также сохраняются выбранные версии документов, IP и сведения
о браузере для проверки механизма согласия.

После показа демонстрационные заявки можно отменить в админке.
Перед открытием сайта для клиентов потребуется опубликовать готовые документы.
"""
DEMO_CONSENT_TEXT = """ДЕМОНСТРАЦИОННОЕ ПОДТВЕРЖДЕНИЕ

Я понимаю, что проверяю работу сайта и создаю демонстрационную заявку.
Я использую вымышленные контактные данные и ознакомился(ась) с описанием
демонстрационной обработки на странице политики.

Это подтверждение используется для показа интерфейса и сохранения версии документа.
Итоговый текст согласия для приёма реальных заказов ещё должен быть подготовлен.
"""


def prepare_demo_documents(db: Session) -> None:
    """Prepare presentation-only records without changing published real documents."""
    if not get_settings().demo_mode:
        return
    for model, version, text, title in (
        (
            PrivacyPolicyVersion,
            DEMO_VERSION_PREFIX + "policy-1",
            DEMO_POLICY_TEXT,
            "Демонстрация политики обработки персональных данных",
        ),
        (ConsentTextVersion, DEMO_VERSION_PREFIX + "consent-1", DEMO_CONSENT_TEXT, None),
    ):
        document = db.scalar(select(model).where(model.version == version))
        checksum = sha256_text(text)
        if document:
            if document.text != text or document.content_sha256 != checksum:
                raise ValueError("Демонстрационная версия документа изменена в базе")
            document.is_active = True
            if document.published_at is None:
                document.published_at = utc_now()
        else:
            values = dict(
                version=version,
                text=text,
                content_sha256=checksum,
                is_active=True,
                published_at=utc_now(),
            )
            if title is not None:
                values["title"] = title
            db.add(model(**values))
    db.commit()


LEGACY_CONSENT = """Я даю согласие на обработку моих персональных данных в объёме,
необходимом для оформления, обработки и исполнения моей заявки на заказ.

Я подтверждаю, что ознакомился(ась) с действующей Политикой обработки
персональных данных."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_document_text(text: str) -> None:
    normalized = " ".join(text.split()).casefold()
    if (
        len(normalized) < 30
        or "здесь будет полный текст" in normalized
        or "заменить на финальную юридическую версию" in normalized
        or normalized == " ".join(LEGACY_CONSENT.split()).casefold()
    ):
        raise ValueError("Нужен готовый документ: публикация старых заглушек запрещена")


def active_document(db: Session, model):
    demo_version = model.version.startswith(DEMO_VERSION_PREFIX, autoescape=True)
    document = db.scalar(
        select(model)
        .where(
            model.is_active.is_(True),
            model.published_at.is_not(None),
            demo_version if get_settings().demo_mode else ~demo_version,
        )
        .order_by(model.published_at.desc(), model.created_at.desc(), model.id.desc())
        .limit(1)
    )
    if document is None:
        return None
    try:
        validate_document_text(document.text)
    except ValueError:
        return None
    return document if sha256_text(document.text) == document.content_sha256 else None


def active_documents(db: Session):
    return active_document(db, PrivacyPolicyVersion), active_document(db, ConsentTextVersion)
