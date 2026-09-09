import pytest
from django.urls import reverse

from accounts.models import User
from accounts.services import build_invite_link, create_flatmate

pytestmark = pytest.mark.django_db


def test_dashboard_redirects_anonymous_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_login_page_is_reachable_without_auth(client):
    assert client.get(reverse("accounts:login")).status_code == 200


def test_flatmate_can_log_in(client):
    User.objects.create_user(username="anuj", password="flat-secret")

    response = client.post(
        reverse("accounts:login"), {"username": "anuj", "password": "flat-secret"}
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("core:dashboard")


def test_dashboard_renders_once_logged_in(client):
    User.objects.create_user(username="anuj", password="x", display_name="Anuj K")
    client.login(username="anuj", password="x")

    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 200
    assert b"Anuj K" in response.content


def test_session_lasts_thirty_days_after_login(client, settings):
    User.objects.create_user(username="anuj", password="x")
    client.post(reverse("accounts:login"), {"username": "anuj", "password": "x"})

    assert client.session.get_expiry_age() > 60 * 60 * 24 * 29


def test_any_flatmate_can_invite(client):
    """Changed deliberately: gatekeeping who adds the new housemate is
    friction with no benefit when everyone already sees all the money."""
    User.objects.create_user(username="plain", password="x")
    client.login(username="plain", password="x")

    assert client.get(reverse("accounts:invite")).status_code == 200


def test_a_plain_flatmate_can_actually_create_one(client):
    User.objects.create_user(username="plain", password="x")
    client.login(username="plain", password="x")

    response = client.post(
        reverse("accounts:invite"),
        {"username": "newbie", "display_name": "New Bie", "phone": "", "upi_id": ""},
    )

    assert response.status_code == 200
    assert User.objects.filter(username="newbie").exists()


def test_editing_someone_else_is_still_admin_only(client):
    """Adding a flatmate opened up; changing their tenancy dates did not."""
    User.objects.create_user(username="plain", password="x")
    other = User.objects.create_user(username="other", password="x")
    client.login(username="plain", password="x")

    assert client.get(reverse("accounts:member_edit", args=[other.pk])).status_code == 403


def test_the_members_list_offers_a_share_link_for_an_unused_invite(client):
    """A lost invite link must be recoverable without starting over."""
    User.objects.create_user(username="anuj", password="x")
    invited = create_flatmate(username="newbie", display_name="New Bie")
    client.login(username="anuj", password="x")

    body = client.get(reverse("accounts:members")).content.decode()

    assert f"/accounts/members/{invited.pk}/link/" in body


def test_the_share_link_page_regenerates_a_working_link(client):
    from django.contrib.auth.tokens import default_token_generator

    User.objects.create_user(username="anuj", password="x")
    invited = create_flatmate(username="newbie", display_name="New Bie")
    client.login(username="anuj", password="x")

    response = client.get(reverse("accounts:member_link", args=[invited.pk]))
    body = response.content.decode()

    assert response.status_code == 200
    assert "/accounts/set-password/" in body
    token = body.split("/accounts/set-password/")[1].split("/")[1]
    assert default_token_generator.check_token(invited, token)


def test_no_share_link_once_they_have_set_a_password(client):
    User.objects.create_user(username="anuj", password="x")
    settled = User.objects.create_user(username="settled", password="chosen")
    client.login(username="anuj", password="x")

    body = client.get(reverse("accounts:members")).content.decode()

    assert f"/accounts/members/{settled.pk}/link/" not in body


def test_sharing_a_link_for_somebody_who_already_joined_is_refused(client):
    User.objects.create_user(username="anuj", password="x")
    settled = User.objects.create_user(username="settled", password="chosen")
    client.login(username="anuj", password="x")

    response = client.get(reverse("accounts:member_link", args=[settled.pk]))

    assert response.status_code == 404


def test_staff_can_invite_and_sees_a_link(client):
    User.objects.create_user(username="boss", password="x", is_staff=True)
    client.login(username="boss", password="x")

    response = client.post(
        reverse("accounts:invite"),
        {"username": "priya", "display_name": "Priya Sharma", "phone": "", "upi_id": ""},
    )

    assert response.status_code == 200
    assert b"/accounts/set-password/" in response.content
    assert User.objects.filter(username="priya").exists()


def test_invited_flatmate_sets_a_password_and_lands_logged_in(client):
    user = create_flatmate(username="priya", display_name="Priya")
    from django.test import RequestFactory

    link = build_invite_link(user, RequestFactory().get("/"))
    path = link.replace("http://testserver", "")

    # Django's PasswordResetConfirmView swaps the token for a session-held one
    # and redirects, so follow the chain rather than posting to the raw URL.
    response = client.get(path, follow=True)
    assert response.status_code == 200

    post_url = response.redirect_chain[-1][0] if response.redirect_chain else path
    response = client.post(
        post_url,
        {"new_password1": "flat-secret-99", "new_password2": "flat-secret-99"},
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("flat-secret-99")
    assert client.session.get("_auth_user_id") == str(user.pk)


def test_a_used_invite_link_stops_working(client):
    user = create_flatmate(username="priya")
    from django.test import RequestFactory

    path = build_invite_link(user, RequestFactory().get("/")).replace("http://testserver", "")

    user.set_password("already-set")
    user.save()

    response = client.get(path, follow=True)
    assert b"already been used" in response.content


def test_members_page_lists_flatmates(client):
    User.objects.create_user(username="anuj", password="x", display_name="Anuj K")
    User.objects.create_user(username="priya", password="x", display_name="Priya Sharma")
    client.login(username="anuj", password="x")

    response = client.get(reverse("accounts:members"))

    assert response.status_code == 200
    assert b"Priya Sharma" in response.content


def test_anyone_can_edit_their_own_upi_id(client):
    User.objects.create_user(username="anuj", password="x", display_name="Anuj K")
    client.login(username="anuj", password="x")

    response = client.post(
        reverse("accounts:profile"),
        {"display_name": "Anuj K", "phone": "", "upi_id": "anuj@okaxis"},
    )

    assert response.status_code == 302
    assert User.objects.get(username="anuj").upi_id == "anuj@okaxis"


def test_a_plain_member_cannot_edit_someone_else(client):
    User.objects.create_user(username="anuj", password="x")
    other = User.objects.create_user(username="priya", password="x")
    client.login(username="anuj", password="x")

    assert client.get(reverse("accounts:member_edit", args=[other.pk])).status_code == 403
