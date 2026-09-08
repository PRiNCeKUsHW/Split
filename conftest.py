"""Shared fixtures: a four-person flat, which is what the app is actually for."""

import datetime as dt
from decimal import Decimal

import pytest


@pytest.fixture
def anuj(django_user_model):
    return django_user_model.objects.create_user(
        username="anuj", password="x", display_name="Anuj Kush",
        upi_id="anuj@okhdfcbank", joined_on=dt.date(2026, 1, 1),
    )


@pytest.fixture
def priya(django_user_model):
    return django_user_model.objects.create_user(
        username="priya", password="x", display_name="Priya Sharma",
        upi_id="priya@okaxis", joined_on=dt.date(2026, 1, 1),
    )


@pytest.fixture
def rohit(django_user_model):
    return django_user_model.objects.create_user(
        username="rohit", password="x", display_name="Rohit Nair",
        joined_on=dt.date(2026, 1, 1),
    )


@pytest.fixture
def dev(django_user_model):
    """Moved in partway through September — the move-in proration case."""
    return django_user_model.objects.create_user(
        username="dev", password="x", display_name="Dev Menon",
        joined_on=dt.date(2026, 9, 11),
    )


@pytest.fixture
def flat(anuj, priya, rohit):
    return [anuj, priya, rohit]


@pytest.fixture
def groceries(db):
    from expenses.models import Category

    category, _ = Category.objects.update_or_create(
        name="Groceries",
        defaults=dict(icon="basket", color="#0b7a4b",
                      prorate_by_tenancy=True, prorate_by_presence=True),
    )
    return category


@pytest.fixture
def rent(db):
    from expenses.models import Category

    category, _ = Category.objects.update_or_create(
        name="Rent",
        defaults=dict(icon="home", color="#3a34c9", is_recurring_by_default=True,
                      prorate_by_tenancy=True, prorate_by_presence=False),
    )
    return category


@pytest.fixture
def one_off(db):
    from expenses.models import Category

    return Category.objects.create(name="One-off", icon="tag", color="#c42b4b")


@pytest.fixture
def make_expense(db):
    """Build an expense without shares; call rebuild_shares to populate them."""
    from expenses.models import Expense

    def _make(*, category, paid_by, amount="100.00", date=dt.date(2026, 9, 15), **kwargs):
        return Expense.objects.create(
            description=kwargs.pop("description", "Test expense"),
            amount=None if amount is None else Decimal(amount),
            category=category,
            paid_by=paid_by,
            created_by=kwargs.pop("created_by", paid_by),
            date=date,
            **kwargs,
        )

    return _make
