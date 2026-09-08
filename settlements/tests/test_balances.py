import datetime as dt
from decimal import Decimal

import pytest

from expenses.services.shares import rebuild_shares
from settlements.models import Settlement
from settlements.services.balances import get_balance_rows, get_balances

pytestmark = pytest.mark.django_db


@pytest.fixture
def split_100(groceries, anuj, priya, make_expense):
    """Anuj pays 100, split evenly with Priya. Anuj is owed 50."""
    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])
    return expense


# ---------------------------------------------------------------- the basics


def test_the_payer_is_owed_what_the_others_consumed(split_100, anuj, priya):
    balances = get_balances([anuj, priya])

    assert balances[anuj.pk] == Decimal("50.00")
    assert balances[priya.pk] == Decimal("-50.00")


def test_balances_always_net_to_zero(split_100, anuj, priya, rohit):
    balances = get_balances([anuj, priya, rohit])

    assert sum(balances.values()) == Decimal("0.00")


def test_somebody_uninvolved_sits_at_zero(split_100, anuj, priya, rohit):
    assert get_balances([anuj, priya, rohit])[rohit.pk] == Decimal("0.00")


def test_paying_for_your_own_share_only_nets_the_difference(
    groceries, anuj, priya, rohit, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="90.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    assert get_balances([anuj, priya, rohit])[anuj.pk] == Decimal("60.00")


def test_two_expenses_from_different_payers_offset(
    groceries, one_off, anuj, priya, make_expense
):
    first = make_expense(category=groceries, paid_by=anuj, amount="100.00")
    rebuild_shares(first, participant_ids=[anuj.pk, priya.pk])
    second = make_expense(category=one_off, paid_by=priya, amount="100.00")
    rebuild_shares(second, participant_ids=[anuj.pk, priya.pk])

    balances = get_balances([anuj, priya])

    assert balances[anuj.pk] == Decimal("0.00")
    assert balances[priya.pk] == Decimal("0.00")


# ------------------------------------------------------------ what counts


def test_a_draft_expense_moves_nobody(rent, anuj, priya, make_expense):
    """A bill with no amount yet cannot make anyone owe anything."""
    make_expense(category=rent, paid_by=anuj, amount=None)

    assert get_balances([anuj, priya])[anuj.pk] == Decimal("0.00")


def test_a_soft_deleted_expense_is_excluded(split_100, anuj, priya):
    split_100.soft_delete()

    assert get_balances([anuj, priya])[anuj.pk] == Decimal("0.00")


# -------------------------------------------------------------- settlements


def test_a_pending_settlement_does_not_move_balances(split_100, anuj, priya):
    """The whole point of the confirm flow. Claiming to have paid is not paying."""
    Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("50.00"),
        status=Settlement.Status.PENDING,
    )

    balances = get_balances([anuj, priya])

    assert balances[anuj.pk] == Decimal("50.00")
    assert balances[priya.pk] == Decimal("-50.00")


def test_a_confirmed_settlement_clears_the_debt(split_100, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("50.00")
    )
    settlement.confirm()

    balances = get_balances([anuj, priya])

    assert balances[anuj.pk] == Decimal("0.00")
    assert balances[priya.pk] == Decimal("0.00")


def test_a_rejected_settlement_does_not_move_balances(split_100, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("50.00")
    )
    settlement.reject()

    assert get_balances([anuj, priya])[anuj.pk] == Decimal("50.00")


def test_a_partial_settlement_leaves_the_remainder(split_100, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("20.00")
    )
    settlement.confirm()

    balances = get_balances([anuj, priya])

    assert balances[anuj.pk] == Decimal("30.00")
    assert balances[priya.pk] == Decimal("-30.00")


def test_overpaying_flips_the_balance(split_100, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("80.00")
    )
    settlement.confirm()

    balances = get_balances([anuj, priya])

    assert balances[anuj.pk] == Decimal("-30.00")
    assert balances[priya.pk] == Decimal("30.00")


def test_balances_still_net_to_zero_after_settlements(split_100, anuj, priya, rohit):
    Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("31.00")
    ).confirm()

    assert sum(get_balances([anuj, priya, rohit]).values()) == Decimal("0.00")


# ------------------------------------------------------------------- detail


def test_balance_rows_break_the_number_down(split_100, anuj, priya):
    Settlement.objects.create(
        from_user=priya, to_user=anuj, amount=Decimal("20.00")
    ).confirm()

    rows = {row.user.pk: row for row in get_balance_rows([anuj, priya])}

    assert rows[anuj.pk].paid == Decimal("100.00")
    assert rows[anuj.pk].owed == Decimal("50.00")
    assert rows[anuj.pk].received == Decimal("20.00")
    assert rows[anuj.pk].sent == Decimal("0.00")
    assert rows[anuj.pk].net == Decimal("30.00")


def test_balance_rows_know_which_way_the_money_goes(split_100, anuj, priya):
    rows = {row.user.pk: row for row in get_balance_rows([anuj, priya])}

    assert rows[anuj.pk].is_owed is True
    assert rows[priya.pk].owes is True


def test_balances_are_computed_without_a_query_per_person(
    split_100, anuj, priya, rohit, dev, django_assert_max_num_queries
):
    with django_assert_max_num_queries(5):
        get_balances([anuj, priya, rohit, dev])


# ------------------------------------------------- end to end with simplify


def test_the_settlement_plan_clears_a_real_ledger(
    groceries, one_off, anuj, priya, rohit, make_expense
):
    from settlements.services.simplify import simplify_debts

    first = make_expense(category=groceries, paid_by=anuj, amount="1000.00")
    rebuild_shares(first, participant_ids=[anuj.pk, priya.pk, rohit.pk])
    second = make_expense(category=one_off, paid_by=priya, amount="250.00")
    rebuild_shares(second, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    balances = get_balances([anuj, priya, rohit])
    transfers = simplify_debts(balances)

    final = dict(balances)
    for transfer in transfers:
        final[transfer.from_user_id] += transfer.amount
        final[transfer.to_user_id] -= transfer.amount

    assert all(value == Decimal("0.00") for value in final.values())


def test_recording_the_simplified_transfers_actually_zeroes_the_flat(
    groceries, anuj, priya, rohit, make_expense
):
    """Follow the app's own advice and check the ledger ends up flat."""
    from settlements.services.simplify import simplify_debts

    expense = make_expense(category=groceries, paid_by=anuj, amount="100.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    for transfer in simplify_debts(get_balances([anuj, priya, rohit])):
        Settlement.objects.create(
            from_user_id=transfer.from_user_id,
            to_user_id=transfer.to_user_id,
            amount=transfer.amount,
        ).confirm()

    balances = get_balances([anuj, priya, rohit])

    assert all(value == Decimal("0.00") for value in balances.values())
