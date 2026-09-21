"""Local development: runserver, permissive hosts, no manifest hashing."""

from .base import *  # noqa: F403

DEBUG = True

# runserver is reached from phones by IP, hostname and .local name alike.
ALLOWED_HOSTS = ["*"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Serve files straight from static/ without a collectstatic round trip.
WHITENOISE_AUTOREFRESH = True

# Any LAN origin may POST; there is no hostile origin on a flat's WiFi.
CSRF_TRUSTED_ORIGINS = [f"http://{host}:8000" for host in ALLOWED_HOSTS if host != "*"] + [
    "https://*.trycloudflare.com",
    "http://*.trycloudflare.com",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
