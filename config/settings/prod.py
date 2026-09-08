"""The 'real' run: Gunicorn behind nothing, still on the flat's LAN.

Not internet-facing. This differs from dev mainly in hashed static assets and
in refusing hosts that were not detected or configured.
"""

from .base import *  # noqa: F403

DEBUG = False

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Django needs scheme-qualified origins for CSRF. Every detected LAN address
# gets one, so a phone POSTing to http://192.168.1.5:8000 is accepted.
CSRF_TRUSTED_ORIGINS = [
    f"http://{host}:8000" for host in ALLOWED_HOSTS if host[0].isdigit()  # noqa: F405
]

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# No HTTPS on the LAN, so these stay off on purpose. Turning them on would
# redirect phones to a port nothing is listening on.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "flatsplit.log",  # noqa: F405
            "maxBytes": 2_000_000,
            "backupCount": 3,
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}
