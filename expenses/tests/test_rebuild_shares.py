"""The bridge between the pure engine and the database."""

from decimal import Decimal

import pytest

from expenses.models import Expense, ExpenseShare
from expenses.services.shares import rebuild_shares
from expenses.services.split import SplitError

pytestmark = pytest.mark.django_db


def test_an_equal_split_writes_one_share_per_participant(
    groceries, anuj, priya, rohit, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")

    shares = rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    assert len(shares) == 3
    assert expense.shares_total == Decimal("100.00")


def test_the_payer_takes_the_odd_paise(groceries, anuj, priya, rohit, make_expense):
    expense = make_expense(category=groceries, paid_by=priya, amount="100.00")

    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    owed = {s.user_id: s.amount_owed for s in expense.shares.all()}
    assert owed[priya.pk] == Decimal("33.34")
    assert owed[anuj.pk] == Decimal("33.33")


def test_participants_default_to_every_active_member(
    groceries, anuj, priya, rohit, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="90.00")

    rebuild_shares(expense)

    assert expense.shares.count() == 3


def test_a_member_who_moved_out_is_not_added_by_default(
    groceries, anuj, priya, rohit, make_expense
):
    import datetime as dt

    rohit.is_active_member = False
    rohit.left_on = dt.date(2026, 8, 31)
    rohit.save()
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")

    rebuild_shares(expense)

    assert set(expense.shares.values_list("user_id", flat=True)) == {anuj.pk, priya.pk}


def test_rebuilding_replaces_rather_than_duplicates(
    groceries, anuj, priya, rohit, make_expense
):
    """Editing an expense must not leave the old split lying around."""
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    assert expense.shares.count() == 2
    assert expense.shares_total == Decimal("100.00")


def test_rebuilding_with_the_same_input_is_idempotent(
    groceries, anuj, priya, rohit, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")
    ids = [anuj.pk, priya.pk, rohit.pk]

    rebuild_shares(expense, participant_ids=ids)
    first = sorted(expense.shares.values_list("user_id", "amount_owed"))
    rebuild_shares(expense, participant_ids=ids)
    second = sorted(expense.shares.values_list("user_id", "amount_owed"))

    assert first == second


def test_a_draft_expense_gets_no_shares(rent, anuj, priya, make_expense):
    """Nobody owes anything until someone types the number in."""
    expense = make_expense(category=rent, paid_by=anuj, amount=None)

    shares = rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    assert shares == []
    assert expense.shares.count() == 0


def test_filling_in_a_draft_amount_then_rebuilding_creates_the_split(
    rent, anuj, priya, make_expense
):
    expense = make_expense(category=rent, paid_by=anuj, amount=None)
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    expense.amount = Decimal("2400.00")
    expense.save()
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    assert expense.shares.count() == 2
    assert expense.shares_total == Decimal("2400.00")


def test_exact_split_records_the_amounts_given(one_off, anuj, priya, make_expense):
    expense = make_expense(
        category=one_off, paid_by=anuj, amount="100.00",
        split_type=Expense.SplitType.EXACT,
    )

    rebuild_shares(
        expense,
        exact_amounts={anuj.pk: Decimal("70.00"), priya.pk: Decimal("30.00")},
    )

    owed = {s.user_id: s.amount_owed for s in expense.shares.all()}
    assert owed == {anuj.pk: Decimal("70.00"), priya.pk: Decimal("30.00")}


def test_exact_split_that_does_not_add_up_is_refused(one_off, anuj, priya, make_expense):
    expense = make_expense(
        category=one_off, paid_by=anuj, amount="100.00",
        split_type=Expense.SplitType.EXACT,
    )

    with pytest.raises(SplitError):
        rebuild_shares(
            expense,
            exact_amounts={anuj.pk: Decimal("70.00"), priya.pk: Decimal("20.00")},
        )


def test_a_refused_split_leaves_the_previous_shares_untouched(
    one_off, anuj, priya, make_expense
):
    """A failed edit must not wipe a good split."""
    expense = make_expense(
        category=one_off, paid_by=anuj, amount="100.00",
        split_type=Expense.SplitType.EQUAL,
    )
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    expense.split_type = Expense.SplitType.EXACT
    with pytest.raises(SplitError):
        rebuild_shares(expense, exact_amounts={anuj.pk: Decimal("1.00")})

    assert expense.shares.count() == 2
    assert expense.shares_total == Decimal("100.00")


def test_percent_split_stores_the_percentages(one_off, anuj, priya, make_expense):
    expense = make_expense(
        category=one_off, paid_by=anuj, amount="200.00",
        split_type=Expense.SplitType.PERCENT,
    )

    rebuild_shares(
        expense, percents={anuj.pk: Decimal("60"), priya.pk: Decimal("40")}
    )

    share = expense.shares.get(user=anuj)
    assert share.percent == Decimal("60.00")
    assert share.amount_owed == Decimal("120.00")
    assert share.basis == "60.00%"


def test_shares_split_stores_the_units(one_off, anuj, priya, rohit, make_expense):
    expense = make_expense(
        category=one_off, paid_by=anuj, amount="100.00",
        split_type=Expense.SplitType.SHARES,
    )

    rebuild_shares(expense, share_units={anuj.pk: 2, priya.pk: 1, rohit.pk: 1})

    share = expense.shares.get(user=anuj)
    assert share.share_units == 2
    assert share.amount_owed == Decimal("50.00")
    assert share.basis == "2 shares"


def test_weighted_split_stores_the_days_present(groceries, anuj, priya, make_expense):
    """Phase 7 supplies these; the column and the wiring already work."""
    expense = make_expense(category=groceries, paid_by=anuj, amount="1000.00")

    rebuild_shares(
        expense,
        participant_ids=[anuj.pk, priya.pk],
        weights={anuj.pk: 30, priya.pk: 20},
    )

    share = expense.shares.get(user=priya)
    assert share.present_days == 20
    assert share.amount_owed == Decimal("400.00")
    assert share.basis == "20 days"


def test_rebuilding_does_not_fire_a_query_per_participant(
    groceries, anuj, priya, rohit, dev, make_expense
):
    """Bulk insert, not a save() loop.

    Asserting a fixed query count would just pin down savepoint bookkeeping.
    The property that matters is that the count is flat in the number of
    people: doubling the flat must not double the queries.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")

    with CaptureQueriesContext(connection) as two_people:
        rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    with CaptureQueriesContext(connection) as four_people:
        rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk, dev.pk])

    assert len(four_people) == len(two_people)
    assert expense.shares.count() == 4


def test_an_expense_with_no_participants_is_refused(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")

    with pytest.raises(SplitError):
        rebuild_shares(expense, participant_ids=[])


def test_shares_are_wiped_when_an_amount_is_cleared(groceries, anuj, priya, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    expense.amount = None
    expense.save()
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])

    assert ExpenseShare.objects.filter(expense=expense).count() == 0
