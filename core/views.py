from __future__ import annotations

import csv
import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.db.models import Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control
from django.views.generic import ListView, TemplateView, View

from core.models import AuditLog, MonthClose
from core.services.monthclose import close_month, is_closed, reopen_month
from expenses.models import Expense, ExpenseShare
from recurring.services import drafts_needing_amounts
from settlements.models import Settlement
from settlements.services.balances import get_balance_for, get_balance_rows, get_balances
from settlements.services.simplify import simplify_debts

User = get_user_model()
ZERO = Decimal("0.00")


class DashboardView(TemplateView):
    """One question, answered in the first line: am I up or down?"""

    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = dt.date.today()

        members = list(User.objects.active_members())
        balances = get_balances(members)
        by_id = {person.pk: person for person in members}

        my_balance = get_balance_for(user)
        month_expenses = Expense.objects.countable().for_month(today.year, today.month)

        context["balance"] = my_balance
        context["transfers"] = [
            {
                "from_user": by_id.get(t.from_user_id),
                "to_user": by_id.get(t.to_user_id),
                "amount": t.amount,
                "involves_me": user.pk in (t.from_user_id, t.to_user_id),
                "i_pay": t.from_user_id == user.pk,
            }
            for t in simplify_debts(balances)
        ]
        context["month_total"] = month_expenses.aggregate(t=Sum("amount"))["t"] or ZERO
        context["my_month_share"] = (
            ExpenseShare.objects.filter(
                user=user,
                expense__is_deleted=False,
                expense__is_draft=False,
                expense__date__year=today.year,
                expense__date__month=today.month,
            ).aggregate(t=Sum("amount_owed"))["t"]
            or ZERO
        )
        context["recent"] = Expense.objects.active().with_related()[:6]
        context["drafts"] = drafts_needing_amounts()[:5]
        context["pending"] = Settlement.objects.awaiting(user)
        context["month_label"] = today.strftime("%B")
        context["month_closed"] = is_closed(today)
        return context


class MonthlySummaryView(TemplateView):
    template_name = "core/summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = _month_from_request(self.request)

        expenses = Expense.objects.countable().for_month(year, month)
        members = list(User.objects.active_members())

        by_category = list(
            expenses.values("category__name", "category__color")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )
        grand_total = sum((row["total"] for row in by_category), ZERO)
        for row in by_category:
            row["percent"] = (
                float(row["total"] / grand_total * 100) if grand_total else 0.0
            )

        paid_by_person = {
            row["paid_by"]: row["total"]
            for row in expenses.values("paid_by").annotate(total=Sum("amount"))
        }
        owed_by_person = {
            row["user"]: row["total"]
            for row in ExpenseShare.objects.filter(
                expense__in=expenses
            ).values("user").annotate(total=Sum("amount_owed"))
        }

        context["year"], context["month"] = year, month
        context["month_label"] = dt.date(year, month, 1).strftime("%B %Y")
        context["by_category"] = by_category
        context["grand_total"] = grand_total
        context["per_person"] = [
            {
                "person": person,
                "paid": paid_by_person.get(person.pk, ZERO),
                "share": owed_by_person.get(person.pk, ZERO),
                "diff": paid_by_person.get(person.pk, ZERO)
                - owed_by_person.get(person.pk, ZERO),
            }
            for person in members
        ]
        context["expense_count"] = expenses.count()
        context["is_closed"] = is_closed(dt.date(year, month, 1))
        context["prev_month"] = _shift_month(year, month, -1)
        context["next_month"] = _shift_month(year, month, +1)
        return context


class MonthlyCSVView(View):
    """One row per share, so the export is useful in a spreadsheet."""

    def get(self, request):
        year, month = _month_from_request(request)
        expenses = (
            Expense.objects.countable()
            .for_month(year, month)
            .select_related("category", "paid_by")
            .prefetch_related("shares__user")
            .order_by("date", "id")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="flatsplit-{year}-{month:02d}.csv"'
        )
        # Excel needs the BOM to read the rupee sign and Indian names properly.
        response.write("﻿")

        writer = csv.writer(response)
        writer.writerow(
            ["Date", "Description", "Category", "Paid by", "Total",
             "Split", "Person", "Owes", "Basis"]
        )
        for expense in expenses:
            for share in expense.shares.all():
                writer.writerow([
                    expense.date.isoformat(),
                    expense.description,
                    expense.category.name,
                    expense.paid_by.name,
                    f"{expense.amount:.2f}",
                    expense.get_split_type_display(),
                    share.user.name,
                    f"{share.amount_owed:.2f}",
                    share.basis,
                ])
        return response


class MonthCloseView(View):
    def post(self, request):
        year, month = _month_from_request(request)
        label = dt.date(year, month, 1).strftime("%B %Y")

        if request.POST.get("action") == "reopen":
            reopen_month(year=year, month=month, actor=request.user)
            messages.success(request, f"{label} is open again.")
        else:
            close_month(year=year, month=month, actor=request.user)
            messages.success(request, f"{label} is closed. Its expenses are now read-only.")

        return redirect(f"{request.path.replace('close/', 'summary/')}?month={year}-{month:02d}")


class AuditLogView(ListView):
    template_name = "core/audit_log.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        return AuditLog.objects.select_related("actor")


class BalancesView(TemplateView):
    """Everybody's position, with the working shown."""

    template_name = "core/balances.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        members = list(User.objects.active_members())
        context["rows"] = sorted(
            get_balance_rows(members), key=lambda row: row.net, reverse=True
        )
        context["closed_months"] = MonthClose.objects.select_related("closed_by")[:12]
        return context


@login_not_required
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request: HttpRequest) -> HttpResponse:
    """Serve sw.js from the site root so its scope covers every page.

    Rendered as a template rather than shipped as a static file so the cache
    name carries the app version -- bumping the version retires stale caches
    on every phone without anyone clearing site data.
    """
    from django.template.loader import render_to_string

    body = render_to_string(
        "sw.js",
        {"version": getattr(settings, "APP_VERSION", "1"), "static_url": settings.STATIC_URL},
        request=request,
    )
    return HttpResponse(body, content_type="application/javascript")


# ------------------------------------------------------------------ helpers


def _month_from_request(request) -> tuple[int, int]:
    raw = request.GET.get("month") or request.POST.get("month") or ""
    try:
        year, month = raw.split("-")
        return int(year), int(month)
    except (ValueError, AttributeError):
        today = dt.date.today()
        return today.year, today.month


def _shift_month(year: int, month: int, delta: int) -> str:
    index = (year * 12 + month - 1) + delta
    return f"{index // 12}-{index % 12 + 1:02d}"
