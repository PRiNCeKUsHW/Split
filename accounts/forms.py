from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from accounts.models import User


class FlatLoginForm(AuthenticationForm):
    """Login tuned for phone keyboards."""

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "autocapitalize": "none",
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": "Username",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "autocomplete": "current-password",
                "placeholder": "Password",
            }
        )
    )


class InviteFlatmateForm(forms.Form):
    """Just enough to create the account; they fill in the rest themselves."""

    username = forms.SlugField(
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "autocapitalize": "none",
                "placeholder": "priya",
            }
        ),
        help_text="Lowercase, no spaces. This is what they type to log in.",
    )
    display_name = forms.CharField(
        max_length=60,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-lg", "placeholder": "Priya Sharma"}
        ),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-lg", "inputmode": "tel"}
        ),
    )
    upi_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "autocapitalize": "none",
                "placeholder": "priya@okhdfcbank",
            }
        ),
    )

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].lower()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Somebody already has that username.")
        return username


class MemberProfileForm(forms.ModelForm):
    """Editing an existing flatmate: contact details and tenancy dates."""

    class Meta:
        model = User
        fields = ["display_name", "phone", "upi_id", "avatar", "joined_on", "left_on"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control form-control-lg"}),
            "phone": forms.TextInput(
                attrs={"class": "form-control form-control-lg", "inputmode": "tel"}
            ),
            "upi_id": forms.TextInput(
                attrs={"class": "form-control form-control-lg", "autocapitalize": "none"}
            ),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "joined_on": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"}
            ),
            "left_on": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        joined_on, left_on = cleaned.get("joined_on"), cleaned.get("left_on")
        if joined_on and left_on and left_on < joined_on:
            self.add_error("left_on", "Move-out date is before the move-in date.")
        return cleaned


class AwayPeriodForm(forms.ModelForm):
    """Marking days you were not in the flat.

    Both dates are inclusive: 5th to 8th means four days you do not pay for.
    The help text says so, because this is the rule people get wrong.
    """

    class Meta:
        from accounts.models import AwayPeriod

        model = AwayPeriod
        fields = ["user", "start_date", "end_date", "reason"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select form-select-lg"}),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"}
            ),
            "reason": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Trip home, work travel…"}
            ),
        }
        help_texts = {
            "end_date": "Both days count as away. 5th to 8th is four days.",
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.active_members()
        if actor and not self.instance.pk:
            self.fields["user"].initial = actor.pk

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "The last day is before the first day.")
        return cleaned
