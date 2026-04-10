from .models import Notification


def unread_notifications(request):
    """Inject unread notification count into every template."""
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            count = Notification.objects.filter(is_read=False).count()
        else:
            member = getattr(request.user, 'member', None)
            if member is None:
                count = 0
            else:
                count = Notification.objects.filter(member=member, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
