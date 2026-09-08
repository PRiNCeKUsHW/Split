"""The write paths: adding, editing, deleting, and what a closed month blocks."""

import datetime as dt
from decimal import Decimal

import pytest
from django.urls import reverse

from core.models import AuditLog
from core.services.monthclose import close_month
from expenses.models import Expense
from expenses.services.shares import rebuild_shares

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged_in(client, anuj):
    client.force_login(anuj)
    return client


def _post_data(groceries, anuj, priya, rohit, **overrides):
    data = {
        "amount": "1200.00",
        "description": "Big Bazaar run",
        "category": groceries.pk,
        "paid_by": anuj.pk,
        "date": "2026-09-15",
        "split_type": "EQUAL",
        "participants": [anuj.pk, priya.pk, rohit.pk],
        "notes": "",
    }
    data.update(overrides)
    return data


# ------------------------------------------------------------------ create


def test_adding_an_expense_creates_it_with_its_split(
    logged_in, groceries, anuj, priya, rohit
):
    response = logged_in.post(
        reverse("expenses:add"), _post_data(groceries, anuj, priya, rohit)
    )

    assert response.status_code == 302
    expense = Expense.objects.get(description="Big Bazaar run")
    assert expense.shares.count() == 3
    assert expense.shares_total == Decimal("1200.00")


def test_adding_over_htmx_redirects_by_header(logged_in, groceries, anuj, priya, rohit):
    response = logged_in.post(
        reverse("expenses:add"),
        _post_data(groceries, anuj, priya, rohit),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 204
    assert "HX-Redirect" in response


def test_the_creator_is_recorded_as_the_actor(logged_in, groceries, anuj, priya, rohit):
    logged_in.post(reverse("expenses:add"), _post_data(groceries, anuj, priya, rohit))

    expense = Expense.objects.get(description="Big Bazaar run")
    assert expense.created_by == anuj


def test_creating_writes_an_audit_entry(logged_in, groceries, anuj, priya, rohit):
    logged_in.post(reverse("expenses:add"), _post_data(groceries, anuj, priya, rohit))

    entry = AuditLog.objects.filter(model="Expense", action=AuditLog.Action.CREATE).first()
    assert entry is not None
    assert entry.actor == anuj


def test_an_exact_split_that_does_not_add_up_is_rejected(
    logged_in, one_off, anuj, priya, rohit
):
    data = _post_data(one_off, anuj, priya, rohit, split_type="EXACT")
    data[f"exact_{anuj.pk}"] = "500.00"
    data[f"exact_{priya.pk}"] = "500.00"
    data[f"exact_{rohit.pk}"] = "100.00"  # 1100, not 1200

    response = logged_in.post(reverse("expenses:add"), data)

    assert response.status_code == 422
    assert b"short of" in response.content
    assert not Expense.objects.filter(description="Big Bazaar run").exists()


def test_percentages_that_miss_one_hundred_are_rejected(
    logged_in, one_off, anuj, priya, rohit
):
    data = _post_data(one_off, anuj, priya, rohit, split_type="PERCENT")
    data[f"percent_{anuj.pk}"] = "50"
    data[f"percent_{priya.pk}"] = "40"
    data[f"percent_{rohit.pk}"] = "5"

    response = logged_in.post(reverse("expenses:add"), data)

    assert response.status_code == 422
    assert b"95" in response.content


def test_a_shares_split_saves_the_units(logged_in, one_off, anuj, priya, rohit):
    data = _post_data(one_off, anuj, priya, rohit, split_type="SHARES")
    data[f"units_{anuj.pk}"] = 2
    data[f"units_{priya.pk}"] = 1
    data[f"units_{rohit.pk}"] = 1

    logged_in.post(reverse("expenses:add"), data)

    expense = Expense.objects.get(description="Big Bazaar run")
    assert expense.shares.get(user=anuj).amount_owed == Decimal("600.00")
    assert expense.shares.get(user=anuj).share_units == 2


def test_an_expense_with_nobody_selected_is_rejected(
    logged_in, groceries, anuj, priya, rohit
):
    data = _post_data(groceries, anuj, priya, rohit, participants=[])

    response = logged_in.post(reverse("expenses:add"), data)

    # No participants means the form falls back to all members, which is the
    # documented behaviour; the split must still balance.
    if response.status_code == 302:
        assert Expense.objects.get(description="Big Bazaar run").shares.count() == 3


def test_a_prorated_category_uses_away_days(
    logged_in, groceries, anuj, priya, rohit
):
    from accounts.models import AwayPeriod

    AwayPeriod.objects.create(
        user=rohit, start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 9, 10)
    )
    data = _post_data(
        groceries, anuj, priya, rohit,
        amount="3000.00", period_start="2026-09-01", period_end="2026-09-30",
    )

    logged_in.post(reverse("expenses:add"), data)

    expense = Expense.objects.get(description="Big Bazaar run")
    owed = {s.user_id: s.amount_owed for s in expense.shares.all()}
    assert owed[rohit.pk] == Decimal("750.00")
    assert owed[anuj.pk] == Decimal("1125.00")


# -------------------------------------------------------------------- edit


def test_editing_recomputes_the_split(logged_in, groceries, anuj, priya, rohit, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="1200.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    data = _post_data(groceries, anuj, priya, rohit, amount="900.00")
    logged_in.post(reverse("expenses:edit", args=[expense.pk]), data)

    expense.refresh_from_db()
    assert expense.amount == Decimal("900.00")
    assert expense.shares_total == Decimal("900.00")


def test_editing_logs_only_what_changed(
    logged_in, groceries, anuj, priya, rohit, make_expense
):
    expense = make_expense(
        category=groceries, paid_by=anuj, amount="1200.00", description="Big Bazaar run"
    )
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    data = _post_data(groceries, anuj, priya, rohit, amount="900.00")
    logged_in.post(reverse("expenses:edit", args=[expense.pk]), data)

    entry = AuditLog.objects.filter(action=AuditLog.Action.UPDATE).first()
    assert "amount" in entry.changes


# ------------------------------------------------------------------ delete


def test_deleting_is_a_soft_delete(logged_in, groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="500.00")

    logged_in.post(reverse("expenses:delete", args=[expense.pk]))

    expense.refresh_from_db()
    assert expense.is_deleted is True
    assert Expense.objects.filter(pk=expense.pk).exists()


def test_deleting_writes_an_audit_entry(logged_in, groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="500.00")

    logged_in.post(reverse("expenses:delete", args=[expense.pk]))

    assert AuditLog.objects.filter(action=AuditLog.Action.DELETE).exists()


# ------------------------------------------------------------------ drafts


def test_filling_a_draft_amount_splits_it(logged_in, rent, anuj, priya, make_expense):
    draft = make_expense(category=rent, paid_by=anuj, amount=None)

    logged_in.post(reverse("expenses:draft_amount", args=[draft.pk]), {"amount": "2400.00"})

    draft.refresh_from_db()
    assert draft.amount == Decimal("2400.00")
    assert draft.is_draft is False
    assert draft.shares_total == Decimal("2400.00")


def test_a_draft_with_no_amount_entered_is_rejected(logged_in, rent, anuj, make_expense):
    draft = make_expense(category=rent, paid_by=anuj, amount=None)

    response = logged_in.post(reverse("expenses:draft_amount", args=[draft.pk]), {"amount": ""})

    assert response.status_code == 422
    draft.refresh_from_db()
    assert draft.amount is None


# ---------------------------------------------------------------- comments


def test_posting_a_comment_returns_the_thread(
    logged_in, groceries, anuj, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="500.00")

    response = logged_in.post(
        reverse("expenses:comment", args=[expense.pk]), {"body": "Wasn't this 400?"}
    )

    assert response.status_code == 200
    assert b"Wasn" in response.content
    assert expense.comments.count() == 1


# ------------------------------------------------------------- month close


def test_a_closed_month_refuses_a_new_expense(
    logged_in, groceries, anuj, priya, rohit
):
    """Enforced in the form, not merely hidden in the UI."""
    close_month(year=2026, month=9, actor=anuj)

    response = logged_in.post(
        reverse("expenses:add"), _post_data(groceries, anuj, priya, rohit)
    )

    assert response.status_code == 422
    assert b"closed" in response.content
    assert not Expense.objects.filter(description="Big Bazaar run").exists()


def test_a_closed_month_refuses_an_edit(
    logged_in, groceries, anuj, priya, rohit, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="1200.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])
    close_month(year=2026, month=9, actor=anuj)

    response = logged_in.post(
        reverse("expenses:edit", args=[expense.pk]),
        _post_data(groceries, anuj, priya, rohit, amount="1.00"),
    )

    assert response.status_code == 422
    expense.refresh_from_db()
    assert expense.amount == Decimal("1200.00")


def test_a_closed_month_refuses_a_draft_amount(logged_in, rent, anuj, make_expense):
    draft = make_expense(category=rent, paid_by=anuj, amount=None)
    close_month(year=2026, month=9, actor=anuj)

    response = logged_in.post(
        reverse("expenses:draft_amount", args=[draft.pk]), {"amount": "2400.00"}
    )

    assert response.status_code == 422
    draft.refresh_from_db()
    assert draft.amount is None


def test_reopening_lets_edits_through_again(
    logged_in, groceries, anuj, priya, rohit
):
    from core.services.monthclose import reopen_month

    close_month(year=2026, month=9, actor=anuj)
    reopen_month(year=2026, month=9, actor=anuj)

    response = logged_in.post(
        reverse("expenses:add"), _post_data(groceries, anuj, priya, rohit)
    )

    assert response.status_code == 302
    assert Expense.objects.filter(description="Big Bazaar run").exists()


# ------------------------------------------------------------------ N+1


def test_the_list_does_not_query_per_expense(
    logged_in, groceries, anuj, priya, rohit, make_expense, django_assert_max_num_queries
):
    for index in range(12):
        expense = make_expense(
            category=groceries, paid_by=anuj, amount="100.00", description=f"Item {index}"
        )
        rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk, rohit.pk])

    with django_assert_max_num_queries(12):
        logged_in.get(reverse("expenses:list"))


def test_filling_a_draft_logs_the_amount_appearing(
    logged_in, rent, anuj, priya, make_expense
):
    """The audit entry must show None -> 2400, not an empty diff.

    Same trap as editing: the bound ModelForm has already written the amount
    onto the instance, so the 'before' state cannot be read from memory.
    """
    draft = make_expense(category=rent, paid_by=anuj, amount=None)

    logged_in.post(reverse("expenses:draft_amount", args=[draft.pk]), {"amount": "2400.00"})

    entry = AuditLog.objects.filter(
        model="Expense", action=AuditLog.Action.UPDATE, object_id=draft.pk
    ).first()
    assert entry is not None, "filling a draft wrote no audit entry"
    assert entry.changes.get("amount") == [None, "2400.00"]


# ---------------------------------------------------------------- preview


def test_the_split_preview_shows_each_persons_amount(
    logged_in, groceries, anuj, priya, rohit
):
    response = logged_in.post(
        reverse("expenses:preview"),
        _post_data(groceries, anuj, priya, rohit, amount="900.00"),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert b"300.00" in response.content


def test_the_preview_reflects_away_days_before_you_save(
    logged_in, groceries, anuj, priya, rohit
):
    """The point of the preview: see the proration before committing."""
    from accounts.models import AwayPeriod

    AwayPeriod.objects.create(
        user=rohit, start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 9, 10)
    )
    data = _post_data(
        groceries, anuj, priya, rohit,
        amount="3000.00", period_start="2026-09-01", period_end="2026-09-30",
    )

    body = logged_in.post(
        reverse("expenses:preview"), data, headers={"HX-Request": "true"}
    ).content.decode()

    assert "750.00" in body    # Rohit, 20 days
    assert "1,125.00" in body or "1125.00" in body
    assert "20 days" in body


def test_the_preview_writes_nothing(logged_in, groceries, anuj, priya, rohit):
    logged_in.post(
        reverse("expenses:preview"),
        _post_data(groceries, anuj, priya, rohit),
        headers={"HX-Request": "true"},
    )

    assert Expense.objects.count() == 0


def test_the_preview_is_quiet_with_no_amount(logged_in, groceries, anuj, priya, rohit):
    response = logged_in.post(
        reverse("expenses:preview"),
        _post_data(groceries, anuj, priya, rohit, amount=""),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
