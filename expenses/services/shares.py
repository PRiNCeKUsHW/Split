"""Turn a computed split into ExpenseShare rows.

Kept apart from ``split.py`` so the arithmetic stays testable without a
database. This module is the only place that writes shares.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from django.db import transaction

from expenses.models import Expense, ExpenseShare
from expenses.services.split import SplitError, compute_shares


def default_participant_ids() -> list[int]:
    from django.contrib.auth import get_user_model

    return list(get_user_model().objects.active_members().values_list("id", flat=True))


@transaction.atomic
def rebuild_shares(
    expense: Expense,
    *,
    participant_ids: Sequence[int] | None = None,
    weights: dict[int, int] | None = None,
    exact_amounts: dict[int, Decimal] | None = None,
    percents: dict[int, Decimal] | None = None,
    share_units: dict[int, int] | None = None,
) -> list[ExpenseShare]:
    """Replace this expense's split with a freshly computed one.

    A draft (no amount yet) clears its shares and stops there — nobody owes
    anything until someone types the number in. Anything the engine refuses
    raises before a single row is touched, so a rejected edit leaves the
    existing split exactly as it was.
    """
    if expense.amount is None:
        expense.shares.all().delete()
        return []

    # Whichever map the split type uses also decides who is in the split.
    ids: Sequence[int]
    if exact_amounts is not None:
        ids = list(exact_amounts)
    elif percents is not None:
        ids = list(percents)
    elif share_units is not None:
        ids = list(share_units)
    elif participant_ids is not None:
        ids = list(participant_ids)
    else:
        ids = default_participant_ids()

    # Raises SplitError before any write, so a bad edit is a no-op.
    computed = compute_shares(
        split_type=expense.split_type,
        total=expense.amount,
        payer_id=expense.paid_by_id,
        participant_ids=ids,
        weights=weights,
        exact_amounts=exact_amounts,
        percents=percents,
        share_units=share_units,
    )

    total = sum(computed.values(), Decimal("0.00"))
    if total != expense.amount:
        # Belt and braces: the engine guarantees this, so a mismatch means a
        # bug, not bad input. Better to fail loudly than to save a bad ledger.
        raise SplitError(
            f"Split came to ₹{total}, expected ₹{expense.amount}. Refusing to save."
        )

    expense.shares.all().delete()
    rows = [
        ExpenseShare(
            expense=expense,
            user_id=user_id,
            amount_owed=amount,
            share_units=None if share_units is None else share_units.get(user_id),
            percent=(
                None if percents is None
                else Decimal(percents.get(user_id, 0)).quantize(Decimal("0.01"))
            ),
            present_days=None if weights is None else weights.get(user_id),
        )
        for user_id, amount in computed.items()
    ]
    ExpenseShare.objects.bulk_create(rows)
    return rows
