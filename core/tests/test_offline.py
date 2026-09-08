"""The flat's WiFi may have no internet. Nothing may depend on a CDN."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from accounts.models import User

pytestmark = pytest.mark.django_db

# Any absolute http(s) URL pointing at a known asset host is a failure.
CDN_PATTERN = re.compile(
    r"""["'(]\s*https?://[^"')\s]*(cdn|unpkg|jsdelivr|fonts\.googleapis|fonts\.gstatic|bootstrapcdn)""",
    re.IGNORECASE,
)

VENDORED = (
    "vendor/bootstrap.min.css",
    "vendor/bootstrap.bundle.min.js",
    "vendor/htmx.min.js",
    "vendor/alpine.min.js",
    "fonts/plex-mono-400.woff2",
    "fonts/plex-mono-600.woff2",
)


def _template_files() -> list[Path]:
    return sorted(Path(settings.BASE_DIR).glob("templates/**/*.html"))


def test_there_are_templates_to_check():
    assert _template_files(), "template glob found nothing — the check would pass vacuously"


def test_no_template_references_a_cdn():
    offenders = [
        path.name
        for path in _template_files()
        if CDN_PATTERN.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"CDN references found in {offenders}"


def test_no_stylesheet_references_a_cdn():
    css = Path(settings.BASE_DIR) / "static" / "css" / "app.css"
    assert not CDN_PATTERN.search(css.read_text(encoding="utf-8"))


def test_vendored_assets_exist_and_are_not_truncated():
    static_dir = Path(settings.BASE_DIR) / "static"
    for rel in VENDORED:
        asset = static_dir / rel
        assert asset.exists(), f"{rel} is not vendored"
        assert asset.stat().st_size > 1000, f"{rel} looks truncated"


def test_bootstrap_is_really_bootstrap():
    css = (Path(settings.BASE_DIR) / "static" / "vendor" / "bootstrap.min.css").read_text(
        encoding="utf-8"
    )[:200]
    assert re.search(r"Bootstrap\s+v5", css)


def test_fonts_are_real_woff2_files():
    for name in ("plex-mono-400.woff2", "plex-mono-600.woff2"):
        head = (Path(settings.BASE_DIR) / "static" / "fonts" / name).read_bytes()[:4]
        assert head == b"wOF2", f"{name} is not a woff2 file"


def test_dashboard_serves_only_local_assets(client):
    User.objects.create_user(username="anuj", password="x")
    client.login(username="anuj", password="x")

    response = client.get(reverse("core:dashboard"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "/static/vendor/bootstrap.min.css" in body
    assert "/static/css/app.css" in body
    assert not CDN_PATTERN.search(body)


def test_login_page_serves_only_local_assets(client):
    body = client.get(reverse("accounts:login")).content.decode()
    assert "/static/vendor/bootstrap.min.css" in body
    assert not CDN_PATTERN.search(body)


def test_offline_fallback_page_renders_without_login(client):
    response = client.get(reverse("offline"))
    assert response.status_code == 200


def test_vendored_assets_have_no_source_map_references():
    """A dangling sourceMappingURL makes prod collectstatic fail outright."""
    vendor = Path(settings.BASE_DIR) / "static" / "vendor"
    offenders = [
        f.name
        for f in vendor.iterdir()
        if "sourceMappingURL" in f.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"source map references left in {offenders}"
