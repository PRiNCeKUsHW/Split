"""Debt simplification. Pure arithmetic — no database in this file."""

import random
from decimal import Decimal

import pytest

from settlements.services.simplify import Transfer, simplify_debts

A, B, C, D, E = 1, 2, 3, 4, 5


def _settles(balances: dict[int, Decimal], transfers: list[Transfer]) -> bool:
    """Apply the transfers and check everyone lands on zero."""
    final = dict(balances)
    for transfer in transfers:
        final[transfer.from_user_id] = final.get(transfer.from_user_id, 0) + transfer.amount
        final[transfer.to_user_id] = final.get(transfer.to_user_id, 0) - transfer.amount
    return all(value == 0 for value in final.values())


# ------------------------------------------------------------------- basics


def test_nobody_owes_anything_means_no_transfers():
    assert simplify_debts({A: Decimal("0.00"), B: Decimal("0.00")}) == []


def test_one_debtor_pays_one_creditor():
    transfers = simplify_debts({A: Decimal("50.00"), B: Decimal("-50.00")})

    assert transfers == [Transfer(from_user_id=B, to_user_id=A, amount=Decimal("50.00"))]


def test_the_transfer_direction_runs_from_debtor_to_creditor():
    """A negative balance means you owe. You are the one who pays."""
    transfers = simplify_debts({A: Decimal("-30.00"), B: Decimal("30.00")})

    assert transfers[0].from_user_id == A
    assert transfers[0].to_user_id == B


def test_two_debtors_settle_with_one_creditor():
    balances = {A: Decimal("100.00"), B: Decimal("-60.00"), C: Decimal("-40.00")}

    transfers = simplify_debts(balances)

    assert len(transfers) == 2
    assert _settles(balances, transfers)


def test_the_largest_debtor_is_matched_with_the_largest_creditor():
    balances = {
        A: Decimal("70.00"), B: Decimal("30.00"),
        C: Decimal("-80.00"), D: Decimal("-20.00"),
    }

    transfers = simplify_debts(balances)

    assert transfers[0].from_user_id == C
    assert transfers[0].to_user_id == A
    assert transfers[0].amount == Decimal("70.00")


# --------------------------------------------------------------- invariants


def test_the_transfers_fully_settle_every_balance():
    balances = {
        A: Decimal("125.50"), B: Decimal("-40.25"),
        C: Decimal("-60.00"), D: Decimal("-25.25"),
    }

    assert _settles(balances, simplify_debts(balances))


def test_the_transfer_amounts_net_to_zero():
    balances = {A: Decimal("90.00"), B: Decimal("-30.00"), C: Decimal("-60.00")}

    transfers = simplify_debts(balances)
    paid_out = sum(t.amount for t in transfers)
    received = sum(t.amount for t in transfers)

    assert paid_out - received == Decimal("0.00")


def test_no_transfer_is_ever_zero():
    balances = {A: Decimal("50.00"), B: Decimal("-50.00"), C: Decimal("0.00")}

    assert all(t.amount > 0 for t in simplify_debts(balances))


def test_nobody_ever_pays_themselves():
    balances = {A: Decimal("40.00"), B: Decimal("-40.00")}

    assert all(t.from_user_id != t.to_user_id for t in simplify_debts(balances))


def test_transfers_never_exceed_one_fewer_than_the_number_of_people():
    """The point of simplifying: n people need at most n-1 payments."""
    balances = {
        A: Decimal("100.00"), B: Decimal("50.00"),
        C: Decimal("-70.00"), D: Decimal("-45.00"), E: Decimal("-35.00"),
    }

    assert len(simplify_debts(balances)) <= 4


def test_a_settled_person_is_left_out_of_the_plan():
    balances = {A: Decimal("50.00"), B: Decimal("-50.00"), C: Decimal("0.00")}

    involved = {t.from_user_id for t in simplify_debts(balances)} | {
        t.to_user_id for t in simplify_debts(balances)
    }

    assert C not in involved


def test_balances_that_do_not_net_to_zero_are_rejected():
    """A non-zero total means the ledger itself is broken. Fail loudly."""
    with pytest.raises(ValueError):
        simplify_debts({A: Decimal("50.00"), B: Decimal("-40.00")})


def test_paise_survive_a_chain_of_transfers():
    """Everything runs in integer paise, so nothing can drift."""
    balances = {
        A: Decimal("33.34"), B: Decimal("33.33"),
        C: Decimal("-33.33"), D: Decimal("-33.34"),
    }

    transfers = simplify_debts(balances)

    assert _settles(balances, transfers)
    assert all(t.amount.as_tuple().exponent == -2 for t in transfers)


def test_simplification_is_deterministic():
    balances = {A: Decimal("60.00"), B: Decimal("40.00"), C: Decimal("-100.00")}

    assert simplify_debts(balances) == simplify_debts(balances)


def test_random_balance_sets_always_settle_completely():
    rng = random.Random(4242)

    for _ in range(500):
        count = rng.randint(2, 6)
        raw = [rng.randint(-50_000, 50_000) for _ in range(count - 1)]
        raw.append(-sum(raw))  # force the ledger to balance
        balances = {i + 1: Decimal(value) / 100 for i, value in enumerate(raw)}

        transfers = simplify_debts(balances)

        assert _settles(balances, transfers), balances
        assert len(transfers) <= count - 1
