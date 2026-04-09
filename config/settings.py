# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Vorgangswerk – Django-Einstellungen

Umgebungsvariablen werden aus .env geladen (python-decouple).
Keine sensiblen Werte direkt im Code.
"""
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Sicherheit
# ---------------------------------------------------------------------------

SECRET_KEY = config("SECRET_KEY", default="dev-key-bitte-in-env-setzen")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # MFA
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    # API
    "ninja",
    # Login-Überwachung
    "axes",
    # Vorgangswerk-Apps
    "core",
    "formulare",
    "workflow",
    "dokumente",
    "kommunikation",
    "korrespondenz",
    "signatur",
    "portal",
    "sicherung",
    "post",
    "quiz",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "signatur.middleware.SignaturKeyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

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
                "config.context_processors.vorgangswerk_einstellungen",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Datenbank – PostgreSQL (einzige Option)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="vorgangswerk"),
        "USER": config("DB_USER", default="vorgangswerk"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
    }
}

# ---------------------------------------------------------------------------
# Passwort-Validierung (BSI: Mindestlaenge 12 Zeichen)
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisierung
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Statische Dateien (WhiteNoise)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Session (BSI: Timeout 8h Standard, konfigurierbar)
# ---------------------------------------------------------------------------

SESSION_COOKIE_AGE = config("SESSION_TIMEOUT", default=28800, cast=int)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://vorgangswerk.georg-klein.com",
    cast=Csv(),
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"

# ---------------------------------------------------------------------------
# E-Mail (SMTP Ausgang)
# ---------------------------------------------------------------------------

EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("EMAIL_HOST_USER", default="noreply@vorgangswerk.local")

# ---------------------------------------------------------------------------
# E-Mail (IMAP Eingang – fuer kommunikation-App)
# ---------------------------------------------------------------------------

IMAP_HOST = config("IMAP_HOST", default="")
IMAP_PORT = config("IMAP_PORT", default=993, cast=int)
IMAP_USER = config("IMAP_USER", default="")
IMAP_PASSWORD = config("IMAP_PASSWORD", default="")
IMAP_POSTFACH = config("IMAP_POSTFACH", default="INBOX")
IMAP_ORDNER = config("IMAP_ORDNER", default="INBOX")
IMAP_BENACHRICHTIGE_STAFF = config("IMAP_BENACHRICHTIGE_STAFF", default=True, cast=bool)

# ---------------------------------------------------------------------------
# Collabora Online WOPI (optional)
# ---------------------------------------------------------------------------

ONLYOFFICE_URL          = config("ONLYOFFICE_URL",          default="")
ONLYOFFICE_INTERNAL_URL = config("ONLYOFFICE_INTERNAL_URL", default="http://host.docker.internal:8012")
ONLYOFFICE_JWT_SECRET   = config("ONLYOFFICE_JWT_SECRET",   default="")
# Oeffentliche Basis-URL dieser Instanz
VORGANGSWERK_BASE_URL   = config("VORGANGSWERK_BASE_URL",   default="http://localhost:8000")
# Interne URL fuer OnlyOffice→Django-Callbacks (vom OO-Container erreichbar)
WOPI_BASE_URL           = config("WOPI_BASE_URL",           default="http://host.docker.internal:8100")
# PDF-Werkzeug (z.B. Stirling-PDF / BentoPDF – self-hosted)
BENTOPDF_URL            = config("BENTOPDF_URL",            default="")

# ---------------------------------------------------------------------------
# Verschluesselung (AES-256-GCM fuer sensible Dokumente)
# ---------------------------------------------------------------------------

VERSCHLUESSEL_KEY = config("VERSCHLUESSEL_KEY", default="")

# ---------------------------------------------------------------------------
# Signatur
# ---------------------------------------------------------------------------

SIGNME_API_KEY = config("SIGNME_API_KEY", default="")
API_KEY = config("API_KEY", default="")
SIGNATUR_BACKEND = config("SIGNATUR_BACKEND", default="intern")
SIGNATUR_SIGN_ME_URL = config("SIGNATUR_SIGN_ME_URL", default="https://api.sign-me.de")
SIGNATUR_SIGN_ME_KEY = config("SIGNATUR_SIGN_ME_KEY", default="")

# ---------------------------------------------------------------------------
# Claude / Anthropic API
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")

# ---------------------------------------------------------------------------
# Stripe (Portal-Zahlungen)
# ---------------------------------------------------------------------------

STRIPE_PUBLIC_KEY  = config("STRIPE_PUBLIC_KEY",  default="")
STRIPE_SECRET_KEY  = config("STRIPE_SECRET_KEY",  default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")

# ---------------------------------------------------------------------------
# Datensicherung (BSI CON.3)
# ---------------------------------------------------------------------------

SICHERUNGS_DIR = config("SICHERUNGS_DIR", default="/app/sicherungen")

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "signatur.auth_backend.SignaturAuthBackend",
]

# ---------------------------------------------------------------------------
# django-axes (Brute-Force-Schutz + Login-Übersicht)
# ---------------------------------------------------------------------------

AXES_FAILURE_LIMIT        = 5          # Sperren nach 5 Fehlversuchen
AXES_COOLOFF_TIME         = 1          # Sperre: 1 Stunde
AXES_LOCKOUT_PARAMETERS   = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS     = True       # Zähler zurücksetzen bei erfolgreichem Login
AXES_VERBOSE              = False

# ---------------------------------------------------------------------------
# Logging (BSI: keine sensiblen Daten in Logs)
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "vorgangswerk": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
