from pathlib import Path
import os
import importlib.util
from urllib.parse import parse_qs, unquote, urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Note: Since this file is in config/settings/, we go up 3 levels.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def get_bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

def get_list_env(name, default=''):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]

def append_unique(items, value):
    if value and value not in items:
        items.append(value)

# -- Basic Settings --
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key-change-it')

ALLOWED_HOSTS = get_list_env('ALLOWED_HOSTS', '127.0.0.1,localhost')

# -- Application definition --
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.library.apps.LibraryConfig', # Changed path to apps.library
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls' # Changed path

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.library.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# -- Database --
# (Keeping it simple in base, will be overridden in local/prod)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -- Password validation --
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -- Internationalization --
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# -- Static & Media --
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -- App-level Settings --
FINE_PER_DAY = int(os.environ.get('FINE_PER_DAY', 2))
DEFAULT_LOAN_DAYS = int(os.environ.get('DEFAULT_LOAN_DAYS', 14))
ENABLE_PUBLIC_REGISTRATION = get_bool_env('ENABLE_PUBLIC_REGISTRATION', default=DEBUG)
ENABLE_SEED_TOOLS = get_bool_env('ENABLE_SEED_TOOLS', default=DEBUG)
ENABLE_DEMO_DATA = get_bool_env('ENABLE_DEMO_DATA', default=DEBUG)

# -- Logging --
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {'class': 'logging.FileHandler', 'filename': BASE_DIR / 'lms.log', 'formatter': 'verbose'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING'},
        'apps.library': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}
