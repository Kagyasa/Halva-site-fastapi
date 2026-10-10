from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from sqladmin import Admin, BaseView, ModelView, expose
from sqladmin.authorization import AuthorizationBackend
from sqladmin.filters import (
    ForeignKeyFilter,
    OperationColumnFilter,
    StaticValuesFilter,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from wtforms import SelectField
from wtforms.validators import NumberRange, Optional

from app.admin_security import HalvaAdminAuth
from app.config import get_settings
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
from app.services.common import format_money, two_months_ago

SNEZHINSK_TZ = timezone(timedelta(hours=5))
logger = logging.getLogger(__name__)
ORDER_STATUS_CHOICES = [
    ("new", "Новая"),
    ("confirmed", "Подтверждена"),
    ("completed", "Выполнена"),
    ("cancelled", "Отменена"),
]
ORDER_STATUS_LABELS = dict(ORDER_STATUS_CHOICES)
DELIVERY_TYPE_LABELS = {
    "pickup": "Самовывоз",
    "delivery": "Доставка",
}


class RussianDateFilter(OperationColumnFilter):
    def get_operation_options(self, column_obj):
        return [
            ("equals", "Равно"),
            ("greater_than", "После"),
            ("less_than", "До"),
        ]


def format_datetime_local(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SNEZHINSK_TZ).strftime("%d.%m.%Y %H:%M")


def format_delivery_type(value: str | None) -> str:
    if not value:
        return "—"
    return DELIVERY_TYPE_LABELS.get(value, value)


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


PRODUCT_CATEGORY_FIELD = "category"
SHOWCASE_LOCATION_FIELD = "pickup_location"
SHOWCASE_PRODUCT_FIELD = "product"


class ThreadedModelView(ModelView):
    async def _run_arbitrary_query(self, statement):
        if self.is_async:
            return await super()._run_arbitrary_query(statement)
        return await run_in_threadpool(self._run_arbitrary_query_sync, statement)


class CategoryAdmin(ThreadedModelView, model=Category):
    name = "Категория"
    name_plural = "Категории"
    icon = "fa-solid fa-tags"
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


class ProductAdmin(ThreadedModelView, model=Product):
    name = "Товар"
    name_plural = "Товары"
    icon = "fa-solid fa-cake-candles"
    form_args = {"price": {"validators": [NumberRange(min=0)]}}
    for field in (
        "weight_min_grams",
        "weight_max_grams",
        "portions_min",
        "portions_max",
    ):
        form_args[field] = {
            "validators": [Optional(), NumberRange(min=1)],
            "render_kw": {"step": "1"},
        }
    for field in (
        "diameter_cm",
        "height_min_cm",
        "height_max_cm",
    ):
        form_args[field] = {
            "validators": [Optional(), NumberRange(min=Decimal("0.01"))],
            "render_kw": {"step": "0.01"},
        }

    async def on_model_change(self, data, model, is_created, request):
        for low, high in (
            ("weight_min_grams", "weight_max_grams"),
            ("portions_min", "portions_max"),
            ("height_min_cm", "height_max_cm"),
        ):
            if data.get(low) is not None and data.get(high) is not None and data[low] > data[high]:
                raise ValueError("Минимальное значение не должно превышать максимальное")

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


class PickupLocationAdmin(ThreadedModelView, model=PickupLocation):
    name = "Точка"
    name_plural = "Точки"
    icon = "fa-solid fa-location-dot"
    column_list = ["name", "address", "phone", "is_active"]
    form_columns = ["name", "address", "phone", "weekday_hours", "weekend_hours", "is_active"]
    column_labels = {
        "name": "Название",
        "address": "Адрес",
        "phone": "Телефон",
        "weekday_hours": "Часы работы, Пн–Пт",
        "weekend_hours": "Часы работы, Сб–Вс",
        "is_active": "Активна",
    }
    can_delete = False


class ShowcaseItemAdmin(ThreadedModelView, model=ShowcaseItem):
    name = "Позиция витрины"
    name_plural = "Техническая витрина"
    icon = "fa-solid fa-store"

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

    @expose("/showcase-manager", methods=["GET", "POST"])
    async def showcase_manager(self, request: Request):
        form = await request.form() if request.method == "POST" else None
        result = await run_in_threadpool(self._load_or_save, request, form)
        if isinstance(result, (HTMLResponse, RedirectResponse)):
            return result
        return await self.templates.TemplateResponse(
            request, "admin/showcase_manager.html", context=result
        )

    def _load_or_save(self, request, form):
        with SessionLocal() as db:
            locations = [
                {"id": p.id, "name": p.name, "address": p.address, "phone": p.phone}
                for p in db.scalars(
                    select(PickupLocation)
                    .where(PickupLocation.is_active.is_(True))
                    .order_by(PickupLocation.address)
                ).all()
            ]
            context = {
                "locations": locations,
                "selected_location": None,
                "product_groups": [],
                "selected_product_ids": set(),
                "csrf_token": request.session["admin_csrf"],
                "saved": request.query_params.get("saved") == "1",
            }
            if not locations:
                return context
            location_id = (
                str(form.get("location_id", ""))
                if form is not None
                else request.query_params.get("location_id")
            )
            valid_ids = {location["id"] for location in locations}
            if form is not None:
                if location_id not in valid_ids:
                    return HTMLResponse("Не удалось определить точку витрины.", status_code=400)
                selected = set(form.getlist("product_ids"))
                active = set(
                    db.scalars(
                        select(Product.id).where(
                            Product.is_active.is_(True),
                            Product.category.has(Category.is_active.is_(True)),
                        )
                    ).all()
                )
                if not selected <= active:
                    return HTMLResponse(
                        "Некоторые товары больше недоступны. Обновите страницу.", status_code=400
                    )
                db.execute(
                    delete(ShowcaseItem).where(ShowcaseItem.pickup_location_id == location_id)
                )
                db.add_all(
                    [
                        ShowcaseItem(pickup_location_id=location_id, product_id=pid)
                        for pid in sorted(selected)
                    ]
                )
                db.commit()
                return RedirectResponse(
                    f"{request.url.path}?location_id={location_id}&saved=1", status_code=303
                )
            if location_id not in valid_ids:
                location_id = locations[0]["id"]
            context["selected_location"] = next(
                location for location in locations if location["id"] == location_id
            )
            context["selected_product_ids"] = set(
                db.scalars(
                    select(ShowcaseItem.product_id).where(
                        ShowcaseItem.pickup_location_id == location_id
                    )
                ).all()
            )
            groups = {}
            for product in db.scalars(
                select(Product)
                .options(selectinload(Product.category))
                .where(
                    Product.is_active.is_(True), Product.category.has(Category.is_active.is_(True))
                )
                .order_by(Product.name)
            ).all():
                groups.setdefault(product.category.name, []).append(
                    {
                        "id": product.id,
                        "name": product.name,
                        "display_name": product.display_name,
                        "price": format_money(product.price),
                        "available_for_order": product.is_available_for_order,
                    }
                )
            context["product_groups"] = [
                {"name": name, "products": products} for name, products in sorted(groups.items())
            ]
            return context


class SiteContactAdmin(ThreadedModelView, model=SiteContact):
    name = "Контакт"
    name_plural = "Контакты"
    icon = "fa-solid fa-address-book"
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


class OrderAdmin(ThreadedModelView, model=Order):
    name = "Заявка"
    name_plural = "Заявки"
    icon = "fa-solid fa-receipt"
    # Показываем связанные позиции каждая с новой строки,
    # а не компактной строкой в скобках.
    show_compact_lists = False
    non_link_related_fields = [Order.items]

    def list_query(self, request: Request):
        return (
            select(Order)
            .where(order_visibility(request))
            .options(selectinload(Order.items), selectinload(Order.pickup_location))
        )

    def details_query(self, request: Request):
        return (
            super()
            .details_query(request)
            .options(selectinload(Order.items), selectinload(Order.pickup_location))
        )

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
    column_details_list = [
        "items",
        "id",
        "customer_name",
        "phone",
        "requested_date",
        "requested_time",
        "delivery_type",
        "pickup_location_id",
        "delivery_address",
        "subtotal",
        "delivery_fee",
        "total",
        "status",
        "staff_notes",
        "created_at",
        "updated_at",
    ]
    column_searchable_list = [Order.customer_name, Order.phone]
    column_filters = [
        StaticValuesFilter(
            "status",
            values=ORDER_STATUS_CHOICES,
            title="Статус",
            parameter_name="status",
        ),
        StaticValuesFilter(
            "delivery_type",
            values=[
                ("pickup", "Самовывоз"),
                ("delivery", "Доставка"),
            ],
            title="Получение",
            parameter_name="delivery_type",
        ),
        ForeignKeyFilter(
            "pickup_location_id",
            "address",
            foreign_model=PickupLocation,
            title="Точка самовывоза",
            parameter_name="pickup_location_id",
        ),
        RussianDateFilter(
            "requested_date",
            title="Дата получения",
            parameter_name="requested_date",
        ),
    ]
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
        "staff_notes": "Уточнения по заказу",
        "created_at": "Создана",
        "updated_at": "Изменена",
        "items": "Позиции",
        "consent_event": "Согласие",
    }
    column_formatters = {
        Order.delivery_type: lambda model, _: format_delivery_type(model.delivery_type),
        Order.pickup_location_id: lambda model, _: (
            model.pickup_location.address if model.pickup_location else "—"
        ),
        Order.total: lambda model, _: format_money(model.total),
        Order.delivery_fee: lambda model, _: format_money(model.delivery_fee),
        Order.status: lambda model, _: ORDER_STATUS_LABELS.get(
            model.status,
            model.status,
        ),
        Order.created_at: lambda model, _: format_datetime_local(model.created_at),
        Order.updated_at: lambda model, _: format_datetime_local(model.updated_at),
        Order.customer_name: lambda model, _: (
            model.customer_name
            if len(model.customer_name) <= 25
            else model.customer_name[:25] + "…"
        ),
    }
    column_formatters_detail = {
        Order.items: lambda model, _: format_order_items(model.items),
        Order.delivery_type: lambda model, _: format_delivery_type(model.delivery_type),
        Order.pickup_location_id: lambda model, _: (
            model.pickup_location.address if model.pickup_location else "—"
        ),
        Order.total: lambda model, _: format_money(model.total),
        Order.subtotal: lambda model, _: format_money(model.subtotal),
        Order.delivery_fee: lambda model, _: format_money(model.delivery_fee),
        Order.status: lambda model, _: ORDER_STATUS_LABELS.get(
            model.status,
            model.status,
        ),
        Order.created_at: lambda model, _: format_datetime_local(model.created_at),
        Order.updated_at: lambda model, _: format_datetime_local(model.updated_at),
    }
    can_create = False
    can_delete = False
    can_edit = True
    form_columns = ["status", "staff_notes"]
    form_overrides = {"status": SelectField}
    form_args = {
        "status": {
            "choices": ORDER_STATUS_CHOICES,
        },
        "staff_notes": {
            "render_kw": {
                "rows": 8,
                "placeholder": (
                    "Например: заказчик поменял вкус, уточнил надпись или время получения."
                ),
            },
        },
    }
    page_size = 50
    page_size_options = [25, 50, 100]


class OrderItemAdmin(ThreadedModelView, model=OrderItem):
    name = "Позиция заказа"
    name_plural = "Позиции заказов"
    icon = "fa-solid fa-list"

    def is_visible(self, request: Request) -> bool:
        return False

    def details_query(self, request):
        return super().details_query(request).join(OrderItem.order).where(order_visibility(request))

    column_details_list = ["order_id", "product_id", "product_name", "price", "quantity"]
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


class PrivacyPolicyAdmin(ThreadedModelView, model=PrivacyPolicyVersion):
    name = "Политика"
    name_plural = "Политика конфиденциальности"
    icon = "fa-solid fa-shield-halved"
    column_list = ["version", "title", "is_active", "published_at", "created_at"]
    column_details_list = "__all__"
    can_create = False
    can_edit = False
    can_delete = False


class ConsentTextAdmin(ThreadedModelView, model=ConsentTextVersion):
    name = "Текст согласия"
    name_plural = "Тексты согласия"
    icon = "fa-solid fa-file-signature"
    column_list = ["version", "is_active", "published_at", "created_at"]
    column_details_list = "__all__"
    can_create = False
    can_edit = False
    can_delete = False


class ConsentEventAdmin(ThreadedModelView, model=ConsentEvent):
    name = "Согласие"
    name_plural = "Согласия"
    icon = "fa-solid fa-check-double"

    def list_query(self, request):
        return select(ConsentEvent).join(ConsentEvent.order).where(order_visibility(request))

    def details_query(self, request):
        return (
            super().details_query(request).join(ConsentEvent.order).where(order_visibility(request))
        )

    column_list = ["order_id", "consent_checked", "consented_at", "ip_address"]
    column_details_list = "__all__"
    column_formatters = {
        ConsentEvent.consented_at: lambda model, _: format_datetime_local(model.consented_at),
    }
    can_create = False
    can_edit = False
    can_delete = False
    can_export = False


def order_visibility(request: Request):
    if request.session.get("halva_admin_role") == "admin":
        return Order.created_at >= two_months_ago()
    return Order.status.not_in(("completed", "cancelled"))


def order_is_visible(request: Request, order: Order) -> bool:
    if request.session.get("halva_admin_role") != "admin":
        return order.status not in {"completed", "cancelled"}
    created = order.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created >= two_months_ago()


class HalvaRoleAuthorization(AuthorizationBackend):
    """
    Разграничение доступа сотрудников к разделам админки.

    admin:
        полный доступ.

    staff:
        каталог, витрины, контакты и заявки.
        Нет доступа к юридическим документам и согласиям.
    """

    ADMIN_ONLY_IDENTITIES = {
        PrivacyPolicyAdmin.identity,
        ConsentTextAdmin.identity,
        ConsentEventAdmin.identity,
    }

    def has_permission(
        self,
        request: Request,
        identity: str,
        action: str,
        obj=None,
    ) -> bool:
        role = request.session.get("halva_admin_role")
        if isinstance(obj, Order) and not order_is_visible(request, obj):
            return False
        if identity == OrderItemAdmin.identity and obj is None:
            return False
        if role == "admin":
            return True
        if role == "staff":
            return identity not in self.ADMIN_ONLY_IDENTITIES
        return False


async def admin_home_redirect():
    return RedirectResponse(
        url="/admin/showcase-manager",
        status_code=307,
    )


def setup_admin(app: FastAPI) -> Admin:
    settings = get_settings()
    authentication_backend = HalvaAdminAuth(settings)
    authorization_backend = HalvaRoleAuthorization()
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
    admin_templates_dir = str(Path(__file__).resolve().parent / "templates")
    admin = Admin(
        app=app,
        engine=engine,
        title="HALVA — Админка",
        base_url="/admin",
        templates_dir=admin_templates_dir,
        authentication_backend=authentication_backend,
        authorization_backend=authorization_backend,
    )
    for route in admin.admin.routes:
        if getattr(route, "name", None) == "logout":
            route.methods = {"POST"}
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
