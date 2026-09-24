from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
ADMIN_PATH = PROJECT_ROOT / "app" / "admin.py"
BACKUP_PATH = PROJECT_ROOT / "app" / "admin.py.before_visible_lock.bak"

def fail(message: str) -> None:
    print("\nОШИБКА:", message)
    sys.exit(1)

if not ADMIN_PATH.exists():
    fail(f"Не найден файл: {ADMIN_PATH}")

text = ADMIN_PATH.read_text(encoding="utf-8")

if "admin_login_rate_limiter" not in text:
    fail("В admin.py не найдена предыдущая защита admin_login_rate_limiter.")

if "def admin_blocked_response(" in text:
    print("Видимая блокировка уже добавлена.")
    sys.exit(0)

shutil.copy2(ADMIN_PATH, BACKUP_PATH)

old_import = "from starlette.responses import RedirectResponse\n"
new_import = "from starlette.responses import HTMLResponse, RedirectResponse\n"

if old_import not in text:
    fail("Не найден импорт RedirectResponse.")

text = text.replace(old_import, new_import, 1)

helper = 'def admin_blocked_response(retry_after: int) -> HTMLResponse:\n    minutes = max(1, (retry_after + 59) // 60)\n\n    html = f"""<!doctype html>\n<html lang="ru">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>HALVA — вход временно заблокирован</title>\n  <style>\n    * {{ box-sizing: border-box; }}\n    body {{\n      min-height: 100vh;\n      margin: 0;\n      display: grid;\n      place-items: center;\n      padding: 24px;\n      background:\n        radial-gradient(circle at 85% 15%, rgba(253, 201, 227, .72), transparent 36%),\n        radial-gradient(circle at 10% 90%, rgba(255, 228, 188, .75), transparent 38%),\n        #fff;\n      color: #1a1a1a;\n      font-family: Inter, Arial, sans-serif;\n    }}\n    .card {{\n      width: min(460px, 100%);\n      padding: 38px 34px;\n      border: 1px solid rgba(26, 26, 26, .08);\n      border-radius: 26px;\n      background: rgba(255, 255, 255, .94);\n      box-shadow: 0 24px 70px rgba(54, 16, 35, .14);\n      text-align: center;\n    }}\n    .icon {{\n      width: 58px;\n      height: 58px;\n      margin: 0 auto 18px;\n      display: grid;\n      place-items: center;\n      border-radius: 50%;\n      background: rgba(223, 19, 117, .10);\n      color: #DF1375;\n      font-size: 28px;\n      font-weight: 700;\n    }}\n    h1 {{\n      margin: 0;\n      font-family: Georgia, "Times New Roman", serif;\n      font-size: 30px;\n      font-weight: 400;\n      line-height: 1.15;\n    }}\n    p {{\n      margin: 14px 0 0;\n      color: #6f6269;\n      font-size: 15px;\n      line-height: 1.5;\n    }}\n    .timer {{\n      margin-top: 22px;\n      color: #DF1375;\n      font-size: 15px;\n      font-weight: 600;\n    }}\n    a {{\n      display: inline-flex;\n      align-items: center;\n      justify-content: center;\n      min-width: 180px;\n      height: 44px;\n      margin-top: 24px;\n      padding: 0 22px;\n      border-radius: 22px;\n      background: #DF1375;\n      color: #fff;\n      text-decoration: none;\n      font-size: 15px;\n      font-weight: 600;\n    }}\n  </style>\n</head>\n<body>\n  <main class="card">\n    <div class="icon">!</div>\n    <h1>Слишком много попыток входа</h1>\n    <p>\n      Вход в админку с этого IP временно заблокирован.\n      Это защита от подбора пароля.\n    </p>\n    <div class="timer" id="timer">\n      Повторите примерно через {minutes} мин.\n    </div>\n    <a href="/admin/login">Вернуться ко входу</a>\n  </main>\n\n  <script>\n    let seconds = {retry_after};\n    const timer = document.getElementById("timer");\n\n    const updateTimer = () => {{\n      if (seconds <= 0) {{\n        timer.textContent = "Блокировка закончилась. Можно попробовать снова.";\n        return;\n      }}\n\n      const mins = Math.floor(seconds / 60);\n      const secs = seconds % 60;\n\n      timer.textContent =\n        `До следующей попытки: ${{mins}}:${{String(secs).padStart(2, "0")}}`;\n\n      seconds -= 1;\n    }};\n\n    updateTimer();\n    setInterval(updateTimer, 1000);\n  </script>\n</body>\n</html>"""\n\n    return HTMLResponse(\n        content=html,\n        status_code=429,\n        headers={\n            "Retry-After": str(retry_after),\n            "Cache-Control": "no-store",\n        },\n    )\n\n\n'
anchor = "class HalvaAdminAuth(AuthenticationBackend):\n"

if anchor not in text:
    fail("Не найден класс HalvaAdminAuth.")

text = text.replace(anchor, helper + anchor, 1)

blocked_old = '        if is_blocked:\n            logger.warning(\n                "Заблокирована попытка входа в админку с IP %s. "\n                "Повтор через %s сек.",\n                client_ip,\n                retry_after,\n            )\n            return False\n'
blocked_new = '        if is_blocked:\n            logger.warning(\n                "Заблокирована попытка входа в админку с IP %s. "\n                "Повтор через %s сек.",\n                client_ip,\n                retry_after,\n            )\n            return admin_blocked_response(retry_after)\n'

if blocked_old not in text:
    fail("Не найден блок is_blocked. admin.py отличается от ожидаемой версии.")

text = text.replace(blocked_old, blocked_new, 1)

failure_old = '            if newly_blocked:\n                logger.warning(\n                    "IP %s временно заблокирован после серии "\n                    "неудачных входов в админку. Блокировка: %s сек.",\n                    client_ip,\n                    retry_after,\n                )\n            else:\n                logger.warning(\n                    "Неудачная попытка входа в админку с IP %s",\n                    client_ip,\n                )\n\n            return False\n'
failure_new = '            if newly_blocked:\n                logger.warning(\n                    "IP %s временно заблокирован после серии "\n                    "неудачных входов в админку. Блокировка: %s сек.",\n                    client_ip,\n                    retry_after,\n                )\n                return admin_blocked_response(retry_after)\n\n            logger.warning(\n                "Неудачная попытка входа в админку с IP %s",\n                client_ip,\n            )\n            return False\n'

if failure_old not in text:
    fail("Не найден блок newly_blocked. admin.py отличается от ожидаемой версии.")

text = text.replace(failure_old, failure_new, 1)

ADMIN_PATH.write_text(text, encoding="utf-8")

try:
    compile(text, str(ADMIN_PATH), "exec")
except SyntaxError as exc:
    shutil.copy2(BACKUP_PATH, ADMIN_PATH)
    fail(
        "После изменения возникла синтаксическая ошибка. "
        f"admin.py восстановлен из резервной копии: {exc}"
    )

print("Готово.")
print(f"Изменён: {ADMIN_PATH}")
print(f"Резервная копия: {BACKUP_PATH}")
print()
print("Теперь на 5-й неверной попытке появится")
print("отдельная страница блокировки с таймером.")
