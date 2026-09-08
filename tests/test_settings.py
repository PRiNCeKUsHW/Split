"""Guardrails on the settings that quietly break money apps."""

from decimal import Decimal

from django.conf import settings

from config.lan import lan_hosts, primary_lan_ip


def test_timezone_is_kolkata():
    assert settings.TIME_ZONE == "Asia/Kolkata"
    assert settings.USE_TZ is True


def test_custom_user_model_is_configured():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_sessions_last_thirty_days():
    assert settings.SESSION_COOKIE_AGE == 60 * 60 * 24 * 30


def test_lan_hosts_include_loopback():
    hosts = lan_hosts()
    assert "127.0.0.1" in hosts
    assert "localhost" in hosts


def test_primary_lan_ip_is_a_dotted_quad():
    parts = primary_lan_ip().split(".")
    assert len(parts) == 4
    assert all(p.isdigit() for p in parts)


def test_whitenoise_sits_directly_after_security_middleware():
    mw = settings.MIDDLEWARE
    assert mw.index("whitenoise.middleware.WhiteNoiseMiddleware") == (
        mw.index("django.middleware.security.SecurityMiddleware") + 1
    )


def test_login_required_middleware_is_installed():
    assert "django.contrib.auth.middleware.LoginRequiredMiddleware" in settings.MIDDLEWARE


def test_float_division_is_not_how_we_do_money():
    """A canary for the whole project: rupees never touch binary floats."""
    assert Decimal("100.00") / 3 != Decimal("33.33")
    assert 0.1 + 0.2 != 0.3
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
