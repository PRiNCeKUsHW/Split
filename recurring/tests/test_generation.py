"""Recurring generation. The hard requirement is that cron can run it twice."""

import datetime as dt
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from expenses.models import Expense
from recurring.models import RecurringExpense
from recurring.services import drafts_needing_amounts, generate_for_month

pytestmark = pytest.mark.django_db


@pytest.fixture
def rent_template(rent, anuj):
    return RecurringExpense.objects.create(
        description="Rent", category=rent, amount=Decimal("30000.00"),
        paid_by=anuj, day_of_month=1,
    )


@pytest.fixture
def electricity_template(db, anuj):
    from expenses.models import Category

    return RecurringExpense.objects.create(
        description="Electricity", category=Category.objects.get(name="Electricity"),
        amount=None, is_variable=True, paid_by=anuj, day_of_month=7,
    )


# ------------------------------------------------------------- generation


def test_a_fixed_template_creates_an_expense_with_its_amount(
    rent_template, anuj, priya, rohit
):
    result = generate_for_month(2026, 9)

    assert result.created_count == 1
    expense = result.created[0]
    assert expense.amount == Decimal("30000.00")
    assert expense.date == dt.date(2026, 9, 1)


def test_a_generated_expense_is_split_among_the_flat(rent_template, anuj, priya, rohit):
    generate_for_month(2026, 9)

    expense = Expense.objects.get(description="Rent")
    assert expense.shares.count() == 3
    assert expense.shares_total == Decimal("30000.00")


def test_a_variable_template_creates_a_draft_with_no_amount(
    electricity_template, anuj, priya
):
    result = generate_for_month(2026, 9)

    expense = result.created[0]
    assert expense.amount is None
    assert expense.is_draft is True
    assert expense.shares.count() == 0


def test_drafts_show_up_in_the_needs_amount_list(electricity_template, anuj, priya):
    generate_for_month(2026, 9)

    assert [e.description for e in drafts_needing_amounts()] == ["Electricity"]


def test_a_whole_month_template_sets_the_period_for_proration(
    rent_template, anuj, priya
):
    generate_for_month(2026, 9)

    expense = Expense.objects.get(description="Rent")
    assert expense.period_start == dt.date(2026, 9, 1)
    assert expense.period_end == dt.date(2026, 9, 30)


def test_generation_prorates_a_mid_month_move_in(rent_template, anuj, priya, rohit, dev):
    """Dev joined on the 11th, so his rent share is smaller."""
    generate_for_month(2026, 9)

    expense = Expense.objects.get(description="Rent")
    owed = {s.user_id: s.amount_owed for s in expense.shares.all()}
    assert owed[dev.pk] < owed[anuj.pk]
    assert expense.shares_total == Decimal("30000.00")


def test_a_day_31_template_lands_on_the_last_day_of_a_short_month(rent, anuj, priya):
    RecurringExpense.objects.create(
        description="Late rent", category=rent, amount=Decimal("100.00"),
        paid_by=anuj, day_of_month=31,
    )

    generate_for_month(2026, 2)

    assert Expense.objects.get(description="Late rent").date == dt.date(2026, 2, 28)


# ------------------------------------------------------------ idempotency


def test_running_twice_creates_nothing_the_second_time(rent_template, anuj, priya):
    generate_for_month(2026, 9)

    second = generate_for_month(2026, 9)

    assert second.created_count == 0
    assert second.skipped == ["Rent"]
    assert Expense.objects.filter(description="Rent").count() == 1


def test_running_five_times_still_leaves_one_expense(rent_template, anuj, priya):
    for _ in range(5):
        generate_for_month(2026, 9)

    assert Expense.objects.filter(source_template=rent_template).count() == 1


def test_regenerating_does_not_overwrite_a_filled_in_draft(
    electricity_template, anuj, priya
):
    """Somebody read the meter. Do not undo that."""
    generate_for_month(2026, 9)
    expense = Expense.objects.get(description="Electricity")
    expense.amount = Decimal("2450.00")
    expense.save()

    generate_for_month(2026, 9)

    expense.refresh_from_db()
    assert expense.amount == Decimal("2450.00")
    assert Expense.objects.filter(description="Electricity").count() == 1


def test_the_same_template_generates_again_in_a_different_month(
    rent_template, anuj, priya
):
    generate_for_month(2026, 9)
    generate_for_month(2026, 10)

    assert Expense.objects.filter(source_template=rent_template).count() == 2


# --------------------------------------------------------------- filtering


def test_an_inactive_template_generates_nothing(rent_template, anuj, priya):
    rent_template.is_active = False
    rent_template.save()

    assert generate_for_month(2026, 9).created_count == 0


def test_a_quarterly_template_skips_the_months_between(rent, anuj, priya):
    RecurringExpense.objects.create(
        description="Water tank cleaning", category=rent, amount=Decimal("1200.00"),
        paid_by=anuj, frequency=RecurringExpense.Frequency.QUARTERLY,
    )

    assert generate_for_month(2026, 1).created_count == 1
    assert generate_for_month(2026, 2).created_count == 0
    assert generate_for_month(2026, 4).created_count == 1


def test_default_participants_override_the_active_member_list(
    rent, anuj, priya, rohit
):
    template = RecurringExpense.objects.create(
        description="Netflix", category=rent, amount=Decimal("649.00"), paid_by=anuj
    )
    template.default_participants.set([anuj, priya])

    generate_for_month(2026, 9)

    assert Expense.objects.get(description="Netflix").shares.count() == 2


def test_a_variable_template_without_an_amount_is_valid(electricity_template):
    electricity_template.full_clean()


def test_a_fixed_template_without_an_amount_is_rejected(rent, anuj):
    from django.core.exceptions import ValidationError

    template = RecurringExpense(
        description="Rent", category=rent, amount=None, is_variable=False, paid_by=anuj
    )

    with pytest.raises(ValidationError):
        template.full_clean()


# ----------------------------------------------------------------- command


def test_the_management_command_generates_the_month(rent_template, anuj, priya):
    out = StringIO()

    call_command("generate_recurring", "--year=2026", "--month=9", stdout=out)

    assert "Created 1" in out.getvalue()
    assert Expense.objects.filter(description="Rent").count() == 1


def test_the_management_command_is_idempotent(rent_template, anuj, priya):
    call_command("generate_recurring", "--year=2026", "--month=9", stdout=StringIO())
    out = StringIO()

    call_command("generate_recurring", "--year=2026", "--month=9", stdout=out)

    assert "Created 0" in out.getvalue()
    assert "already generated" in out.getvalue()
    assert Expense.objects.filter(description="Rent").count() == 1


def test_a_dry_run_writes_nothing(rent_template, anuj, priya):
    out = StringIO()

    call_command("generate_recurring", "--year=2026", "--month=9", "--dry-run", stdout=out)

    assert "Would create 1" in out.getvalue()
    assert Expense.objects.count() == 0


def test_the_command_flags_drafts_that_need_an_amount(electricity_template, anuj, priya):
    out = StringIO()

    call_command("generate_recurring", "--year=2026", "--month=9", stdout=out)

    assert "need an amount" in out.getvalue()
