"""Presence-day weighting: away days and move-in/move-out, one function.

Every row of the edge-case table from the design doc is a test here.
"""

import datetime as dt

import pytest

from accounts.models import AwayPeriod
from expenses.services.presence import AwayIndex, presence_days, weights_for

pytestmark = pytest.mark.django_db

SEPT_1 = dt.date(2026, 9, 1)
SEPT_30 = dt.date(2026, 9, 30)


def _index(*users, start=SEPT_1, end=SEPT_30) -> AwayIndex:
    return AwayIndex.for_users([u.pk for u in users], start, end)


def _away(user, first: int, last: int, month: int = 9) -> AwayPeriod:
    return AwayPeriod.objects.create(
        user=user,
        start_date=dt.date(2026, month, first),
        end_date=dt.date(2026, month, last),
    )


# ------------------------------------------------------------ the core rule


def test_someone_present_all_month_counts_every_day(anuj):
    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 30


def test_an_away_period_is_inclusive_of_both_ends(anuj):
    """5-8 September is four days off, not two and not three."""
    _away(anuj, 5, 8)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 26


def test_a_single_day_away_costs_exactly_one_day(anuj):
    _away(anuj, 12, 12)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 29


def test_overlapping_away_periods_are_counted_once(anuj):
    """Two trips booked over each other must not subtract twice."""
    _away(anuj, 5, 10)
    _away(anuj, 8, 12)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 30 - 8  # 5th to 12th inclusive


def test_one_away_period_wholly_inside_another_is_counted_once(anuj):
    _away(anuj, 1, 20)
    _away(anuj, 5, 8)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 10


def test_touching_away_periods_do_not_double_count_the_boundary(anuj):
    _away(anuj, 5, 8)
    _away(anuj, 9, 12)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 22


def test_an_away_period_is_clipped_to_the_expense_window(anuj):
    """Away 25 Aug to 5 Sept only costs the September days on a September bill."""
    AwayPeriod.objects.create(
        user=anuj, start_date=dt.date(2026, 8, 25), end_date=dt.date(2026, 9, 5)
    )

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 25


def test_an_away_period_outside_the_window_changes_nothing(anuj):
    _away(anuj, 5, 8, month=7)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 30


def test_away_the_whole_month_gives_zero_days(anuj):
    _away(anuj, 1, 30)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(anuj),
    )

    assert days == 0


# -------------------------------------------------------- tenancy vs travel


def test_travel_is_ignored_when_presence_proration_is_off(anuj):
    """This is the rent rule: your empty room still costs what it costs."""
    _away(anuj, 1, 20)

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=False, away_index=_index(anuj),
    )

    assert days == 30


def test_moving_in_mid_month_only_charges_from_the_move_in_day(dev):
    """Dev joined on the 11th: 11th to 30th inclusive is 20 days."""
    days = presence_days(
        dev, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=False, away_index=_index(dev),
    )

    assert days == 20


def test_moving_out_mid_month_only_charges_up_to_the_move_out_day(anuj):
    anuj.left_on = dt.date(2026, 9, 10)
    anuj.save()

    days = presence_days(
        anuj, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=False, away_index=_index(anuj),
    )

    assert days == 10


def test_tenancy_and_travel_compose(dev):
    """Joined the 11th, then away the 15th to 20th: 20 days minus 6."""
    _away(dev, 15, 20)

    days = presence_days(
        dev, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(dev),
    )

    assert days == 14


def test_travel_before_moving_in_is_not_subtracted_twice(dev):
    """Away 1-14 Sept but only a tenant from the 11th. Only 11-14 overlap."""
    _away(dev, 1, 14)

    days = presence_days(
        dev, SEPT_1, SEPT_30,
        use_tenancy=True, use_presence=True, away_index=_index(dev),
    )

    assert days == 16


def test_someone_who_had_not_moved_in_yet_counts_zero(dev):
    days = presence_days(
        dev, dt.date(2026, 8, 1), dt.date(2026, 8, 31),
        use_tenancy=True, use_presence=False, away_index=_index(dev),
    )

    assert days == 0


def test_tenancy_is_ignored_for_an_unprorated_category(dev):
    days = presence_days(
        dev, SEPT_1, SEPT_30,
        use_tenancy=False, use_presence=False, away_index=_index(dev),
    )

    assert days == 30


# -------------------------------------------------------------- the window


def test_a_single_day_window_counts_one_day(anuj):
    day = dt.date(2026, 9, 15)

    days = presence_days(
        anuj, day, day, use_tenancy=True, use_presence=True,
        away_index=_index(anuj, start=day, end=day),
    )

    assert days == 1


def test_a_single_day_window_counts_zero_if_away_that_day(anuj):
    day = dt.date(2026, 9, 15)
    _away(anuj, 15, 15)

    days = presence_days(
        anuj, day, day, use_tenancy=True, use_presence=True,
        away_index=_index(anuj, start=day, end=day),
    )

    assert days == 0


# ------------------------------------------------------------- AwayIndex


def test_the_away_index_loads_every_participant_in_one_query(
    anuj, priya, rohit, django_assert_num_queries
):
    _away(anuj, 5, 8)
    _away(priya, 10, 12)

    with django_assert_num_queries(1):
        AwayIndex.for_users([anuj.pk, priya.pk, rohit.pk], SEPT_1, SEPT_30)


def test_the_away_index_ignores_periods_outside_the_window(anuj):
    _away(anuj, 5, 8, month=3)
    index = _index(anuj)

    assert index.away_days(anuj.pk, SEPT_1, SEPT_30) == 0


# --------------------------------------------------------------- weights_for


def test_groceries_weight_by_presence(groceries, anuj, priya, rohit, make_expense):
    _away(rohit, 1, 10)
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="3000.00",
        period_start=SEPT_1, period_end=SEPT_30,
    )

    weights = weights_for(expense, [anuj, priya, rohit])

    assert weights == {anuj.pk: 30, priya.pk: 30, rohit.pk: 20}


def test_rent_weights_by_tenancy_only(rent, anuj, priya, rohit, dev, make_expense):
    _away(rohit, 1, 20)
    expense = make_expense(
        category=rent, paid_by=anuj, amount="30000.00",
        period_start=SEPT_1, period_end=SEPT_30,
    )

    weights = weights_for(expense, [anuj, priya, rohit, dev])

    assert weights == {anuj.pk: 30, priya.pk: 30, rohit.pk: 30, dev.pk: 20}


def test_an_unprorated_category_gets_no_weights(one_off, anuj, priya, make_expense):
    """None means 'split it evenly' — no proration machinery involved."""
    _away(priya, 1, 20)
    expense = make_expense(category=one_off, paid_by=anuj, amount="500.00")

    assert weights_for(expense, [anuj, priya]) is None


def test_a_non_equal_split_is_never_prorated(groceries, anuj, priya, make_expense):
    """EXACT, PERCENT and SHARES are the user overriding the machine."""
    from expenses.models import Expense

    _away(priya, 1, 20)
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="500.00",
        split_type=Expense.SplitType.EXACT,
    )

    assert weights_for(expense, [anuj, priya]) is None


# ------------------------------------------------- end-to-end through split


def test_groceries_split_discounts_the_flatmate_who_was_away(
    groceries, anuj, priya, rohit, make_expense
):
    """The worked example from the design doc, straight through the engine."""
    from decimal import Decimal

    from expenses.services.shares import rebuild_shares

    _away(rohit, 1, 10)
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="3000.00",
        period_start=SEPT_1, period_end=SEPT_30,
    )

    rebuild_shares(
        expense,
        participant_ids=[anuj.pk, priya.pk, rohit.pk],
        weights=weights_for(expense, [anuj, priya, rohit]),
    )

    owed = {s.user_id: s.amount_owed for s in expense.shares.all()}
    assert owed == {
        anuj.pk: Decimal("1125.00"),
        priya.pk: Decimal("1125.00"),
        rohit.pk: Decimal("750.00"),
    }
    assert expense.shares_total == Decimal("3000.00")


def test_rent_split_prorates_a_mid_month_move_in(
    rent, anuj, priya, rohit, dev, make_expense
):
    """30000 across four people, one of whom joined on the 11th."""
    from decimal import Decimal

    from expenses.services.shares import rebuild_shares

    expense = make_expense(
        category=rent, paid_by=anuj, amount="30000.00",
        period_start=SEPT_1, period_end=SEPT_30,
    )
    people = [anuj, priya, rohit, dev]

    rebuild_shares(
        expense,
        participant_ids=[p.pk for p in people],
        weights=weights_for(expense, people),
    )

    owed = {s.user_id: s.amount_owed for s in expense.shares.all()}
    assert owed[dev.pk] == Decimal("5454.54")
    assert owed[anuj.pk] == Decimal("8181.82")
    assert expense.shares_total == Decimal("30000.00")


def test_a_flatmate_away_all_period_still_appears_owing_nothing(
    groceries, anuj, priya, rohit, make_expense
):
    from decimal import Decimal

    from expenses.services.shares import rebuild_shares

    _away(rohit, 1, 30)
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="2400.00",
        period_start=SEPT_1, period_end=SEPT_30,
    )
    people = [anuj, priya, rohit]

    rebuild_shares(
        expense,
        participant_ids=[p.pk for p in people],
        weights=weights_for(expense, people),
    )

    share = expense.shares.get(user=rohit)
    assert share.amount_owed == Decimal("0.00")
    assert share.present_days == 0
    assert expense.shares_total == Decimal("2400.00")


def test_everyone_away_falls_back_to_an_even_split(
    groceries, anuj, priya, rohit, make_expense
):
    """Nonsense period dates must not produce a divide-by-zero."""
    from decimal import Decimal

    from expenses.services.shares import rebuild_shares

    for person in (anuj, priya, rohit):
        _away(person, 1, 30)
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="300.00",
        period_start=SEPT_1, period_end=SEPT_30,
    )
    people = [anuj, priya, rohit]

    rebuild_shares(
        expense,
        participant_ids=[p.pk for p in people],
        weights=weights_for(expense, people),
    )

    assert expense.shares_total == Decimal("300.00")
    assert expense.shares.get(user=anuj).amount_owed == Decimal("100.00")
