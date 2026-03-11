from .base import *
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = False
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")

# Since traffic is reverse proxied via nginx to the django app, communications between nginx <-> django occur using http
# These lines tell django that if the X-forwarded-proto header is set to https, then it can trust the commuinication to the server was secure
# (otherwise it will not serve the request)
# The `proxy_set_header X-Forwarded-Proto $scheme;` line in nginx config is also required
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST", "db"),
        "PORT": "5432"
    }
}

ROOT_URLCONF = 'ubc_voc_website.urls'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'email-smtp.us-west-2.amazonaws.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("SMTP_USERNAME")
EMAIL_HOST_PASSWORD = os.getenv("SMTP_PASSWORD")

DEFAULT_FROM_EMAIL = "UBC VOC <noreply@ubc-voc.com>"
SERVER_EMAIL = "errors@ubc-voc.com"

SITE_URL = "https://ubc-voc.com"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/home/ubc_voc_website/staticfiles'

MEDIA_URL = "/media/"
MEDIA_ROOT = '/home/ubc_voc_website/media'

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{"
        }
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/home/ubc_voc_website/logs/django.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 100,
            "backupCount": 5,
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose"
        }
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True
        }
    }
}

WAGTAILADMIN_BASE_URL = "https://ubc-voc.com"
