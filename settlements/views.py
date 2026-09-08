from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView, View

from core.models import AuditLog
from core.services.audit import record
from settlements.models import Settlement
from settlements.services.balances import get_balance_for, get_balances
from settlements.services.simplify import simplify_debts
from settlements.services.upi import payment_qr, upi_link

User = get_user_model()


class SettlementForm(forms.ModelForm):
    class Meta:
        model = Settlement
        fields = ["amount", "date", "method", "note", "proof"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg money",
                    "inputmode": "decimal",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control form-control-lg"}
            ),
            "method": forms.RadioSelect(),
            "note": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional note"}
            ),
            "proof": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount is None or amount <= 0:
            raise forms.ValidationError("Enter an amount greater than zero.")
        return amount


class SettleUpView(View):
    """Who pays whom, simplified. The dashboard's plan, in full."""

    def get(self, request):
        members = list(User.objects.active_members())
        balances = get_balances(members)
        by_id = {person.pk: person for person in members}

        transfers = [
            {
                "from_user": by_id.get(t.from_user_id),
                "to_user": by_id.get(t.to_user_id),
                "amount": t.amount,
                "involves_me": request.user.pk in (t.from_user_id, t.to_user_id),
                "i_pay": t.from_user_id == request.user.pk,
            }
            for t in simplify_debts(balances)
        ]

        return render(
            request,
            "settlements/settle_up.html",
            {
                "transfers": transfers,
                "my_balance": get_balance_for(request.user),
                "pending_count": Settlement.objects.awaiting(request.user).count(),
            },
        )


class RecordPaymentView(View):
    """Record that you paid someone. They confirm it before it counts."""

    template_name = "settlements/record_payment.html"

    def _context(self, request, recipient, form):
        suggested = self._suggested_amount(request.user, recipient)
        amount = form["amount"].value() or suggested
        try:
            amount = Decimal(str(amount))
        except Exception:
            amount = suggested

        note = f"FlatSplit — {request.user.name}"
        return {
            "recipient": recipient,
            "form": form,
            "suggested": suggested,
            "upi_link": upi_link(
                upi_id=recipient.upi_id, name=recipient.name, amount=amount, note=note
            ),
            "qr": payment_qr(
                upi_id=recipient.upi_id, name=recipient.name, amount=amount, note=note
            ),
        }

    @staticmethod
    def _suggested_amount(payer, recipient) -> Decimal:
        """Prefill from the simplified plan, so the common case is one tap."""
        members = list(User.objects.active_members())
        for transfer in simplify_debts(get_balances(members)):
            if transfer.from_user_id == payer.pk and transfer.to_user_id == recipient.pk:
                return transfer.amount
        return Decimal("0.00")

    def get(self, request, pk):
        recipient = get_object_or_404(User, pk=pk)
        form = SettlementForm(initial={"amount": self._suggested_amount(request.user, recipient)})
        return render(request, self.template_name, self._context(request, recipient, form))

    def post(self, request, pk):
        recipient = get_object_or_404(User, pk=pk)
        if recipient.pk == request.user.pk:
            messages.error(request, "You cannot settle up with yourself.")
            return redirect("settlements:settle_up")

        form = SettlementForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(
                request, self.template_name, self._context(request, recipient, form), status=422
            )

        settlement = form.save(commit=False)
        settlement.from_user = request.user
        settlement.to_user = recipient
        settlement.save()
        record(actor=request.user, action=AuditLog.Action.CREATE, instance=settlement)

        messages.success(
            request,
            f"Recorded ₹{settlement.amount} to {recipient.name}. "
            f"It counts once {recipient.name} confirms it.",
        )
        return redirect("settlements:settle_up")


class PendingConfirmationsView(ListView):
    template_name = "settlements/pending.html"
    context_object_name = "settlements"

    def get_queryset(self):
        return Settlement.objects.awaiting(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mine_pending"] = (
            Settlement.objects.pending()
            .filter(from_user=self.request.user)
            .select_related("to_user")
        )
        return context


class ConfirmSettlementView(View):
    def post(self, request, pk):
        settlement = get_object_or_404(
            Settlement.objects.pending(), pk=pk, to_user=request.user
        )
        settlement.confirm()
        record(actor=request.user, action=AuditLog.Action.CONFIRM, instance=settlement)
        messages.success(request, f"Confirmed ₹{settlement.amount} from {settlement.from_user.name}.")
        return self._respond(request)

    def _respond(self, request):
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("settlements:pending")
            return response
        return redirect("settlements:pending")


class RejectSettlementView(ConfirmSettlementView):
    def post(self, request, pk):
        settlement = get_object_or_404(
            Settlement.objects.pending(), pk=pk, to_user=request.user
        )
        settlement.reject()
        record(actor=request.user, action=AuditLog.Action.REJECT, instance=settlement)
        messages.warning(
            request,
            f"Rejected ₹{settlement.amount} from {settlement.from_user.name}. "
            "Worth telling them why.",
        )
        return self._respond(request)


class SettlementHistoryView(ListView):
    template_name = "settlements/history.html"
    context_object_name = "settlements"
    paginate_by = 25

    def get_queryset(self):
        return Settlement.objects.with_related().all()


class PaymentQRView(View):
    """Standalone QR, for holding the phone up to somebody else's camera."""

    def get(self, request, pk):
        recipient = get_object_or_404(User, pk=pk)
        try:
            amount = Decimal(request.GET.get("amount", "0"))
        except Exception:
            amount = Decimal("0.00")

        note = f"FlatSplit — {request.user.name}"
        return render(
            request,
            "settlements/qr.html",
            {
                "recipient": recipient,
                "amount": amount,
                "qr": payment_qr(
                    upi_id=recipient.upi_id, name=recipient.name, amount=amount, note=note
                ),
                "upi_link": upi_link(
                    upi_id=recipient.upi_id, name=recipient.name, amount=amount, note=note
                ),
            },
        )
