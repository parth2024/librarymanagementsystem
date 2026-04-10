"""
Management command: update_fines
Usage:  python manage.py update_fines
        python manage.py update_fines --dry-run

Schedule with cron for daily execution:
    0 0 * * * /path/to/venv/bin/python /path/to/manage.py update_fines
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from library.models import BookIssue


class Command(BaseCommand):
    help = 'Updates overdue status and recalculates fines for all active issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.localdate()

        active_issues = BookIssue.objects.filter(
            status__in=['issued', 'overdue']
        ).select_related('member', 'book')

        updated_count = 0
        fine_total = 0

        self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Running fine update — {today}\n")
        self.stdout.write("-" * 60)

        for issue in active_issues:
            new_fine = issue.calculate_fine()
            new_status = 'overdue' if today > issue.due_date else 'issued'

            changed = (issue.fine_amount != new_fine) or (issue.status != new_status)

            if changed:
                updated_count += 1
                fine_total += new_fine
                self.stdout.write(
                    f"  Issue #{issue.pk} | {issue.member.full_name} | "
                    f"{issue.book.title[:30]} | "
                    f"Status: {issue.status}→{new_status} | "
                    f"Fine: ₹{issue.fine_amount}→₹{new_fine}"
                )
                if not dry_run:
                    issue.fine_amount = new_fine
                    issue.status = new_status
                    issue.save(update_fields=['fine_amount', 'status'])

        self.stdout.write("-" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ {'Would update' if dry_run else 'Updated'} {updated_count} issue(s). "
                f"Total active fines: ₹{fine_total}\n"
            )
        )
