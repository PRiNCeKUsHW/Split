"""seed_demo --clear must empty the flat without touching the app's own data."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from accounts.models import AwayPeriod
from core.models import AuditLog, MonthClose
from expenses.models import Category, Comment, Expense, ExpenseShare
from recurring.models import RecurringExpense
from settlements.models import Settlement

pytestmark = pytest.mark.django_db
User = get_user_model()


def _seed():
    call_command("seed_demo", "--month=2026-09", stdout=StringIO())


def _clear():
    out = StringIO()
    call_command("seed_demo", "--clear", stdout=out)
    return out.getvalue()


def test_seeding_then_clearing_leaves_no_demo_rows():
    _seed()
    assert Expense.objects.exists()

    _clear()

    assert not User.objects.exists()
    assert not Expense.objects.exists()
    assert not ExpenseShare.objects.exists()
    assert not Comment.objects.exists()
    assert not Settlement.objects.exists()
    assert not RecurringExpense.objects.exists()
    assert not AwayPeriod.objects.exists()
    assert not AuditLog.objects.exists()
    assert not MonthClose.objects.exists()


def test_clearing_keeps_the_categories():
    """They come from a migration, not the demo. Deleting them breaks the app."""
    _seed()

    _clear()

    assert Category.objects.count() == 8
    assert Category.objects.get(name="Groceries").prorate_by_presence is True
    assert Category.objects.get(name="Rent").prorate_by_presence is False


def test_clearing_an_already_empty_database_is_harmless():
    _clear()

    assert Category.objects.count() == 8


def test_clearing_twice_is_harmless():
    _seed()
    _clear()
    _clear()

    assert not Expense.objects.exists()


def test_clear_warns_when_it_removes_the_last_superuser():
    """Otherwise you clear the demo and quietly lock yourself out."""
    _seed()
    assert User.objects.filter(is_superuser=True).exists()

    output = _clear()

    assert "No superuser left" in output
    assert "createsuperuser" in output


def test_clear_does_not_warn_when_a_real_admin_survives():
    _seed()
    User.objects.create_superuser(username="realadmin", password="x")

    output = _clear()

    assert "No superuser left" not in output
    assert User.objects.filter(username="realadmin").exists()


def test_clear_survives_a_closed_month():
    """MonthClose.closed_by is PROTECT, so it must go before the users do."""
    from core.services.monthclose import close_month

    _seed()
    close_month(year=2026, month=9, actor=User.objects.get(username="anuj"))

    _clear()

    assert not User.objects.exists()
    assert not MonthClose.objects.exists()


def test_clear_reports_expenses_and_shares_separately():
    """delete() counts cascades, so 18 expenses must not read as 81."""
    _seed()
    expense_count = Expense.objects.count()

    output = _clear()

    assert f"removed {expense_count} Expense" in output
    assert "ExpenseShare" in output


def test_clear_does_not_reseed():
    _seed()

    _clear()

    assert not Expense.objects.exists()
    assert not User.objects.exists()


def test_reset_still_reseeds():
    """--reset is the wipe-then-rebuild path and must keep working."""
    _seed()
    call_command("seed_demo", "--reset", "--month=2026-09", stdout=StringIO())

    assert User.objects.count() == 4
    assert Expense.objects.exists()
