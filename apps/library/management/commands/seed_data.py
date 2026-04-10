"""
Management command: seed_data
Adds sample books, members and a few issue records for testing.
Usage:  python manage.py seed_data
        python manage.py seed_data --clear   (wipe existing data first)
"""

from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.library.models import Book, BookIssue, Category, Member


CATEGORIES = [
    'Computer Science', 'Mathematics', 'Physics', 'Chemistry',
    'Biology', 'Literature', 'History', 'Economics', 'Psychology', 'Law',
]

BOOKS = [
    # (title, author, isbn, category, publisher, year, copies)
    ("Clean Code", "Robert C. Martin", "9780132350884", "Computer Science", "Prentice Hall", 2008, 3),
    ("The Pragmatic Programmer", "David Thomas", "9780135957059", "Computer Science", "Addison-Wesley", 2019, 2),
    ("Introduction to Algorithms", "Thomas H. Cormen", "9780262033848", "Computer Science", "MIT Press", 2009, 4),
    ("Python Crash Course", "Eric Matthes", "9781593279288", "Computer Science", "No Starch Press", 2019, 5),
    ("Design Patterns", "Gang of Four", "9780201633610", "Computer Science", "Addison-Wesley", 1994, 2),
    ("Django for Beginners", "William S. Vincent", "9781735467221", "Computer Science", "WelcomeToCode", 2022, 3),
    ("Calculus", "James Stewart", "9781305271760", "Mathematics", "Cengage", 2015, 3),
    ("Linear Algebra Done Right", "Sheldon Axler", "9783319307664", "Mathematics", "Springer", 2015, 2),
    ("Discrete Mathematics", "Kenneth Rosen", "9780073383095", "Mathematics", "McGraw-Hill", 2018, 4),
    ("A Brief History of Time", "Stephen Hawking", "9780553380163", "Physics", "Bantam", 1988, 3),
    ("Concepts of Physics", "H.C. Verma", "9788177091878", "Physics", "Bharati Bhawan", 2010, 5),
    ("Organic Chemistry", "Paula Bruice", "9780134042282", "Chemistry", "Pearson", 2016, 2),
    ("Cell Biology", "Thomas Pollard", "9780323341264", "Biology", "Elsevier", 2017, 2),
    ("To Kill a Mockingbird", "Harper Lee", "9780061935466", "Literature", "HarperCollins", 1960, 4),
    ("1984", "George Orwell", "9780451524935", "Literature", "Signet Classic", 1949, 3),
    ("Pride and Prejudice", "Jane Austen", "9780141439518", "Literature", "Penguin", 1813, 3),
    ("Sapiens", "Yuval Noah Harari", "9780062316110", "History", "Harper", 2015, 4),
    ("The Art of War", "Sun Tzu", "9781599869773", "History", "Filiquarian", 2007, 2),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "9780374533557", "Psychology", "FSG", 2011, 2),
    ("Principles of Economics", "N. Gregory Mankiw", "9781305585126", "Economics", "Cengage", 2014, 3),
]

MEMBERS = [
    # (member_id, first_name, last_name, email, phone, type)
    ("U15KY23S0001", "Simeen", "Jamadar", "simeen@college.edu", "9876543210", "student"),
    ("U15KY23S0002", "Naziya", "Hebbal", "naziya@college.edu", "9876543211", "student"),
    ("U15KY23S0003", "Kausar", "Kalaigar", "kausar@college.edu", "9876543212", "student"),
    ("U15KY23S0004", "Arjun", "Sharma", "arjun@college.edu", "9876543213", "student"),
    ("U15KY23S0005", "Priya", "Kulkarni", "priya@college.edu", "9876543214", "student"),
    ("U15KY23S0006", "Rohit", "Patil", "rohit@college.edu", "9876543215", "student"),
    ("U15KY23S0007", "Sneha", "Desai", "sneha@college.edu", "9876543216", "student"),
    ("U15KY23S0008", "Akash", "More", "akash@college.edu", "9876543217", "student"),
    ("FAC001", "Rajeshwari", "Pathak", "rpathak@college.edu", "9876543218", "faculty"),
    ("FAC002", "Suresh", "Kumar", "skumar@college.edu", "9876543219", "faculty"),
    ("STF001", "Meena", "Gaikwad", "mgaikwad@college.edu", "9876543220", "staff"),
]


class Command(BaseCommand):
    help = 'Seeds the database with sample library data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('  Clearing existing data...')
            BookIssue.objects.all().delete()
            Book.objects.all().delete()
            Member.objects.all().delete()
            Category.objects.all().delete()

        admin = User.objects.filter(is_superuser=True).order_by('id').first()
        if settings.ENABLE_DEMO_DATA and not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@library.com', 'admin123')
            self.stdout.write('  Created demo admin user (admin / admin123)')
            admin = User.objects.get(username='admin')

        cats = {}
        for name in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name)
            cats[name] = cat
        self.stdout.write(f'  Added or verified {len(CATEGORIES)} categories')

        books_created = 0
        book_objs = {}
        for title, author, isbn, cat_name, publisher, year, copies in BOOKS:
            book, created = Book.objects.get_or_create(
                isbn=isbn,
                defaults={
                    'title': title,
                    'author': author,
                    'category': cats.get(cat_name),
                    'publisher': publisher,
                    'publication_year': year,
                    'total_copies': copies,
                    'available_copies': copies,
                    'shelf_location': f"{cat_name[:3].upper()}-{str(year)[-2:]}",
                }
            )
            book_objs[isbn] = book
            if created:
                books_created += 1
        self.stdout.write(f'  Added {books_created} new books ({len(BOOKS)} total configured)')

        members_created = 0
        member_objs = []
        for mid, fn, ln, email, phone, mtype in MEMBERS:
            member, created = Member.objects.get_or_create(
                member_id=mid,
                defaults={
                    'first_name': fn,
                    'last_name': ln,
                    'email': email,
                    'phone': phone,
                    'membership_type': mtype,
                    'membership_expiry': date(2026, 12, 31),
                    'max_books_allowed': 5 if mtype == 'faculty' else 3,
                }
            )
            member_objs.append(member)
            if created:
                members_created += 1
        self.stdout.write(f'  Added {members_created} new members ({len(MEMBERS)} total configured)')

        if BookIssue.objects.count() == 0 and admin is not None:
            today = timezone.localdate()
            sample_issues = [
                # (member_idx, isbn, days_ago_issued, days_until_due, returned)
                (0, "9780132350884", 5, 9, False),
                (1, "9781593279288", 3, 11, False),
                (2, "9780062316110", 20, -6, False),
                (3, "9780061935466", 10, 4, False),
                (4, "9780451524935", 15, -1, False),
                (0, "9780135957059", 30, -16, True),
                (5, "9780073383095", 2, 12, False),
                (6, "9780553380163", 7, 7, False),
            ]

            issues_created = 0
            for m_idx, isbn, days_ago, days_due, returned in sample_issues:
                member = member_objs[m_idx]
                book_qs = Book.objects.filter(isbn=isbn)
                if not book_qs.exists():
                    continue
                book = book_qs.first()
                if book.available_copies < 1 and not returned:
                    continue

                issue_date = today - timedelta(days=days_ago)
                due_date = today + timedelta(days=days_due)

                issue = BookIssue(
                    member=member,
                    book=book,
                    due_date=due_date,
                    issued_by=admin,
                )
                issue.save()
                BookIssue.objects.filter(pk=issue.pk).update(issue_date=issue_date)
                issue.refresh_from_db()

                if returned:
                    return_date = today - timedelta(days=1)
                    fine = issue.calculate_fine()
                    issue.status = 'returned'
                    issue.return_date = return_date
                    issue.fine_amount = fine
                    issue.returned_to = admin
                    issue.save()
                    book.save()
                elif due_date < today:
                    issue.status = 'overdue'
                    issue.fine_amount = issue.calculate_fine()
                    issue.save()
                    book.available_copies -= 1
                    book.save()
                else:
                    book.available_copies -= 1
                    book.save()

                issues_created += 1

            self.stdout.write(f'  Added {issues_created} sample issue records')
        elif BookIssue.objects.count() == 0:
            self.stdout.write('  Demo data is disabled; skipping sample issue records that require an issuing admin.')

        self.stdout.write(self.style.SUCCESS('\n  Seed complete.\n'))
