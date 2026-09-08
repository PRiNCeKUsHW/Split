"""The confirm flow, which is the part that must not be spoofable."""

from decimal import Decimal

import pytest
from django.urls import reverse

from core.models import AuditLog
from expenses.services.shares import rebuild_shares
from settlements.models import Settlement
from settlements.services.balances import get_balances

pytestmark = pytest.mark.django_db


@pytest.fixture
def owing(groceries, anuj, priya, make_expense):
    """Priya paid 100 split with Anuj, so Anuj owes Priya 50."""
    expense = make_expense(category=groceries, paid_by=priya, amount="100.00")
    rebuild_shares(expense, participant_ids=[anuj.pk, priya.pk])
    return expense


def test_recording_a_payment_creates_a_pending_settlement(client, owing, anuj, priya):
    client.force_login(anuj)

    client.post(
        reverse("settlements:record", args=[priya.pk]),
        {"amount": "50.00", "date": "2026-09-15", "method": "UPI", "note": ""},
    )

    settlement = Settlement.objects.get()
    assert settlement.from_user == anuj
    assert settlement.to_user == priya
    assert settlement.status == Settlement.Status.PENDING


def test_a_recorded_payment_does_not_move_balances_yet(client, owing, anuj, priya):
    client.force_login(anuj)

    client.post(
        reverse("settlements:record", args=[priya.pk]),
        {"amount": "50.00", "date": "2026-09-15", "method": "UPI", "note": ""},
    )

    assert get_balances([anuj, priya])[anuj.pk] == Decimal("-50.00")


def test_the_receiver_confirming_clears_the_debt(client, owing, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=anuj, to_user=priya, amount=Decimal("50.00")
    )
    client.force_login(priya)

    client.post(reverse("settlements:confirm", args=[settlement.pk]))

    settlement.refresh_from_db()
    assert settlement.status == Settlement.Status.CONFIRMED
    assert settlement.confirmed_at is not None
    assert get_balances([anuj, priya])[anuj.pk] == Decimal("0.00")


def test_the_payer_cannot_confirm_their_own_payment(client, owing, anuj, priya):
    """Otherwise 'I sent it' would be enough to zero a debt."""
    settlement = Settlement.objects.create(
        from_user=anuj, to_user=priya, amount=Decimal("50.00")
    )
    client.force_login(anuj)

    response = client.post(reverse("settlements:confirm", args=[settlement.pk]))

    assert response.status_code == 404
    settlement.refresh_from_db()
    assert settlement.status == Settlement.Status.PENDING


def test_an_uninvolved_flatmate_cannot_confirm(client, owing, anuj, priya, rohit):
    settlement = Settlement.objects.create(
        from_user=anuj, to_user=priya, amount=Decimal("50.00")
    )
    client.force_login(rohit)

    assert client.post(reverse("settlements:confirm", args=[settlement.pk])).status_code == 404


def test_rejecting_leaves_the_debt_standing(client, owing, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=anuj, to_user=priya, amount=Decimal("50.00")
    )
    client.force_login(priya)

    client.post(reverse("settlements:reject", args=[settlement.pk]))

    settlement.refresh_from_db()
    assert settlement.status == Settlement.Status.REJECTED
    assert get_balances([anuj, priya])[anuj.pk] == Decimal("-50.00")


def test_a_settlement_cannot_be_confirmed_twice(client, owing, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=anuj, to_user=priya, amount=Decimal("50.00")
    )
    client.force_login(priya)
    client.post(reverse("settlements:confirm", args=[settlement.pk]))

    response = client.post(reverse("settlements:confirm", args=[settlement.pk]))

    assert response.status_code == 404
    assert get_balances([anuj, priya])[anuj.pk] == Decimal("0.00")


def test_confirming_is_audited(client, owing, anuj, priya):
    settlement = Settlement.objects.create(
        from_user=anuj, to_user=priya, amount=Decimal("50.00")
    )
    client.force_login(priya)

    client.post(reverse("settlements:confirm", args=[settlement.pk]))

    entry = AuditLog.objects.filter(model="Settlement", action=AuditLog.Action.CONFIRM).first()
    assert entry.actor == priya


def test_you_cannot_settle_up_with_yourself(client, anuj):
    client.force_login(anuj)

    response = client.post(
        reverse("settlements:record", args=[anuj.pk]),
        {"amount": "50.00", "date": "2026-09-15", "method": "CASH", "note": ""},
    )

    assert response.status_code == 302
    assert Settlement.objects.count() == 0


def test_a_zero_payment_is_refused(client, owing, anuj, priya):
    client.force_login(anuj)

    response = client.post(
        reverse("settlements:record", args=[priya.pk]),
        {"amount": "0", "date": "2026-09-15", "method": "UPI", "note": ""},
    )

    assert response.status_code == 422
    assert Settlement.objects.count() == 0


def test_the_amount_is_prefilled_from_the_settle_up_plan(client, owing, anuj, priya):
    client.force_login(anuj)

    response = client.get(reverse("settlements:record", args=[priya.pk]))

    assert b"50.00" in response.content


def test_the_upi_link_carries_the_id_and_the_amount(client, owing, anuj, priya):
    client.force_login(anuj)

    body = client.get(reverse("settlements:record", args=[priya.pk])).content.decode()

    assert "upi://pay" in body
    assert "priya%40okaxis" in body or "priya@okaxis" in body
    assert "am=50.00" in body


def test_somebody_without_a_upi_id_gets_told_so(client, owing, anuj, rohit):
    client.force_login(anuj)

    response = client.get(reverse("settlements:record", args=[rohit.pk]))

    assert response.status_code == 200
    assert b"no UPI ID saved" in response.content


def test_pending_screen_shows_only_what_is_addressed_to_me(
    client, owing, anuj, priya, rohit
):
    Settlement.objects.create(from_user=anuj, to_user=priya, amount=Decimal("50.00"))
    Settlement.objects.create(from_user=rohit, to_user=anuj, amount=Decimal("20.00"))
    client.force_login(priya)

    response = client.get(reverse("settlements:pending"))
    body = response.content.decode()

    assert "Anuj Kush" in body
    assert "Rohit Nair" not in body
