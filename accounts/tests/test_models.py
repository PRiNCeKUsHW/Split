import datetime as dt

import pytest
from django.core.exceptions import ValidationError

from accounts.models import User

pytestmark = pytest.mark.django_db


def test_name_prefers_display_name():
    user = User.objects.create_user(username="anuj", password="x", display_name="Anuj K")
    assert user.name == "Anuj K"


def test_name_falls_back_to_username():
    user = User.objects.create_user(username="priya", password="x")
    assert user.name == "priya"


def test_new_member_defaults_to_active_and_joined_today():
    user = User.objects.create_user(username="rohit", password="x")
    assert user.is_active_member is True
    assert user.joined_on == dt.date.today()
    assert user.left_on is None


def test_active_members_excludes_departed_flatmate():
    User.objects.create_user(username="stay", password="x")
    User.objects.create_user(username="gone", password="x", is_active_member=False)
    assert [u.username for u in User.objects.active_members()] == ["stay"]


def test_active_members_excludes_someone_whose_move_out_has_passed():
    User.objects.create_user(username="stay", password="x")
    User.objects.create_user(username="left", password="x", left_on=dt.date(2020, 1, 1))
    assert [u.username for u in User.objects.active_members()] == ["stay"]


def test_active_members_keeps_someone_leaving_in_the_future():
    User.objects.create_user(
        username="leaving", password="x", left_on=dt.date.today() + dt.timedelta(days=10)
    )
    assert [u.username for u in User.objects.active_members()] == ["leaving"]


def test_is_current_member_is_false_after_move_out():
    user = User.objects.create_user(
        username="moved", password="x", left_on=dt.date(2020, 1, 1)
    )
    assert user.is_current_member is False


def test_members_on_respects_tenancy_window():
    User.objects.create_user(
        username="early", password="x", joined_on=dt.date(2026, 1, 1)
    )
    User.objects.create_user(
        username="late", password="x", joined_on=dt.date(2026, 9, 11)
    )
    on_first = [u.username for u in User.objects.members_on(dt.date(2026, 9, 1))]
    on_twentieth = [u.username for u in User.objects.members_on(dt.date(2026, 9, 20))]
    assert on_first == ["early"]
    assert on_twentieth == ["early", "late"]


def test_initials_are_built_from_the_display_name():
    user = User.objects.create_user(username="a", password="x", display_name="Priya Sharma")
    assert user.initials == "PS"


def test_move_out_before_move_in_is_rejected():
    user = User(
        username="bad", joined_on=dt.date(2026, 5, 1), left_on=dt.date(2026, 4, 1)
    )
    with pytest.raises(ValidationError):
        user.full_clean()


def test_invited_flatmate_has_no_usable_login_until_they_set_a_password():
    user = User.objects.create_user(username="invited", password=None)
    user.set_unusable_password()
    user.save()
    assert user.has_usable_login is False
    user.set_password("chosen")
    assert user.has_usable_login is True
