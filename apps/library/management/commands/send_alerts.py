from django.core.management.base import BaseCommand
from library.utils import send_overdue_alerts

class Command(BaseCommand):
    help = 'Sends automated email alerts to members with overdue books'

    def handle(self, *args, **options):
        self.stdout.write('Checking for overdue books...')
        count = send_overdue_alerts()
        self.stdout.write(self.style.SUCCESS(f'Successfully sent alerts to {count} members.'))
