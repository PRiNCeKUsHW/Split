"""Month closing.

A closed month is read-only. This is enforced here and called from the forms
and the views -- hiding the edit button is not enforcement.
"""

from __future__ import annotations

import datetime as dt

from django.core.exceptions import PermissionDenied, ValidationError

from core.models import AuditLog, MonthClose
from core.services.audit import record


def is_closed(day: dt.date) -> bool:
    return MonthClose.objects.filter(year=day.year, month=day.month).exists()


def closed_months() -> set[tuple[int, int]]:
    return set(MonthClose.objects.values_list("year", "month"))


def assert_open(day: dt.date) -> None:
    """Raise if this date falls in a closed month. Message is user-facing."""
    if is_closed(day):
        raise ValidationError(
            f"{day:%B %Y} is closed. Reopen the month before changing anything in it."
        )


def assert_open_or_403(day: dt.date) -> None:
    """View-layer guard, for requests that should never have got this far."""
    if is_closed(day):
        raise PermissionDenied(f"{day:%B %Y} is closed.")


def close_month(*, year: int, month: int, actor, note: str = "") -> MonthClose:
    closure, created = MonthClose.objects.get_or_create(
        year=year, month=month, defaults={"closed_by": actor, "note": note}
    )
    if created:
        record(
            actor=actor,
            action=AuditLog.Action.CLOSE,
            instance=closure,
            label=f"{dt.date(year, month, 1):%B %Y}",
        )
    return closure


def reopen_month(*, year: int, month: int, actor) -> None:
    closure = MonthClose.objects.filter(year=year, month=month).first()
    if not closure:
        return
    record(
        actor=actor,
        action=AuditLog.Action.REOPEN,
        instance=closure,
        label=f"{dt.date(year, month, 1):%B %Y}",
    )
    closure.delete()
