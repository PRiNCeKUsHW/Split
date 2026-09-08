from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class SettlementQuerySet(models.QuerySet):
    def confirmed(self) -> "SettlementQuerySet":
        return self.filter(status=Settlement.Status.CONFIRMED)

    def pending(self) -> "SettlementQuerySet":
        return self.filter(status=Settlement.Status.PENDING)

    def awaiting(self, user) -> "SettlementQuerySet":
        """Payments this person needs to confirm they actually received."""
        return self.pending().filter(to_user=user).select_related("from_user", "to_user")

    def with_related(self) -> "SettlementQuerySet":
        return self.select_related("from_user", "to_user")


class Settlement(models.Model):
    """One person paying another back.

    Recorded by the payer, but it does not move any balance until the
    receiver confirms it. Otherwise "I sent it, check your phone" would be
    enough to zero out a debt.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Waiting to be confirmed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"

    class Method(models.TextChoices):
        UPI = "UPI", "UPI"
        CASH = "CASH", "Cash"
        BANK = "BANK", "Bank transfer"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="settlements_sent"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="settlements_received",
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    date = models.DateField(default=dt.date.today)
    method = models.CharField(max_length=6, choices=Method.choices, default=Method.UPI)
    note = models.CharField(max_length=140, blank=True)
    proof = models.ImageField(upload_to="proofs/%Y/%m/", blank=True, null=True)

    status = models.CharField(
        max_length=9, choices=Status.choices, default=Status.PENDING
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SettlementQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["status", "to_user"])]

    def __str__(self) -> str:
        return f"{self.from_user} → {self.to_user}: ₹{self.amount} ({self.status})"

    def clean(self) -> None:
        super().clean()
        if self.from_user_id and self.from_user_id == self.to_user_id:
            raise ValidationError("You cannot settle up with yourself.")

    def confirm(self) -> None:
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at"])

    def reject(self) -> None:
        self.status = self.Status.REJECTED
        self.confirmed_at = None
        self.save(update_fields=["status", "confirmed_at"])

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def affects_balances(self) -> bool:
        return self.status == self.Status.CONFIRMED
