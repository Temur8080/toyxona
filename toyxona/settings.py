import os
import time
from pathlib import Path

import jinja2
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
from django_jinja.builtins import DEFAULT_EXTENSIONS
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is not set. Add it to .env")
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
def _parse_allowed_hosts():
    """Host:port (masalan 176.101.56.247:8000) ham qabul qilinadi."""
    hosts = []
    for host in os.environ.get('ALLOWED_HOSTS', '127.0.0.1').replace(',', ' ').split():
        host = host.strip()
        if not host:
            continue
        hosts.append(host)
        if ':' not in host:
            hosts.extend((f'{host}:80', f'{host}:8000'))
    return list(dict.fromkeys(hosts))


ALLOWED_HOSTS = _parse_allowed_hosts()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jinja',
    'django_bootstrap5',
    'rest_framework',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'apps.account',
    'apps.main',
    'apps.camera',
    'apps.counting',
]
if DEBUG:
    INSTALLED_APPS.insert(7, 'debug_toolbar')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.account.middleware.HallActivitySuspendedMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]
if DEBUG:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'toyxona.urls'

STATIC_VERSION = time.time() if DEBUG else int(os.getenv('STATIC_VERSION', '1'))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'DIRS': [BASE_DIR / 'templates'],
        'OPTIONS': {
            'match_extension': 'j2',
            'undefined': jinja2.Undefined,
            'bytecode_cache': {'enabled': not DEBUG},
            'extensions': DEFAULT_EXTENSIONS + [
                "django_bootstrap5.jinja2.BootstrapTags",
                "toyxona.jinja2_extension.ToyxonaUtils",
            ],
            'globals': {
                "DEBUG": DEBUG,
                'STATIC_VERSION': STATIC_VERSION,
            },
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.static',
                'django.template.context_processors.media',
                'django.template.context_processors.i18n',
                'django.contrib.messages.context_processors.messages',
                'toyxona.context_processors.toyxona',
            ],
        }
    }
]

WSGI_APPLICATION = 'toyxona.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'USER': os.environ["DATABASE_USER"],
        'PASSWORD': os.environ["DATABASE_PASSWORD"],
        'NAME': os.environ["DATABASE_NAME"],
        'HOST': os.environ["DATABASE_HOST"],
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGES = (
    ('uz', "O'zbekcha"),
    ('ru', "Ruscha"),
    ('en', "Inglizcha"),
)
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = 'static/backend/'
STATICFILES_DIRS = [BASE_DIR / 'assets']
STATIC_ROOT = BASE_DIR / 'static' / 'backend'
WHITENOISE_USE_FINDERS = DEBUG
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_THOUSAND_SEPARATOR = True
AUTH_USER_MODEL = 'account.User'

LOGIN_URL = reverse_lazy('account:login')
LOGIN_REDIRECT_URL = reverse_lazy('main:dashboard')
LOGOUT_REDIRECT_URL = reverse_lazy('main:index')

SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '86400'))
SESSION_SAVE_EVERY_REQUEST = True
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

INTERNAL_IPS = ["127.0.0.1"]
BOOTSTRAP5 = {"wrapper_class": "mb-2"}

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_RESULT_EXPIRES = 30
CELERY_ENABLE_UTC = False

REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Odamlar soni: >= TOY_EVENT_THRESHOLD bo'lsa «toy» (tadbir) hisoblanadi (12–15 tavsiya)
TOY_EVENT_THRESHOLD = int(os.getenv("TOY_EVENT_THRESHOLD", "12"))
# Avtomatik sanash intervali (soniya), Celery Beat uchun
PEOPLE_COUNT_SYNC_INTERVAL = int(os.getenv("PEOPLE_COUNT_SYNC_INTERVAL", "300"))

OTP_TOTP_ISSUER = "toyxona.uz"
OTP_ADMIN_HIDE_SENSITIVE_DATA = os.getenv('OTP_ADMIN_HIDE_SENSITIVE_DATA', '').lower() != 'false'
OTP_ADMIN_REQUIRED = os.getenv('OTP_ADMIN_REQUIRED', 'true').lower() == 'true'

EDGE_DEVICES_TIMEOUT = int(os.getenv('EDGE_DEVICES_TIMEOUT', '15'))
EDGE_API_TIMEOUT = int(os.getenv('EDGE_API_TIMEOUT', '45'))
