from django.contrib import admin
from .models import Book, Member, BookIssue, Category, Notification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'isbn', 'category', 'total_copies', 'available_copies']
    list_filter = ['category']
    search_fields = ['title', 'author', 'isbn']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_id', 'first_name', 'last_name', 'email', 'membership_type', 'status']
    list_filter = ['membership_type', 'status']
    search_fields = ['member_id', 'first_name', 'last_name', 'email']


@admin.register(BookIssue)
class BookIssueAdmin(admin.ModelAdmin):
    list_display = ['member', 'book', 'issue_date', 'due_date', 'return_date', 'status', 'fine_amount']
    list_filter = ['status', 'fine_paid']
    search_fields = ['member__first_name', 'member__last_name', 'book__title']
