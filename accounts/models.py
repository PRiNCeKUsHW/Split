from __future__ import annotations

import datetime as dt

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q


class FlatmateManager(UserManager):
    """Queries the rest of the app uses to decide who counts as a flatmate."""

    def active_members(self) -> models.QuerySet["User"]:
        """Flatmates who live here now and should appear in split pickers."""
        today = dt.date.today()
        return self.filter(
            Q(is_active_member=True),
            Q(is_active=True),
            Q(left_on__isnull=True) | Q(left_on__gte=today),
        ).order_by("id")

    def members_on(self, day: dt.date) -> models.QuerySet["User"]:
        """Everyone whose tenancy covers ``day`` -- used by prorated splits."""
        return self.filter(
            Q(joined_on__lte=day),
            Q(left_on__isnull=True) | Q(left_on__gte=day),
        ).order_by("id")


class User(AbstractUser):
    """A flatmate.

    ``is_active`` (from AbstractUser) controls whether they can log in;
    ``is_active_member`` controls whether they are part of new splits. Someone
    who moved out keeps their login so they can settle up, but stops being
    added to the grocery bill.
    """

    display_name = models.CharField(max_length=60, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    upi_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. name@okhdfcbank -- used for the pay link and QR code.",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_active_member = models.BooleanField(
        default=True,
        help_text="Uncheck when someone moves out. They keep their login.",
    )
    joined_on = models.DateField(default=dt.date.today)
    left_on = models.DateField(null=True, blank=True)

    objects = FlatmateManager()

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        from django.core.exceptions import ValidationError

        if self.left_on and self.left_on < self.joined_on:
            raise ValidationError({"left_on": "Move-out date is before the move-in date."})

    @property
    def name(self) -> str:
        return self.display_name or self.get_full_name() or self.username

    @property
    def is_current_member(self) -> bool:
        if not self.is_active_member:
            return False
        return self.left_on is None or self.left_on >= dt.date.today()

    @property
    def initials(self) -> str:
        parts = [p for p in self.name.replace(".", " ").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def has_usable_login(self) -> bool:
        """False while an invited flatmate has not yet set a password."""
        return self.has_usable_password()


class AwayPeriod(models.Model):
    """Days a flatmate was not in the flat.

    Both ends are inclusive: 5–8 September means four days not paid for.
    That is the rule people can hold in their head — "mark every day you
    weren't here for dinner" — and the date picker maps to it one to one.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="away_periods"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        indexes = [models.Index(fields=["user", "start_date", "end_date"])]

    def __str__(self) -> str:
        return f"{self.user} away {self.start_date} to {self.end_date}"

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "The last day is before the first day."})

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1
