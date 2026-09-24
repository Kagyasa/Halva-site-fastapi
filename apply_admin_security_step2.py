from pathlib import Path
import re
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
ADMIN_PATH = PROJECT_ROOT / "app" / "admin.py"
BACKUP_PATH = PROJECT_ROOT / "app" / "admin.py.before_security_step2.bak"


def fail(message: str) -> None:
    print(f"\nОШИБКА: {message}")
    sys.exit(1)


if not ADMIN_PATH.exists():
    fail(f"Не найден файл {ADMIN_PATH}")

text = ADMIN_PATH.read_text(encoding="utf-8")

if "admin_login_rate_limiter" in text:
    print("Защита входа уже добавлена. Ничего менять не нужно.")
    sys.exit(0)

shutil.copy2(ADMIN_PATH, BACKUP_PATH)

if "import logging" not in text:
    text = text.replace(
        "import hmac\n",
        "import hmac\nimport logging\n",
        1,
    )

import_anchor = "from app.database import SessionLocal, engine\n"
if import_anchor not in text:
    fail("Не удалось найти импорт app.database в admin.py")

text = text.replace(
    import_anchor,
    import_anchor + "from app.services.rate_limit import admin_login_rate_limiter\n",
    1,
)

logger_anchor = "SNEZHINSK_TZ = timezone(timedelta(hours=5))\n"
if logger_anchor not in text:
    fail("Не удалось найти SNEZHINSK_TZ в admin.py")

text = text.replace(
    logger_anchor,
    logger_anchor + "\nlogger = logging.getLogger(__name__)\n",
    1,
)

pattern = re.compile(
    r"    async def login\(self, request: Request\) -> bool:\n"
    r".*?"
    r"        return True\n\n"
    r"    async def logout",
    re.DOTALL,
)

replacement = '''    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        client_ip = request.client.host if request.client else "unknown"

        is_blocked, retry_after = admin_login_rate_limiter.is_blocked(
            client_ip
        )

        if is_blocked:
            logger.warning(
                "Заблокирована попытка входа в админку с IP %s. "
                "Повтор через %s сек.",
                client_ip,
                retry_after,
            )
            return False

        username_ok = hmac.compare_digest(
            username,
            self.settings.admin_username,
        )
        password_ok = hmac.compare_digest(
            password,
            self.settings.admin_password,
        )

        if not (username_ok and password_ok):
            newly_blocked, retry_after = (
                admin_login_rate_limiter.record_failure(client_ip)
            )

            if newly_blocked:
                logger.warning(
                    "IP %s временно заблокирован после серии "
                    "неудачных входов в админку. Блокировка: %s сек.",
                    client_ip,
                    retry_after,
                )
            else:
                logger.warning(
                    "Неудачная попытка входа в админку с IP %s",
                    client_ip,
                )

            return False

        admin_login_rate_limiter.reset(client_ip)

        request.session.clear()
        request.session.update(
            {
                "halva_admin_authenticated": True,
                "halva_admin_username": self.settings.admin_username,
            }
        )
        return True

    async def logout'''

text, count = pattern.subn(replacement, text, count=1)

if count != 1:
    fail(
        "Не удалось автоматически заменить функцию login(). "
        f"Резервная копия сохранена: {BACKUP_PATH}"
    )

ADMIN_PATH.write_text(text, encoding="utf-8")

try:
    compile(text, str(ADMIN_PATH), "exec")
except SyntaxError as exc:
    shutil.copy2(BACKUP_PATH, ADMIN_PATH)
    fail(
        "После изменения возникла синтаксическая ошибка, поэтому "
        f"admin.py восстановлен из резервной копии. {exc}"
    )

print("Готово.")
print(f"Изменён: {ADMIN_PATH}")
print(f"Резервная копия: {BACKUP_PATH}")
print()
print("Теперь после 5 неудачных попыток входа с одного IP")
print("админка блокирует этот IP на 15 минут.")
