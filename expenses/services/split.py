"""Money arithmetic. Integer paise in, integer paise out.

Decimal appears only at the two boundaries -- reading an amount off a form
and writing one to a DecimalField. Everything between is int, because a
float somewhere in the middle is how a ledger quietly stops adding up.

Nothing here imports Django. It is meant to be tested on its own.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

RUPEE = Decimal("0.01")


def to_paise(amount: Decimal) -> int:
    """Convert rupees to whole paise, refusing anything finer.

    A third decimal place means something upstream did float arithmetic or
    accepted input we never validated. Better to stop than to silently round.
    """
    scaled = Decimal(amount) * 100
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{amount} is finer than one paise")
    return int(scaled)


def to_rupees(paise: int) -> Decimal:
    """Convert whole paise back to a two-decimal Decimal for storage."""
    return (Decimal(paise) / 100).quantize(RUPEE)


def allocate(
    total_paise: int,
    weights: Sequence[int],
    *,
    tie_break: Sequence[int],
) -> list[int]:
    """Split ``total_paise`` across ``weights``, summing to exactly the total.

    Floor every share, then hand the leftover paise out one each by largest
    fractional part -- whoever the floor treated worst is paid back first.
    ``tie_break`` breaks equal fractions: lower rank wins, and callers put the
    payer at rank 0, so on a plain equal split (where every fraction is
    identical) the payer absorbs the odd paise.

    Returns one share per weight, in the order the weights were given.
    """
    count = len(weights)
    if count == 0:
        raise ValueError("a split needs at least one participant")
    if len(tie_break) != count:
        raise ValueError("tie_break needs one rank per participant")
    if total_paise < 0:
        raise ValueError("an expense cannot be negative")
    if any(weight < 0 for weight in weights):
        raise ValueError("weights cannot be negative")

    total_weight = sum(weights)
    if total_weight == 0:
        # Everyone weighted out -- e.g. the whole flat away for the period.
        # An even split beats a ZeroDivisionError.
        weights = [1] * count
        total_weight = count

    shares = [total_paise * weight // total_weight for weight in weights]
    leftover = total_paise - sum(shares)

    # The exact fractional part, kept as an integer numerator so the ordering
    # never depends on float comparison.
    order = sorted(
        range(count),
        key=lambda i: (-((total_paise * weights[i]) % total_weight), tie_break[i]),
    )
    for index in order[:leftover]:
        shares[index] += 1

    return shares


class SplitError(ValueError):
    """Bad split input. Messages here are shown to users, so keep them plain."""


class SplitType:
    """Mirrored by Expense.SplitType; kept here so this module stays Django-free."""

    EQUAL = "EQUAL"
    EXACT = "EXACT"
    PERCENT = "PERCENT"
    SHARES = "SHARES"
    ALL = (EQUAL, EXACT, PERCENT, SHARES)


def _tie_break_ranks(user_ids: Sequence[int], payer_id: int) -> list[int]:
    """Payer first, then ascending user id. Lower rank takes leftover paise."""
    ordered = sorted(user_ids, key=lambda uid: (uid != payer_id, uid))
    rank = {uid: position for position, uid in enumerate(ordered)}
    return [rank[uid] for uid in user_ids]


def _percent_to_basis_points(percent: Decimal) -> int:
    scaled = Decimal(percent) * 100
    if scaled != scaled.to_integral_value():
        raise SplitError(f"{percent}% is more precise than two decimal places.")
    return int(scaled)


def split_equal(
    total: Decimal,
    participant_ids: Sequence[int],
    *,
    payer_id: int,
    weights: dict[int, int] | None = None,
) -> dict[int, Decimal]:
    """Divide among the chosen participants, optionally weighted.

    ``weights`` is how presence-day and tenancy proration reach the engine:
    pass days present per person and the division follows. Left out, everyone
    weighs the same and this is a plain 1/n split.
    """
    ids = list(participant_ids)
    if not ids:
        raise SplitError("Pick at least one person to split this with.")

    if weights is None:
        resolved = [1] * len(ids)
    else:
        resolved = [int(weights.get(uid, 0)) for uid in ids]
        if any(weight < 0 for weight in resolved):
            raise SplitError("A weight cannot be negative.")

    shares = allocate(
        to_paise(total), resolved, tie_break=_tie_break_ranks(ids, payer_id)
    )
    return {uid: to_rupees(paise) for uid, paise in zip(ids, shares)}


def split_exact(total: Decimal, amounts: dict[int, Decimal]) -> dict[int, Decimal]:
    """Take the amounts as typed, and refuse them if they do not add up."""
    if not amounts:
        raise SplitError("Pick at least one person to split this with.")
    if any(Decimal(amount) < 0 for amount in amounts.values()):
        raise SplitError("A share cannot be negative.")

    total_paise = to_paise(total)
    entered = sum(to_paise(Decimal(amount)) for amount in amounts.values())

    if entered != total_paise:
        gap = to_rupees(abs(total_paise - entered))
        direction = "short of" if entered < total_paise else "over"
        raise SplitError(
            f"The shares are \u20b9{gap} {direction} the \u20b9{to_rupees(total_paise)} total."
        )

    return {uid: Decimal(amount).quantize(RUPEE) for uid, amount in amounts.items()}


def split_percent(
    total: Decimal,
    percents: dict[int, Decimal],
    *,
    payer_id: int,
) -> dict[int, Decimal]:
    """Divide by percentage. The percentages must add up to exactly 100."""
    if not percents:
        raise SplitError("Pick at least one person to split this with.")
    if any(Decimal(pct) < 0 for pct in percents.values()):
        raise SplitError("A percentage cannot be negative.")

    entered = sum(Decimal(pct) for pct in percents.values())
    if entered != Decimal("100"):
        raise SplitError(f"The percentages add up to {entered}%, not 100%.")

    ids = list(percents)
    weights = [_percent_to_basis_points(percents[uid]) for uid in ids]
    shares = allocate(
        to_paise(total), weights, tie_break=_tie_break_ranks(ids, payer_id)
    )
    return {uid: to_rupees(paise) for uid, paise in zip(ids, shares)}


def split_shares(
    total: Decimal,
    units: dict[int, int],
    *,
    payer_id: int,
) -> dict[int, Decimal]:
    """Divide by integer weights, e.g. 2:1:1 for a couple sharing a room."""
    if not units:
        raise SplitError("Pick at least one person to split this with.")
    if any(int(unit) < 0 for unit in units.values()):
        raise SplitError("A share count cannot be negative.")
    if sum(int(unit) for unit in units.values()) == 0:
        raise SplitError("Give at least one person a share.")

    ids = list(units)
    weights = [int(units[uid]) for uid in ids]
    shares = allocate(
        to_paise(total), weights, tie_break=_tie_break_ranks(ids, payer_id)
    )
    return {uid: to_rupees(paise) for uid, paise in zip(ids, shares)}


def compute_shares(
    *,
    split_type: str,
    total: Decimal,
    payer_id: int,
    participant_ids: Sequence[int],
    weights: dict[int, int] | None = None,
    exact_amounts: dict[int, Decimal] | None = None,
    percents: dict[int, Decimal] | None = None,
    share_units: dict[int, int] | None = None,
) -> dict[int, Decimal]:
    """One entry point the views and models call, whatever the split type."""
    if split_type == SplitType.EQUAL:
        return split_equal(total, participant_ids, payer_id=payer_id, weights=weights)

    if split_type == SplitType.EXACT:
        if exact_amounts is None:
            raise SplitError("Enter an amount for each person.")
        return split_exact(total, exact_amounts)

    if split_type == SplitType.PERCENT:
        if percents is None:
            raise SplitError("Enter a percentage for each person.")
        return split_percent(total, percents, payer_id=payer_id)

    if split_type == SplitType.SHARES:
        if share_units is None:
            raise SplitError("Enter a share count for each person.")
        return split_shares(total, share_units, payer_id=payer_id)

    raise SplitError(f"Unknown split type: {split_type}")
