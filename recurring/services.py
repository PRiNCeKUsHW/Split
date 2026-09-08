"""Generating a month's recurring expenses.

Idempotency is the whole design constraint here: this runs from cron, and
cron runs things twice. A template that has already produced an expense for
a given month must never produce a second one, so generated expenses carry a
`source_template` link and the month is looked up before anything is created.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass, field

from django.db import transaction

from expenses.models import Expense
from expenses.services.presence import weights_for
from expenses.services.shares import rebuild_shares
from recurring.models import RecurringExpense


@dataclass
class GenerationResult:
    created: list[Expense] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def draft_count(self) -> int:
        return sum(1 for expense in self.created if expense.is_draft)

    def __str__(self) -> str:
        return f"{self.created_count} created, {len(self.skipped)} already there"


def _participants_for(template: RecurringExpense) -> list:
    from django.contrib.auth import get_user_model

    chosen = list(template.default_participants.all())
    return chosen or list(get_user_model().objects.active_members())


@transaction.atomic
def generate_for_month(
    year: int, month: int, *, actor=None, templates=None
) -> GenerationResult:
    """Create this month's expenses from the active templates.

    Safe to run repeatedly: anything already generated for the month is left
    alone, including drafts somebody has since filled in.
    """
    result = GenerationResult()
    queryset = (
        templates
        if templates is not None
        else RecurringExpense.objects.filter(is_active=True).select_related(
            "category", "paid_by"
        )
    )

    last_day = calendar.monthrange(year, month)[1]
    month_start = dt.date(year, month, 1)
    month_end = dt.date(year, month, last_day)

    already = set(
        Expense.objects.filter(
            source_template__isnull=False, date__year=year, date__month=month
        ).values_list("source_template_id", flat=True)
    )

    for template in queryset:
        if not template.due_in_month(year, month):
            continue
        if template.pk in already:
            result.skipped.append(template.description)
            continue

        payer = template.paid_by or _participants_for(template)[0]
        expense = Expense.objects.create(
            description=template.description,
            amount=None if template.is_variable else template.amount,
            category=template.category,
            paid_by=payer,
            created_by=actor or payer,
            date=template.date_in_month(year, month),
            period_start=month_start if template.covers_whole_month else None,
            period_end=month_end if template.covers_whole_month else None,
            split_type=template.split_type,
            source_template=template,
            notes=f"Generated from the {template.description} template.",
        )

        people = _participants_for(template)
        rebuild_shares(
            expense,
            participant_ids=[person.pk for person in people],
            weights=weights_for(expense, people),
        )
        result.created.append(expense)

    return result


def generate_for_today(*, actor=None) -> GenerationResult:
    today = dt.date.today()
    return generate_for_month(today.year, today.month, actor=actor)


def drafts_needing_amounts():
    """Generated bills still waiting for somebody to read the meter."""
    return (
        Expense.objects.filter(is_draft=True, is_deleted=False)
        .select_related("category", "paid_by")
        .order_by("date")
    )
