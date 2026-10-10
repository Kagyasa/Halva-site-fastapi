import calendar
import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

SNEZHINSK_TZ = timezone(timedelta(hours=5))


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return uuid.uuid4().hex


def minimum_order_date():
    return datetime.now(SNEZHINSK_TZ).date() + timedelta(days=1)


def two_months_ago(now: datetime | None = None) -> datetime:
    now = (now or utc_now()).astimezone(SNEZHINSK_TZ)
    month_index = now.year * 12 + now.month - 1 - 2
    year, month = divmod(month_index, 12)
    month += 1
    return now.replace(
        year=year, month=month, day=min(now.day, calendar.monthrange(year, month)[1])
    ).astimezone(UTC)


def format_money(value) -> str:
    if value is None:
        return "—"
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount:.0f} ₽" if amount == amount.to_integral() else f"{amount:.2f} ₽"
