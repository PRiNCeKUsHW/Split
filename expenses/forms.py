from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model

from core.services.monthclose import assert_open
from expenses.models import Category, Comment, Expense
from expenses.services.split import SplitError

User = get_user_model()


class ExpenseForm(forms.ModelForm):
    """Add or edit an expense, including whichever split inputs apply.

    The per-person fields are built in __init__ from the flat's members, so
    there is no manual request.POST digging anywhere: `exact_7`, `percent_7`
    and `units_7` are real form fields with real validation.
    """

    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Expense
        fields = [
            "amount", "description", "category", "paid_by", "date",
            "split_type", "period_start", "period_end", "notes", "receipt",
        ]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control amount-input",
                    "inputmode": "decimal",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                    "autofocus": True,
                }
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control form-control-lg", "placeholder": "What was it for?"}
            ),
            "category": forms.RadioSelect(),
            "paid_by": forms.Select(attrs={"class": "form-select form-select-lg"}),
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"}
            ),
            "split_type": forms.RadioSelect(),
            "period_start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "period_end": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "receipt": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.members = list(User.objects.active_members())

        # An edit must keep people who are in the split but have since left.
        if self.instance.pk:
            existing = list(
                User.objects.filter(expense_shares__expense=self.instance).distinct()
            )
            for person in existing:
                if person not in self.members:
                    self.members.append(person)

        member_ids = [m.pk for m in self.members]
        self.fields["participants"].queryset = User.objects.filter(pk__in=member_ids)
        self.fields["paid_by"].queryset = User.objects.filter(pk__in=member_ids)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = None

        if not self.is_bound:
            self.fields["date"].initial = dt.date.today()
            if actor and not self.instance.pk:
                self.fields["paid_by"].initial = actor.pk
            self.fields["participants"].initial = (
                [s.user_id for s in self.instance.shares.all()]
                if self.instance.pk
                else member_ids
            )

        for person in self.members:
            self.fields[f"exact_{person.pk}"] = forms.DecimalField(
                required=False, min_value=Decimal("0"), max_digits=10, decimal_places=2,
                widget=forms.NumberInput(
                    attrs={"class": "form-control money", "inputmode": "decimal", "step": "0.01"}
                ),
            )
            self.fields[f"percent_{person.pk}"] = forms.DecimalField(
                required=False, min_value=Decimal("0"), max_value=Decimal("100"),
                max_digits=5, decimal_places=2,
                widget=forms.NumberInput(
                    attrs={"class": "form-control money", "inputmode": "decimal", "step": "0.01"}
                ),
            )
            self.fields[f"units_{person.pk}"] = forms.IntegerField(
                required=False, min_value=0,
                widget=forms.NumberInput(
                    attrs={"class": "form-control money", "inputmode": "numeric"}
                ),
            )

        if self.instance.pk:
            for share in self.instance.shares.all():
                self.fields[f"exact_{share.user_id}"].initial = share.amount_owed
                self.fields[f"percent_{share.user_id}"].initial = share.percent
                self.fields[f"units_{share.user_id}"].initial = share.share_units

    # -- helpers the template uses to pair a person with their inputs -------

    def participant_rows(self):
        for person in self.members:
            yield {
                "person": person,
                "exact": self[f"exact_{person.pk}"],
                "percent": self[f"percent_{person.pk}"],
                "units": self[f"units_{person.pk}"],
            }

    def _chosen_ids(self) -> list[int]:
        chosen = self.cleaned_data.get("participants")
        if chosen:
            return [person.pk for person in chosen]
        return [person.pk for person in self.members]

    # -- validation --------------------------------------------------------

    def clean_date(self):
        date = self.cleaned_data["date"]
        # A closed month is read-only. Enforced here, not just in the UI.
        assert_open(date)
        if self.instance.pk and self.instance.date != date:
            assert_open(self.instance.date)
        return date

    def clean(self):
        cleaned = super().clean()
        split_type = cleaned.get("split_type")
        amount = cleaned.get("amount")
        ids = self._chosen_ids()

        if not ids:
            self.add_error("participants", "Pick at least one person.")
            return cleaned

        start, end = cleaned.get("period_start"), cleaned.get("period_end")
        if start and end and end < start:
            self.add_error("period_end", "The period ends before it starts.")

        # A draft has no amount yet, so there is nothing to validate against.
        if amount is None:
            self.split_inputs = {}
            return cleaned

        self.split_inputs = self._collect_split_inputs(split_type, ids)

        try:
            from expenses.services.split import compute_shares

            compute_shares(
                split_type=split_type,
                total=amount,
                payer_id=(cleaned.get("paid_by").pk if cleaned.get("paid_by") else ids[0]),
                participant_ids=ids,
                **self.split_inputs,
            )
        except SplitError as error:
            # One source of truth for these messages: the engine.
            self.add_error(None, str(error))

        return cleaned

    def _collect_split_inputs(self, split_type: str, ids: list[int]) -> dict:
        if split_type == Expense.SplitType.EXACT:
            return {
                "exact_amounts": {
                    pk: self.cleaned_data.get(f"exact_{pk}") or Decimal("0.00")
                    for pk in ids
                }
            }
        if split_type == Expense.SplitType.PERCENT:
            return {
                "percents": {
                    pk: self.cleaned_data.get(f"percent_{pk}") or Decimal("0")
                    for pk in ids
                }
            }
        if split_type == Expense.SplitType.SHARES:
            return {
                "share_units": {pk: self.cleaned_data.get(f"units_{pk}") or 0 for pk in ids}
            }
        return {}

    @property
    def participant_ids(self) -> list[int]:
        return self._chosen_ids()


class DraftAmountForm(forms.ModelForm):
    """The one-field form for filling in a variable bill."""

    class Meta:
        model = Expense
        fields = ["amount"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg money",
                    "inputmode": "decimal",
                    "step": "0.01",
                    "min": "0",
                    "autofocus": True,
                    "placeholder": "0.00",
                }
            )
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount is None:
            raise forms.ValidationError("Enter the amount from the bill.")
        assert_open(self.instance.date)
        return amount


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Add a note for the others…",
                }
            )
        }


class ExpenseFilterForm(forms.Form):
    """Filters for the list screen. Everything optional."""

    month = forms.CharField(required=False, widget=forms.HiddenInput)
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(), required=False, empty_label="All categories",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    paid_by = forms.ModelChoiceField(
        queryset=User.objects.none(), required=False, empty_label="Anyone paid",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    involving = forms.ModelChoiceField(
        queryset=User.objects.none(), required=False, empty_label="Anyone involved",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        everyone = User.objects.all()
        self.fields["paid_by"].queryset = everyone
        self.fields["involving"].queryset = everyone
