"""Populate a realistic month so the UI is worth looking at immediately.

Four flatmates, a month of the bills a shared flat in India actually has,
a couple of trips away, some settlements in every state, and the recurring
templates that generated the fixed bills.

    python manage.py seed_demo          # add to whatever is there
    python manage.py seed_demo --reset  # wipe the demo data, then re-seed
    python manage.py seed_demo --clear  # wipe the demo data and stop
"""

from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import AwayPeriod
from core.models import AuditLog, MonthClose
from expenses.models import Category, Comment, Expense
from expenses.services.presence import weights_for
from expenses.services.shares import rebuild_shares
from recurring.models import RecurringExpense
from settlements.models import Settlement

User = get_user_model()
PASSWORD = "flatsplit"

FLATMATES = [
    # username, display name, upi, phone, joined
    ("anuj", "Anuj Kush", "anuj@okhdfcbank", "98860 11223", dt.date(2025, 6, 1)),
    ("priya", "Priya Sharma", "priya@okaxis", "99012 44556", dt.date(2025, 6, 1)),
    ("rohit", "Rohit Nair", "rohit@ybl", "97400 77889", dt.date(2025, 11, 15)),
    ("meera", "Meera Iyer", "meera@okicici", "96320 99001", None),  # joins mid-month
]

# description, category, amount (None = variable draft), day offset, period?
ONE_OFFS = [
    ("Big Bazaar — weekly shop", "Groceries", "2840.00", 2, True),
    ("Milk and eggs", "Groceries", "410.00", 4, False),
    ("Gas cylinder refill", "Gas cylinder", "1120.00", 6, True),
    ("Zepto — late night snacks", "Groceries", "685.50", 8, False),
    ("Plumber for the kitchen tap", "Maintenance", "650.00", 9, False),
    ("Big Bazaar — weekly shop", "Groceries", "3120.00", 11, True),
    ("New mop and cleaning stuff", "One-off purchase", "745.00", 13, False),
    ("Vegetables from the market", "Groceries", "520.00", 15, False),
    ("Air filter for the AC", "Maintenance", "1200.00", 17, False),
    ("Big Bazaar — weekly shop", "Groceries", "2650.00", 19, True),
    ("Gas cylinder refill", "Gas cylinder", "1120.00", 22, True),
    ("Pest control", "Maintenance", "1800.00", 24, False),
    ("Dinner when Priya's parents visited", "One-off purchase", "3400.00", 25, False),
]


class Command(BaseCommand):
    help = "Create four flatmates and a month of realistic expenses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete existing demo data first."
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete the demo data and stop. Leaves an empty, usable flat.",
        )
        parser.add_argument(
            "--month", type=str, default="", help="YYYY-MM. Defaults to this month."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(20260908)

        if options["month"]:
            year, month = (int(part) for part in options["month"].split("-"))
        else:
            today = dt.date.today()
            year, month = today.year, today.month

        if options["clear"]:
            self._reset()
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Demo data removed."))
            self.stdout.write(
                f"  {Category.objects.count()} categories kept — they ship with the "
                "app, not with the demo."
            )
            if not User.objects.filter(is_superuser=True).exists():
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        "  No superuser left. Create one before you can log in:\n"
                        "    python manage.py createsuperuser"
                    )
                )
            return

        if options["reset"]:
            self._reset()

        people = self._make_flatmates(year, month)
        anuj, priya, rohit, meera = people

        self._make_away_periods(year, month, priya, rohit)
        templates = self._make_templates(year, month, people)
        self._make_recurring_expenses(year, month, templates, people)
        self._make_one_offs(year, month, people, rng)
        self._make_settlements(year, month, people)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("FlatSplit demo data is ready."))
        self.stdout.write(f"  {User.objects.count()} flatmates, "
                          f"{Expense.objects.count()} expenses, "
                          f"{Settlement.objects.count()} settlements")
        self.stdout.write("")
        self.stdout.write(f"  Log in as any of: {', '.join(u for u, *_ in FLATMATES)}")
        self.stdout.write(f"  Password: {PASSWORD}")
        self.stdout.write(self.style.WARNING("  Change these before anyone real uses it."))

    # -- pieces ------------------------------------------------------------

    def _reset(self) -> None:
        """Remove everything the demo created, in dependency order.

        Categories survive: they come from a migration, not from here.
        MonthClose has to go before the users do, because closed_by is
        PROTECT and would otherwise block the delete.
        """
        # delete() returns (total_including_cascades, {label: count}). Report
        # the per-model breakdown, or deleting 18 expenses reads as 81.
        removed: dict[str, int] = {}
        for queryset in (
            Comment.objects.all(),
            Settlement.objects.all(),
            Expense.objects.all(),
            RecurringExpense.objects.all(),
            AwayPeriod.objects.all(),
            MonthClose.objects.all(),
            AuditLog.objects.all(),
            User.objects.filter(username__in=[u for u, *_ in FLATMATES]),
        ):
            for label, count in queryset.delete()[1].items():
                removed[label] = removed.get(label, 0) + count

        for label in sorted(removed):
            self.stdout.write(f"  removed {removed[label]} {label.split('.')[-1]}")

    def _make_flatmates(self, year: int, month: int) -> list:
        people = []
        for index, (username, name, upi, phone, joined) in enumerate(FLATMATES):
            # The last flatmate moves in on the 11th, so move-in proration
            # is visible on the rent without anyone having to set it up.
            joined_on = joined or dt.date(year, month, 11)
            person, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "display_name": name,
                    "upi_id": upi,
                    "phone": phone,
                    "joined_on": joined_on,
                    "is_staff": index == 0,
                    "is_superuser": index == 0,
                },
            )
            if created:
                person.set_password(PASSWORD)
                person.save()
            people.append(person)

        self.stdout.write(f"Flatmates: {', '.join(p.name for p in people)}")
        return people

    def _make_away_periods(self, year, month, priya, rohit) -> None:
        AwayPeriod.objects.get_or_create(
            user=priya,
            start_date=dt.date(year, month, 5),
            end_date=dt.date(year, month, 12),
            defaults={"reason": "Home for a wedding"},
        )
        AwayPeriod.objects.get_or_create(
            user=rohit,
            start_date=dt.date(year, month, 20),
            end_date=dt.date(year, month, 23),
            defaults={"reason": "Work trip to Pune"},
        )
        self.stdout.write("Away periods: Priya 8 days, Rohit 4 days")

    def _make_templates(self, year, month, people) -> dict:
        anuj, priya, rohit, meera = people
        specs = [
            ("Rent", "Rent", "42000.00", False, 1, anuj),
            ("WiFi — ACT Fibernet", "WiFi", "1180.00", False, 5, priya),
            ("Electricity", "Electricity", None, True, 7, anuj),
            ("Maid — Lakshmi", "Maid", "3500.00", False, 3, priya),
            ("Society maintenance", "Maintenance", "2400.00", False, 10, rohit),
        ]
        templates = {}
        for description, category_name, amount, variable, day, payer in specs:
            template, _ = RecurringExpense.objects.get_or_create(
                description=description,
                defaults={
                    "category": Category.objects.get(name=category_name),
                    "amount": None if variable else Decimal(amount),
                    "is_variable": variable,
                    "paid_by": payer,
                    "day_of_month": day,
                },
            )
            templates[description] = template

        self.stdout.write(f"Recurring templates: {len(templates)}")
        return templates

    def _make_recurring_expenses(self, year, month, templates, people) -> None:
        """Run the real generator, so the demo matches what cron produces."""
        from recurring.services import generate_for_month

        result = generate_for_month(year, month, actor=people[0])
        self.stdout.write(
            f"Generated {result.created_count} recurring "
            f"({result.draft_count} still needing an amount)"
        )

    def _make_one_offs(self, year, month, people, rng) -> None:
        anuj, priya, rohit, meera = people
        payers = [anuj, priya, rohit, meera]
        created = 0

        for description, category_name, amount, day, whole_period in ONE_OFFS:
            date = dt.date(year, month, min(day, 28))
            payer = payers[created % len(payers)]

            # Meera cannot have paid for anything before she moved in.
            if payer == meera and date < meera.joined_on:
                payer = anuj

            expense = Expense.objects.create(
                description=description,
                amount=Decimal(amount),
                category=Category.objects.get(name=category_name),
                paid_by=payer,
                created_by=payer,
                date=date,
                # A weekly shop feeds people across the week, so it gets a
                # period and away days count against it.
                period_start=date - dt.timedelta(days=6) if whole_period else None,
                period_end=date if whole_period else None,
            )

            participants = [
                person
                for person in people
                if person.joined_on <= expense.period_end
            ]
            rebuild_shares(
                expense,
                participant_ids=[p.pk for p in participants],
                weights=weights_for(expense, participants),
            )
            created += 1

        Comment.objects.get_or_create(
            expense=Expense.objects.filter(description__startswith="Dinner").first(),
            author=rohit,
            defaults={"body": "Should this one be split four ways? I only had the starter."},
        )
        Comment.objects.get_or_create(
            expense=Expense.objects.filter(description__startswith="Dinner").first(),
            author=priya,
            defaults={"body": "Fair. Changed it to shares — you're on 1, we're on 2 each."},
        )

        self.stdout.write(f"One-off expenses: {created}")

    def _make_settlements(self, year, month, people) -> None:
        anuj, priya, rohit, meera = people

        confirmed = Settlement.objects.create(
            from_user=rohit, to_user=anuj, amount=Decimal("4200.00"),
            date=dt.date(year, month, 14), method=Settlement.Method.UPI,
            note="Part of the rent",
        )
        confirmed.confirm()

        Settlement.objects.create(
            from_user=meera, to_user=anuj, amount=Decimal("3000.00"),
            date=dt.date(year, month, 26), method=Settlement.Method.UPI,
            note="Rent for my half month",
        )
        Settlement.objects.create(
            from_user=priya, to_user=rohit, amount=Decimal("850.00"),
            date=dt.date(year, month, 27), method=Settlement.Method.CASH,
            note="Groceries",
        )

        self.stdout.write("Settlements: 1 confirmed, 2 waiting to be confirmed")
