from .base import *
import os

DEBUG = False

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("The SECRET_KEY environment variable must be set in production.")

ALLOWED_HOSTS = get_list_env('ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    # Fallback to local if testing production-like mode locally
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# CSRF & Session Security
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = get_bool_env('SECURE_SSL_REDIRECT', default=False) # Set to True if using HTTPS

# WhiteNoise Configuration for Static Files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# WhiteNoise storage to compress and cache static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Database configuration can be pulled from DATABASE_URL
import dj_database_url
DATABASES['default'] = dj_database_url.config(
    default=os.environ.get('DATABASE_URL'),
    conn_max_age=600,
    conn_health_checks=True,
)

# Email Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
