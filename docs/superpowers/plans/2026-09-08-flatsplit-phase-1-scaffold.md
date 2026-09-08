# FlatSplit Phase 1 — Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A running, styled, installable, login-protected Django app on the LAN with a custom User model in place — the foundation every later phase builds on.

**Architecture:** Django 5.2 project with a three-file settings split (`base`/`dev`/`prod`) driven by a `.env`. Custom `accounts.User` lands in the very first migration so no painful swap is ever needed. WhiteNoise serves fully vendored Bootstrap/HTMX/Alpine so the app is styled with the internet unplugged. A base template supplies a fixed bottom nav sized for one-handed phone use, and a manifest plus service worker make it installable.

**Tech Stack:** Django 5.2, Python 3.12, SQLite, WhiteNoise, django-environ, Bootstrap 5.3, HTMX 2, Alpine 3, pytest + pytest-django, Pillow.

**Spec:** `docs/superpowers/specs/2026-09-08-flatsplit-design.md`

## Global Constraints

- Django 5.x, Python 3.11+ (this machine: 3.12.10).
- `TIME_ZONE = "Asia/Kolkata"`, `USE_TZ = True`.
- All money is `Decimal` via `DecimalField(max_digits=10, decimal_places=2)`. Never `float`.
- Zero CDN references in any template. Every asset resolves from `/static/`.
- `AUTH_USER_MODEL = "accounts.User"` set before the first `migrate` ever runs.
- Server-rendered templates + HTMX + Alpine only. No React, no Node build step.
- `ALLOWED_HOSTS` configurable via `.env` and permissive enough for `192.168.*` LAN IPs.
- Session cookie age 30 days, so phones do not re-login.
- Mobile-first: minimum 44px tap targets, bottom nav, thumb-reachable primary actions.
- Business logic in `services.py` modules with type hints, not in views or models.

---

### Task 1: Project skeleton, settings split, environment

**Files:**
- Create: `requirements.txt`, `.env.example`, `.env`, `.gitignore`, `pytest.ini`, `manage.py`
- Create: `config/__init__.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`, `config/lan.py`
- Create: `config/settings/__init__.py`, `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `config.lan.lan_hosts() -> list[str]` returning hostnames/IPs this machine answers to; settings modules `config.settings.dev` and `config.settings.prod`.

- [ ] **Step 1: Create the virtualenv and install dependencies**

`requirements.txt`:
```
Django>=5.2,<6.0
django-environ>=0.11
whitenoise>=6.6
Pillow>=10.3
qrcode[pil]>=7.4
gunicorn>=22.0; sys_platform != "win32"
waitress>=3.0; sys_platform == "win32"
pytest>=8.2
pytest-django>=4.8
```

Run:
```bash
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -r requirements.txt
```

Note: Gunicorn has no Windows support; `run.sh` targets the Linux/macOS host the flat actually runs on, and Waitress is the Windows-dev equivalent. Both are pinned by platform marker above.

- [ ] **Step 2: Write the failing settings test**

`tests/test_settings.py`:
```python
from decimal import Decimal

from django.conf import settings


def test_timezone_is_kolkata():
    assert settings.TIME_ZONE == "Asia/Kolkata"
    assert settings.USE_TZ is True


def test_custom_user_model_is_configured():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_sessions_last_thirty_days():
    assert settings.SESSION_COOKIE_AGE == 60 * 60 * 24 * 30


def test_lan_hosts_include_loopback():
    from config.lan import lan_hosts

    hosts = lan_hosts()
    assert "127.0.0.1" in hosts
    assert "localhost" in hosts


def test_money_precision_helper():
    assert Decimal("100.00") / 3 != Decimal("33.33")
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `.venv/Scripts/python -m pytest tests/test_settings.py -v`
Expected: collection error — `config.settings` does not exist yet.

- [ ] **Step 4: Write `config/lan.py`**

```python
"""Discover the addresses this machine answers to on the flat's WiFi."""

from __future__ import annotations

import socket


def lan_hosts() -> list[str]:
    """Return hostnames and IPv4 addresses usable to reach this machine.

    Django's ALLOWED_HOSTS has no wildcard for `192.168.*`, so instead of
    guessing we detect the real addresses at startup.
    """
    hosts: set[str] = {"127.0.0.1", "localhost", "0.0.0.0"}

    try:
        hostname = socket.gethostname()
        hosts.add(hostname)
        hosts.add(f"{hostname}.local")
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            hosts.add(info[4][0])
    except OSError:
        pass

    # Ask the routing table which interface would reach the outside world.
    # UDP connect() sends no packets, so this works with no internet present.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            hosts.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass

    return sorted(hosts)
```

- [ ] **Step 5: Write `config/settings/base.py`**

```python
from pathlib import Path

import environ

from config.lan import lan_hosts

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "dev-only-insecure-key-change-me"),
    ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = list(dict.fromkeys(env("ALLOWED_HOSTS") + lan_hosts()))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"transaction_mode": "IMMEDIATE", "init_command": "PRAGMA journal_mode=WAL;"},
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days — phones stay logged in
SESSION_SAVE_EVERY_REQUEST = True

# Phones reach the host over plain HTTP on the LAN; these must stay False.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
```

Password validators are deliberately relaxed to two: this is a four-person flat on a private LAN, and `UserAttributeSimilarityValidator` plus `NumericPasswordValidator` mostly generate friction for people typing on a phone keyboard.

- [ ] **Step 6: Write `config/settings/dev.py` and `config/settings/prod.py`**

`dev.py`:
```python
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_AUTOREFRESH = True
```

`prod.py`:
```python
from .base import *  # noqa: F403

DEBUG = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# CSRF needs the scheme-qualified origins for LAN IPs on Django 4+.
CSRF_TRUSTED_ORIGINS = [f"http://{host}:8000" for host in ALLOWED_HOSTS if host[0].isdigit()]  # noqa: F405
X_FRAME_OPTIONS = "DENY"
```

- [ ] **Step 7: Write `.env.example`, copy it to `.env`, write `.gitignore` and `pytest.ini`**

`.env.example`:
```
DEBUG=True
SECRET_KEY=change-me-to-a-long-random-string
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.5
DJANGO_SETTINGS_MODULE=config.settings.dev
```

`pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.dev
python_files = test_*.py
addopts = -q --reuse-db
```

`.gitignore` must exclude `.venv/`, `.env`, `db.sqlite3`, `media/`, `staticfiles/`, `__pycache__/`, `.pytest_cache/`.

- [ ] **Step 8: Run tests — expect pass on settings, failure on missing `accounts` app**

Run: `.venv/Scripts/python -m pytest tests/test_settings.py -v`
Expected: `ModuleNotFoundError: accounts` until Task 2. Comment `accounts`/`core` out of `INSTALLED_APPS` only if you need a green checkpoint here; Task 2 restores them.

- [ ] **Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: django project skeleton with split settings and LAN host detection"
```

---

### Task 2: Custom User model

**Files:**
- Create: `accounts/__init__.py`, `accounts/apps.py`, `accounts/models.py`, `accounts/admin.py`, `accounts/migrations/__init__.py`
- Test: `accounts/tests/__init__.py`, `accounts/tests/test_models.py`

**Interfaces:**
- Consumes: `AUTH_USER_MODEL` from Task 1.
- Produces: `accounts.models.User` with fields `display_name`, `phone`, `upi_id`, `avatar`, `is_active_member`, `joined_on`, `left_on`; properties `User.name -> str`, `User.is_current_member -> bool`; manager method `User.objects.active_members() -> QuerySet[User]`.

- [ ] **Step 1: Write the failing model test**

`accounts/tests/test_models.py`:
```python
import datetime as dt

import pytest

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


def test_is_current_member_is_false_after_move_out():
    user = User.objects.create_user(
        username="moved", password="x", left_on=dt.date(2020, 1, 1)
    )
    assert user.is_current_member is False
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python -m pytest accounts -v`
Expected: FAIL — `accounts.models` does not exist.

- [ ] **Step 3: Write `accounts/models.py`**

```python
from __future__ import annotations

import datetime as dt

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q


class FlatmateManager(UserManager):
    def active_members(self) -> models.QuerySet["User"]:
        """Flatmates who currently live here and should appear in split pickers."""
        today = dt.date.today()
        return self.filter(
            Q(is_active_member=True),
            Q(is_active=True),
            Q(left_on__isnull=True) | Q(left_on__gte=today),
        ).order_by("id")


class User(AbstractUser):
    display_name = models.CharField(max_length=60, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    upi_id = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_active_member = models.BooleanField(default=True)
    joined_on = models.DateField(default=dt.date.today)
    left_on = models.DateField(null=True, blank=True)

    objects = FlatmateManager()

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        return self.display_name or self.get_full_name() or self.username

    @property
    def is_current_member(self) -> bool:
        if not self.is_active_member:
            return False
        return self.left_on is None or self.left_on >= dt.date.today()

    @property
    def initials(self) -> str:
        parts = [p for p in self.name.replace(".", " ").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"
```

- [ ] **Step 4: Make and run migrations, then run the tests**

```bash
.venv/Scripts/python manage.py makemigrations accounts
.venv/Scripts/python -m pytest accounts -v
```
Expected: all five tests PASS.

- [ ] **Step 5: Register in admin**

`accounts/admin.py` subclasses `UserAdmin`, appending a `"Flatmate"` fieldset with
`display_name`, `phone`, `upi_id`, `avatar`, `is_active_member`, `joined_on`, `left_on`,
and sets `list_display = ("username", "display_name", "is_active_member", "joined_on")`.

- [ ] **Step 6: Commit**

```bash
git add accounts config
git commit -m "feat(accounts): custom User model with membership dates"
```

---

### Task 3: Auth — login, logout, and the one-time set-password link

**Files:**
- Create: `accounts/urls.py`, `accounts/views.py`, `accounts/forms.py`, `accounts/services.py`
- Create: `templates/accounts/login.html`, `templates/accounts/set_password.html`, `templates/accounts/invite_created.html`, `templates/accounts/members.html`
- Modify: `config/urls.py`
- Test: `accounts/tests/test_auth.py`, `accounts/tests/test_services.py`

**Interfaces:**
- Consumes: `accounts.models.User` from Task 2.
- Produces: `accounts.services.build_invite_link(user: User, request: HttpRequest) -> str` returning an absolute one-time set-password URL; URL names `accounts:login`, `accounts:logout`, `accounts:members`, `accounts:invite`, `accounts:set_password`.

- [ ] **Step 1: Write the failing service test**

`accounts/tests/test_services.py`:
```python
import pytest
from django.contrib.auth.tokens import default_token_generator
from django.test import RequestFactory
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User
from accounts.services import build_invite_link

pytestmark = pytest.mark.django_db


def test_invite_link_is_absolute_and_contains_a_valid_token():
    user = User.objects.create_user(username="newmate", password=None)
    request = RequestFactory().get("/", HTTP_HOST="192.168.1.5:8000")

    link = build_invite_link(user, request)

    assert link.startswith("http://192.168.1.5:8000/")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    assert uid in link


def test_invite_token_validates_for_the_right_user():
    user = User.objects.create_user(username="newmate", password=None)
    request = RequestFactory().get("/", HTTP_HOST="testserver")

    link = build_invite_link(user, request)
    token = link.rstrip("/").rsplit("/", 1)[-1]

    assert default_token_generator.check_token(user, token)


def test_invite_token_is_invalidated_once_a_password_is_set():
    user = User.objects.create_user(username="newmate", password=None)
    request = RequestFactory().get("/", HTTP_HOST="testserver")
    token = build_invite_link(user, request).rstrip("/").rsplit("/", 1)[-1]

    user.set_password("chosen-by-them")
    user.save()

    assert not default_token_generator.check_token(user, token)
```

The third test is the security-relevant one: Django's token hash includes the password
hash, so the link burns itself the moment it is used. That is what makes it "one-time"
without storing any invite state.

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python -m pytest accounts/tests/test_services.py -v`
Expected: FAIL — `accounts.services` does not exist.

- [ ] **Step 3: Write `accounts/services.py`**

```python
from __future__ import annotations

from django.contrib.auth.tokens import default_token_generator
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User


def build_invite_link(user: User, request: HttpRequest) -> str:
    """Absolute URL letting a new flatmate choose their own password, once.

    No email backend is involved — the admin reads this off the screen and
    sends it over WhatsApp. The token embeds the user's current password
    hash, so it stops working the instant the password is set.
    """
    path = reverse(
        "accounts:set_password",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        },
    )
    return request.build_absolute_uri(path)


def create_flatmate(*, username: str, display_name: str, phone: str = "", upi_id: str = "") -> User:
    """Create a member with an unusable password; they set it via the invite link."""
    user = User.objects.create_user(
        username=username,
        display_name=display_name,
        phone=phone,
        upi_id=upi_id,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user
```

- [ ] **Step 4: Write `accounts/urls.py` and `accounts/views.py`**

Use Django's built-in `LoginView`, `LogoutView` and `PasswordResetConfirmView`. The
set-password view is `PasswordResetConfirmView` with `post_reset_login = True`, so the new
flatmate lands straight in the app rather than being bounced to a login form.

```python
# accounts/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.FlatLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("members/", views.MemberListView.as_view(), name="members"),
    path("members/add/", views.InviteFlatmateView.as_view(), name="invite"),
    path(
        "set-password/<uidb64>/<token>/",
        views.SetPasswordView.as_view(),
        name="set_password",
    ),
]
```

`views.py` defines:
- `FlatLoginView(LoginView)` — `template_name = "accounts/login.html"`, decorated with
  `@method_decorator(login_not_required, name="dispatch")` so `LoginRequiredMiddleware`
  lets it through.
- `SetPasswordView(PasswordResetConfirmView)` — same `login_not_required` treatment,
  `post_reset_login = True`, `success_url = reverse_lazy("core:dashboard")`.
- `MemberListView(ListView)` — `User.objects.all()`, staff-only via `UserPassesTestMixin`.
- `InviteFlatmateView(FormView)` — calls `create_flatmate` then `build_invite_link`,
  renders `invite_created.html` showing the link with a copy button.

- [ ] **Step 5: Write the failing view test**

`accounts/tests/test_auth.py`:
```python
import pytest
from django.urls import reverse

from accounts.models import User

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
        reverse("accounts:login"),
        {"username": "anuj", "password": "flat-secret"},
    )
    assert response.status_code == 302


def test_only_staff_can_invite(client):
    User.objects.create_user(username="plain", password="x")
    client.login(username="plain", password="x")
    assert client.get(reverse("accounts:invite")).status_code == 403
```

- [ ] **Step 6: Run the full suite**

Run: `.venv/Scripts/python -m pytest -v`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add accounts templates config
git commit -m "feat(accounts): login, logout and one-time invite links"
```

---

### Task 4: Vendored assets, base template, bottom nav

**Files:**
- Create: `static/vendor/bootstrap.min.css`, `static/vendor/bootstrap.bundle.min.js`, `static/vendor/htmx.min.js`, `static/vendor/alpine.min.js`
- Create: `static/css/app.css`
- Create: `templates/base.html`, `templates/partials/_nav.html`, `templates/partials/_messages.html`
- Create: `core/__init__.py`, `core/apps.py`, `core/urls.py`, `core/views.py`, `templates/core/dashboard.html`
- Modify: `config/urls.py`
- Test: `core/tests/__init__.py`, `core/tests/test_offline.py`

**Interfaces:**
- Consumes: auth from Task 3.
- Produces: `core:dashboard` URL name; `base.html` with blocks `title`, `content`, `fab`, `extra_js`.

- [ ] **Step 1: Download the vendored assets**

```bash
mkdir -p static/vendor static/css static/icons
curl -fsSL -o static/vendor/bootstrap.min.css https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/css/bootstrap.min.css
curl -fsSL -o static/vendor/bootstrap.bundle.min.js https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/js/bootstrap.bundle.min.js
curl -fsSL -o static/vendor/htmx.min.js https://cdnjs.cloudflare.com/ajax/libs/htmx/2.0.4/htmx.min.js
curl -fsSL -o static/vendor/alpine.min.js https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.14.8/cdn.min.js
```

Verify each file is non-empty and is what it claims to be before trusting it:
```bash
wc -c static/vendor/*
head -c 100 static/vendor/bootstrap.min.css
```
Expected: bootstrap CSS ≈ 230KB starting with `@charset "UTF-8";/*! Bootstrap v5.3.3`.
If any download fails, stop and report — do not fall back to a CDN link in the template.

- [ ] **Step 2: Write the failing offline test**

`core/tests/test_offline.py`:
```python
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from accounts.models import User

pytestmark = pytest.mark.django_db

CDN_PATTERN = re.compile(r"https?://(?!\{)[^\"'\s]*(cdn|unpkg|jsdelivr|googleapis)", re.I)


def test_no_template_references_a_cdn():
    offenders = []
    for path in Path(settings.BASE_DIR).glob("templates/**/*.html"):
        if CDN_PATTERN.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert offenders == [], f"CDN references found in {offenders}"


def test_vendored_assets_exist_on_disk():
    vendor = Path(settings.BASE_DIR) / "static" / "vendor"
    for name in ("bootstrap.min.css", "bootstrap.bundle.min.js", "htmx.min.js", "alpine.min.js"):
        asset = vendor / name
        assert asset.exists(), f"{name} not vendored"
        assert asset.stat().st_size > 1000, f"{name} looks truncated"


def test_dashboard_renders_for_a_logged_in_flatmate(client):
    User.objects.create_user(username="anuj", password="x")
    client.login(username="anuj", password="x")
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 200
    assert b"/static/vendor/bootstrap.min.css" in response.content
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `.venv/Scripts/python -m pytest core -v`
Expected: FAIL — no `core` app, no dashboard URL.

- [ ] **Step 4: Write `templates/base.html`**

Mobile-first shell. Key requirements, all enforced by the test above plus visual review:
- `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`
- `{% load static %}` and `{% static 'vendor/bootstrap.min.css' %}` — never a URL literal
- `<link rel="manifest" href="{% static 'manifest.json' %}">` (Task 5 creates it)
- HTMX and Alpine loaded with `defer`
- `<body class="pb-5">` so the fixed bottom nav never covers content
- blocks: `title`, `content`, `fab`, `extra_js`

- [ ] **Step 5: Write `templates/partials/_nav.html` and `static/css/app.css`**

Bottom nav is a fixed five-item bar: Home, Expenses, **Add** (raised circular FAB), Settle,
More. Requirements:
- `position: fixed; bottom: 0` with `padding-bottom: env(safe-area-inset-bottom)` for iPhone
- every `<a>` at least `44px` tall and wide
- active item highlighted by comparing `request.resolver_match.namespace`
- the centre Add button is a 56px circle raised above the bar

`app.css` also defines the money type scale used by the dashboard from Phase 4 onward:
`.money-hero { font-size: 2.75rem; font-weight: 700; font-variant-numeric: tabular-nums; }`
Tabular numerals matter — without them, rupee columns visibly jitter as digits change.

- [ ] **Step 6: Write the placeholder dashboard**

`core/views.py` holds `DashboardView(TemplateView)` with `template_name = "core/dashboard.html"`.
Phase 4 replaces the body with real balances; for now it renders a greeting and confirms the
nav and styling work.

- [ ] **Step 7: Run tests, then look at it on a phone**

```bash
.venv/Scripts/python manage.py migrate
.venv/Scripts/python -m pytest -v
.venv/Scripts/python manage.py runserver 0.0.0.0:8000
```
Expected: tests PASS. Then open `http://<LAN-IP>:8000` on a phone, turn the laptop's
internet off, hard-refresh, and confirm the page is still fully styled.

- [ ] **Step 8: Commit**

```bash
git add static templates core config
git commit -m "feat(core): vendored bootstrap, mobile base template and bottom nav"
```

---

### Task 5: PWA manifest, icons and service worker

**Files:**
- Create: `static/manifest.json`, `static/sw.js`, `static/icons/icon-192.png`, `static/icons/icon-512.png`, `static/icons/icon-maskable-512.png`
- Create: `core/management/commands/make_icons.py`
- Modify: `templates/base.html`, `config/urls.py`
- Test: `core/tests/test_pwa.py`

**Interfaces:**
- Consumes: `base.html` from Task 4.
- Produces: `/sw.js` and `/manifest.json` served from the site root scope.

- [ ] **Step 1: Write the failing PWA test**

`core/tests/test_pwa.py`:
```python
import json
from pathlib import Path

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db


def test_manifest_is_valid_and_installable():
    manifest = json.loads((Path(settings.BASE_DIR) / "static" / "manifest.json").read_text())
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_icons_exist():
    icons = Path(settings.BASE_DIR) / "static" / "icons"
    assert (icons / "icon-192.png").stat().st_size > 500
    assert (icons / "icon-512.png").stat().st_size > 500


def test_service_worker_is_served_from_root_scope(client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response["Content-Type"]
```

A service worker can only control pages at or below its own URL, so serving `sw.js` from
`/static/sw.js` would scope it to `/static/`. The root-scope test is the one that catches it.

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python -m pytest core/tests/test_pwa.py -v`
Expected: FAIL — no manifest, 404 on `/sw.js`.

- [ ] **Step 3: Generate the icons**

`core/management/commands/make_icons.py` draws the icons with Pillow — a rounded indigo
square with a white rupee glyph — so no binary assets need fetching and the icons can be
regenerated if the palette changes. Maskable variant keeps the glyph inside the safe 80%
circle.

Run: `.venv/Scripts/python manage.py make_icons`

- [ ] **Step 4: Write `static/manifest.json`**

```json
{
  "name": "FlatSplit",
  "short_name": "FlatSplit",
  "description": "Split flat expenses with your flatmates",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#ffffff",
  "theme_color": "#4f46e5",
  "icons": [
    {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
    {"src": "/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
```

- [ ] **Step 5: Write `static/sw.js` and serve it at root**

Caching strategy:
- **Static assets** (`/static/`): cache-first. They are versioned by WhiteNoise and never
  change under a given URL.
- **Pages**: network-first with a cached fallback. Money data must never be served stale
  when the LAN is reachable; a cached shell is only for when the host machine is off.
- **Never cache** anything but GET, and never cache `/admin/`.
- Bump `CACHE_NAME` on release and delete old caches in `activate`.

Serve it at root in `config/urls.py`:
```python
path("sw.js", TemplateView.as_view(
    template_name="sw.js", content_type="application/javascript"), name="sw"),
```
This requires `sw.js` to also be reachable as a template; put the real file in
`templates/sw.js` and have `static/sw.js` be a copy for the manifest test, or point the
template loader at the static file. Prefer the template route — it lets the cache name be
stamped from Django settings at render time.

- [ ] **Step 6: Register the worker in `base.html`**

```html
<script>
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
  }
</script>
```

- [ ] **Step 7: Run the full suite and verify installability on a phone**

Run: `.venv/Scripts/python -m pytest -v`
Expected: every test PASSES.

Then on an Android phone on the same WiFi, open `http://<LAN-IP>:8000` in Chrome and
confirm "Add to Home screen" offers an app install rather than a plain bookmark.

Note: Chrome treats `http://` origins other than `localhost` as insecure, which normally
blocks service worker registration. On the LAN, the page will still install and run, but
the worker may not register from a plain IP. Verify this on the actual phone and, if the
worker is refused, record it in the README as a known limitation with the workaround
(`chrome://flags/#unsafely-treat-insecure-origin-as-secure`, or run behind a self-signed
HTTPS proxy). Do not silently ship a worker that never registers.

- [ ] **Step 8: Commit**

```bash
git add static templates core config
git commit -m "feat(core): PWA manifest, generated icons and root-scoped service worker"
```

---

## Phase 1 Exit Criteria

- [ ] `.venv/Scripts/python -m pytest` — all green
- [ ] `python manage.py runserver 0.0.0.0:8000` reachable from a phone on the flat WiFi
- [ ] Page fully styled with the host's internet disconnected
- [ ] Anonymous visit to `/` redirects to login; login works and survives an app restart
- [ ] Admin can create a flatmate and read a working invite link off the screen
- [ ] Manifest and icons served; install behaviour on a real phone recorded in the README

Stop here for review before Phase 2.
