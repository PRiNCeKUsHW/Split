"""Comprehensive financial and arithmetic audit tests for FlatSplit.

Tests the fundamental invariant:
    sum(shares) == total_paise
across all edge cases, rounding boundaries, and random distributions.
Ensures zero float drift and strict Decimal / integer paise adherence.
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from expenses.services.split import (
    SplitError,
    allocate,
    split_equal,
    split_exact,
    split_percent,
    split_shares,
    to_paise,
    to_rupees,
)
from settlements.services.simplify import simplify_debts


def test_audit_hundred_split_three():
    """₹100 divided among 3 people: exactly 33.34, 33.33, 33.33."""
    res = split_equal(Decimal("100.00"), [1, 2, 3], payer_id=1)
    assert res[1] == Decimal("33.34")
    assert res[2] == Decimal("33.33")
    assert res[3] == Decimal("33.33")
    assert sum(res.values()) == Decimal("100.00")


def test_audit_ten_split_three():
    """₹10 divided among 3 people: exactly 3.34, 3.33, 3.33."""
    res = split_equal(Decimal("10.00"), [1, 2, 3], payer_id=1)
    assert res[1] == Decimal("3.34")
    assert res[2] == Decimal("3.33")
    assert res[3] == Decimal("3.33")
    assert sum(res.values()) == Decimal("10.00")


def test_audit_one_split_three():
    """₹1 divided among 3 people: exactly 0.34, 0.33, 0.33."""
    res = split_equal(Decimal("1.00"), [1, 2, 3], payer_id=1)
    assert res[1] == Decimal("0.34")
    assert res[2] == Decimal("0.33")
    assert res[3] == Decimal("0.33")
    assert sum(res.values()) == Decimal("1.00")


def test_audit_nine_nine_nine_split_seven():
    """₹999 divided among 7 people: sum must equal exactly ₹999.00."""
    users = list(range(1, 8))
    res = split_equal(Decimal("999.00"), users, payer_id=1)
    assert sum(res.values()) == Decimal("999.00")
    for share in res.values():
        assert share > Decimal("0")


def test_audit_hundred_point_zero_one_split_three():
    """₹100.01 divided among 3 people: sum must equal exactly ₹100.01."""
    res = split_equal(Decimal("100.01"), [1, 2, 3], payer_id=1)
    assert sum(res.values()) == Decimal("100.01")


def test_audit_one_paise_split_three():
    """₹0.01 divided among 3 people: payer gets ₹0.01, others ₹0.00."""
    res = split_equal(Decimal("0.01"), [1, 2, 3], payer_id=1)
    assert res[1] == Decimal("0.01")
    assert res[2] == Decimal("0.00")
    assert res[3] == Decimal("0.00")
    assert sum(res.values()) == Decimal("0.01")


def test_audit_million_split_seven():
    """₹1,000,000.00 divided among 7 people: sum must equal exactly ₹1,000,000.00."""
    users = list(range(1, 8))
    res = split_equal(Decimal("1000000.00"), users, payer_id=1)
    assert sum(res.values()) == Decimal("1000000.00")


def test_audit_fuzz_random_splits():
    """Randomized fuzz test verifying sum(shares) == total for 200 random splits."""
    rng = random.Random(42)
    for _ in range(200):
        total_paise = rng.randint(1, 10000000)
        n_participants = rng.randint(1, 20)
        weights = [rng.randint(0, 31) for _ in range(n_participants)]
        tie_break = list(range(n_participants))
        rng.shuffle(tie_break)

        shares = allocate(total_paise, weights, tie_break=tie_break)
        assert sum(shares) == total_paise
        assert all(s >= 0 for s in shares)


def test_audit_negative_amount_rejection():
    """Negative expense amounts must be rejected."""
    with pytest.raises(ValueError, match="negative"):
        allocate(-100, [1, 1], tie_break=[0, 1])


def test_audit_sub_paise_rejection():
    """Fractional paise (e.g. ₹10.005) must be rejected with ValueError."""
    with pytest.raises(ValueError, match="finer than one paise"):
        to_paise(Decimal("10.005"))


def test_audit_percent_validation():
    """Percentage splits must sum to exactly 100%."""
    with pytest.raises(SplitError, match="add up to"):
        split_percent(
            Decimal("100.00"),
            {1: Decimal("50.00"), 2: Decimal("40.00")},
            payer_id=1,
        )

    with pytest.raises(SplitError, match="add up to"):
        split_percent(
            Decimal("100.00"),
            {1: Decimal("50.00"), 2: Decimal("60.00")},
            payer_id=1,
        )

    res = split_percent(
        Decimal("100.00"),
        {1: Decimal("33.33"), 2: Decimal("33.33"), 3: Decimal("33.34")},
        payer_id=1,
    )
    assert sum(res.values()) == Decimal("100.00")


def test_audit_exact_validation():
    """Exact splits must sum to exactly total amount."""
    with pytest.raises(SplitError, match="short of"):
        split_exact(
            Decimal("100.00"),
            {1: Decimal("50.00"), 2: Decimal("40.00")},
        )

    res = split_exact(
        Decimal("100.00"),
        {1: Decimal("50.00"), 2: Decimal("50.00")},
    )
    assert sum(res.values()) == Decimal("100.00")


def test_audit_shares_validation():
    """Validates custom share counts."""
    # Zero shares validation
    with pytest.raises(SplitError, match="Give at least one person a share"):
        split_shares(
            Decimal("60.00"),
            {1: 0, 2: 0, 3: 0},
            payer_id=1,
        )

    # Valid shares 2:1:1
    res = split_shares(
        Decimal("60.00"),
        {1: 2, 2: 1, 3: 1},
        payer_id=1,
    )
    assert sum(res.values()) == Decimal("60.00")
    assert res[1] == Decimal("30.00")
    assert res[2] == Decimal("15.00")
    assert res[3] == Decimal("15.00")


def test_audit_debt_simplification():
    """Verify greedy debt simplification invariants."""
    balances = {1: Decimal("50.00"), 2: Decimal("-30.00"), 3: Decimal("-20.00")}
    txs = simplify_debts(balances)

    net_transfers = {1: Decimal("0.00"), 2: Decimal("0.00"), 3: Decimal("0.00")}
    for tx in txs:
        assert tx.amount > Decimal("0.00")
        assert tx.from_user_id != tx.to_user_id
        net_transfers[tx.from_user_id] -= tx.amount
        net_transfers[tx.to_user_id] += tx.amount

    for uid in (1, 2, 3):
        assert net_transfers[uid] == balances[uid]
