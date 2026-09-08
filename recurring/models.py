from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from expenses.models import Category, Expense


class RecurringExpense(models.Model):
    """A template for a bill that turns up every month.

    Fixed ones (rent, WiFi) carry their amount. Variable ones (electricity)
    do not: they generate a draft with no amount, which the dashboard nags
    about until somebody reads the meter.
    """

    class Frequency(models.TextChoices):
        MONTHLY = "MONTHLY", "Every month"
        QUARTERLY = "QUARTERLY", "Every three months"
        YEARLY = "YEARLY", "Every year"

    description = models.CharField(max_length=140)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="recurring_templates"
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Leave blank for a bill that changes every month.",
    )
    is_variable = models.BooleanField(
        default=False,
        help_text="Generate a draft with no amount, for somebody to fill in.",
    )
    split_type = models.CharField(
        max_length=10, choices=Expense.SplitType.choices, default=Expense.SplitType.EQUAL
    )
    default_participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="recurring_templates",
        help_text="Leave empty to use whoever is living here when it generates.",
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="recurring_paid", null=True, blank=True,
        help_text="Who usually pays this. Can be changed on the generated expense.",
    )
    day_of_month = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    frequency = models.CharField(
        max_length=9, choices=Frequency.choices, default=Frequency.MONTHLY
    )
    covers_whole_month = models.BooleanField(
        default=True,
        help_text="Set the expense period to the whole month, so proration works.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day_of_month", "description"]

    def __str__(self) -> str:
        amount = "variable" if self.is_variable else f"₹{self.amount}"
        return f"{self.description} ({amount}, day {self.day_of_month})"

    def clean(self) -> None:
        super().clean()
        if not self.is_variable and self.amount is None:
            raise ValidationError(
                {"amount": "Enter an amount, or tick 'changes every month'."}
            )

    def due_in_month(self, year: int, month: int) -> bool:
        """Does this template produce an expense in this month?"""
        if not self.is_active:
            return False
        if self.frequency == self.Frequency.MONTHLY:
            return True
        if self.frequency == self.Frequency.QUARTERLY:
            return month % 3 == 1
        return month == 1

    def date_in_month(self, year: int, month: int) -> dt.date:
        """The template's day, clamped to months that are too short for it."""
        import calendar

        last = calendar.monthrange(year, month)[1]
        return dt.date(year, month, min(self.day_of_month, last))
