"""Turn a set of net balances into the fewest payments that clear them.

Greedy: repeatedly match the largest creditor with the largest debtor. That
is not provably the theoretical minimum for every graph — that problem is
NP-hard — but it never exceeds n-1 payments, it is instant for a flat's worth
of people, and it produces an answer anyone can check by eye.

Everything runs in integer paise so a chain of transfers cannot drift.
"""

from __future__ import annotations

import heapq
from decimal import Decimal
from typing import NamedTuple

from expenses.services.split import to_paise, to_rupees


class Transfer(NamedTuple):
    from_user_id: int
    to_user_id: int
    amount: Decimal

    def __str__(self) -> str:
        return f"{self.from_user_id} pays {self.to_user_id} ₹{self.amount}"


def simplify_debts(balances: dict[int, Decimal]) -> list[Transfer]:
    """Fewest payments that bring every balance to zero.

    A positive balance means the person is owed money; a negative one means
    they owe it. The balances must net to zero -- if they do not, the ledger
    itself is broken and we would rather say so than invent a payment.
    """
    in_paise = {user_id: to_paise(amount) for user_id, amount in balances.items()}

    residue = sum(in_paise.values())
    if residue != 0:
        raise ValueError(
            f"Balances do not net to zero (off by ₹{to_rupees(abs(residue))}). "
            "Something is wrong with the ledger, not with the settlement plan."
        )

    # Max-heaps via negated keys. The user id is the tiebreaker, so equal
    # amounts always resolve the same way and the plan is reproducible.
    creditors = [(-amount, uid) for uid, amount in in_paise.items() if amount > 0]
    debtors = [(amount, uid) for uid, amount in in_paise.items() if amount < 0]
    heapq.heapify(creditors)
    heapq.heapify(debtors)

    transfers: list[Transfer] = []
    while creditors and debtors:
        credit, creditor_id = heapq.heappop(creditors)
        debit, debtor_id = heapq.heappop(debtors)

        owed, due = -credit, -debit
        paid = min(owed, due)
        transfers.append(
            Transfer(
                from_user_id=debtor_id, to_user_id=creditor_id, amount=to_rupees(paid)
            )
        )

        if owed > paid:
            heapq.heappush(creditors, (-(owed - paid), creditor_id))
        if due > paid:
            heapq.heappush(debtors, (-(due - paid), debtor_id))

    return transfers
