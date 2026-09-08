"""The rounding core. No database, no Django — just the arithmetic.

Every test here answers one question: does the split add back up to exactly
what was spent? A split that loses a paise is a split that starts an argument.
"""

import random
from decimal import Decimal

import pytest

from expenses.services.split import allocate, to_paise, to_rupees

# ---------------------------------------------------------------- conversion


def test_rupees_convert_to_paise_exactly():
    assert to_paise(Decimal("100.00")) == 10000
    assert to_paise(Decimal("0.05")) == 5
    assert to_paise(Decimal("1234.56")) == 123456


def test_conversion_round_trips():
    for amount in ("0.01", "99.99", "12345.67", "0.00"):
        assert to_rupees(to_paise(Decimal(amount))) == Decimal(amount)


def test_paise_conversion_rejects_sub_paise_precision():
    """Nothing upstream should ever hand us a third decimal place."""
    with pytest.raises(ValueError):
        to_paise(Decimal("10.005"))


def test_rupees_come_back_with_two_decimal_places():
    assert str(to_rupees(3334)) == "33.34"
    assert str(to_rupees(0)) == "0.00"
    assert str(to_rupees(5)) == "0.05"


# ------------------------------------------------------------- the headline


def test_hundred_rupees_between_three_people():
    """The canonical case. 33.33 x 3 = 99.99, so someone takes the paise."""
    shares = allocate(10000, [1, 1, 1], tie_break=[0, 1, 2])

    assert shares == [3334, 3333, 3333]
    assert sum(shares) == 10000


def test_the_payer_absorbs_the_leftover_paise_on_an_even_split():
    """Payer sits at index 1 here, so the extra paise moves with them."""
    shares = allocate(10000, [1, 1, 1], tie_break=[1, 0, 2])

    assert shares == [3333, 3334, 3333]


def test_five_paise_between_three_people():
    shares = allocate(5, [1, 1, 1], tie_break=[0, 1, 2])

    assert shares == [2, 2, 1]
    assert sum(shares) == 5


def test_thousand_rupees_between_seven_people():
    shares = allocate(100000, [1] * 7, tie_break=list(range(7)))

    assert shares == [14286] * 5 + [14285] * 2
    assert sum(shares) == 100000


# ----------------------------------------------------------------- weighting


def test_weights_of_two_one_one_divide_cleanly():
    shares = allocate(10000, [2, 1, 1], tie_break=[0, 1, 2])

    assert shares == [5000, 2500, 2500]


def test_the_person_rounded_down_hardest_gets_the_leftover_paise():
    """30/30/25 days. The 25-day share has the largest fraction, so it wins.

    This is the case that separates largest-remainder from payer-takes-all:
    the payer is at index 0, but index 2 is the one the floor treated worst.
    """
    shares = allocate(100000, [30, 30, 25], tie_break=[0, 1, 2])

    assert shares == [35294, 35294, 29412]
    assert sum(shares) == 100000


def test_a_zero_weight_participant_owes_nothing():
    shares = allocate(10000, [1, 1, 0], tie_break=[0, 1, 2])

    assert shares[2] == 0
    assert sum(shares) == 10000


def test_all_zero_weights_falls_back_to_an_even_split():
    """Everyone away for the whole period. Dividing by zero is not an option."""
    shares = allocate(10000, [0, 0, 0], tie_break=[0, 1, 2])

    assert shares == [3334, 3333, 3333]
    assert sum(shares) == 10000


def test_a_single_participant_owes_the_whole_amount():
    assert allocate(12345, [1], tie_break=[0]) == [12345]


def test_zero_rupees_splits_into_zeros():
    assert allocate(0, [1, 1, 1], tie_break=[0, 1, 2]) == [0, 0, 0]


# ------------------------------------------------------------------- guards


def test_negative_total_is_rejected():
    with pytest.raises(ValueError):
        allocate(-100, [1, 1], tie_break=[0, 1])


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        allocate(100, [1, -1], tie_break=[0, 1])


def test_no_participants_is_rejected():
    with pytest.raises(ValueError):
        allocate(100, [], tie_break=[])


def test_mismatched_tie_break_length_is_rejected():
    with pytest.raises(ValueError):
        allocate(100, [1, 1, 1], tie_break=[0, 1])


# ---------------------------------------------------------------- invariants


def test_allocation_is_deterministic():
    first = allocate(99991, [3, 5, 7, 11], tie_break=[0, 1, 2, 3])
    second = allocate(99991, [3, 5, 7, 11], tie_break=[0, 1, 2, 3])

    assert first == second


def test_the_leftover_is_never_more_than_one_paise_each():
    """Largest-remainder can only ever hand out a single paise per person."""
    shares = allocate(100000, [1] * 7, tie_break=list(range(7)))
    floors = [100000 * 1 // 7] * 7

    assert all(0 <= s - f <= 1 for s, f in zip(shares, floors))


def test_shares_always_sum_to_the_total_across_random_splits():
    """The invariant the whole app rests on, hammered with random input."""
    rng = random.Random(20260908)

    for _ in range(2000):
        n = rng.randint(2, 8)
        total = rng.randint(0, 5_000_00)
        weights = [rng.randint(0, 60) for _ in range(n)]
        tie_break = list(range(n))
        rng.shuffle(tie_break)

        shares = allocate(total, weights, tie_break=tie_break)

        assert sum(shares) == total, (total, weights)
        assert all(s >= 0 for s in shares)
        assert len(shares) == n


def test_share_order_matches_participant_order_not_tie_break_order():
    """A caller zips this with their participant list. Order must be stable."""
    shares = allocate(10000, [5, 1, 1], tie_break=[2, 1, 0])

    assert shares[0] > shares[1]
    assert shares[0] > shares[2]


def test_every_share_is_within_one_paise_of_its_exact_proportion():
    """Summing correctly is not enough — the split must also be *fair*.

    Checked against exact rational arithmetic, so this is independent of the
    implementation rather than a restatement of it.
    """
    from fractions import Fraction

    rng = random.Random(11235)

    for _ in range(2000):
        n = rng.randint(2, 8)
        total = rng.randint(1, 10_000_00)
        weights = [rng.randint(1, 60) for _ in range(n)]

        shares = allocate(total, weights, tie_break=list(range(n)))

        total_weight = sum(weights)
        for share, weight in zip(shares, weights):
            exact = Fraction(total * weight, total_weight)
            assert abs(Fraction(share) - exact) < 1, (total, weights, shares)
