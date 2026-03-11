from .base import *
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.

env_path = BASE_DIR / '..' / '.env'
load_dotenv(dotenv_path=env_path)

DEBUG = True
ALLOWED_HOSTS = []

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-q1)@6lv@!rpbp6f&ph#vxk_e4ps1_r68!tw^t9o4nkit!yvj4e'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3"
    }
}

# Outputs all emails to the console, so we don't need a separate SMTP server in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@localhost'

SITE_URL = "http://127.0.0.1:8000"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

WAGTAILADMIN_BASE_URL = "http://localhost:8000"