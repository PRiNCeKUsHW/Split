import pytest
from django.contrib.auth.tokens import default_token_generator
from django.test import RequestFactory
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User
from accounts.services import (
    build_invite_link,
    create_flatmate,
    deactivate_member,
    reactivate_member,
)

pytestmark = pytest.mark.django_db


def _request(host="testserver"):
    return RequestFactory().get("/", headers={"host": host})


def test_invite_link_is_absolute_and_carries_the_user_id():
    user = create_flatmate(username="newmate", display_name="New Mate")

    link = build_invite_link(user, _request("192.168.1.5:8000"))

    assert link.startswith("http://192.168.1.5:8000/")
    assert urlsafe_base64_encode(force_bytes(user.pk)) in link


def test_invite_token_validates_for_the_right_user():
    user = create_flatmate(username="newmate")

    token = build_invite_link(user, _request()).rstrip("/").rsplit("/", 1)[-1]

    assert default_token_generator.check_token(user, token)


def test_invite_token_is_dead_once_a_password_is_set():
    """This is what makes the link single-use without storing invite state."""
    user = create_flatmate(username="newmate")
    token = build_invite_link(user, _request()).rstrip("/").rsplit("/", 1)[-1]

    user.set_password("chosen-by-them")
    user.save()

    assert not default_token_generator.check_token(user, token)


def test_invite_token_does_not_work_for_a_different_user():
    a = create_flatmate(username="a")
    b = create_flatmate(username="b")
    token = build_invite_link(a, _request()).rstrip("/").rsplit("/", 1)[-1]

    assert not default_token_generator.check_token(b, token)


def test_created_flatmate_cannot_log_in_until_they_set_a_password():
    user = create_flatmate(username="newmate", display_name="New Mate", upi_id="new@ok")

    assert user.has_usable_password() is False
    assert user.display_name == "New Mate"
    assert user.upi_id == "new@ok"


def test_deactivating_a_member_keeps_the_row_and_the_login():
    import datetime as dt

    user = create_flatmate(username="leaving")
    user.set_password("x")
    user.save()

    deactivate_member(user, left_on=dt.date(2026, 9, 30))
    user.refresh_from_db()

    assert User.objects.filter(pk=user.pk).exists()
    assert user.is_active is True  # can still log in to settle up
    assert user.is_active_member is False
    assert user not in User.objects.active_members()


def test_reactivating_clears_the_move_out_date():
    import datetime as dt

    user = create_flatmate(username="returning")
    deactivate_member(user, left_on=dt.date(2020, 1, 1))

    reactivate_member(user)
    user.refresh_from_db()

    assert user.left_on is None
    assert user.is_active_member is True
