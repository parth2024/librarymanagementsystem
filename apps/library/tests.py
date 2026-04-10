from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.checks import run_checks
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from lms_project.settings import _database_config_from_url
from .forms import BookForm, BookIssueForm, ReturnBookForm
from .models import Book, BookIssue, Category, Member, Notification


class LibraryRegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Science')
        self.staff_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            is_staff=True,
        )
        self.member_user = User.objects.create_user(
            username='reader',
            password='readerpass123',
        )
        self.member = Member.objects.create(
            user=self.member_user,
            member_id='MEM20260001',
            first_name='Read',
            last_name='Only',
            email='reader@example.com',
            phone='1234567890',
            status='active',
            membership_type='student',
            max_books_allowed=3,
        )
        self.book = Book.objects.create(
            title='Django Patterns',
            author='A. Author',
            isbn='9780000000001',
            category=self.category,
            total_copies=3,
            available_copies=2,
        )

    def test_member_with_overdue_issue_cannot_borrow(self):
        overdue_issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=3),
            status='overdue',
            issued_by=self.staff_user,
        )

        self.assertEqual(self.member.active_issues, 1)
        self.assertFalse(self.member.can_borrow)
        self.assertEqual(self.member.total_fine, overdue_issue.calculate_fine())

    def test_member_with_unpaid_fine_cannot_borrow(self):
        BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=10),
            return_date=timezone.localdate() - timedelta(days=5),
            status='returned',
            fine_amount=Decimal('20.00'),
            fine_paid=False,
            issued_by=self.staff_user,
        )

        self.assertFalse(self.member.can_borrow)

    def test_book_form_rejects_available_copies_above_total(self):
        form = BookForm(data={
            'title': 'Bad Inventory',
            'author': 'Tester',
            'isbn': '9780000000002',
            'category': self.category.pk,
            'publisher': '',
            'publication_year': '',
            'total_copies': 1,
            'available_copies': 2,
            'shelf_location': '',
            'description': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('available_copies', form.errors)

    def test_issue_form_rejects_past_due_date(self):
        form = BookIssueForm(data={
            'member': self.member.pk,
            'book': self.book.pk,
            'due_date': (timezone.localdate() - timedelta(days=1)).isoformat(),
            'remarks': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)

    def test_return_form_rejects_future_return_date(self):
        issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate(),
            status='issued',
            issued_by=self.staff_user,
        )
        form = ReturnBookForm(
            data={
                'issue_id': issue.pk,
                'return_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
                'remarks': '',
            },
            issue=issue,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('return_date', form.errors)

    def test_return_book_uses_selected_return_date_for_fine(self):
        self.client.force_login(self.staff_user)
        issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=5),
            status='issued',
            issued_by=self.staff_user,
        )
        issue.issue_date = timezone.localdate() - timedelta(days=14)
        issue.save(update_fields=['issue_date'])

        response = self.client.post(
            reverse('return_book', args=[issue.pk]),
            data={
                'issue_id': issue.pk,
                'return_date': (timezone.localdate() - timedelta(days=2)).isoformat(),
                'remarks': 'Returned late',
            },
        )

        self.assertRedirects(response, reverse('issue_list'))
        issue.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(issue.status, 'returned')
        self.assertEqual(issue.fine_amount, Decimal('6.00'))
        self.assertEqual(self.book.available_copies, 3)

    def test_return_book_cannot_be_processed_twice(self):
        self.client.force_login(self.staff_user)
        issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate(),
            return_date=timezone.localdate(),
            status='returned',
            issued_by=self.staff_user,
            returned_to=self.staff_user,
            fine_amount=Decimal('0.00'),
        )

        response = self.client.get(reverse('return_book', args=[issue.pk]))

        self.assertRedirects(response, reverse('issue_list'))
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)

    def test_notifications_view_handles_user_without_member(self):
        user_without_member = User.objects.create_user(
            username='nomember',
            password='nomemberpass123',
        )
        self.client.force_login(user_without_member)

        response = self.client.get(reverse('notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['notifications']), [])

    def test_mark_all_read_handles_user_without_member(self):
        user_without_member = User.objects.create_user(
            username='nomember2',
            password='nomemberpass123',
        )
        self.client.force_login(user_without_member)

        response = self.client.post(reverse('mark_all_read'))

        self.assertRedirects(response, reverse('notifications'))

    def test_mark_all_read_rejects_get_requests(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('mark_all_read'))

        self.assertEqual(response.status_code, 405)

    def test_mark_read_rejects_get_requests(self):
        notification = Notification.objects.create(
            member=self.member,
            message='Test notification',
            notification_type='info',
        )
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('mark_read', args=[notification.pk]))

        self.assertEqual(response.status_code, 405)

    def test_pay_fine_requires_post(self):
        issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=7),
            return_date=timezone.localdate(),
            status='returned',
            fine_amount=Decimal('10.00'),
            fine_paid=False,
            issued_by=self.staff_user,
        )
        self.client.force_login(self.staff_user)

        get_response = self.client.get(reverse('pay_fine', args=[issue.pk]))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse('pay_fine', args=[issue.pk]))
        self.assertRedirects(post_response, reverse('fine_list'))
        issue.refresh_from_db()
        self.assertTrue(issue.fine_paid)

    def test_logout_requires_post(self):
        self.client.force_login(self.staff_user)

        get_response = self.client.get(reverse('logout'))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse('logout'))
        self.assertRedirects(post_response, reverse('login'))

    def test_reports_category_counts_use_distinct_books(self):
        extra_book = Book.objects.create(
            title='Second Book',
            author='B. Author',
            isbn='9780000000003',
            category=self.category,
            total_copies=1,
            available_copies=1,
        )
        BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=7),
            status='issued',
            issued_by=self.staff_user,
        )
        BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=10),
            status='returned',
            return_date=timezone.localdate(),
            issued_by=self.staff_user,
        )
        BookIssue.objects.create(
            member=self.member,
            book=extra_book,
            due_date=timezone.localdate() + timedelta(days=8),
            status='issued',
            issued_by=self.staff_user,
        )

        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('reports'))

        category_stats = list(response.context['category_stats'])
        self.assertEqual(len(category_stats), 1)
        self.assertEqual(category_stats[0].book_count, 2)
        self.assertEqual(category_stats[0].issue_count, 3)


class LibrarySmokeFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Engineering')
        self.staff_user = User.objects.create_user(
            username='librarian',
            password='adminpass123',
            is_staff=True,
        )
        self.member_user = User.objects.create_user(
            username='member1',
            password='memberpass123',
        )
        self.member = Member.objects.create(
            user=self.member_user,
            member_id='MEM20260010',
            first_name='Flow',
            last_name='User',
            email='flow@example.com',
            phone='9876543210',
            status='active',
            membership_type='student',
            max_books_allowed=2,
        )
        self.book = Book.objects.create(
            title='Secure Django',
            author='Sec Ops',
            isbn='9780000000010',
            category=self.category,
            total_copies=2,
            available_copies=2,
        )

    def test_anonymous_dashboard_redirects_to_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_login_flow_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            data={'username': 'librarian', 'password': 'adminpass123'},
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_staff_pages_render(self):
        self.client.force_login(self.staff_user)

        for name in ['dashboard', 'book_list', 'issue_list', 'reports', 'notifications', 'profile']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_member_cannot_access_admin_issue_page(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('issue_book'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_staff_can_issue_book_end_to_end(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('issue_book'),
            data={
                'member': self.member.pk,
                'book': self.book.pk,
                'due_date': (timezone.localdate() + timedelta(days=7)).isoformat(),
                'remarks': 'Smoke test issue',
            },
        )

        self.assertRedirects(response, reverse('issue_list'))
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)
        issue = BookIssue.objects.get(member=self.member, book=self.book)
        self.assertEqual(issue.status, 'issued')
        self.assertTrue(
            Notification.objects.filter(member=self.member, message__icontains='has been issued').exists()
        )

    def test_member_can_mark_own_notification_read(self):
        notification = Notification.objects.create(
            member=self.member,
            message='Book due soon',
            notification_type='reminder',
        )
        self.client.force_login(self.member_user)

        page_response = self.client.get(reverse('notifications'))
        self.assertEqual(page_response.status_code, 200)

        mark_response = self.client.post(reverse('mark_read', args=[notification.pk]))

        self.assertRedirects(mark_response, reverse('notifications'))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_staff_can_export_reports_csv(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('export_books'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('books_report.csv', response['Content-Disposition'])


class LibraryAccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Access Control')
        self.staff_user = User.objects.create_user(
            username='access_admin',
            password='adminpass123',
            is_staff=True,
        )
        self.member_user = User.objects.create_user(
            username='access_member',
            password='memberpass123',
        )
        self.member = Member.objects.create(
            user=self.member_user,
            member_id='MEM20260100',
            first_name='Access',
            last_name='Member',
            email='access@example.com',
            phone='1111111111',
            status='active',
            membership_type='student',
            max_books_allowed=2,
        )
        self.other_member = Member.objects.create(
            member_id='MEM20260101',
            first_name='Other',
            last_name='Reader',
            email='other@example.com',
            phone='2222222222',
            status='active',
            membership_type='student',
            max_books_allowed=2,
        )
        self.book = Book.objects.create(
            title='Production Django',
            author='Ops Author',
            isbn='9780000000099',
            category=self.category,
            total_copies=2,
            available_copies=2,
        )
        self.own_issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=5),
            status='issued',
            issued_by=self.staff_user,
        )
        self.other_issue = BookIssue.objects.create(
            member=self.other_member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=3),
            status='issued',
            issued_by=self.staff_user,
        )

    def test_member_cannot_access_member_directory(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('member_list'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_member_can_only_view_own_member_profile(self):
        self.client.force_login(self.member_user)

        own_response = self.client.get(reverse('member_detail', args=[self.member.pk]))
        other_response = self.client.get(reverse('member_detail', args=[self.other_member.pk]))

        self.assertEqual(own_response.status_code, 200)
        self.assertRedirects(other_response, reverse('dashboard'))

    def test_member_issue_list_is_scoped_to_own_records(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('issue_list'))

        issues = list(response.context['issues'])
        self.assertTrue(issues)
        self.assertEqual({issue.member_id for issue in issues}, {self.member.pk})

    def test_member_fine_list_is_scoped_to_own_records(self):
        returned_issue = BookIssue.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=6),
            return_date=timezone.localdate(),
            status='returned',
            fine_amount=Decimal('12.00'),
            fine_paid=False,
            issued_by=self.staff_user,
            returned_to=self.staff_user,
        )
        BookIssue.objects.create(
            member=self.other_member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=8),
            return_date=timezone.localdate(),
            status='returned',
            fine_amount=Decimal('30.00'),
            fine_paid=False,
            issued_by=self.staff_user,
            returned_to=self.staff_user,
        )
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('fine_list'))

        fines = list(response.context['fines'])
        self.assertTrue(fines)
        self.assertEqual({issue.member_id for issue in fines}, {self.member.pk})
        self.assertEqual(response.context['unpaid_total'], returned_issue.current_fine)

    def test_member_dashboard_shows_only_own_recent_issues(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('dashboard'))

        recent_issues = list(response.context['recent_issues'])
        overdue_issues = list(response.context['overdue_issues'])
        self.assertTrue(recent_issues)
        self.assertEqual({issue.member_id for issue in recent_issues}, {self.member.pk})
        self.assertEqual(overdue_issues, [])

    def test_member_book_detail_hides_issue_history(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('book_detail', args=[self.book.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['issue_history']), [])

    def test_pay_fine_rejects_unreturned_issue(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse('pay_fine', args=[self.other_issue.pk]))

        self.assertRedirects(response, reverse('fine_list'))
        self.other_issue.refresh_from_db()
        self.assertFalse(self.other_issue.fine_paid)


class LibraryProductionSettingsTests(TestCase):
    @override_settings(ENABLE_PUBLIC_REGISTRATION=False)
    def test_registration_view_is_disabled_when_flag_is_off(self):
        response = self.client.post(
            reverse('register'),
            data={
                'username': 'newmember',
                'password1': 'ComplexPass123!',
                'password2': 'ComplexPass123!',
                'first_name': 'New',
                'last_name': 'Member',
                'email': 'newmember@example.com',
                'phone': '9999999999',
            },
        )

        self.assertRedirects(response, reverse('login'))
        self.assertFalse(User.objects.filter(username='newmember').exists())

    @override_settings(
        DEBUG=False,
        ENABLE_PUBLIC_REGISTRATION=True,
        ENABLE_SEED_TOOLS=False,
        ENABLE_DEMO_DATA=False,
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
    )
    def test_deploy_checks_reject_public_registration_in_production(self):
        errors = run_checks(include_deployment_checks=True)

        self.assertTrue(any(error.id == 'library.E001' for error in errors))

    @override_settings(
        DEBUG=False,
        ENABLE_PUBLIC_REGISTRATION=False,
        ENABLE_SEED_TOOLS=False,
        ENABLE_DEMO_DATA=False,
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
    )
    def test_deploy_checks_reject_console_email_backend_in_production(self):
        errors = run_checks(include_deployment_checks=True)

        self.assertTrue(any(error.id == 'library.E004' for error in errors))


class RailwayReadinessTests(TestCase):
    def test_healthcheck_endpoint_returns_ok(self):
        response = self.client.get(reverse('healthcheck'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_database_url_parser_handles_postgres_urls(self):
        config = _database_config_from_url(
            'postgresql://railway:secret@postgres.railway.internal:5432/railway',
            None,
        )

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'railway')
        self.assertEqual(config['USER'], 'railway')
        self.assertEqual(config['PASSWORD'], 'secret')
        self.assertEqual(config['HOST'], 'postgres.railway.internal')
        self.assertEqual(config['PORT'], '5432')
