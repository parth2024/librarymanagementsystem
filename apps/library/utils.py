import logging

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import BookIssue, Notification, Member

logger = logging.getLogger("library")

def send_overdue_alerts():
    """
    Finds all overdue book issues and sends an alert email to the member.
    Also creates a Notification in the system.
    """
    today = timezone.localdate()
    overdue_issues = BookIssue.objects.filter(
        status__in=['issued', 'overdue'],
        due_date__lt=today
    ).select_related('member', 'book')
    
    count = 0
    for issue in overdue_issues:
        member = issue.member
        book = issue.book
        
        # Calculate current fine for the email
        fine = issue.calculate_fine()
        
        # 1. Draft the Email
        subject = f"⚠️ Overdue Library Book: {book.title}"
        message = f"""
Dear {member.full_name},

This is an automated reminder from Nexa Lib. The following book is currently overdue:

📖 Book: {book.title}
📅 Due Date: {issue.due_date}
💸 Current Fine: ₹{fine}

Please return the book as soon as possible to avoid further fines. If you have already returned it, please ignore this message.

Thank you,
Nexa Lib Team
        """
        
        notification_message = (
            f"Urgent: '{book.title}' was due on {issue.due_date}. Please return it immediately."
        )
        if not Notification.objects.filter(
            member=member,
            notification_type='overdue',
            message=notification_message,
        ).exists():
            Notification.objects.create(
                member=member,
                notification_type='overdue',
                message=notification_message,
            )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [member.email],
                fail_silently=False,
            )
            count += 1
        except Exception:
            logger.exception("Failed to send overdue alert email for member_id=%s issue_id=%s", member.pk, issue.pk)
            
    return count

def update_overdue_statuses():
    """
    Checks for all 'issued' books that have passed their due date,
    updates their status to 'overdue', and creates an in-app notification.
    """
    today = timezone.localdate()
    new_overdue = BookIssue.objects.filter(
        status='issued', 
        due_date__lt=today
    ).select_related('member', 'book')
    
    count = 0
    for issue in new_overdue:
        issue.status = 'overdue'
        issue.save(update_fields=['status'])
        
        notification_message = (
            f"Reminder: Book '{issue.book.title}' is now overdue. Please return it as soon as possible."
        )
        if not Notification.objects.filter(
            member=issue.member,
            notification_type='overdue',
            message=notification_message,
        ).exists():
            Notification.objects.create(
                member=issue.member,
                notification_type='overdue',
                message=notification_message,
            )
        count += 1
    return count

def seed_500_books():
    """
    Seeds the library with 500 books across CS, AI, Management, and Commerce.
    """
    import random
    from .models import Book, Category
    
    # 1. Define Categories
    categories_names = ["Computer Science", "Business Management", "Commerce", "AI"]
    categories = {}
    for name in categories_names:
        cat, _ = Category.objects.get_or_create(name=name)
        categories[name] = cat

    # 2. Define Patterns for Real-Sounding Titles
    cs_patterns = ["Algorithms in {v}", "Advanced {v}", "{v} for Professionals", "Mastering {v}", "The Future of {v}"]
    cs_topics = ["Python", "Java", "Web Development", "Cyber Security", "Database Systems", "Cloud Computing"]
    
    ai_patterns = ["Deep Learning and {v}", "The Ethics of {v}", "Neural Networks: {v}", "{v} in AI", "Practical {v}"]
    ai_topics = ["NLP", "Robotics", "Computer Vision", "Generative AI", "Statistical Modeling"]
    
    biz_patterns = ["Essentials of {v}", "Strategic {v}", "Modern {v}", "Leaders in {v}", "The {v} Playbook"]
    biz_topics = ["Leadership", "Operations", "Finance", "Strategy", "Global Marketing"]
    
    comm = ["Fundamentals of {v}", "International {v}", "Digital {v}", "{v} & Trade", "{v} Law Essentials"]
    c_topics = ["E-Commerce", "Economics", "Stock Markets", "Banking", "Accounting"]

    books_to_add = []
    authors = ["Robert Martin", "Andrew Ng", "Geoffrey Hinton", "Simon Sinek", "Adam Smith", "Michael Porter"]

    pattern_map = {
        "Computer Science": (cs_patterns, cs_topics),
        "AI": (ai_patterns, ai_topics),
        "Business Management": (biz_patterns, biz_topics),
        "Commerce": (comm, c_topics)
    }

    for cat_name, (patterns, topics) in pattern_map.items():
        cat = categories[cat_name]
        for i in range(1, 126):
            title = f"{random.choice(patterns).format(v=random.choice(topics))} (Vol. {i})"
            copies = random.randint(1, 25)
            books_to_add.append(Book(
                title=title, 
                author=random.choice(authors), 
                category=cat,
                isbn=f"978-{random.randint(100, 999)}-{random.randint(1000, 9999)}-{random.randint(0, 9)}",
                total_copies=copies,
                available_copies=copies, 
                shelf_location=f"Floor {random.randint(1, 4)}, Rack {random.choice(['A','B','C','D'])}{random.randint(1,20)}",
                publisher="Nexa Lib Press",
                publication_year=random.randint(2018, 2024)
            ))

    Book.objects.bulk_create(books_to_add, ignore_conflicts=True)
    return 500
