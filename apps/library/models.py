from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

CLOSED_ISSUE_STATUSES = ('returned', 'lost')


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    total_copies = models.IntegerField(default=1)
    available_copies = models.IntegerField(default=1)
    shelf_location = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.title} by {self.author}"

    @property
    def is_available(self):
        return self.available_copies > 0

    @property
    def issued_copies(self):
        return self.total_copies - self.available_copies


class Member(models.Model):
    MEMBERSHIP_TYPES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('external', 'External'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    member_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    membership_type = models.CharField(max_length=20, choices=MEMBERSHIP_TYPES, default='student')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    date_of_birth = models.DateField(null=True, blank=True)
    join_date = models.DateField(auto_now_add=True)
    membership_expiry = models.DateField(null=True, blank=True)
    max_books_allowed = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.member_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def active_issues(self):
        return self.bookissue_set.exclude(status__in=CLOSED_ISSUE_STATUSES).count()

    @property
    def has_overdue_books(self):
        return self.bookissue_set.exclude(status__in=CLOSED_ISSUE_STATUSES).filter(
            due_date__lt=timezone.localdate()
        ).exists()

    @property
    def has_unpaid_fines(self):
        today = timezone.localdate()
        return (
            self.bookissue_set.exclude(status__in=CLOSED_ISSUE_STATUSES)
            .filter(due_date__lt=today, fine_paid=False)
            .exists()
            or self.bookissue_set.filter(
                status__in=CLOSED_ISSUE_STATUSES,
                fine_paid=False,
                fine_amount__gt=0,
            ).exists()
        )

    @property
    def can_borrow(self):
        return (
            self.status == 'active'
            and self.active_issues < self.max_books_allowed
            and not self.has_overdue_books
            and not self.has_unpaid_fines
        )

    @property
    def total_fine(self):
        total = Decimal('0.00')
        for issue in self.bookissue_set.exclude(status__in=CLOSED_ISSUE_STATUSES).filter(fine_paid=False):
            total += issue.calculate_fine()
        for issue in self.bookissue_set.filter(
            status__in=CLOSED_ISSUE_STATUSES,
            fine_paid=False,
            fine_amount__gt=0,
        ):
            total += issue.fine_amount
        return total


class BookIssue(models.Model):
    CLOSED_STATUSES = CLOSED_ISSUE_STATUSES
    STATUS_CHOICES = [
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    fine_paid = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_books')
    returned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_books')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.member.full_name} - {self.book.title}"

    def save(self, *args, **kwargs):
        if not self.due_date:
            from django.conf import settings

            self.due_date = timezone.localdate() + timedelta(days=getattr(settings, 'DEFAULT_LOAN_DAYS', 14))
        super().save(*args, **kwargs)

    def get_days_overdue(self, check_date=None):
        if check_date is None:
            if self.status == 'returned' and self.return_date:
                check_date = self.return_date
            else:
                check_date = timezone.localdate()
        if check_date > self.due_date:
            return (check_date - self.due_date).days
        return 0

    @property
    def days_overdue(self):
        return self.get_days_overdue()

    @property
    def effective_status(self):
        if self.status in self.CLOSED_STATUSES:
            return self.status
        if timezone.localdate() > self.due_date:
            return 'overdue'
        return 'issued'

    @property
    def current_fine(self):
        if self.status in self.CLOSED_STATUSES:
            return self.fine_amount
        return self.calculate_fine()

    def calculate_fine(self, check_date=None):
        from django.conf import settings
        fine_per_day = Decimal(str(getattr(settings, 'FINE_PER_DAY', 2)))
        return Decimal(self.get_days_overdue(check_date)) * fine_per_day

    def update_fine(self):
        self.fine_amount = self.calculate_fine()
        self.save()


class Notification(models.Model):
    TYPE_CHOICES = [
        ('overdue', 'Overdue'),
        ('reminder', 'Due Soon'),
        ('info', 'Information'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.member.full_name}"
