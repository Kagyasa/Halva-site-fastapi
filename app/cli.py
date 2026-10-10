"""Run with python -m app.cli; passwords are entered interactively."""

import argparse
import getpass
import secrets
from pathlib import Path

from sqlalchemy import select, update

from app.admin_security import password_hasher
from app.config import get_settings
from app.database import SessionLocal
from app.models.admin_users import AdminUser
from app.models.orders import ConsentTextVersion, PrivacyPolicyVersion
from app.services.common import utc_now
from app.services.legal import DEMO_VERSION_PREFIX, sha256_text, validate_document_text
from app.services.notifications import deliver_one, run_worker


def publish_document(db, model, *, version: str, text: str, title: str | None = None):
    validate_document_text(text)
    if not version.strip() or len(version) > 50:
        raise ValueError("Версия должна содержать от 1 до 50 символов")
    if version.startswith(DEMO_VERSION_PREFIX):
        raise ValueError("Префикс halva-demo- зарезервирован для демонстрационных документов")
    existing = db.scalar(select(model).where(model.version == version))
    checksum = sha256_text(text)
    if existing:
        if (
            existing.text != text
            or existing.content_sha256 != checksum
            or (title is not None and existing.title != title)
        ):
            raise ValueError(
                "Эта версия уже опубликована с другим содержимым. Укажите новую версию."
            )
        document = existing
    else:
        values = dict(
            version=version,
            text=text,
            content_sha256=checksum,
            published_at=utc_now(),
            is_active=True,
        )
        if title is not None:
            values["title"] = title
        document = model(**values)
        db.add(document)
    db.execute(update(model).values(is_active=False))
    document.is_active = True
    if document.published_at is None:
        document.published_at = utc_now()
    db.flush()
    return document


def read_document(path: Path) -> str:
    if not path.is_file() or path.stat().st_size > 500_000:
        raise ValueError("Нужен файл UTF-8 размером до 500 КБ")
    text = path.read_text(encoding="utf-8-sig").strip()
    validate_document_text(text)
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Обслуживание Halva")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("generate-secret", help="Сгенерировать ключ для .env")
    admin = commands.add_parser("create-admin", help="Создать пользователя админки")
    admin.add_argument("--username", required=True)
    admin.add_argument("--role", choices=("admin", "staff"), default="admin")
    admin.add_argument(
        "--update",
        action="store_true",
        help="Явно заменить пароль и роль существующего пользователя",
    )
    legal = commands.add_parser(
        "publish-legal", help="Опубликовать два готовых документа одной транзакцией"
    )
    legal.add_argument("--policy-file", type=Path, required=True)
    legal.add_argument("--policy-version", required=True)
    legal.add_argument("--consent-file", type=Path, required=True)
    legal.add_argument("--consent-version", required=True)
    legal.add_argument("--title", default="Политика обработки персональных данных")
    legal.add_argument(
        "--confirm-final",
        action="store_true",
        help="Подтверждаю, что передаю готовые тексты для публикации",
    )
    worker = commands.add_parser("email-worker", help="Отправить очередь почтовых уведомлений")
    worker.add_argument(
        "--once", action="store_true", help="Обработать одну доступную запись и выйти"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "generate-secret":
            print(secrets.token_urlsafe(48))
        elif args.command == "create-admin":
            username = args.username.strip()
            if not 2 <= len(username) <= 100:
                raise ValueError("Логин должен содержать от 2 до 100 символов")
            password = getpass.getpass("Пароль (не менее 12 символов): ")
            if len(password) < 12 or len(password) > 1024:
                raise ValueError("Пароль должен содержать от 12 до 1024 символов")
            if password != getpass.getpass("Повторите пароль: "):
                raise ValueError("Пароли не совпадают")
            with SessionLocal() as db:
                user = db.scalar(select(AdminUser).where(AdminUser.username == username))
                if user and not args.update:
                    raise ValueError(
                        "Пользователь уже существует. Для замены пароля нужен --update"
                    )
                if user is None:
                    user = AdminUser(username=username)
                    db.add(user)
                user.password_hash, user.role, user.is_active = (
                    password_hasher.hash(password),
                    args.role,
                    True,
                )
                db.commit()
            print(f"Пользователь {username} ({args.role}) сохранён")
        elif args.command == "publish-legal":
            if not args.confirm_final:
                raise ValueError(
                    "Укажите --confirm-final только для готовых юридических документов"
                )
            if not args.title.strip() or len(args.title) > 255:
                raise ValueError("Название политики должно содержать от 1 до 255 символов")
            policy, consent = read_document(args.policy_file), read_document(args.consent_file)
            with SessionLocal() as db:
                publish_document(
                    db,
                    PrivacyPolicyVersion,
                    version=args.policy_version,
                    text=policy,
                    title=args.title,
                )
                publish_document(db, ConsentTextVersion, version=args.consent_version, text=consent)
                db.commit()
            print(
                "Политика и согласие опубликованы. Старые версии и свидетельства согласия сохранены."
            )
        else:
            get_settings().validate_smtp()
            if args.once:
                print("Обработано уведомление" if deliver_one() else "Очередь пуста")
            else:
                run_worker()
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
