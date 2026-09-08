from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from expenses.services.split import SplitType as SplitConstants


class Category(models.Model):
    """A kind of expense, plus how it should be prorated.

    The two proration flags are independent on purpose. Groceries respond to
    who was actually in the flat; rent does not, because a room you are away
    from is still a room you are renting.
    """

    name = models.CharField(max_length=40, unique=True)
    icon = models.CharField(max_length=30, blank=True)
    color = models.CharField(max_length=7, default="#3a34c9")
    is_recurring_by_default = models.BooleanField(default=False)
    prorate_by_tenancy = models.BooleanField(
        default=False,
        verbose_name="Prorate by move-in / move-out",
        help_text="Charge only for the days someone was living here.",
    )
    prorate_by_presence = models.BooleanField(
        default=False,
        verbose_name="Prorate by away days",
        help_text="Also discount the days someone was away. Use for food, gas, maid.",
    )
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.prorate_by_presence and not self.prorate_by_tenancy:
            raise ValidationError(
                {
                    "prorate_by_tenancy": (
                        "Away-day proration needs move-in proration too — nobody can "
                        "owe for days before they moved in."
                    )
                }
            )


class ExpenseQuerySet(models.QuerySet):
    def active(self) -> "ExpenseQuerySet":
        """Everything not soft-deleted."""
        return self.filter(is_deleted=False)

    def countable(self) -> "ExpenseQuerySet":
        """Everything that moves money: live, and with an amount filled in."""
        return self.filter(is_deleted=False, is_draft=False, amount__isnull=False)

    def for_month(self, year: int, month: int) -> "ExpenseQuerySet":
        return self.filter(date__year=year, date__month=month)

    def with_related(self) -> "ExpenseQuerySet":
        """The joins every list view needs. Use this instead of hand-rolling."""
        return self.select_related("category", "paid_by", "created_by").prefetch_related(
            "shares__user"
        )


class Expense(models.Model):
    class SplitType(models.TextChoices):
        EQUAL = SplitConstants.EQUAL, "Equally"
        EXACT = SplitConstants.EXACT, "Exact amounts"
        PERCENT = SplitConstants.PERCENT, "Percentages"
        SHARES = SplitConstants.SHARES, "Shares"

    description = models.CharField(max_length=140)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Leave blank for a variable bill nobody knows the total of yet.",
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="expenses")
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_paid"
    )
    date = models.DateField(default=dt.date.today)

    # The window a prorated split measures presence over. Both default to
    # `date`, so downstream code never has to branch on null.
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    split_type = models.CharField(
        max_length=10, choices=SplitType.choices, default=SplitType.EQUAL
    )
    notes = models.TextField(blank=True)
    receipt = models.ImageField(upload_to="receipts/%Y/%m/", blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_draft = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Set when a recurring template produced this expense. It is what makes
    # `generate_recurring` idempotent: the month is checked against this link
    # before anything is created.
    source_template = models.ForeignKey(
        "recurring.RecurringExpense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_expenses",
    )

    objects = ExpenseQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["-date"]),
            models.Index(fields=["is_deleted", "is_draft"]),
        ]

    def __str__(self) -> str:
        amount = "no amount yet" if self.amount is None else f"₹{self.amount}"
        return f"{self.description} ({amount})"

    def clean(self) -> None:
        super().clean()
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValidationError({"period_end": "The period ends before it starts."})

    def save(self, *args, **kwargs) -> None:
        # A blank period means a single-day expense.
        if self.period_start is None:
            self.period_start = self.date
        if self.period_end is None:
            self.period_end = self.date
        # Draft status is derived, never set by hand — one less thing to
        # forget when someone fills the amount in.
        self.is_draft = self.amount is None
        super().save(*args, **kwargs)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])

    @property
    def needs_amount(self) -> bool:
        return self.amount is None

    @property
    def period_days(self) -> int:
        """Length of the split window, both ends inclusive."""
        return (self.period_end - self.period_start).days + 1

    @property
    def shares_total(self) -> Decimal:
        return sum((share.amount_owed for share in self.shares.all()), Decimal("0.00"))


class ExpenseShare(models.Model):
    """One person's slice, plus the input that produced it.

    The `share_units` / `percent` / `present_days` columns are what let the
    detail screen explain a number instead of merely asserting it.
    """

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expense_shares"
    )
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)

    share_units = models.PositiveIntegerField(null=True, blank=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    present_days = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "user"], name="one_share_per_person_per_expense"
            )
        ]
        ordering = ["user_id"]

    def __str__(self) -> str:
        return f"{self.user} owes ₹{self.amount_owed}"

    @property
    def basis(self) -> str:
        """Short human explanation of where this number came from."""
        if self.present_days is not None:
            return f"{self.present_days} day{'s' if self.present_days != 1 else ''}"
        if self.share_units is not None:
            return f"{self.share_units} share{'s' if self.share_units != 1 else ''}"
        if self.percent is not None:
            return f"{self.percent}%"
        return ""


class Comment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.author}: {self.body[:40]}"
