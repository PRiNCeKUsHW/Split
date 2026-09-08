"""Net position per flatmate.

    net(u) = what u paid out
           - what u consumed
           + what u has settled to others   (confirmed only)
           - what others have settled to u  (confirmed only)

Paying someone back makes you *less* in debt, so a sent settlement moves your
balance up. Receiving one moves it down. Only CONFIRMED settlements count:
saying you sent the money is not the same as the other person having it.

Four aggregate queries regardless of how many people live in the flat.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from django.db.models import Sum

from expenses.models import Expense, ExpenseShare
from settlements.models import Settlement

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BalanceRow:
    """A balance with its working shown, for screens that explain themselves."""

    user: object
    paid: Decimal
    owed: Decimal
    sent: Decimal
    received: Decimal

    @property
    def net(self) -> Decimal:
        return self.paid - self.owed + self.sent - self.received

    @property
    def is_owed(self) -> bool:
        return self.net > ZERO

    @property
    def owes(self) -> bool:
        return self.net < ZERO

    @property
    def is_settled(self) -> bool:
        return self.net == ZERO

    @property
    def magnitude(self) -> Decimal:
        """The number to show. The sign is carried by the colour, not a minus."""
        return abs(self.net)


def _totals(queryset, group_by: str, field: str) -> dict[int, Decimal]:
    rows = queryset.values(group_by).annotate(total=Sum(field))
    return {row[group_by]: row["total"] or ZERO for row in rows}


def _active_members() -> list:
    from django.contrib.auth import get_user_model

    return list(get_user_model().objects.active_members())


def get_balance_rows(users: Sequence | None = None) -> list[BalanceRow]:
    """Balances with their components, for every given user (or all members)."""
    people = list(users) if users is not None else _active_members()

    paid = _totals(Expense.objects.countable(), "paid_by", "amount")
    owed = _totals(
        ExpenseShare.objects.filter(
            expense__is_deleted=False, expense__is_draft=False
        ),
        "user",
        "amount_owed",
    )
    sent = _totals(Settlement.objects.confirmed(), "from_user", "amount")
    received = _totals(Settlement.objects.confirmed(), "to_user", "amount")

    return [
        BalanceRow(
            user=person,
            paid=paid.get(person.pk, ZERO),
            owed=owed.get(person.pk, ZERO),
            sent=sent.get(person.pk, ZERO),
            received=received.get(person.pk, ZERO),
        )
        for person in people
    ]


def get_balances(users: Sequence | None = None) -> dict[int, Decimal]:
    """Net position per user id. Positive means they are owed money."""
    return {row.user.pk: row.net for row in get_balance_rows(users)}


def get_balance_for(user) -> BalanceRow:
    return get_balance_rows([user])[0]
