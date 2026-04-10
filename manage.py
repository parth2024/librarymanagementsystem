#!/usr/bin/env python
import os
import sys

def main():
    """Run administrative tasks."""
    # Add 'apps' directory to sys.path so we can import apps directly
    # This allows both 'import apps.library' and 'import library' (if we add the path)
    # However, keeping it as 'apps.library' in settings is more explicit.
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed or "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
