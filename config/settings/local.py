from .base import *

DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-local-only-key-do-not-use-in-production')

ALLOWED_HOSTS = ['*']

# Optional: Add local-only apps like django-debug-toolbar
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Use console email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
