import hmac
import logging
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from app.config import Settings
from app.database import SessionLocal
from app.models.admin_users import AdminUser
from app.services.rate_limit import admin_login_rate_limiter

logger = logging.getLogger(__name__)
password_hasher = PasswordHasher()


def admin_blocked_response(retry_after: int) -> HTMLResponse:

    minutes = max(1, (retry_after + 59) // 60)

    html = f"""<!doctype html>

<html lang="ru">

<head>

  <meta charset="utf-8">

  <meta name="viewport" content="width=device-width, initial-scale=1">

  <title>HALVA — вход временно заблокирован</title>

  <style>

    * {{ box-sizing: border-box; }}

    body {{

      min-height: 100vh;

      margin: 0;

      display: grid;

      place-items: center;

      padding: 24px;

      background:

        radial-gradient(circle at 85% 15%, rgba(253, 201, 227, .72), transparent 36%),

        radial-gradient(circle at 10% 90%, rgba(255, 228, 188, .75), transparent 38%),

        #fff;

      color: #1a1a1a;

      font-family: Inter, Arial, sans-serif;

    }}

    .card {{

      width: min(460px, 100%);

      padding: 38px 34px;

      border: 1px solid rgba(26, 26, 26, .08);

      border-radius: 26px;

      background: rgba(255, 255, 255, .94);

      box-shadow: 0 24px 70px rgba(54, 16, 35, .14);

      text-align: center;

    }}

    .icon {{

      width: 58px;

      height: 58px;

      margin: 0 auto 18px;

      display: grid;

      place-items: center;

      border-radius: 50%;

      background: rgba(223, 19, 117, .10);

      color: #DF1375;

      font-size: 28px;

      font-weight: 700;

    }}

    h1 {{

      margin: 0;

      font-family: Georgia, "Times New Roman", serif;

      font-size: 30px;

      font-weight: 400;

      line-height: 1.15;

    }}

    p {{

      margin: 14px 0 0;

      color: #6f6269;

      font-size: 15px;

      line-height: 1.5;

    }}

    .timer {{

      margin-top: 22px;

      color: #DF1375;

      font-size: 15px;

      font-weight: 600;

    }}

    a {{

      display: inline-flex;

      align-items: center;

      justify-content: center;

      min-width: 180px;

      height: 44px;

      margin-top: 24px;

      padding: 0 22px;

      border-radius: 22px;

      background: #DF1375;

      color: #fff;

      text-decoration: none;

      font-size: 15px;

      font-weight: 600;

    }}

  </style>

</head>

<body>

  <main class="card">

    <div class="icon">!</div>

    <h1>Слишком много попыток входа</h1>

    <p>

      Вход в админку с этого IP временно заблокирован.

      Это защита от подбора пароля.

    </p>

    <div class="timer" id="timer">

      Повторите примерно через {minutes} мин.

    </div>

    <a href="/admin/login">Вернуться ко входу</a>

  </main>

  <script>

    let seconds = {retry_after};

    const timer = document.getElementById("timer");

    const updateTimer = () => {{

      if (seconds <= 0) {{

        timer.textContent = "Блокировка закончилась. Можно попробовать снова.";

        return;

      }}

      const mins = Math.floor(seconds / 60);

      const secs = seconds % 60;

      timer.textContent =

        `До следующей попытки: ${{mins}}:${{String(secs).padStart(2, "0")}}`;

      seconds -= 1;

    }};

    updateTimer();

    setInterval(updateTimer, 1000);

  </script>

</body>

</html>"""

    return HTMLResponse(
        content=html,
        status_code=429,
        headers={
            "Retry-After": str(retry_after),
            "Cache-Control": "no-store",
        },
    )


class AdminCSRFMiddleware:
    """Session token checks for every state-changing SQLAdmin/custom request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        if "/statics/" in request.url.path:
            return await self.app(scope, receive, send)
        token = request.session.setdefault("admin_csrf", secrets.token_urlsafe(32))
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            expected_origin = f"{request.url.scheme}://{request.url.netloc}"
            invalid_origin = origin is not None and origin != expected_origin
            if invalid_origin or request.headers.get("sec-fetch-site") == "cross-site":
                return await HTMLResponse("Недопустимый источник запроса.", status_code=403)(
                    scope, receive, send
                )
            body = await request.body()
            submitted = request.headers.get("x-csrf-token", "")
            if not submitted and request.headers.get("content-type", "").startswith(
                ("application/x-www-form-urlencoded", "multipart/form-data")
            ):
                form = await request.form()
                submitted = str(form.get("csrf_token", ""))
            if not hmac.compare_digest(submitted, token):
                return await HTMLResponse(
                    "Сессия формы устарела. Обновите страницу.", status_code=403
                )(scope, receive, send)
            body_sent = False

            async def replay():
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            return await self.app(scope, replay, send)
        return await self.app(scope, receive, send)


def verify_credentials(username: str, password: str):
    with SessionLocal() as db:
        user = db.scalar(select(AdminUser).where(AdminUser.username == username))
        if user is None or not user.is_active:
            return None
        try:
            password_hasher.verify(user.password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return None
        if password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = password_hasher.hash(password)
            db.commit()
        return user.id, user.username, user.role


def load_user(user_id):
    with SessionLocal() as db:
        user = db.get(AdminUser, user_id)
        return (user.username, user.role) if user and user.is_active else None


class HalvaAdminAuth(AuthenticationBackend):
    def __init__(self, settings: Settings):
        super().__init__(
            secret_key=settings.admin_secret_key,
            session_cookie="halva_admin",
            same_site="lax",
            https_only=settings.admin_session_https_only,
            max_age=60 * 30,
            path="/admin",
        )
        self.middlewares.append(Middleware(AdminCSRFMiddleware))

    async def login(self, request: Request) -> bool | Response:
        form = await request.form()
        username, password = str(form.get("username", "")).strip(), str(form.get("password", ""))
        ip = request.client.host if request.client else "unknown"
        blocked, retry = admin_login_rate_limiter.is_blocked(ip)
        if blocked:
            return admin_blocked_response(retry)
        if len(username) > 100 or len(password) > 1024:
            credentials = None
        else:
            credentials = await run_in_threadpool(verify_credentials, username, password)
        if credentials is None:
            blocked, retry = admin_login_rate_limiter.record_failure(ip)
            return admin_blocked_response(retry) if blocked else False
        admin_login_rate_limiter.reset(ip)
        user_id, username, role = credentials
        request.session.clear()
        request.session.update(
            halva_admin_authenticated=True,
            halva_admin_user_id=user_id,
            halva_admin_username=username,
            halva_admin_role=role,
            admin_csrf=secrets.token_urlsafe(32),
        )
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        if request.session.get("halva_admin_authenticated") is not True:
            return False
        user = await run_in_threadpool(load_user, request.session.get("halva_admin_user_id"))
        if user is None:
            request.session.clear()
            return False
        request.session["halva_admin_username"], request.session["halva_admin_role"] = user
        return True

    async def get_user_id(self, request):
        return request.session.get("halva_admin_user_id")
