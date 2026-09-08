"""The four split types, still with no database in sight.

Each type gets the same non-negotiable check: the shares add back up to the
expense total, to the paise.
"""

from decimal import Decimal

import pytest

from expenses.services.split import (
    SplitError,
    SplitType,
    compute_shares,
    split_equal,
    split_exact,
    split_percent,
    split_shares,
)

ANUJ, PRIYA, ROHIT, DEV = 1, 2, 3, 4


# ------------------------------------------------------------------- EQUAL


def test_equal_split_of_one_hundred_between_three():
    shares = split_equal(Decimal("100.00"), [ANUJ, PRIYA, ROHIT], payer_id=ANUJ)

    assert shares == {
        ANUJ: Decimal("33.34"),
        PRIYA: Decimal("33.33"),
        ROHIT: Decimal("33.33"),
    }
    assert sum(shares.values()) == Decimal("100.00")


def test_equal_split_gives_the_odd_paise_to_whoever_paid():
    shares = split_equal(Decimal("100.00"), [ANUJ, PRIYA, ROHIT], payer_id=ROHIT)

    assert shares[ROHIT] == Decimal("33.34")
    assert shares[ANUJ] == Decimal("33.33")


def test_equal_split_only_covers_the_chosen_participants():
    """The picker decides who is in. Nobody else is charged."""
    shares = split_equal(Decimal("90.00"), [ANUJ, PRIYA], payer_id=ANUJ)

    assert set(shares) == {ANUJ, PRIYA}
    assert shares[ANUJ] == Decimal("45.00")


def test_equal_split_accepts_weights_for_prorated_categories():
    """Phase 7 supplies presence days here; the engine already takes them."""
    shares = split_equal(
        Decimal("3000.00"),
        [ANUJ, PRIYA, ROHIT],
        payer_id=ANUJ,
        weights={ANUJ: 30, PRIYA: 30, ROHIT: 20},
    )

    assert shares == {
        ANUJ: Decimal("1125.00"),
        PRIYA: Decimal("1125.00"),
        ROHIT: Decimal("750.00"),
    }
    assert sum(shares.values()) == Decimal("3000.00")


def test_weighted_split_pays_the_leftover_to_whoever_was_rounded_down_hardest():
    shares = split_equal(
        Decimal("1000.00"),
        [ANUJ, PRIYA, ROHIT],
        payer_id=ANUJ,
        weights={ANUJ: 30, PRIYA: 30, ROHIT: 25},
    )

    assert shares[ROHIT] == Decimal("294.12")
    assert sum(shares.values()) == Decimal("1000.00")


def test_a_participant_present_zero_days_owes_nothing_but_still_appears():
    shares = split_equal(
        Decimal("2400.00"),
        [ANUJ, PRIYA, ROHIT],
        payer_id=ANUJ,
        weights={ANUJ: 30, PRIYA: 30, ROHIT: 0},
    )

    assert shares[ROHIT] == Decimal("0.00")
    assert ROHIT in shares
    assert sum(shares.values()) == Decimal("2400.00")


def test_equal_split_needs_at_least_one_participant():
    with pytest.raises(SplitError):
        split_equal(Decimal("100.00"), [], payer_id=ANUJ)


# ------------------------------------------------------------------- EXACT


def test_exact_split_uses_the_amounts_as_entered():
    amounts = {ANUJ: Decimal("50.00"), PRIYA: Decimal("30.00"), ROHIT: Decimal("20.00")}

    assert split_exact(Decimal("100.00"), amounts) == amounts


def test_exact_split_rejects_amounts_that_do_not_add_up():
    amounts = {ANUJ: Decimal("50.00"), PRIYA: Decimal("30.00")}

    with pytest.raises(SplitError) as excinfo:
        split_exact(Decimal("100.00"), amounts)

    assert "20.00" in str(excinfo.value)


def test_exact_split_rejects_an_overshoot_and_says_by_how_much():
    amounts = {ANUJ: Decimal("60.00"), PRIYA: Decimal("50.00")}

    with pytest.raises(SplitError) as excinfo:
        split_exact(Decimal("100.00"), amounts)

    assert "10.00" in str(excinfo.value)


def test_exact_split_allows_a_zero_for_someone_who_owes_nothing():
    amounts = {ANUJ: Decimal("100.00"), PRIYA: Decimal("0.00")}

    assert split_exact(Decimal("100.00"), amounts) == amounts


def test_exact_split_rejects_a_negative_share():
    amounts = {ANUJ: Decimal("110.00"), PRIYA: Decimal("-10.00")}

    with pytest.raises(SplitError):
        split_exact(Decimal("100.00"), amounts)


# ----------------------------------------------------------------- PERCENT


def test_percent_split_of_one_hundred():
    percents = {ANUJ: Decimal("50"), PRIYA: Decimal("30"), ROHIT: Decimal("20")}

    shares = split_percent(Decimal("200.00"), percents, payer_id=ANUJ)

    assert shares == {
        ANUJ: Decimal("100.00"),
        PRIYA: Decimal("60.00"),
        ROHIT: Decimal("40.00"),
    }


def test_percent_split_rounds_to_the_paise_and_still_totals():
    """50/50 of 99.99 cannot divide evenly. The payer takes the odd paise."""
    percents = {ANUJ: Decimal("50"), PRIYA: Decimal("50")}

    shares = split_percent(Decimal("99.99"), percents, payer_id=ANUJ)

    assert shares[ANUJ] == Decimal("50.00")
    assert shares[PRIYA] == Decimal("49.99")
    assert sum(shares.values()) == Decimal("99.99")


def test_percent_split_accepts_two_decimal_percentages():
    percents = {
        ANUJ: Decimal("33.33"),
        PRIYA: Decimal("33.33"),
        ROHIT: Decimal("33.34"),
    }

    shares = split_percent(Decimal("100.00"), percents, payer_id=ANUJ)

    assert sum(shares.values()) == Decimal("100.00")
    assert shares[ROHIT] == Decimal("33.34")


def test_percent_split_rejects_totals_that_are_not_one_hundred():
    with pytest.raises(SplitError) as excinfo:
        split_percent(
            Decimal("100.00"), {ANUJ: Decimal("50"), PRIYA: Decimal("40")}, payer_id=ANUJ
        )

    assert "90" in str(excinfo.value)


def test_percent_split_rejects_a_negative_percentage():
    with pytest.raises(SplitError):
        split_percent(
            Decimal("100.00"),
            {ANUJ: Decimal("110"), PRIYA: Decimal("-10")},
            payer_id=ANUJ,
        )


# ------------------------------------------------------------------ SHARES


def test_shares_split_of_two_to_one_to_one():
    units = {ANUJ: 2, PRIYA: 1, ROHIT: 1}

    shares = split_shares(Decimal("100.00"), units, payer_id=ANUJ)

    assert shares == {
        ANUJ: Decimal("50.00"),
        PRIYA: Decimal("25.00"),
        ROHIT: Decimal("25.00"),
    }


def test_shares_split_handles_an_uneven_ratio():
    units = {ANUJ: 2, PRIYA: 1}

    shares = split_shares(Decimal("100.00"), units, payer_id=ANUJ)

    assert sum(shares.values()) == Decimal("100.00")
    assert shares[ANUJ] == Decimal("66.67")
    assert shares[PRIYA] == Decimal("33.33")


def test_shares_split_lets_someone_take_zero_units():
    units = {ANUJ: 3, PRIYA: 1, ROHIT: 0}

    shares = split_shares(Decimal("100.00"), units, payer_id=ANUJ)

    assert shares[ROHIT] == Decimal("0.00")
    assert sum(shares.values()) == Decimal("100.00")


def test_shares_split_rejects_all_zero_units():
    """Unlike presence days, zero units everywhere is a typo, not a fact."""
    with pytest.raises(SplitError):
        split_shares(Decimal("100.00"), {ANUJ: 0, PRIYA: 0}, payer_id=ANUJ)


def test_shares_split_rejects_negative_units():
    with pytest.raises(SplitError):
        split_shares(Decimal("100.00"), {ANUJ: 2, PRIYA: -1}, payer_id=ANUJ)


# --------------------------------------------------------------- dispatcher


def test_compute_shares_dispatches_on_split_type():
    shares = compute_shares(
        split_type=SplitType.EQUAL,
        total=Decimal("100.00"),
        payer_id=ANUJ,
        participant_ids=[ANUJ, PRIYA, ROHIT],
    )

    assert sum(shares.values()) == Decimal("100.00")


def test_compute_shares_passes_exact_amounts_through():
    shares = compute_shares(
        split_type=SplitType.EXACT,
        total=Decimal("100.00"),
        payer_id=ANUJ,
        participant_ids=[ANUJ, PRIYA],
        exact_amounts={ANUJ: Decimal("70.00"), PRIYA: Decimal("30.00")},
    )

    assert shares[ANUJ] == Decimal("70.00")


def test_compute_shares_rejects_an_unknown_split_type():
    with pytest.raises(SplitError):
        compute_shares(
            split_type="TELEPATHY",
            total=Decimal("100.00"),
            payer_id=ANUJ,
            participant_ids=[ANUJ],
        )


@pytest.mark.parametrize(
    "total",
    ["0.01", "0.03", "7.77", "100.00", "999.99", "12345.67", "1000000.00"],
)
def test_every_split_type_sums_to_the_total(total):
    amount = Decimal(total)
    ids = [ANUJ, PRIYA, ROHIT]

    equal = split_equal(amount, ids, payer_id=PRIYA)
    shares = split_shares(amount, {ANUJ: 3, PRIYA: 2, ROHIT: 1}, payer_id=PRIYA)
    percent = split_percent(
        amount,
        {ANUJ: Decimal("33.33"), PRIYA: Decimal("33.33"), ROHIT: Decimal("33.34")},
        payer_id=PRIYA,
    )

    assert sum(equal.values()) == amount
    assert sum(shares.values()) == amount
    assert sum(percent.values()) == amount
