"""Create this month's recurring expenses. Safe to run from cron every day."""

from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand

from recurring.services import generate_for_month


class Command(BaseCommand):
    help = "Generate recurring expenses for a month. Running twice is harmless."

    def add_arguments(self, parser):
        today = dt.date.today()
        parser.add_argument("--year", type=int, default=today.year)
        parser.add_argument("--month", type=int, default=today.month)
        parser.add_argument(
            "--dry-run", action="store_true", help="Report without writing anything."
        )

    def handle(self, *args, **options):
        year, month = options["year"], options["month"]

        if options["dry_run"]:
            from django.db import transaction

            with transaction.atomic():
                result = generate_for_month(year, month)
                self._report(result, year, month, dry=True)
                transaction.set_rollback(True)
            return

        result = generate_for_month(year, month)
        self._report(result, year, month, dry=False)

    def _report(self, result, year, month, *, dry: bool) -> None:
        prefix = "Would create" if dry else "Created"
        label = f"{dt.date(year, month, 1):%B %Y}"

        self.stdout.write(self.style.SUCCESS(f"{prefix} {result.created_count} for {label}"))
        for expense in result.created:
            amount = "needs an amount" if expense.is_draft else f"₹{expense.amount}"
            self.stdout.write(f"  + {expense.description} — {amount}")
        for name in result.skipped:
            self.stdout.write(f"  · {name} already generated")
        if result.draft_count:
            self.stdout.write(
                self.style.WARNING(f"{result.draft_count} need an amount filling in.")
            )
