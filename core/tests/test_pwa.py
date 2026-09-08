import json
from pathlib import Path

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db


def _manifest() -> dict:
    path = Path(settings.BASE_DIR) / "static" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_is_installable():
    manifest = _manifest()
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["name"]


def test_manifest_has_the_icon_sizes_android_requires():
    sizes = {icon["sizes"] for icon in _manifest()["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_manifest_includes_a_maskable_icon():
    purposes = {icon.get("purpose", "any") for icon in _manifest()["icons"]}
    assert "maskable" in purposes


def test_every_manifest_icon_exists_on_disk():
    for icon in _manifest()["icons"]:
        rel = icon["src"].removeprefix("/static/")
        path = Path(settings.BASE_DIR) / "static" / rel
        assert path.exists(), f"{icon['src']} is missing"
        assert path.stat().st_size > 500, f"{icon['src']} looks empty"


def test_service_worker_is_served_from_the_root_scope(client):
    """A worker at /static/sw.js could only control /static/. It must be at /."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response["Content-Type"]


def test_service_worker_is_reachable_without_logging_in(client):
    """LoginRequiredMiddleware must not redirect the worker to the login page."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert b"flatsplit-v" in response.content


def test_service_worker_is_never_cached_by_the_browser(client):
    """A stale worker pins every phone to an old cache. Must revalidate."""
    cache_control = client.get("/sw.js")["Cache-Control"]
    assert "no-cache" in cache_control or "max-age=0" in cache_control


def test_service_worker_precaches_the_vendored_assets(client):
    body = client.get("/sw.js").content.decode()
    for asset in ("bootstrap.min.css", "htmx.min.js", "app.css", "plex-mono-400.woff2"):
        assert asset in body, f"{asset} missing from the precache list"


def test_service_worker_leaves_admin_and_writes_alone(client):
    body = client.get("/sw.js").content.decode()
    assert "/admin/" in body
    assert 'request.method !== "GET"' in body


def test_base_template_registers_the_worker(client):
    from accounts.models import User

    User.objects.create_user(username="anuj", password="x")
    client.login(username="anuj", password="x")

    body = client.get("/").content.decode()

    assert 'navigator.serviceWorker.register("/sw.js")' in body
    assert 'rel="manifest"' in body
    assert 'name="viewport"' in body
    assert "viewport-fit=cover" in body
