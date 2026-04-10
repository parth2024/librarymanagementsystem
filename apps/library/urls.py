from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Books
    path('books/', views.book_list, name='book_list'),
    path('books/add/', views.book_add, name='book_add'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),
    path('books/<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('books/<int:pk>/delete/', views.book_delete, name='book_delete'),

    # Members
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.member_add, name='member_add'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),

    # Issues
    path('issues/', views.issue_list, name='issue_list'),
    path('issues/new/', views.issue_book, name='issue_book'),
    path('issues/<int:pk>/return/', views.return_book, name='return_book'),

    # Fines
    path('fines/', views.fine_list, name='fine_list'),
    path('fines/<int:pk>/pay/', views.pay_fine, name='pay_fine'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_read, name='mark_read'),
    path('notifications/read-all/', views.mark_all_read, name='mark_all_read'),

    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),

    # Reports & Alerts
    path('reports/', views.reports, name='reports'),
    path('reports/export/books/', views.export_books_csv, name='export_books'),
    path('reports/export/members/', views.export_members_csv, name='export_members'),
    path('reports/export/issues/', views.export_issues_csv, name='export_issues'),
    path('reports/trigger-alerts/', views.trigger_overdue_alerts, name='trigger_alerts'),
    path('reports/seed-data/', views.seed_books_view, name='seed_data'),
]
