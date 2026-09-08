from __future__ import annotations

import datetime as dt

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, View

from core.services.audit import history_for
from core.services.monthclose import is_closed
from expenses.forms import CommentForm, DraftAmountForm, ExpenseFilterForm, ExpenseForm
from expenses.models import Expense
from expenses.services.crud import (
    create_expense,
    delete_expense,
    fill_draft_amount,
    update_expense,
)

PAGE_SIZE = 20


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


class ExpenseCreateView(View):
    """The most-used screen. Posts over HTMX so the keypad never reloads."""

    template_name = "expenses/expense_form.html"

    def get(self, request):
        form = ExpenseForm(actor=request.user)
        return render(request, self.template_name, {"form": form, "is_edit": False})

    def post(self, request):
        form = ExpenseForm(request.POST, request.FILES, actor=request.user)
        if not form.is_valid():
            return render(
                request,
                "expenses/partials/_expense_form_body.html",
                {"form": form, "is_edit": False},
                status=422,
            )

        expense = create_expense(form=form, actor=request.user)
        messages.success(request, f"Added {expense.description}.")

        if _is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("expenses:detail", args=[expense.pk])
            return response
        return redirect("expenses:detail", pk=expense.pk)


class ExpenseUpdateView(View):
    template_name = "expenses/expense_form.html"

    def get_object(self, pk) -> Expense:
        return get_object_or_404(Expense.objects.active(), pk=pk)

    def get(self, request, pk):
        expense = self.get_object(pk)
        form = ExpenseForm(instance=expense, actor=request.user)
        return render(
            request, self.template_name,
            {"form": form, "expense": expense, "is_edit": True},
        )

    def post(self, request, pk):
        expense = self.get_object(pk)
        form = ExpenseForm(request.POST, request.FILES, instance=expense, actor=request.user)
        if not form.is_valid():
            return render(
                request,
                "expenses/partials/_expense_form_body.html",
                {"form": form, "expense": expense, "is_edit": True},
                status=422,
            )

        update_expense(expense=expense, form=form, actor=request.user)
        messages.success(request, "Saved.")

        if _is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("expenses:detail", args=[expense.pk])
            return response
        return redirect("expenses:detail", pk=expense.pk)


class ExpenseListView(ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        queryset = Expense.objects.active().with_related()
        params = self.request.GET

        month = params.get("month")
        if month:
            try:
                year_part, month_part = month.split("-")
                queryset = queryset.for_month(int(year_part), int(month_part))
            except (ValueError, TypeError):
                pass

        if params.get("category"):
            queryset = queryset.filter(category_id=params["category"])
        if params.get("paid_by"):
            queryset = queryset.filter(paid_by_id=params["paid_by"])
        if params.get("involving"):
            queryset = queryset.filter(shares__user_id=params["involving"]).distinct()
        if params.get("q"):
            queryset = queryset.filter(
                Q(description__icontains=params["q"]) | Q(notes__icontains=params["q"])
            )
        return queryset

    def get_template_names(self):
        # HTMX "load more" asks for just the next slice of rows.
        if _is_htmx(self.request):
            return ["expenses/partials/_expense_rows.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = ExpenseFilterForm(self.request.GET or None)
        context["months"] = _recent_months()
        context["active_month"] = self.request.GET.get("month", "")
        context["querystring"] = _querystring_without_page(self.request.GET)
        return context


class ExpenseDetailView(DetailView):
    model = Expense
    template_name = "expenses/expense_detail.html"
    context_object_name = "expense"

    def get_queryset(self):
        return Expense.objects.with_related().select_related("source_template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expense = self.object
        context["shares"] = expense.shares.select_related("user").order_by("-amount_owed")
        context["comments"] = expense.comments.select_related("author")
        context["comment_form"] = CommentForm()
        context["history"] = history_for(expense)[:20]
        context["month_closed"] = is_closed(expense.date)
        context["draft_form"] = DraftAmountForm(instance=expense) if expense.is_draft else None
        return context


class ExpenseDeleteView(View):
    def post(self, request, pk):
        expense = get_object_or_404(Expense.objects.active(), pk=pk)
        delete_expense(expense=expense, actor=request.user)
        messages.success(request, f"Deleted {expense.description}.")
        return redirect("expenses:list")


class DraftAmountView(View):
    """Fill in a variable bill. Swaps in place over HTMX."""

    def post(self, request, pk):
        expense = get_object_or_404(Expense.objects.active(), pk=pk)
        form = DraftAmountForm(request.POST, instance=expense)

        if not form.is_valid():
            return render(
                request, "expenses/partials/_draft_form.html",
                {"expense": expense, "draft_form": form}, status=422,
            )

        fill_draft_amount(
            expense=expense, amount=form.cleaned_data["amount"], actor=request.user
        )
        messages.success(request, f"{expense.description} is now split.")

        if _is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("expenses:detail", args=[expense.pk])
            return response
        return redirect("expenses:detail", pk=expense.pk)


class CommentCreateView(View):
    def post(self, request, pk):
        expense = get_object_or_404(Expense.objects.active(), pk=pk)
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.expense = expense
            comment.author = request.user
            comment.save()

        return render(
            request,
            "expenses/partials/_comments.html",
            {
                "expense": expense,
                "comments": expense.comments.select_related("author"),
                "comment_form": CommentForm(),
            },
        )


class SplitPreviewView(View):
    """Live preview of the split as somebody types. Read-only, no writes."""

    def post(self, request):
        form = ExpenseForm(request.POST, actor=request.user)
        form.is_valid()  # populates cleaned_data and any errors

        preview, error = [], None
        amount = form.cleaned_data.get("amount") if hasattr(form, "cleaned_data") else None

        if amount is not None:
            try:
                from expenses.services.presence import weights_for
                from expenses.services.split import compute_shares

                ids = form.participant_ids
                people = [p for p in form.members if p.pk in ids]
                stub = Expense(
                    amount=amount,
                    category=form.cleaned_data.get("category"),
                    split_type=form.cleaned_data.get("split_type"),
                    date=form.cleaned_data.get("date") or dt.date.today(),
                    period_start=form.cleaned_data.get("period_start"),
                    period_end=form.cleaned_data.get("period_end"),
                )
                stub.period_start = stub.period_start or stub.date
                stub.period_end = stub.period_end or stub.date

                weights = weights_for(stub, people) if stub.category else None
                payer = form.cleaned_data.get("paid_by")
                shares = compute_shares(
                    split_type=stub.split_type,
                    total=amount,
                    payer_id=payer.pk if payer else ids[0],
                    participant_ids=ids,
                    weights=weights,
                    **getattr(form, "split_inputs", {}),
                )
                by_id = {p.pk: p for p in people}
                preview = [
                    {
                        "person": by_id[pk],
                        "amount": value,
                        "days": (weights or {}).get(pk),
                    }
                    for pk, value in shares.items()
                ]
            except Exception as exc:  # surfaced to the user, never swallowed
                error = str(exc)

        return render(
            request,
            "expenses/partials/_split_preview.html",
            {"preview": preview, "preview_error": error, "total": amount},
        )


def _recent_months(count: int = 12) -> list[dict]:
    today = dt.date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(
            {"value": f"{year}-{month:02d}", "label": dt.date(year, month, 1).strftime("%b %Y")}
        )
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return months


def _querystring_without_page(params) -> str:
    pairs = [
        f"{key}={value}"
        for key, value in params.items()
        if key != "page" and value
    ]
    return "&".join(pairs)
