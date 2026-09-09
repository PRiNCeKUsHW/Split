"""Template hygiene checks that catch whole classes of visible breakage."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

TEMPLATES = sorted(Path(settings.BASE_DIR).glob("templates/**/*.html"))


def test_there_are_templates_to_check():
    assert TEMPLATES


def test_no_comment_spans_more_than_one_line():
    """Django's {# #} is single-line only.

    A multi-line one is not a comment at all -- it is emitted verbatim, so
    the note you wrote for yourself shows up on the page. Use
    {% comment %}...{% endcomment %} instead.
    """
    offenders = []
    for path in TEMPLATES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "{#" in line and "#}" not in line:
                offenders.append(f"{path.name}:{number}")

    assert offenders == [], (
        "multi-line {# #} comments render as visible text: " + ", ".join(offenders)
    )


def test_no_template_leaks_a_stray_comment_marker():
    for path in TEMPLATES:
        text = path.read_text(encoding="utf-8")
        assert text.count("{#") == text.count("#}"), f"{path.name} has unbalanced {{# #}}"


@pytest.mark.django_db
def test_no_rendered_page_contains_a_comment_marker(client, django_user_model):
    """The end-to-end version: nothing that looks like template syntax may
    survive into the HTML a person actually receives."""
    user = django_user_model.objects.create_user(
        username="anuj", password="x", display_name="Anuj K"
    )
    client.force_login(user)

    pages = [
        "core:dashboard", "core:balances", "core:summary", "core:audit",
        "expenses:list", "expenses:add", "expenses:category_list",
        "expenses:category_add", "settlements:settle_up", "settlements:pending",
        "recurring:list", "accounts:away", "accounts:members", "accounts:profile",
    ]
    for name in pages:
        body = client.get(reverse(name)).content.decode()
        for marker in ("{#", "#}", "{%", "%}"):
            assert marker not in body, f"{name} leaked {marker!r} into the page"


@pytest.mark.django_db
def test_the_invite_screen_does_not_leak_template_syntax(client, django_user_model):
    django_user_model.objects.create_user(username="anuj", password="x")
    client.force_login(user=django_user_model.objects.get(username="anuj"))

    body = client.post(
        reverse("accounts:invite"),
        {"username": "newbie", "display_name": "New Bie", "phone": "", "upi_id": ""},
    ).content.decode()

    assert "{#" not in body
    assert "#}" not in body


@pytest.mark.django_db
def test_copying_an_invite_link_works_without_a_secure_context(client, django_user_model):
    """On http:// over a LAN IP the Clipboard API does not exist.

    The share sheet is unavailable there too, so copy is the only route out
    and it must not depend on navigator.clipboard alone.
    """
    django_user_model.objects.create_user(username="anuj", password="x")
    client.force_login(django_user_model.objects.get(username="anuj"))

    body = client.post(
        reverse("accounts:invite"),
        {"username": "newbie", "display_name": "New Bie", "phone": "", "upi_id": ""},
    ).content.decode()

    assert "navigator.clipboard" in body, "no modern path"
    assert "execCommand" in body, "no fallback for insecure contexts"


@pytest.mark.django_db
def test_the_theme_toggle_has_exactly_two_states(client, django_user_model):
    django_user_model.objects.create_user(username="anuj", password="x")
    client.force_login(django_user_model.objects.get(username="anuj"))

    body = client.get(reverse("core:dashboard")).content.decode()

    assert 'var ORDER = ["light", "dark"]' in body
    assert "icon-auto" not in body, "the auto state was removed"
    assert 'class="icon-light"' in body
    assert 'class="icon-dark"' in body
