import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from html.parser import HTMLParser

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import Order
from app.services.common import two_months_ago, utc_now


def csrf(client, path="/admin/login"):
    response = client.get(path)
    assert response.status_code == 200, response.text
    return re.search(r'name="csrf-token" content="([^"]+)"', response.text)[1]


def login(client, username):
    token = csrf(client)
    response = client.post(
        "/admin/login",
        data=dict(username=username, password="test-password-123", csrf_token=token),
        follow_redirects=False,
    )
    assert response.status_code == 302, response.text
    return csrf(client, "/admin/order/list")


def add_order(db, name, status, created):
    order = Order(
        customer_name=name,
        phone="+79227330330",
        requested_date=utc_now().date(),
        requested_time=datetime.now().time(),
        delivery_type="delivery",
        delivery_address="Тест",
        subtotal=Decimal("100"),
        delivery_fee=0,
        total=Decimal("100"),
        status=status,
        created_at=created,
    )
    db.add(order)
    db.commit()
    return order


def test_admin_and_staff_scopes(client, db_session, users):
    add_order(db_session, "recent-open", "confirmed", utc_now())
    recent_closed = add_order(db_session, "recent-closed", "completed", utc_now())
    old_open = add_order(db_session, "old-open", "new", utc_now() - timedelta(days=100))
    old_closed = add_order(db_session, "old-closed", "cancelled", utc_now() - timedelta(days=100))
    login(client, "staff")
    page = client.get("/admin/order/list").text
    assert "recent-open" in page and "old-open" in page
    assert "recent-closed" not in page and "old-closed" not in page
    assert client.get(f"/admin/order/details/{recent_closed.id}").status_code == 403
    assert client.get(f"/admin/order/edit/{old_closed.id}").status_code == 403
    assert client.get("/admin/consent-event/list").status_code == 403
    assert client.get("/admin/order-item/list").status_code == 403
    login(client, "admin")
    page = client.get("/admin/order/list").text
    assert "recent-open" in page and "recent-closed" in page
    assert "old-open" not in page and "old-closed" not in page
    assert client.get(f"/admin/order/details/{old_open.id}").status_code == 403


@pytest.mark.parametrize("username", ["admin", "staff"])
@pytest.mark.parametrize("delivery_type", ["pickup", "delivery"])
def test_order_details_show_items_and_pickup_location(
    client, users, payload, catalog, username, delivery_type
):
    if delivery_type == "delivery":
        payload.update(
            delivery_type="delivery",
            address="Демонстрационный адрес доставки",
            expected_total="351.50",
        )
    response = client.post("/api/orders/", json=payload)
    assert response.status_code == 200, response.text
    order_id = response.json()["order_id"]
    login(client, username)
    response = client.get(f"/admin/order/details/{order_id}")
    assert response.status_code == 200, response.text
    assert (
        catalog[1].address if delivery_type == "pickup" else payload["address"]
    ) in response.text
    assert payload["expected_total"] in response.text
    assert "Тестовый десерт" in response.text


def test_csrf_all_admin_forms(client, db_session, users):
    order = add_order(db_session, "csrf-order", "new", utc_now())
    token = login(client, "staff")
    url = f"/admin/order/edit/{order.id}"
    data = dict(status="cancelled", staff_notes="test", save="Save")
    assert client.post(url, data=data, follow_redirects=False).status_code == 403
    data["csrf_token"] = token
    assert (
        client.post(
            url, data=data, headers={"Origin": "https://attacker.example"}, follow_redirects=False
        ).status_code
        == 403
    )
    response = client.post(
        url, data=data, headers={"Origin": "http://testserver"}, follow_redirects=False
    )
    assert response.status_code in (302, 303), response.text
    db_session.refresh(order)
    assert order.status == "cancelled"
    assert client.post("/admin/showcase-manager", data={}).status_code == 403


def test_no_arbitrary_100_order_limit(client, db_session, users):
    for index in range(105):
        add_order(db_session, f"order-{index}", "new", utc_now())
    login(client, "admin")
    page = client.get("/admin/order/list?pageSize=100&page=2").text
    assert "of 105" in page or "из 105" in page


def test_production_rejects_public_secret():
    with pytest.raises(ValidationError, match="ADMIN_SECRET_KEY"):
        Settings(
            _env_file=None,
            database_url=None,
            app_env="production",
            admin_secret_key="change_me_to_a_long_random_secret",
            admin_session_https_only=True,
            db_password="a-real-password",
            allowed_hosts=["example.com"],
        )


@pytest.mark.parametrize("username", ["admin", "staff"])
@pytest.mark.parametrize("mode", ["create", "edit"])
def test_product_numeric_fields_accept_integer_weight(client, users, catalog, username, mode):
    login(client, username)
    product = catalog[0]
    url = "/admin/product/create" if mode == "create" else f"/admin/product/edit/{product.id}"
    response = client.get(url)
    assert response.status_code == 200

    class Inputs(HTMLParser):
        def __init__(self):
            super().__init__()
            self.fields = {}

        def handle_starttag(self, tag, attrs):
            if tag == "input":
                attributes = dict(attrs)
                self.fields[attributes.get("name")] = attributes

    inputs = Inputs()
    inputs.feed(response.text)
    for name, value in (
        ("weight_min_grams", "900"),
        ("weight_max_grams", "1000"),
        ("portions_min", "2"),
        ("portions_max", "3"),
        ("diameter_cm", "18.50"),
        ("height_min_cm", "5.25"),
        ("height_max_cm", "6.00"),
    ):
        field = inputs.fields[name]
        assert field["type"] == "number"
        minimum = Decimal(field["min"])
        step = Decimal(field.get("step", "1"))
        # Browser step validity is measured from min, not necessarily from zero.
        assert Decimal(value) >= minimum
        assert (Decimal(value) - minimum) % step == 0, (name, field)


def test_calendar_month_cutoff():
    assert two_months_ago(datetime(2026, 4, 30, 10, tzinfo=UTC)) == datetime(
        2026, 2, 28, 10, tzinfo=UTC
    )


def test_logout_requires_post_and_csrf(client, users):
    token = login(client, "admin")
    assert client.get("/admin/logout").status_code == 405
    assert client.post("/admin/logout", data={}).status_code == 403
    assert (
        client.post("/admin/logout", data={"csrf_token": token}, follow_redirects=False).status_code
        == 302
    )
    assert client.get("/admin/order/list", follow_redirects=False).status_code == 302


@pytest.mark.parametrize("username", ["admin", "staff"])
def test_logout_button_submits_native_form_without_javascript(client, users, username):
    login(client, username)
    html = client.get("/admin/order/list").text
    form = re.search(
        r'<form\b([^>]*action="([^"]*/admin/logout)"[^>]*)>(.*?)</form>',
        html,
        re.DOTALL,
    )
    assert form is not None
    assert 'method="post"' in form[1]
    assert "Выйти" in form[3]
    token = re.search(r'name="csrf_token" value="([^"]+)"', form[3])[1]
    response = client.post(form[2], data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 302
    assert client.get("/admin/order/list", follow_redirects=False).status_code == 302
