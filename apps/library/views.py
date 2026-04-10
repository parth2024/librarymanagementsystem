import csv
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import admin_required
from .forms import (
    BookForm,
    BookIssueForm,
    BookSearchForm,
    CategoryForm,
    LoginForm,
    MemberForm,
    RegisterForm,
    ReturnBookForm,
)
from .models import Book, BookIssue, Category, Member, Notification
from .utils import send_overdue_alerts

CLOSED_ISSUE_STATUSES = ("returned", "lost")


def _generate_member_id():
    year = timezone.now().year
    prefix = f"MEM{year}"
    latest_member_id = (
        Member.objects.filter(member_id__startswith=prefix)
        .order_by("-member_id")
        .values_list("member_id", flat=True)
        .first()
    )

    next_number = 1
    if latest_member_id:
        suffix = latest_member_id[len(prefix):]
        if suffix.isdigit():
            next_number = int(suffix) + 1

    member_id = f"{prefix}{next_number:04d}"
    while Member.objects.filter(member_id=member_id).exists():
        next_number += 1
        member_id = f"{prefix}{next_number:04d}"
    return member_id


def _get_request_member(user):
    return getattr(user, "member", None)


def _is_admin_user(user):
    return user.is_staff or user.is_superuser


def _open_issue_queryset(queryset):
    return queryset.exclude(status__in=CLOSED_ISSUE_STATUSES)


def _filter_issues_by_status(queryset, status, today):
    if status == "all":
        return queryset
    if status == "returned":
        return queryset.filter(status="returned")
    if status == "lost":
        return queryset.filter(status="lost")

    open_issues = _open_issue_queryset(queryset)
    if status == "overdue":
        return open_issues.filter(due_date__lt=today)
    if status == "issued":
        return open_issues.filter(due_date__gte=today)
    return queryset


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(
        request,
        "library/login.html",
        {
            "form": form,
            "registration_enabled": settings.ENABLE_PUBLIC_REGISTRATION,
        },
    )


def register_view(request):
    if not settings.ENABLE_PUBLIC_REGISTRATION:
        messages.info(request, "Self-registration is disabled.")
        return redirect("login")
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            member_id = _generate_member_id()

            Member.objects.create(
                user=user,
                member_id=member_id,
                first_name=form.cleaned_data.get("first_name"),
                last_name=form.cleaned_data.get("last_name"),
                email=form.cleaned_data.get("email"),
                phone=form.cleaned_data.get("phone"),
                status="active",
                membership_type="student",
            )

            messages.success(
                request,
                f"Account created for {user.username}. Your Member ID is {member_id}. Please log in.",
            )
            return redirect("login")
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()
    return render(request, "library/register.html", {"form": form})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


@login_required
def dashboard(request):
    today = timezone.localdate()
    is_admin = _is_admin_user(request.user)
    member = _get_request_member(request.user)
    active_issues = _open_issue_queryset(BookIssue.objects.all())

    total_books = Book.objects.count()
    total_members = Member.objects.filter(status="active").count()
    total_issued = active_issues.count()
    overdue_count = active_issues.filter(due_date__lt=today).count()

    recent_issue_queryset = BookIssue.objects.select_related("member", "book")
    overdue_issue_queryset = active_issues.select_related("member", "book")
    if not is_admin:
        if member is None:
            recent_issue_queryset = BookIssue.objects.none()
            overdue_issue_queryset = BookIssue.objects.none()
        else:
            recent_issue_queryset = recent_issue_queryset.filter(member=member)
            overdue_issue_queryset = overdue_issue_queryset.filter(member=member)

    recent_issues = recent_issue_queryset.order_by("-created_at")[:8]
    overdue_issues = overdue_issue_queryset.filter(due_date__lt=today).order_by("due_date")[:5]
    popular_books = Book.objects.annotate(issue_count=Count("bookissue")).order_by("-issue_count")[:5]

    chart_labels = []
    chart_data = []
    for i in range(5, -1, -1):
        month = today.replace(day=1) - timedelta(days=i * 30)
        count = BookIssue.objects.filter(issue_date__year=month.year, issue_date__month=month.month).count()
        chart_labels.append(month.strftime("%b %Y"))
        chart_data.append(count)

    context = {
        "total_books": total_books,
        "total_members": total_members,
        "total_issued": total_issued,
        "overdue_count": overdue_count,
        "recent_issues": recent_issues,
        "overdue_issues": overdue_issues,
        "popular_books": popular_books,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "is_admin": is_admin,
        "show_seed_tools": is_admin and settings.ENABLE_SEED_TOOLS and total_books == 0,
    }
    return render(request, "library/dashboard.html", context)


@login_required
def book_list(request):
    form = BookSearchForm(request.GET)
    books = Book.objects.select_related("category").all()

    if form.is_valid():
        query = form.cleaned_data.get("query")
        category = form.cleaned_data.get("category")
        available_only = form.cleaned_data.get("available_only")

        if query:
            books = books.filter(
                Q(title__icontains=query)
                | Q(author__icontains=query)
                | Q(isbn__icontains=query)
                | Q(publisher__icontains=query)
            )
        if category:
            books = books.filter(category=category)
        if available_only:
            books = books.filter(available_copies__gt=0)

    return render(
        request,
        "library/book_list.html",
        {
            "books": books,
            "form": form,
            "total": books.count(),
        },
    )


@login_required
@admin_required
def book_add(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Book "{book.title}" added successfully.')
            return redirect("book_list")
    else:
        form = BookForm()
    return render(request, "library/book_form.html", {"form": form, "title": "Add New Book"})


@login_required
@admin_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'Book "{book.title}" updated successfully.')
            return redirect("book_list")
    else:
        form = BookForm(instance=book)
    return render(request, "library/book_form.html", {"form": form, "title": "Edit Book", "book": book})


@login_required
@admin_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        title = book.title
        book.delete()
        messages.success(request, f'Book "{title}" deleted.')
        return redirect("book_list")
    return render(request, "library/confirm_delete.html", {"object": book, "type": "Book"})


@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    is_admin = _is_admin_user(request.user)
    issue_history = BookIssue.objects.none()
    if is_admin:
        issue_history = BookIssue.objects.filter(book=book).select_related("member").order_by("-issue_date")[:10]
    return render(
        request,
        "library/book_detail.html",
        {
            "book": book,
            "issue_history": issue_history,
            "is_admin": is_admin,
        },
    )


@login_required
@admin_required
def member_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    members = Member.objects.all()

    if query:
        members = members.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(member_id__icontains=query)
            | Q(email__icontains=query)
        )
    if status:
        members = members.filter(status=status)

    return render(
        request,
        "library/member_list.html",
        {
            "members": members,
            "query": query,
            "status": status,
            "total": members.count(),
        },
    )


@login_required
@admin_required
def member_add(request):
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save()
            messages.success(request, f'Member "{member.full_name}" registered successfully.')
            return redirect("member_list")
    else:
        form = MemberForm()
    return render(request, "library/member_form.html", {"form": form, "title": "Register New Member"})


@login_required
@admin_required
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f'Member "{member.full_name}" updated.')
            return redirect("member_list")
    else:
        form = MemberForm(instance=member)
    return render(request, "library/member_form.html", {"form": form, "title": "Edit Member", "member": member})


@login_required
@admin_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        name = member.full_name
        member.delete()
        messages.success(request, f'Member "{name}" removed.')
        return redirect("member_list")
    return render(request, "library/confirm_delete.html", {"object": member, "type": "Member"})


@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    is_admin = _is_admin_user(request.user)
    if not is_admin:
        request_member = _get_request_member(request.user)
        if request_member is None or request_member.pk != member.pk:
            messages.error(request, "Access denied.")
            return redirect("dashboard")
    issues = BookIssue.objects.filter(member=member).select_related("book").order_by("-issue_date")
    return render(
        request,
        "library/member_detail.html",
        {
            "member": member,
            "issues": issues,
            "can_manage_member": is_admin,
        },
    )


@login_required
def issue_list(request):
    status = request.GET.get("status", "issued")
    category_id = request.GET.get("category")
    today = timezone.localdate()
    is_admin = _is_admin_user(request.user)
    member = _get_request_member(request.user)

    issues = BookIssue.objects.select_related("member", "book", "book__category").all()
    if not is_admin:
        if member is None:
            issues = BookIssue.objects.none()
        else:
            issues = issues.filter(member=member)

    issues = _filter_issues_by_status(issues, status, today)
    if category_id:
        issues = issues.filter(book__category_id=category_id)

    return render(
        request,
        "library/issue_list.html",
        {
            "issues": issues.order_by("-created_at"),
            "status": status,
            "selected_category": category_id,
            "categories": Category.objects.all(),
            "total": issues.count(),
            "is_admin": is_admin,
            "status_tabs": [
                ("all", "All"),
                ("issued", "Issued"),
                ("overdue", "Overdue"),
                ("returned", "Returned"),
            ],
        },
    )


@login_required
@admin_required
def issue_book(request):
    if request.method == "POST":
        form = BookIssueForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                member = Member.objects.select_for_update().get(pk=form.cleaned_data["member"].pk)
                book = Book.objects.select_for_update().get(pk=form.cleaned_data["book"].pk)

                if not member.can_borrow:
                    form.add_error(
                        None,
                        (
                            f"Member {member.full_name} cannot borrow more books. "
                            f"They have reached their limit or have outstanding fines."
                        ),
                    )
                elif book.available_copies <= 0:
                    form.add_error("book", f"Book '{book.title}' is no longer available.")
                else:
                    issue = form.save(commit=False)
                    issue.member = member
                    issue.book = book
                    issue.issued_by = request.user
                    issue.save()

                    book.available_copies -= 1
                    book.save(update_fields=["available_copies"])

                    messages.success(request, f'Book "{book.title}" issued to {issue.member.full_name}.')
                    Notification.objects.create(
                        member=issue.member,
                        message=f'Book "{book.title}" has been issued to you. Due date: {issue.due_date.strftime("%d %b %Y")}.',
                        notification_type="info",
                    )
                    return redirect("issue_list")
    else:
        form = BookIssueForm()

    available_books = Book.objects.filter(available_copies__gt=0).values("id", "category_id")
    book_category_map = {book["id"]: book["category_id"] for book in available_books}
    return render(
        request,
        "library/issue_form.html",
        {
            "form": form,
            "title": "Issue Book",
            "categories": Category.objects.all(),
            "book_category_map": book_category_map,
        },
    )


@login_required
@admin_required
def return_book(request, pk):
    issue = get_object_or_404(BookIssue.objects.select_related("book", "member"), pk=pk)
    today = timezone.localdate()

    if issue.status == "returned":
        messages.info(request, f'Book "{issue.book.title}" was already returned.')
        return redirect("issue_list")

    if request.method == "POST":
        form = ReturnBookForm(request.POST, issue=issue)
        if form.is_valid():
            with transaction.atomic():
                locked_issue = (
                    BookIssue.objects.select_for_update()
                    .select_related("book", "member")
                    .get(pk=issue.pk)
                )
                if locked_issue.status == "returned":
                    messages.info(request, f'Book "{locked_issue.book.title}" was already returned.')
                    return redirect("issue_list")

                return_date = form.cleaned_data["return_date"]
                fine = locked_issue.calculate_fine(return_date)
                locked_issue.return_date = return_date
                locked_issue.status = "returned"
                locked_issue.fine_amount = fine
                locked_issue.fine_paid = form.cleaned_data["fine_paid"]
                locked_issue.remarks = form.cleaned_data.get("remarks", "")
                locked_issue.returned_to = request.user
                locked_issue.save()

                book = Book.objects.select_for_update().get(pk=locked_issue.book_id)
                book.available_copies = min(book.available_copies + 1, book.total_copies)
                book.save(update_fields=["available_copies"])

                messages.success(request, f'Book "{book.title}" returned successfully.')
                Notification.objects.create(
                    member=locked_issue.member,
                    message=f'Book "{book.title}" has been returned. Thank you!',
                    notification_type="info",
                )

                if fine > 0 and not locked_issue.fine_paid:
                    messages.warning(request, f"Pending fine: Rs. {fine}")
                return redirect("issue_list")
    else:
        form = ReturnBookForm(issue=issue, initial={"issue_id": issue.pk, "return_date": today})

    preview_return_date = today
    if getattr(form, "cleaned_data", None):
        preview_return_date = form.cleaned_data.get("return_date") or today
    fine = issue.calculate_fine(preview_return_date)

    return render(
        request,
        "library/return_book.html",
        {
            "form": form,
            "issue": issue,
            "fine": fine,
        },
    )


@login_required
def fine_list(request):
    today = timezone.localdate()
    is_admin = _is_admin_user(request.user)
    member = _get_request_member(request.user)

    fines = BookIssue.objects.select_related("member", "book")
    if not is_admin:
        if member is None:
            fines = BookIssue.objects.none()
        else:
            fines = fines.filter(member=member)

    fine_queryset = fines.filter(
        Q(fine_amount__gt=0)
        | (~Q(status__in=CLOSED_ISSUE_STATUSES) & Q(due_date__lt=today))
    )
    fine_list_items = sorted(fine_queryset, key=lambda issue: issue.current_fine, reverse=True)
    unpaid_total = sum((issue.current_fine for issue in fine_list_items if not issue.fine_paid), Decimal("0.00"))

    return render(
        request,
        "library/fine_list.html",
        {
            "fines": fine_list_items,
            "unpaid_total": unpaid_total,
            "is_admin": is_admin,
        },
    )


@require_POST
@login_required
@admin_required
def pay_fine(request, pk):
    issue = get_object_or_404(BookIssue, pk=pk)
    if issue.status != "returned":
        messages.error(request, "Fines can only be collected after a book has been returned.")
        return redirect("fine_list")
    issue.fine_amount = issue.current_fine
    issue.fine_paid = True
    issue.save(update_fields=["fine_amount", "fine_paid"])
    messages.success(request, f"Fine of Rs. {issue.fine_amount} marked as paid for {issue.member.full_name}.")
    return redirect("fine_list")


@login_required
@admin_required
def reports(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    issued_this_month = BookIssue.objects.filter(issue_date__gte=month_start).count()
    returned_this_month = BookIssue.objects.filter(return_date__gte=month_start).count()
    fines_collected = (
        BookIssue.objects.filter(fine_paid=True, return_date__gte=month_start).aggregate(total=Sum("fine_amount"))[
            "total"
        ]
        or 0
    )

    category_stats = Category.objects.annotate(
        book_count=Count("book", distinct=True),
        issue_count=Count("book__bookissue", distinct=True),
    )
    top_members = Member.objects.annotate(total_issues=Count("bookissue")).order_by("-total_issues")[:10]
    top_books = Book.objects.annotate(total_issues=Count("bookissue")).order_by("-total_issues")[:10]

    return render(
        request,
        "library/reports.html",
        {
            "issued_this_month": issued_this_month,
            "returned_this_month": returned_this_month,
            "fines_collected": fines_collected,
            "category_stats": category_stats,
            "top_members": top_members,
            "top_books": top_books,
            "seed_tools_enabled": settings.ENABLE_SEED_TOOLS,
        },
    )


@login_required
@admin_required
def export_books_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="books_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Title", "Author", "ISBN", "Category", "Publisher", "Year", "Total Copies", "Available", "Shelf"])

    for book in Book.objects.select_related("category").all():
        writer.writerow(
            [
                book.title,
                book.author,
                book.isbn,
                book.category.name if book.category else "",
                book.publisher,
                book.publication_year,
                book.total_copies,
                book.available_copies,
                book.shelf_location,
            ]
        )
    return response


@login_required
@admin_required
def export_members_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="members_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Member ID", "Name", "Email", "Phone", "Type", "Status", "Join Date"])

    for member in Member.objects.all():
        writer.writerow(
            [
                member.member_id,
                member.full_name,
                member.email,
                member.phone,
                member.membership_type,
                member.status,
                member.join_date,
            ]
        )
    return response


@login_required
def notifications(request):
    if request.user.is_staff or request.user.is_superuser:
        notifs = Notification.objects.select_related("member").order_by("-created_at")[:100]
    else:
        member = _get_request_member(request.user)
        if member is None:
            notifs = Notification.objects.none()
        else:
            notifs = Notification.objects.filter(member=member).order_by("-created_at")[:50]
    return render(request, "library/notifications.html", {"notifications": notifs})


@require_POST
@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    member = _get_request_member(request.user)
    if request.user.is_staff or request.user.is_superuser or (member and notif.member == member):
        notif.is_read = True
        notif.save(update_fields=["is_read"])
    else:
        messages.error(request, "Access denied.")
    return redirect("notifications")


@require_POST
@login_required
def mark_all_read(request):
    if request.user.is_staff or request.user.is_superuser:
        Notification.objects.filter(is_read=False).update(is_read=True)
    else:
        member = _get_request_member(request.user)
        if member is None:
            messages.info(request, "No member notifications found for this account.")
            return redirect("notifications")
        Notification.objects.filter(member=member, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications")


@login_required
def profile(request):
    return render(request, "library/profile.html")


@require_POST
@login_required
def change_password(request):
    old_pw = request.POST.get("old_password")
    new_pw1 = request.POST.get("new_password1")
    new_pw2 = request.POST.get("new_password2")

    if not request.user.check_password(old_pw):
        messages.error(request, "Current password is incorrect.")
    elif new_pw1 != new_pw2:
        messages.error(request, "New passwords do not match.")
    elif len(new_pw1) < 8:
        messages.error(request, "New password must be at least 8 characters.")
    else:
        request.user.set_password(new_pw1)
        request.user.save()
        from django.contrib.auth import update_session_auth_hash

        update_session_auth_hash(request, request.user)
        messages.success(request, "Password updated successfully.")
    return redirect("profile")


@login_required
@admin_required
def export_issues_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="issues_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Member", "Book", "Issue Date", "Due Date", "Return Date", "Status", "Fine"])

    for issue in BookIssue.objects.select_related("member", "book").all():
        writer.writerow(
            [
                issue.member.full_name,
                issue.book.title,
                issue.issue_date,
                issue.due_date,
                issue.return_date or "",
                issue.status,
                issue.fine_amount,
            ]
        )
    return response


@login_required
def category_list(request):
    categories = Category.objects.annotate(book_count=Count("book"))
    return render(request, "library/category_list.html", {"categories": categories})


@login_required
@admin_required
def category_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "library/category_form.html", {"form": form})


@login_required
@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "library/category_form.html", {"form": form, "category": category})


@require_POST
@login_required
@admin_required
def trigger_overdue_alerts(request):
    count = send_overdue_alerts()
    if count > 0:
        messages.success(request, f"Sent overdue alerts to {count} members.")
    else:
        messages.info(request, "No overdue books found to alert.")
    return redirect("reports")


@require_POST
@login_required
@admin_required
def seed_books_view(request):
    if not settings.ENABLE_SEED_TOOLS:
        messages.error(request, "Seed tools are disabled in this environment.")
        return redirect("reports")

    from .utils import seed_500_books

    count = seed_500_books()
    messages.success(request, f"Nexa Lib archives seeded with {count} high-quality books.")
    return redirect("reports")
