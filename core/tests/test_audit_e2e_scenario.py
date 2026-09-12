"""Full-stack end-to-end audit scenario test.

Simulates a realistic multi-user shared flat lifecycle:
1. Three roommates (Alice, Bob, Charlie).
2. Bob travels for 4 days; Charlie moves in mid-month (Sept 10).
3. Mixed expenses:
   - Grocery with presence proration (different days present).
   - Electricity variable draft created without amount, filled later.
   - High-value Rent (₹30,000) equal split.
   - Odd amount (₹999) split across 3 roommates.
4. Mathematical verification of exact paise allocation and invariant preservation.
5. Debt simplification and settlement lifecycle (recording, unauthorized confirm prevention, recipient confirmation).
6. Month close and strict immutability verification (rejection of edits, deletes, and additions).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import AwayPeriod
from core.models import AuditLog, MonthClose
from core.services.monthclose import close_month, is_closed
from expenses.models import Category, Expense, ExpenseShare
from expenses.services.crud import (
    create_expense,
    delete_expense,
    fill_draft_amount,
    update_expense,
)
from expenses.services.presence import weights_for
from expenses.services.split import allocate, to_paise, to_rupees
from settlements.models import Settlement
from settlements.services.balances import get_balance_rows, get_balances
from settlements.services.simplify import simplify_debts

User = get_user_model()


@pytest.fixture
def flatmates(db):
    alice = User.objects.create_user(
        username="alice",
        password="password123",
        display_name="Alice Admin",
        upi_id="alice@upi",
        is_staff=True,
        joined_on=dt.date(2026, 1, 1),
    )
    bob = User.objects.create_user(
        username="bob",
        password="password123",
        display_name="Bob Roomie",
        upi_id="bob@upi",
        joined_on=dt.date(2026, 1, 1),
    )
    charlie = User.objects.create_user(
        username="charlie",
        password="password123",
        display_name="Charlie New",
        upi_id="charlie@upi",
        joined_on=dt.date(2026, 9, 10),  # Moved in Sept 10
    )
    return alice, bob, charlie


@pytest.fixture
def categories(db):
    groceries, _ = Category.objects.get_or_create(
        name="Groceries",
        defaults={
            "icon": "cart",
            "prorate_by_tenancy": True,
            "prorate_by_presence": True,
        },
    )
    # Ensure proration flags are set if category was already pre-seeded
    groceries.prorate_by_tenancy = True
    groceries.prorate_by_presence = True
    groceries.save()

    utilities, _ = Category.objects.get_or_create(name="Utilities", defaults={"icon": "zap"})
    rent, _ = Category.objects.get_or_create(name="Rent", defaults={"icon": "home"})
    misc, _ = Category.objects.get_or_create(name="Miscellaneous", defaults={"icon": "star"})
    return groceries, utilities, rent, misc


@pytest.mark.django_db
def test_realistic_e2e_full_lifecycle(flatmates, categories, client):
    alice, bob, charlie = flatmates
    cat_groceries, cat_utilities, cat_rent, cat_misc = categories

    # 1. Setup Away Period for Bob (away Sept 5 to Sept 8 = 4 days)
    AwayPeriod.objects.create(
        user=bob,
        start_date=dt.date(2026, 9, 5),
        end_date=dt.date(2026, 9, 8),
    )

    # Verify presence calculation for Sept 2026 (30 days total)
    # Alice: 30 days present
    # Bob: 30 - 4 = 26 days present
    # Charlie: moved in Sept 10 -> 21 days present (Sept 10 to Sept 30)
    # 2. Create Grocery expense with Presence Proration (₹1,000 paid by Alice)
    # Sept 1 to Sept 30: 30 total days.
    # Alice: 30 days present
    # Bob: 30 - 4 = 26 days present
    # Charlie: moved in Sept 10 -> 21 days present (Sept 10 to Sept 30)
    exp_grocery = Expense.objects.create(
        description="Weekly Groceries",
        amount=Decimal("1000.00"),
        paid_by=alice,
        created_by=alice,
        category=cat_groceries,
        date=dt.date(2026, 9, 12),
        period_start=dt.date(2026, 9, 1),
        period_end=dt.date(2026, 9, 30),
        split_type=Expense.SplitType.EQUAL,
    )

    weights_dict = weights_for(exp_grocery, [alice, bob, charlie])
    assert weights_dict[alice.pk] == 30
    assert weights_dict[bob.pk] == 26
    assert weights_dict[charlie.pk] == 21
    assert sum(weights_dict.values()) == 77

    # Allocate shares with proration
    weights = [weights_dict[alice.pk], weights_dict[bob.pk], weights_dict[charlie.pk]]
    paise_shares = allocate(100000, weights, tie_break=[0, 1, 2])
    assert sum(paise_shares) == 100000
    ExpenseShare.objects.create(expense=exp_grocery, user=alice, amount_owed=to_rupees(paise_shares[0]))
    ExpenseShare.objects.create(expense=exp_grocery, user=bob, amount_owed=to_rupees(paise_shares[1]))
    ExpenseShare.objects.create(expense=exp_grocery, user=charlie, amount_owed=to_rupees(paise_shares[2]))

    # Sum of shares must equal exactly 1000.00
    grocery_shares_sum = sum(s.amount_owed for s in exp_grocery.shares.all())
    assert grocery_shares_sum == Decimal("1000.00")

    # 3. Create Variable Bill Draft (Electricity) without amount
    exp_draft = Expense.objects.create(
        description="Sept Electricity Bill",
        amount=None,
        is_draft=True,
        paid_by=bob,
        created_by=bob,
        category=cat_utilities,
        date=dt.date(2026, 9, 1),
        split_type=Expense.SplitType.EQUAL,
    )
    for u in (alice, bob, charlie):
        ExpenseShare.objects.create(expense=exp_draft, user=u, amount_owed=Decimal("0.00"))

    # Later: Bill arrives, fill in ₹1,800.00
    fill_draft_amount(expense=exp_draft, amount=Decimal("1800.00"), actor=bob)
    exp_draft.refresh_from_db()
    assert exp_draft.amount == Decimal("1800.00")
    assert not exp_draft.is_draft
    draft_shares_sum = sum(s.amount_owed for s in exp_draft.shares.all())
    assert draft_shares_sum == Decimal("1800.00")
    for s in exp_draft.shares.all():
        assert s.amount_owed == Decimal("600.00")

    # 4. Rent: ₹30,000.00 equal split paid by Alice
    exp_rent = Expense.objects.create(
        description="September Rent",
        amount=Decimal("30000.00"),
        paid_by=alice,
        created_by=alice,
        category=cat_rent,
        date=dt.date(2026, 9, 1),
        split_type=Expense.SplitType.EQUAL,
    )
    for u in (alice, bob, charlie):
        ExpenseShare.objects.create(expense=exp_rent, user=u, amount_owed=Decimal("10000.00"))
    assert sum(s.amount_owed for s in exp_rent.shares.all()) == Decimal("30000.00")

    # 5. Odd Split: ₹999.00 paid by Charlie
    exp_odd = Expense.objects.create(
        description="Kitchen Supplies",
        amount=Decimal("999.00"),
        paid_by=charlie,
        created_by=charlie,
        category=cat_misc,
        date=dt.date(2026, 9, 15),
        split_type=Expense.SplitType.EQUAL,
    )
    odd_shares = allocate(99900, [1, 1, 1], tie_break=[2, 0, 1])  # Charlie (idx 2) is payer
    assert sum(odd_shares) == 99900
    ExpenseShare.objects.create(expense=exp_odd, user=alice, amount_owed=to_rupees(odd_shares[0]))
    ExpenseShare.objects.create(expense=exp_odd, user=bob, amount_owed=to_rupees(odd_shares[1]))
    ExpenseShare.objects.create(expense=exp_odd, user=charlie, amount_owed=to_rupees(odd_shares[2]))
    assert sum(s.amount_owed for s in exp_odd.shares.all()) == Decimal("999.00")

    # 6. Ledger balances & Debt Simplification
    balances = get_balances([alice, bob, charlie])
    # Sum of all net balances in the flat must equal 0
    total_net = sum(balances.values())
    assert total_net == Decimal("0.00")

    paise_balances = {uid: to_paise(amt) for uid, amt in balances.items()}
    assert sum(paise_balances.values()) == 0

    simplified = simplify_debts(balances)
    assert len(simplified) > 0

    # Verify simplified debts fully extinguish all balances
    sim_net = {uid: Decimal("0.00") for uid in (alice.pk, bob.pk, charlie.pk)}
    for tx in simplified:
        assert tx.amount > Decimal("0.00")
        sim_net[tx.from_user_id] -= tx.amount
        sim_net[tx.to_user_id] += tx.amount

    for uid in (alice.pk, bob.pk, charlie.pk):
        assert sim_net[uid] == balances[uid]

    # 7. Settlement Lifecycle: Bob pays Alice
    bob_to_alice_tx = next((t for t in simplified if t.from_user_id == bob.pk and t.to_user_id == alice.pk), None)
    if bob_to_alice_tx:
        settlement_amt = bob_to_alice_tx.amount
        settlement = Settlement.objects.create(
            from_user=bob,
            to_user=alice,
            amount=settlement_amt,
            date=dt.date(2026, 9, 20),
            status=Settlement.Status.PENDING,
        )

        # Charlie cannot confirm Bob's settlement to Alice
        client.force_login(charlie)
        res = client.post(f"/api/settlements/{settlement.pk}/confirm")
        assert res.status_code == 403

        # Alice (recipient) confirms settlement
        client.force_login(alice)
        res = client.post(f"/api/settlements/{settlement.pk}/confirm")
        assert res.status_code == 200
        settlement.refresh_from_db()
        assert settlement.status == Settlement.Status.CONFIRMED

    # 8. Close Month: September 2026
    close_month(year=2026, month=9, actor=alice, note="All settled")
    assert is_closed(dt.date(2026, 9, 1))
    assert is_closed(dt.date(2026, 9, 30))

    # 9. Verify Immutability of Closed Month
    # Attempting to delete closed expense fails in service layer
    with pytest.raises(ValidationError, match="is closed"):
        delete_expense(expense=exp_grocery, actor=alice)

    # API delete endpoint rejects with 403
    res = client.post(f"/api/expenses/{exp_grocery.pk}/delete")
    assert res.status_code == 403
    assert b"closed" in res.content

    # API update endpoint rejects with 403
    res = client.post(
        f"/api/expenses/{exp_grocery.pk}/edit",
        data={"description": "Hacked Groceries", "amount": "2000.00"},
        content_type="application/json",
    )
    assert res.status_code == 403
    assert b"closed" in res.content

    # API fill draft endpoint rejects with 403
    res = client.post(
        f"/api/expenses/{exp_draft.pk}/amount",
        data={"amount": "2500.00"},
        content_type="application/json",
    )
    assert res.status_code == 403
    assert b"closed" in res.content

    # API create endpoint in closed month rejects with 422/403
    res = client.post(
        "/api/expenses/create",
        data={
            "description": "Late Sept Coffee",
            "amount": "150.00",
            "date": "2026-09-25",
            "paid_by": str(alice.pk),
            "category": str(cat_misc.pk),
            "split_type": "EQUAL",
            "participants": [str(alice.pk), str(bob.pk)],
        },
        content_type="application/json",
    )
    assert res.status_code in (403, 422)

    # Verify audit logs captured everything
    assert AuditLog.objects.filter(action=AuditLog.Action.CLOSE).exists()
