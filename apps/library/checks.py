from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_safety_checks(app_configs, **kwargs):
    errors = []

    if settings.DEBUG:
        return errors

    if getattr(settings, "ENABLE_PUBLIC_REGISTRATION", False):
        errors.append(
            Error(
                "Public registration is enabled while DEBUG is False.",
                hint="Set ENABLE_PUBLIC_REGISTRATION=False in production.",
                id="library.E001",
            )
        )

    if getattr(settings, "ENABLE_SEED_TOOLS", False):
        errors.append(
            Error(
                "Seed tools are enabled while DEBUG is False.",
                hint="Set ENABLE_SEED_TOOLS=False in production.",
                id="library.E002",
            )
        )

    if getattr(settings, "ENABLE_DEMO_DATA", False):
        errors.append(
            Error(
                "Demo data mode is enabled while DEBUG is False.",
                hint="Set ENABLE_DEMO_DATA=False in production.",
                id="library.E003",
            )
        )

    if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        errors.append(
            Error(
                "Console email backend is enabled while DEBUG is False.",
                hint="Configure a real SMTP or provider-backed EMAIL_BACKEND in production.",
                id="library.E004",
            )
        )

    return errors
