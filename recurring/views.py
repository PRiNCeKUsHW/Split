from __future__ import annotations

import datetime as dt

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from recurring.models import RecurringExpense
from recurring.services import generate_for_month

User = get_user_model()


class RecurringForm(forms.ModelForm):
    class Meta:
        model = RecurringExpense
        fields = [
            "description", "category", "amount", "is_variable", "split_type",
            "paid_by", "default_participants", "day_of_month", "frequency",
            "covers_whole_month", "is_active",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control form-control-lg"}),
            "category": forms.Select(attrs={"class": "form-select form-select-lg"}),
            "amount": forms.NumberInput(
                attrs={"class": "form-control form-control-lg money",
                       "inputmode": "decimal", "step": "0.01"}
            ),
            "split_type": forms.Select(attrs={"class": "form-select"}),
            "paid_by": forms.Select(attrs={"class": "form-select"}),
            "default_participants": forms.CheckboxSelectMultiple(),
            "day_of_month": forms.NumberInput(
                attrs={"class": "form-control", "inputmode": "numeric", "min": 1, "max": 31}
            ),
            "frequency": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        members = User.objects.active_members()
        self.fields["paid_by"].queryset = members
        self.fields["default_participants"].queryset = members
        self.fields["amount"].required = False


class RecurringListView(ListView):
    model = RecurringExpense
    template_name = "recurring/recurring_list.html"
    context_object_name = "templates"

    def get_queryset(self):
        return RecurringExpense.objects.select_related("category", "paid_by").prefetch_related(
            "default_participants"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = dt.date.today()
        context["this_month"] = today.strftime("%B %Y")
        return context


class RecurringCreateView(CreateView):
    model = RecurringExpense
    form_class = RecurringForm
    template_name = "recurring/recurring_form.html"
    success_url = reverse_lazy("recurring:list")

    def form_valid(self, form):
        messages.success(self.request, f"Added the {form.instance.description} template.")
        return super().form_valid(form)


class RecurringUpdateView(UpdateView):
    model = RecurringExpense
    form_class = RecurringForm
    template_name = "recurring/recurring_form.html"
    success_url = reverse_lazy("recurring:list")

    def form_valid(self, form):
        messages.success(self.request, "Saved.")
        return super().form_valid(form)


class RecurringDeleteView(DeleteView):
    model = RecurringExpense
    success_url = reverse_lazy("recurring:list")
    template_name = "recurring/recurring_confirm_delete.html"


class GenerateNowView(View):
    """Manual trigger, for when cron has not run or somebody is impatient."""

    def post(self, request):
        today = dt.date.today()
        result = generate_for_month(today.year, today.month, actor=request.user)

        if result.created_count:
            note = f"Created {result.created_count} for {today:%B}."
            if result.draft_count:
                note += f" {result.draft_count} still need an amount."
            messages.success(request, note)
        else:
            messages.info(request, f"{today:%B} is already generated. Nothing to do.")

        return redirect("recurring:list")
