"""Creating, editing and removing expenses.

Every write goes through here so that the split, the audit entry and the
closed-month check can never drift apart. Views call these; they do not talk
to the ORM themselves.
"""

from __future__ import annotations

from django.db import transaction

from core.models import AuditLog
from core.services.audit import record, record_create, record_update, snapshot
from core.services.monthclose import assert_open
from expenses.models import Expense
from expenses.services.presence import weights_for
from expenses.services.shares import rebuild_shares


def _people(ids):
    from django.contrib.auth import get_user_model

    return list(get_user_model().objects.filter(pk__in=ids))


def apply_split(expense: Expense, *, participant_ids, split_inputs: dict) -> None:
    """Recompute this expense's shares, prorating if its category asks for it."""
    people = _people(participant_ids)
    rebuild_shares(
        expense,
        participant_ids=participant_ids,
        weights=weights_for(expense, people),
        **split_inputs,
    )


@transaction.atomic
def create_expense(*, form, actor) -> Expense:
    expense = form.save(commit=False)
    expense.created_by = actor
    expense.save()

    apply_split(
        expense,
        participant_ids=form.participant_ids,
        split_inputs=getattr(form, "split_inputs", {}),
    )
    record_create(actor=actor, instance=expense)
    return expense


@transaction.atomic
def update_expense(*, expense: Expense, form, actor) -> Expense:
    # A bound ModelForm writes cleaned_data onto its instance during
    # is_valid(), so `expense` in memory already holds the *new* values by the
    # time we get here. The prior state has to be re-read from the database or
    # the audit entry records nothing that changed.
    before = snapshot(Expense.objects.get(pk=expense.pk))
    updated = form.save(commit=False)
    updated.save()

    apply_split(
        updated,
        participant_ids=form.participant_ids,
        split_inputs=getattr(form, "split_inputs", {}),
    )
    record_update(actor=actor, instance=updated, before=before)
    return updated


@transaction.atomic
def fill_draft_amount(*, expense: Expense, amount, actor) -> Expense:
    """Put a number on a variable bill and split it for the first time."""
    assert_open(expense.date)
    # As in update_expense: the bound form has already put the amount on the
    # instance, so the prior state comes from the database.
    before = snapshot(Expense.objects.get(pk=expense.pk))
    expense.amount = amount
    expense.save()

    participant_ids = list(expense.shares.values_list("user_id", flat=True))
    if not participant_ids:
        from django.contrib.auth import get_user_model

        participant_ids = list(
            get_user_model().objects.active_members().values_list("id", flat=True)
        )

    apply_split(expense, participant_ids=participant_ids, split_inputs={})
    record_update(actor=actor, instance=expense, before=before)
    return expense


@transaction.atomic
def delete_expense(*, expense: Expense, actor) -> None:
    """Soft delete, so the audit trail still has something to point at."""
    assert_open(expense.date)
    expense.soft_delete()
    record(
        actor=actor,
        action=AuditLog.Action.DELETE,
        instance=expense,
        label=f"{expense.description} (₹{expense.amount})",
    )


@transaction.atomic
def restore_expense(*, expense: Expense, actor) -> Expense:
    assert_open(expense.date)
    expense.is_deleted = False
    expense.save(update_fields=["is_deleted", "updated_at"])
    record(actor=actor, action=AuditLog.Action.UPDATE, instance=expense, label="Restored")
    return expense
