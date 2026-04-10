from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name_plural': 'Categories', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('author', models.CharField(max_length=200)),
                ('isbn', models.CharField(max_length=20, unique=True)),
                ('publisher', models.CharField(blank=True, max_length=200)),
                ('publication_year', models.IntegerField(blank=True, null=True)),
                ('total_copies', models.IntegerField(default=1)),
                ('available_copies', models.IntegerField(default=1)),
                ('shelf_location', models.CharField(blank=True, max_length=50)),
                ('description', models.TextField(blank=True)),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='book_covers/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='library.category')),
            ],
            options={'ordering': ['title']},
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_id', models.CharField(max_length=20, unique=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(unique=True)),
                ('phone', models.CharField(max_length=15)),
                ('address', models.TextField(blank=True)),
                ('membership_type', models.CharField(choices=[('student', 'Student'), ('faculty', 'Faculty'), ('staff', 'Staff'), ('external', 'External')], default='student', max_length=20)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended')], default='active', max_length=20)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('join_date', models.DateField(auto_now_add=True)),
                ('membership_expiry', models.DateField(blank=True, null=True)),
                ('max_books_allowed', models.IntegerField(default=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['first_name', 'last_name']},
        ),
        migrations.CreateModel(
            name='BookIssue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('issue_date', models.DateField(auto_now_add=True)),
                ('due_date', models.DateField()),
                ('return_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('issued', 'Issued'), ('returned', 'Returned'), ('overdue', 'Overdue'), ('lost', 'Lost')], default='issued', max_length=20)),
                ('fine_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=8)),
                ('fine_paid', models.BooleanField(default=False)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.book')),
                ('issued_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_books', to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.member')),
                ('returned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_books', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-issue_date']},
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('overdue', 'Overdue'), ('reminder', 'Due Soon'), ('info', 'Information')], default='info', max_length=20)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.member')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
