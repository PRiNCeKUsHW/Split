import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from core.models import AuditLog, MonthClose
from core.services.audit import (
    diff,
    history_for,
    record_create,
    record_delete,
    record_update,
    snapshot,
)
from core.services.monthclose import (
    assert_open,
    assert_open_or_403,
    close_month,
    is_closed,
    reopen_month,
)

pytestmark = pytest.mark.django_db


# ------------------------------------------------------------------ audit


def test_creating_an_expense_is_logged_with_a_full_snapshot(
    groceries, anuj, make_expense
):
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")

    entry = record_create(actor=anuj, instance=expense)

    assert entry.action == AuditLog.Action.CREATE
    assert entry.model == "Expense"
    assert entry.object_id == expense.pk
    assert entry.changes["amount"] == [None, "450.00"]


def test_an_edit_logs_only_what_actually_changed(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")
    before = snapshot(expense)

    expense.amount = Decimal("475.00")
    expense.save()
    entry = record_update(actor=anuj, instance=expense, before=before)

    assert entry.changed_fields == ["amount"]
    assert entry.changes["amount"] == ["450.00", "475.00"]


def test_an_edit_that_changes_nothing_writes_no_entry(groceries, anuj, make_expense):
    """An audit trail full of empty rows is worse than none."""
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")
    before = snapshot(expense)

    expense.save()

    assert record_update(actor=anuj, instance=expense, before=before) is None


def test_the_audit_trail_reads_back_in_order(groceries, anuj, priya, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")
    record_create(actor=anuj, instance=expense)
    before = snapshot(expense)
    expense.amount = Decimal("500.00")
    expense.save()
    record_update(actor=priya, instance=expense, before=before)

    entries = list(history_for(expense))

    assert len(entries) == 2
    assert entries[0].actor == priya  # newest first
    assert entries[1].action == AuditLog.Action.CREATE


def test_deleting_is_logged(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")

    entry = record_delete(actor=anuj, instance=expense)

    assert entry.action == AuditLog.Action.DELETE


def test_the_audit_log_survives_the_actor_being_removed(groceries, anuj, make_expense):
    """History must not vanish when somebody's account is deleted."""
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")
    entry = record_create(actor=anuj, instance=expense)

    expense.paid_by = None
    AuditLog.objects.filter(pk=entry.pk).update(actor=None)
    entry.refresh_from_db()

    assert entry.pk is not None
    assert entry.actor is None


def test_diff_ignores_noise_fields(groceries, anuj, make_expense):
    expense = make_expense(category=groceries, paid_by=anuj, amount="450.00")

    assert "updated_at" not in snapshot(expense)
    assert "id" not in snapshot(expense)


def test_diff_reports_both_sides():
    assert diff({"a": 1}, {"a": 2}) == {"a": [1, 2]}
    assert diff({"a": 1}, {"a": 1}) == {}


# ------------------------------------------------------------ month close


def test_a_month_starts_open(anuj):
    assert is_closed(dt.date(2026, 9, 15)) is False


def test_closing_a_month_marks_it_closed(anuj):
    close_month(year=2026, month=9, actor=anuj)

    assert is_closed(dt.date(2026, 9, 15)) is True


def test_closing_only_affects_that_month(anuj):
    close_month(year=2026, month=9, actor=anuj)

    assert is_closed(dt.date(2026, 10, 1)) is False
    assert is_closed(dt.date(2026, 8, 31)) is False


def test_editing_in_a_closed_month_is_refused(anuj):
    close_month(year=2026, month=9, actor=anuj)

    with pytest.raises(ValidationError) as excinfo:
        assert_open(dt.date(2026, 9, 15))

    assert "September 2026" in str(excinfo.value)


def test_the_view_guard_raises_permission_denied(anuj):
    close_month(year=2026, month=9, actor=anuj)

    with pytest.raises(PermissionDenied):
        assert_open_or_403(dt.date(2026, 9, 15))


def test_an_open_month_passes_both_guards(anuj):
    assert_open(dt.date(2026, 9, 15))
    assert_open_or_403(dt.date(2026, 9, 15))


def test_closing_twice_is_harmless(anuj):
    close_month(year=2026, month=9, actor=anuj)
    close_month(year=2026, month=9, actor=anuj)

    assert MonthClose.objects.filter(year=2026, month=9).count() == 1


def test_closing_is_recorded_in_the_audit_log(anuj):
    close_month(year=2026, month=9, actor=anuj)

    entry = AuditLog.objects.filter(action=AuditLog.Action.CLOSE).first()
    assert entry.actor == anuj
    assert "September 2026" in entry.label


def test_reopening_makes_the_month_editable_again(anuj):
    close_month(year=2026, month=9, actor=anuj)

    reopen_month(year=2026, month=9, actor=anuj)

    assert is_closed(dt.date(2026, 9, 15)) is False
    assert_open(dt.date(2026, 9, 15))


def test_reopening_is_recorded_before_the_row_disappears(anuj):
    close_month(year=2026, month=9, actor=anuj)

    reopen_month(year=2026, month=9, actor=anuj)

    assert AuditLog.objects.filter(action=AuditLog.Action.REOPEN).exists()


def test_reopening_a_month_that_was_never_closed_is_harmless(anuj):
    reopen_month(year=2026, month=9, actor=anuj)

    assert is_closed(dt.date(2026, 9, 1)) is False
