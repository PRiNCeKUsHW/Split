"""Recording who changed what.

Snapshots are stored as {field: [before, after]} so a diff can be rendered
without keeping a full copy of every version.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.models import AuditLog

# Noise nobody wants in an audit trail.
IGNORED_FIELDS = {"updated_at", "created_at", "id"}


def _serialise(value: Any) -> Any:
    """Make a field value safe for JSONField."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def snapshot(instance, fields: list[str] | None = None) -> dict[str, Any]:
    """Field values as they stand right now."""
    names = fields or [
        f.name
        for f in instance._meta.fields
        if f.name not in IGNORED_FIELDS
    ]
    return {name: _serialise(getattr(instance, name, None)) for name in names}


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Only the fields that actually moved."""
    return {
        key: [before.get(key), after.get(key)]
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    }


def record(
    *,
    actor,
    action: str,
    instance,
    changes: dict | None = None,
    label: str = "",
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        action=action,
        model=instance.__class__.__name__,
        object_id=instance.pk,
        label=label or str(instance)[:140],
        changes=changes or {},
    )


def record_create(*, actor, instance) -> AuditLog:
    return record(
        actor=actor,
        action=AuditLog.Action.CREATE,
        instance=instance,
        changes={k: [None, v] for k, v in snapshot(instance).items()},
    )


def record_update(*, actor, instance, before: dict) -> AuditLog | None:
    """Returns None when nothing actually changed -- no empty log entries."""
    changes = diff(before, snapshot(instance))
    if not changes:
        return None
    return record(
        actor=actor, action=AuditLog.Action.UPDATE, instance=instance, changes=changes
    )


def record_delete(*, actor, instance) -> AuditLog:
    return record(actor=actor, action=AuditLog.Action.DELETE, instance=instance)


def history_for(instance):
    return AuditLog.objects.filter(
        model=instance.__class__.__name__, object_id=instance.pk
    ).select_related("actor")
