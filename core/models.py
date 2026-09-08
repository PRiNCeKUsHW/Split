from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Who changed what, and what it looked like before.

    Money arguments are usually really arguments about what changed. This is
    the answer to "I'm sure that said 400 yesterday".
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Created"
        UPDATE = "UPDATE", "Edited"
        DELETE = "DELETE", "Deleted"
        CONFIRM = "CONFIRM", "Confirmed"
        REJECT = "REJECT", "Rejected"
        CLOSE = "CLOSE", "Closed the month"
        REOPEN = "REOPEN", "Reopened the month"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=8, choices=Action.choices)
    model = models.CharField(max_length=40)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    label = models.CharField(max_length=140, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["model", "object_id"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        who = self.actor.name if self.actor else "somebody"
        return f"{who} {self.get_action_display().lower()} {self.model} #{self.object_id}"

    @property
    def changed_fields(self) -> list[str]:
        return sorted(self.changes.keys())


class MonthCloseQuerySet(models.QuerySet):
    def is_closed(self, day: dt.date) -> bool:
        return self.filter(year=day.year, month=day.month).exists()


class MonthClose(models.Model):
    """A month someone has declared final.

    Once closed, expenses dated in that month stop being editable. Enforced
    in the forms and the views, not merely hidden in the UI.
    """

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="months_closed"
    )
    closed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=140, blank=True)

    objects = MonthCloseQuerySet.as_manager()

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="one_close_per_month")
        ]

    def __str__(self) -> str:
        return f"{dt.date(self.year, self.month, 1):%B %Y} (closed)"

    @property
    def first_day(self) -> dt.date:
        return dt.date(self.year, self.month, 1)
