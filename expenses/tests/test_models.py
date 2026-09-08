import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from expenses.models import Category, Comment, Expense, ExpenseShare

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------- Category


def test_a_category_prorated_by_presence_must_also_prorate_by_tenancy():
    """You cannot owe for days before you moved in, under any flag."""
    category = Category(name="Maid", prorate_by_presence=True, prorate_by_tenancy=False)

    with pytest.raises(ValidationError):
        category.full_clean()


def test_rent_prorates_by_tenancy_but_not_by_presence(rent):
    """Your room sits empty while you travel. You still pay for it."""
    assert rent.prorate_by_tenancy is True
    assert rent.prorate_by_presence is False


def test_groceries_prorate_by_both(groceries):
    assert groceries.prorate_by_presence is True
    assert groceries.prorate_by_tenancy is True


def test_category_names_are_unique(one_off):
    with pytest.raises(IntegrityError):
        Category.objects.create(name="One-off")


# ---------------------------------------------------------------- Expense


def test_an_expense_without_a_period_covers_only_its_own_day(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, date=dt.date(2026, 9, 15))

    assert expense.period_start == dt.date(2026, 9, 15)
    assert expense.period_end == dt.date(2026, 9, 15)


def test_an_explicit_period_is_kept(groceries, anuj, make_expense):
    expense = make_expense(
        category=groceries, paid_by=anuj,
        period_start=dt.date(2026, 9, 1), period_end=dt.date(2026, 9, 30),
    )

    assert expense.period_days == 30


def test_period_end_before_period_start_is_rejected(groceries, anuj):
    expense = Expense(
        description="Backwards", amount=Decimal("100.00"), category=groceries,
        paid_by=anuj, created_by=anuj, date=dt.date(2026, 9, 15),
        period_start=dt.date(2026, 9, 20), period_end=dt.date(2026, 9, 10),
    )

    with pytest.raises(ValidationError):
        expense.full_clean()


def test_an_expense_with_no_amount_is_a_draft(rent, anuj, make_expense):
    """Variable bills arrive before anyone knows the number."""
    expense = make_expense(category=rent, paid_by=anuj, amount=None)

    assert expense.is_draft is True
    assert expense.needs_amount is True


def test_filling_in_the_amount_clears_the_draft_flag(rent, anuj, make_expense):
    expense = make_expense(category=rent, paid_by=anuj, amount=None)

    expense.amount = Decimal("2400.00")
    expense.save()

    assert expense.is_draft is False
    assert expense.needs_amount is False


def test_a_negative_amount_is_rejected(groceries, anuj):
    expense = Expense(
        description="Refund", amount=Decimal("-50.00"), category=groceries,
        paid_by=anuj, created_by=anuj, date=dt.date(2026, 9, 15),
    )

    with pytest.raises(ValidationError):
        expense.full_clean()


def test_soft_deleted_expenses_drop_out_of_the_active_queryset(groceries, anuj, make_expense):
    kept = make_expense(category=groceries, paid_by=anuj)
    removed = make_expense(category=groceries, paid_by=anuj)

    removed.soft_delete()

    assert list(Expense.objects.active()) == [kept]
    assert Expense.objects.filter(pk=removed.pk).exists()


def test_drafts_are_excluded_from_the_countable_queryset(rent, anuj, make_expense):
    real = make_expense(category=rent, paid_by=anuj, amount="2400.00")
    make_expense(category=rent, paid_by=anuj, amount=None)

    assert list(Expense.objects.countable()) == [real]


def test_expense_string_shows_the_description_and_amount(groceries, anuj, make_expense):
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="450.50", description="Big Bazaar"
    )

    assert "Big Bazaar" in str(expense)
    assert "450.50" in str(expense)


# ----------------------------------------------------------- ExpenseShare


def test_a_person_cannot_hold_two_shares_of_one_expense(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj)
    ExpenseShare.objects.create(expense=expense, user=anuj, amount_owed=Decimal("50.00"))

    with pytest.raises(IntegrityError):
        ExpenseShare.objects.create(
            expense=expense, user=anuj, amount_owed=Decimal("50.00")
        )


def test_shares_are_removed_with_their_expense(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj)
    ExpenseShare.objects.create(expense=expense, user=anuj, amount_owed=Decimal("100.00"))

    expense.delete()

    assert ExpenseShare.objects.count() == 0


# --------------------------------------------------------------- Comment


def test_a_comment_belongs_to_an_expense_and_an_author(groceries, anuj, priya, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj)

    comment = Comment.objects.create(
        expense=expense, author=priya, body="Wasn't this 400?"
    )

    assert list(expense.comments.all()) == [comment]
    assert comment.author == priya


def test_comments_come_back_oldest_first(groceries, anuj, priya, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj)
    first = Comment.objects.create(expense=expense, author=anuj, body="First")
    second = Comment.objects.create(expense=expense, author=priya, body="Second")

    assert list(expense.comments.all()) == [first, second]
