"""Every screen renders for a logged-in flatmate.

A broad, shallow sweep. It will not catch a wrong number, but it catches the
template typo that takes a whole screen down, which unit tests never see.
"""

import datetime as dt
from decimal import Decimal

import pytest
from django.urls import reverse

from expenses.services.shares import rebuild_shares
from settlements.models import Settlement

pytestmark = pytest.mark.django_db


@pytest.fixture
def populated(groceries, rent, anuj, priya, rohit, make_expense):
    """A flat with a bit of history, so screens have something to draw."""
    first = make_expense(
        category=groceries, paid_by=anuj, amount="1200.00", description="Big Bazaar",
        period_start=dt.date(2026, 9, 1), period_end=dt.date(2026, 9, 30),
    )
    rebuild_shares(first, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    second = make_expense(
        category=rent, paid_by=priya, amount="30000.00", description="September rent"
    )
    rebuild_shares(second, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    draft = make_expense(
        category=rent, paid_by=anuj, amount=None, description="Electricity"
    )

    Settlement.objects.create(from_user=rohit, to_user=priya, amount=Decimal("500.00"))
    return {"expense": first, "draft": draft}


@pytest.fixture
def logged_in(client, anuj):
    client.force_login(anuj)
    return client


SIMPLE_SCREENS = [
    ("core:dashboard", {}),
    ("core:balances", {}),
    ("core:summary", {}),
    ("core:audit", {}),
    ("expenses:list", {}),
    ("expenses:add", {}),
    ("settlements:settle_up", {}),
    ("settlements:pending", {}),
    ("settlements:history", {}),
    ("recurring:list", {}),
    ("recurring:add", {}),
    ("accounts:away", {}),
    ("accounts:members", {}),
    ("accounts:profile", {}),
]


@pytest.mark.parametrize("name,kwargs", SIMPLE_SCREENS)
def test_screen_renders(logged_in, populated, name, kwargs):
    response = logged_in.get(reverse(name, kwargs=kwargs))

    assert response.status_code == 200, f"{name} returned {response.status_code}"


@pytest.mark.parametrize("name,kwargs", SIMPLE_SCREENS)
def test_screen_renders_for_an_empty_flat(logged_in, name, kwargs):
    """Empty states matter: this is what the app looks like on day one."""
    response = logged_in.get(reverse(name, kwargs=kwargs))

    assert response.status_code == 200, f"{name} broke with no data"


def test_expense_detail_renders(logged_in, populated):
    response = logged_in.get(reverse("expenses:detail", args=[populated["expense"].pk]))

    assert response.status_code == 200
    assert b"Big Bazaar" in response.content


def test_expense_detail_shows_the_full_split(logged_in, populated):
    response = logged_in.get(reverse("expenses:detail", args=[populated["expense"].pk]))
    body = response.content.decode()

    assert "The split" in body
    assert "400.00" in body  # 1200 / 3


def test_expense_edit_renders(logged_in, populated):
    response = logged_in.get(reverse("expenses:edit", args=[populated["expense"].pk]))

    assert response.status_code == 200


def test_a_draft_offers_an_amount_box(logged_in, populated):
    response = logged_in.get(reverse("expenses:detail", args=[populated["draft"].pk]))

    assert b"needs an amount" in response.content


def test_record_payment_screen_renders(logged_in, populated, priya):
    response = logged_in.get(reverse("settlements:record", args=[priya.pk]))

    assert response.status_code == 200
    assert b"upi://pay" in response.content


def test_the_qr_screen_renders_an_image(logged_in, priya):
    response = logged_in.get(reverse("settlements:qr", args=[priya.pk]) + "?amount=250")

    assert response.status_code == 200
    assert b"data:image/png;base64," in response.content


def test_the_summary_exports_csv(logged_in, populated):
    response = logged_in.get(reverse("core:summary_csv") + "?month=2026-09")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]

    body = response.content.decode("utf-8-sig")
    assert "Big Bazaar" in body
    assert "Anuj Kush" in body


def test_the_csv_has_one_row_per_share(logged_in, populated):
    response = logged_in.get(reverse("core:summary_csv") + "?month=2026-09")
    lines = [line for line in response.content.decode("utf-8-sig").splitlines() if line]

    # header + 3 shares for groceries + 3 for rent
    assert len(lines) == 7


def test_every_screen_needs_a_login(client, populated):
    for name, kwargs in SIMPLE_SCREENS:
        response = client.get(reverse(name, kwargs=kwargs))
        assert response.status_code == 302, f"{name} was reachable anonymously"
        assert "/accounts/login/" in response["Location"]
