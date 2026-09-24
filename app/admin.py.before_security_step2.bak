from __future__ import annotations

import hmac
import secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from sqlalchemy import delete, select
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqladmin import Admin, BaseView, ModelView, expose
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from wtforms import SelectField

from app.database import SessionLocal, engine
from app.models.catalog import (
    Category,
    PickupLocation,
    Product,
    ShowcaseItem,
    SiteContact,
)
from app.models.orders import (
    ConsentEvent,
    ConsentTextVersion,
    Order,
    OrderItem,
    PrivacyPolicyVersion,
)

SNEZHINSK_TZ = timezone(timedelta(hours=5))

ORDER_STATUS_CHOICES = [
    ("new", "Новая"),
    ("confirmed", "Подтверждена"),
    ("completed", "Выполнена"),
    ("cancelled", "Отменена"),
]
ORDER_STATUS_LABELS = dict(ORDER_STATUS_CHOICES)


class AdminSettings(BaseSettings):
    admin_username: str
    admin_password: str
    admin_secret_key: str
    admin_session_https_only: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class HalvaAdminAuth(AuthenticationBackend):
    def __init__(self, settings: AdminSettings):
        self.settings = settings
        super().__init__(
            secret_key=settings.admin_secret_key,
            session_cookie="halva_admin",
            same_site="lax",
            https_only=settings.admin_session_https_only,
            max_age=60 * 60 * 8,
        )

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        if not (
            hmac.compare_digest(username, self.settings.admin_username)
            and hmac.compare_digest(password, self.settings.admin_password)
        ):
            return False

        request.session.clear()
        request.session.update(
            {
                "halva_admin_authenticated": True,
                "halva_admin_username": self.settings.admin_username,
            }
        )
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("halva_admin_authenticated") is True


def format_datetime_local(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(SNEZHINSK_TZ).strftime("%d.%m.%Y %H:%M")


def format_money(value) -> str:
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{int(amount)} ₽" if amount.is_integer() else f"{amount:.2f} ₽"


def format_order_items(items) -> list[str]:
    """One formatted label for every related OrderItem.

    SQLAdmin treats relationships as lists and zips the original items
    with this formatted list. Returning HTML/string here makes SQLAdmin
    iterate over characters, which caused the (<) (d) (i) (v) output.
    """
    result = []

    for item in items or []:
        line_total = item.price * item.quantity
        result.append(
            f"{item.product_name} × {item.quantity} — "
            f"{format_money(item.price)} / шт. = "
            f"{format_money(line_total)}"
        )

    return result



Category.__str__ = lambda self: self.name  # type: ignore[method-assign]
Product.__str__ = lambda self: self.name  # type: ignore[method-assign]
PickupLocation.__str__ = lambda self: f"{self.name} — {self.address}"  # type: ignore[method-assign]
OrderItem.__str__ = lambda self: f"{self.product_name} × {self.quantity}"  # type: ignore[method-assign]

PRODUCT_CATEGORY_FIELD = "category" if hasattr(Product, "category") else "category_id"
SHOWCASE_LOCATION_FIELD = (
    "pickup_location"
    if hasattr(ShowcaseItem, "pickup_location")
    else "pickup_location_id"
)
SHOWCASE_PRODUCT_FIELD = (
    "product"
    if hasattr(ShowcaseItem, "product")
    else "product_id"
)


class CategoryAdmin(ModelView, model=Category):
    name = "Категория"
    name_plural = "Категории"
    icon = "fa-solid fa-tags"
    category = "Каталог"

    column_list = ["name", "slug", "is_active", "updated_at"]
    column_searchable_list = [Category.name, Category.slug]
    form_columns = ["name", "slug", "is_active"]
    column_labels = {
        "name": "Название",
        "slug": "Slug",
        "is_active": "Активна",
        "created_at": "Создана",
        "updated_at": "Изменена",
    }
    can_delete = False


class ProductAdmin(ModelView, model=Product):
    name = "Товар"
    name_plural = "Товары"
    icon = "fa-solid fa-cake-candles"
    category = "Каталог"

    column_list = [
        "name",
        "display_name",
        "price",
        PRODUCT_CATEGORY_FIELD,
        "is_active",
        "is_available_for_order",
        "updated_at",
    ]
    column_searchable_list = [Product.name, Product.slug]
    column_sortable_list = [Product.name, Product.price, Product.updated_at]
    form_columns = [
        "name",
        "display_name",
        "slug",
        "price",
        PRODUCT_CATEGORY_FIELD,
        "weight_min_grams",
        "weight_max_grams",
        "portions_min",
        "portions_max",
        "diameter_cm",
        "height_min_cm",
        "height_max_cm",
        "size",
        "image_url",
        "vk_url",
        "is_active",
        "is_available_for_order",
    ]
    column_labels = {
        "name": "Полное название",
        "display_name": "Название в карусели",
        "slug": "Slug",
        "price": "Цена",
        "category": "Категория",
        "category_id": "Категория",
        "weight_min_grams": "Вес от, г",
        "weight_max_grams": "Вес до, г",
        "portions_min": "Порций от",
        "portions_max": "Порций до",
        "diameter_cm": "Диаметр, см",
        "height_min_cm": "Высота от, см",
        "height_max_cm": "Высота до, см",
        "size": "Размер",
        "image_url": "Фото",
        "vk_url": "Ссылка VK",
        "is_active": "Активен",
        "is_available_for_order": "Доступен для заказа",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    column_formatters = {
        Product.price: lambda model, _: format_money(model.price),
        Product.created_at: lambda model, _: format_datetime_local(model.created_at),
        Product.updated_at: lambda model, _: format_datetime_local(model.updated_at),
    }
    can_delete = False
    page_size = 50
    page_size_options = [25, 50, 100]


class PickupLocationAdmin(ModelView, model=PickupLocation):
    name = "Точка"
    name_plural = "Точки"
    icon = "fa-solid fa-location-dot"
    category = "Витрины"

    column_list = ["name", "address", "phone", "is_active"]
    form_columns = ["name", "address", "phone", "is_active"]
    column_labels = {
        "name": "Название",
        "address": "Адрес",
        "phone": "Телефон",
        "is_active": "Активна",
    }
    can_delete = False


class ShowcaseItemAdmin(ModelView, model=ShowcaseItem):
    name = "Позиция витрины"
    name_plural = "Техническая витрина"
    icon = "fa-solid fa-store"
    category = "Витрины"

    def is_visible(self, request: Request) -> bool:
        return False

    column_list = [
        SHOWCASE_LOCATION_FIELD,
        SHOWCASE_PRODUCT_FIELD,
        "updated_at",
    ]
    form_columns = [
        SHOWCASE_LOCATION_FIELD,
        SHOWCASE_PRODUCT_FIELD,
    ]
    column_labels = {
        "pickup_location": "Точка",
        "pickup_location_id": "Точка",
        "product": "Товар",
        "product_id": "Товар",
        "created_at": "Добавлено",
        "updated_at": "Изменено",
    }
    column_default_sort = ("updated_at", True)
    page_size = 50


class ShowcaseManagerAdmin(BaseView):
    name = "Управление витриной"
    icon = "fa-solid fa-store"
    category = "Витрины"

    @expose("/showcase-manager", methods=["GET", "POST"])
    async def showcase_manager(self, request: Request):
        csrf_token = request.session.get("showcase_manager_csrf")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            request.session["showcase_manager_csrf"] = csrf_token

        with SessionLocal() as db:
            locations_db = db.scalars(
                select(PickupLocation)
                .where(PickupLocation.is_active.is_(True))
                .order_by(PickupLocation.address)
            ).all()

            locations = [
                {
                    "id": location.id,
                    "name": location.name,
                    "address": location.address,
                    "phone": location.phone,
                }
                for location in locations_db
            ]

            if not locations:
                return await self.templates.TemplateResponse(
                    request,
                    "admin/showcase_manager.html",
                    context={
                        "locations": [],
                        "selected_location": None,
                        "product_groups": [],
                        "selected_product_ids": set(),
                        "csrf_token": csrf_token,
                        "saved": False,
                    },
                )

            requested_location_id = (
                request.query_params.get("location_id")
                if request.method == "GET"
                else None
            )

            if request.method == "POST":
                form = await request.form()

                submitted_csrf = str(form.get("csrf_token", ""))
                if not hmac.compare_digest(submitted_csrf, csrf_token):
                    raise ValueError(
                        "Сессия формы устарела. Обновите страницу и попробуйте ещё раз."
                    )

                requested_location_id = str(form.get("location_id", ""))
                selected_product_ids = {
                    str(product_id)
                    for product_id in form.getlist("product_ids")
                }

                valid_location_ids = {
                    location["id"]
                    for location in locations
                }

                if requested_location_id not in valid_location_ids:
                    raise ValueError("Не удалось определить точку витрины.")

                active_product_ids = set(
                    db.scalars(
                        select(Product.id).where(
                            Product.is_active.is_(True)
                        )
                    ).all()
                )

                selected_product_ids &= active_product_ids

                db.execute(
                    delete(ShowcaseItem).where(
                        ShowcaseItem.pickup_location_id
                        == requested_location_id
                    )
                )

                for product_id in sorted(selected_product_ids):
                    db.add(
                        ShowcaseItem(
                            pickup_location_id=requested_location_id,
                            product_id=product_id,
                        )
                    )

                db.commit()

                return RedirectResponse(
                    url=(
                        f"{request.url.path}"
                        f"?location_id={requested_location_id}&saved=1"
                    ),
                    status_code=303,
                )

            valid_location_ids = {
                location["id"]
                for location in locations
            }

            if requested_location_id not in valid_location_ids:
                requested_location_id = locations[0]["id"]

            selected_location = next(
                location
                for location in locations
                if location["id"] == requested_location_id
            )

            selected_product_ids = set(
                db.scalars(
                    select(ShowcaseItem.product_id).where(
                        ShowcaseItem.pickup_location_id
                        == requested_location_id
                    )
                ).all()
            )

            products_db = db.scalars(
                select(Product)
                .where(Product.is_active.is_(True))
                .order_by(Product.name)
            ).all()

            grouped: dict[str, list[dict]] = {}

            for product in products_db:
                category_name = (
                    product.category.name
                    if getattr(product, "category", None)
                    else "Без категории"
                )

                grouped.setdefault(category_name, []).append(
                    {
                        "id": product.id,
                        "name": product.name,
                        "display_name": product.display_name,
                        "price": format_money(product.price),
                        "available_for_order": product.is_available_for_order,
                    }
                )

            product_groups = [
                {
                    "name": category_name,
                    "products": products,
                }
                for category_name, products in sorted(
                    grouped.items(),
                    key=lambda item: item[0].casefold(),
                )
            ]

        return await self.templates.TemplateResponse(
            request,
            "admin/showcase_manager.html",
            context={
                "locations": locations,
                "selected_location": selected_location,
                "product_groups": product_groups,
                "selected_product_ids": selected_product_ids,
                "csrf_token": csrf_token,
                "saved": request.query_params.get("saved") == "1",
            },
        )


class SiteContactAdmin(ModelView, model=SiteContact):
    name = "Контакт"
    name_plural = "Контакты"
    icon = "fa-solid fa-address-book"
    category = "Сайт"

    column_list = ["type", "title", "value", "is_active", "updated_at"]
    column_searchable_list = [
        SiteContact.type,
        SiteContact.title,
        SiteContact.value,
    ]
    form_columns = ["type", "title", "value", "is_active"]
    column_labels = {
        "type": "Тип",
        "title": "Подпись",
        "value": "Значение / ссылка",
        "is_active": "Активен",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    can_delete = False


class OrderAdmin(ModelView, model=Order):
    name = "Заявка"
    name_plural = "Заявки"
    icon = "fa-solid fa-receipt"
    category = "Заказы"

    # Показываем связанные позиции каждая с новой строки,
    # а не компактной строкой в скобках.
    show_compact_lists = False

    column_list = [
        "customer_name",
        "phone",
        "requested_date",
        "requested_time",
        "delivery_type",
        "total",
        "status",
        "created_at",
    ]
    column_details_list = "__all__"
    column_searchable_list = [Order.customer_name, Order.phone]
    column_sortable_list = [
        Order.requested_date,
        Order.total,
        Order.status,
        Order.created_at,
    ]
    column_default_sort = (Order.created_at, True)
    column_labels = {
        "id": "ID",
        "customer_name": "Клиент",
        "phone": "Телефон",
        "requested_date": "Дата получения",
        "requested_time": "Время получения",
        "delivery_type": "Получение",
        "pickup_location_id": "Точка самовывоза",
        "delivery_address": "Адрес доставки",
        "subtotal": "Товары",
        "delivery_fee": "Доставка",
        "total": "Итого",
        "status": "Статус",
        "created_at": "Создана",
        "updated_at": "Изменена",
        "items": "Позиции",
        "consent_event": "Согласие",
    }
    column_formatters = {
        Order.total: lambda model, _: format_money(model.total),
        Order.delivery_fee: lambda model, _: format_money(model.delivery_fee),
        Order.status: lambda model, _: ORDER_STATUS_LABELS.get(model.status, model.status),
        Order.created_at: lambda model, _: format_datetime_local(model.created_at),
        Order.updated_at: lambda model, _: format_datetime_local(model.updated_at),
    }

    column_formatters_detail = {
        Order.items: lambda model, _: format_order_items(model.items),
        Order.total: lambda model, _: format_money(model.total),
        Order.subtotal: lambda model, _: format_money(model.subtotal),
        Order.delivery_fee: lambda model, _: format_money(model.delivery_fee),
        Order.status: lambda model, _: ORDER_STATUS_LABELS.get(model.status, model.status),
        Order.created_at: lambda model, _: format_datetime_local(model.created_at),
        Order.updated_at: lambda model, _: format_datetime_local(model.updated_at),
    }
    can_create = False
    can_delete = False
    can_edit = True
    form_columns = ["status"]
    form_overrides = {"status": SelectField}
    form_args = {
        "status": {
            "choices": ORDER_STATUS_CHOICES,
        }
    }
    page_size = 50
    page_size_options = [25, 50, 100]


class OrderItemAdmin(ModelView, model=OrderItem):
    name = "Позиция заказа"
    name_plural = "Позиции заказов"
    icon = "fa-solid fa-list"
    category = "Заказы"

    def is_visible(self, request: Request) -> bool:
        return False

    column_list = ["order_id", "product_name", "price", "quantity"]
    column_searchable_list = [OrderItem.product_name]
    column_labels = {
        "order_id": "ID заявки",
        "product_id": "ID товара",
        "product_name": "Товар",
        "price": "Цена за штуку",
        "quantity": "Количество",
    }
    column_formatters = {
        OrderItem.price: lambda model, _: format_money(model.price),
    }
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


class PrivacyPolicyAdmin(ModelView, model=PrivacyPolicyVersion):
    name = "Политика"
    name_plural = "Политика конфиденциальности"
    icon = "fa-solid fa-shield-halved"
    category = "Документы"

    column_list = ["version", "title", "is_active", "published_at", "created_at"]
    column_details_list = "__all__"
    can_create = False
    can_edit = False
    can_delete = False


class ConsentTextAdmin(ModelView, model=ConsentTextVersion):
    name = "Текст согласия"
    name_plural = "Тексты согласия"
    icon = "fa-solid fa-file-signature"
    category = "Документы"

    column_list = ["version", "is_active", "published_at", "created_at"]
    column_details_list = "__all__"
    can_create = False
    can_edit = False
    can_delete = False


class ConsentEventAdmin(ModelView, model=ConsentEvent):
    name = "Согласие"
    name_plural = "Согласия"
    icon = "fa-solid fa-check-double"
    category = "Система"

    column_list = ["order_id", "consent_checked", "consented_at", "ip_address"]
    column_details_list = "__all__"
    column_formatters = {
        ConsentEvent.consented_at: lambda model, _: format_datetime_local(
            model.consented_at
        ),
    }
    can_create = False
    can_edit = False
    can_delete = False
    can_export = False



async def admin_home_redirect():
    return RedirectResponse(
        url="/admin/showcase-manager",
        status_code=307,
    )


def setup_admin(app: FastAPI) -> Admin:
    settings = AdminSettings()
    authentication_backend = HalvaAdminAuth(settings)

    # При переходе на /admin сразу открываем управление витриной.
    # Маршруты добавляются до SQLAdmin, поэтому остальные страницы
    # /admin/login, /admin/... продолжают работать как обычно.
    app.add_api_route(
        "/admin",
        admin_home_redirect,
        methods=["GET"],
        include_in_schema=False,
        name="halva_admin_home",
    )
    app.add_api_route(
        "/admin/",
        admin_home_redirect,
        methods=["GET"],
        include_in_schema=False,
        name="halva_admin_home_slash",
    )

    admin_templates_dir = str(
        Path(__file__).resolve().parent / "templates"
    )

    admin = Admin(
        app=app,
        engine=engine,
        title="HALVA — Админка",
        base_url="/admin",
        templates_dir=admin_templates_dir,
        authentication_backend=authentication_backend,
    )

    admin.add_view(CategoryAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(PickupLocationAdmin)
    admin.add_view(ShowcaseManagerAdmin)
    admin.add_view(ShowcaseItemAdmin)
    admin.add_view(SiteContactAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(PrivacyPolicyAdmin)
    admin.add_view(ConsentTextAdmin)
    admin.add_view(ConsentEventAdmin)

    return admin
