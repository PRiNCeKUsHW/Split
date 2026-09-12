import json
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from expenses.models import Category, Expense, ExpenseShare
from settlements.models import Settlement

User = get_user_model()


@pytest.fixture
def flatmates(db):
    u1 = User.objects.create_user(username="anuj", password="password123", display_name="Anuj")
    u2 = User.objects.create_user(username="priya", password="password123", display_name="Priya")
    u3 = User.objects.create_user(username="rohit", password="password123", display_name="Rohit")
    cat, _ = Category.objects.get_or_create(
        name="Groceries",
        defaults={"prorate_by_tenancy": True, "prorate_by_presence": True},
    )
    return {"u1": u1, "u2": u2, "u3": u3, "cat": cat}


@pytest.mark.django_db
def test_api_auth_and_me(client, flatmates):
    u1 = flatmates["u1"]

    # Not logged in
    resp = client.get(reverse("api:me"))
    assert resp.status_code == 401

    # Login
    resp = client.post(
        reverse("api:login"),
        data=json.dumps({"username": "anuj", "password": "password123"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["user"]["username"] == "anuj"

    # Me
    resp = client.get(reverse("api:me"))
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True

    # Logout
    resp = client.post(reverse("api:logout"))
    assert resp.status_code == 200
    resp = client.get(reverse("api:me"))
    assert resp.status_code == 401


@pytest.mark.django_db
def test_api_dashboard_and_expenses(client, flatmates):
    u1, u2, u3, cat = flatmates["u1"], flatmates["u2"], flatmates["u3"], flatmates["cat"]
    client.force_login(u1)

    # Categories and Members
    resp = client.get(reverse("api:categories"))
    assert resp.status_code == 200
    assert len(resp.json()["categories"]) >= 1

    resp = client.get(reverse("api:members"))
    assert resp.status_code == 200
    assert len(resp.json()["members"]) == 3

    # Preview split
    resp = client.post(
        reverse("api:expense_preview"),
        data=json.dumps({
            "amount": "300.00",
            "participants": [u1.pk, u2.pk, u3.pk],
            "split_type": "EQUAL",
            "paid_by": u1.pk,
            "category": cat.pk,
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    shares = resp.json()["shares"]
    assert len(shares) == 3
    assert sum(Decimal(s["amount_owed"]) for s in shares) == Decimal("300.00")

    # Create expense
    resp = client.post(
        reverse("api:expense_create"),
        data=json.dumps({
            "description": "Vegetables",
            "amount": "300.00",
            "category": cat.pk,
            "paid_by": u1.pk,
            "date": "2026-09-08",
            "split_type": "EQUAL",
            "participants": [u1.pk, u2.pk, u3.pk],
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    exp_id = resp.json()["id"]

    # List expenses
    resp = client.get(reverse("api:expense_list"))
    assert resp.status_code == 200
    expenses = resp.json()["expenses"]
    assert len(expenses) == 1
    assert expenses[0]["description"] == "Vegetables"

    # Detail expense
    resp = client.get(reverse("api:expense_detail", kwargs={"pk": exp_id}))
    assert resp.status_code == 200
    detail = resp.json()
    assert len(detail["shares"]) == 3

    # Dashboard
    resp = client.get(reverse("api:dashboard"))
    assert resp.status_code == 200
    dash = resp.json()
    # u1 paid 300, owes 100, so net is +200
    assert Decimal(dash["my_balance"]) == Decimal("200.00")
    assert len(dash["transfers"]) == 2  # u2 and u3 pay u1


@pytest.mark.django_db
def test_api_settlements(client, flatmates):
    u1, u2 = flatmates["u1"], flatmates["u2"]
    client.force_login(u2)

    # u2 records payment to u1
    resp = client.post(
        reverse("api:settlement_create"),
        data=json.dumps({
            "to_user": u1.pk,
            "amount": "100.00",
            "method": "UPI",
            "note": "test settle",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    settle_id = resp.json()["id"]

    # Check overview for u1
    client.force_login(u1)
    resp = client.get(reverse("api:settlements_overview"))
    assert resp.status_code == 200
    awaiting = resp.json()["awaiting_confirmation"]
    assert len(awaiting) == 1
    assert awaiting[0]["id"] == settle_id

    # Confirm settlement
    resp = client.post(reverse("api:settlement_confirm", kwargs={"pk": settle_id}))
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"

    # Confirm settlement status in DB
    settle = Settlement.objects.get(pk=settle_id)
    assert settle.status == Settlement.Status.CONFIRMED


@pytest.mark.django_db
def test_api_members_create(client, flatmates):
    u1 = flatmates["u1"]
    client.force_login(u1)

    # Missing username
    resp = client.post(reverse("api:member_create"), data=json.dumps({"display_name": "Test"}), content_type="application/json")
    assert resp.status_code == 400

    # Successful creation
    resp = client.post(
        reverse("api:member_create"),
        data=json.dumps({
            "username": "vikram",
            "display_name": "Vikram Seth",
            "upi_id": "vikram@upi",
            "phone": "9876543210",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["member"]["username"] == "vikram"
    assert "invite_link" in data

    # Duplicate username check
    resp = client.post(
        reverse("api:member_create"),
        data=json.dumps({
            "username": "vikram",
            "display_name": "Vikram 2",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_api_profile_update(client, flatmates):
    u1, u2 = flatmates["u1"], flatmates["u2"]
    client.force_login(u1)

    # Update own profile
    resp = client.post(
        reverse("api:profile_update"),
        data=json.dumps({
            "display_name": "Anuj Updated",
            "phone": "9998887776",
            "upi_id": "anuj@okhdfc",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["user"]["display_name"] == "Anuj Updated"
    assert data["user"]["phone"] == "9998887776"
    assert data["user"]["upi_id"] == "anuj@okhdfc"

    u1.refresh_from_db()
    assert u1.display_name == "Anuj Updated"

    # Non-staff cannot edit another member's profile
    resp = client.post(
        reverse("api:member_update", args=[u2.pk]),
        data=json.dumps({"display_name": "Hacked"}),
        content_type="application/json",
    )
    assert resp.status_code == 403

    # User can edit own profile via member_update
    resp = client.post(
        reverse("api:member_update", args=[u1.pk]),
        data=json.dumps({"display_name": "Anuj Second"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    u1.refresh_from_db()
    assert u1.display_name == "Anuj Second"


