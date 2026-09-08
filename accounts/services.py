"""Flatmate lifecycle. No view logic, no request parsing beyond the host."""

from __future__ import annotations

from django.contrib.auth.tokens import default_token_generator
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User


def build_invite_link(user: User, request: HttpRequest) -> str:
    """Absolute URL letting a new flatmate choose their own password, once.

    No email backend is involved -- an admin reads this off the screen and
    sends it over WhatsApp. Django's token hash includes the user's current
    password hash, so the link stops working the moment a password is set.
    That is what makes it single-use without storing any invite state.
    """
    path = reverse(
        "accounts:set_password",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        },
    )
    return request.build_absolute_uri(path)


def create_flatmate(
    *,
    username: str,
    display_name: str = "",
    phone: str = "",
    upi_id: str = "",
) -> User:
    """Create a member with no usable password; they set it via the invite link."""
    user = User.objects.create_user(
        username=username,
        display_name=display_name,
        phone=phone,
        upi_id=upi_id,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def deactivate_member(user: User, *, left_on) -> User:
    """Mark someone as moved out without deleting their history.

    Their past expenses and shares must survive, so this never deletes. They
    also keep their login, so they can still settle what they owe.
    """
    user.is_active_member = False
    user.left_on = left_on
    user.save(update_fields=["is_active_member", "left_on"])
    return user


def reactivate_member(user: User) -> User:
    user.is_active_member = True
    user.left_on = None
    user.save(update_fields=["is_active_member", "left_on"])
    return user
