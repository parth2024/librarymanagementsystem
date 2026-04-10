"""
Management command: send_reminders
Sends due-date reminder notifications for books due in the next N days.
Usage:  python manage.py send_reminders
        python manage.py send_reminders --days 3
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from library.models import BookIssue, Notification


class Command(BaseCommand):
    help = 'Creates reminder notifications for books due soon'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Number of days ahead to check (default: 2)',
        )

    def handle(self, *args, **options):
        days_ahead = options['days']
        today = timezone.localdate()
        due_by = today + timedelta(days=days_ahead)

        due_soon = BookIssue.objects.filter(
            status='issued',
            due_date__gte=today,
            due_date__lte=due_by,
        ).select_related('member', 'book')

        created = 0
        for issue in due_soon:
            days_left = (issue.due_date - today).days
            msg = (
                f"Reminder: '{issue.book.title}' is due in {days_left} day(s) "
                f"(on {issue.due_date.strftime('%d %b %Y')}). Please return on time."
            )
            Notification.objects.create(
                member=issue.member,
                message=msg,
                notification_type='reminder',
            )
            created += 1
            self.stdout.write(f"  → {issue.member.full_name}: {issue.book.title} due in {days_left}d")

        overdue = BookIssue.objects.filter(
            status__in=['issued', 'overdue'],
            due_date__lt=today,
        ).exclude(status='lost').select_related('member', 'book')

        for issue in overdue:
            msg = (
                f"Overdue: '{issue.book.title}' was due on {issue.due_date.strftime('%d %b %Y')}. "
                f"Fine: ₹{issue.calculate_fine()}. Please return immediately."
            )
            Notification.objects.create(
                member=issue.member,
                message=msg,
                notification_type='overdue',
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"\n✓ Created {created} notification(s).\n"))
