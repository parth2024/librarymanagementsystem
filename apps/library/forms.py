from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Book, Member, BookIssue, Category


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username',
        'autofocus': True,
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password',
    }))


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'category', 'publisher',
                  'publication_year', 'total_copies', 'available_copies',
                  'shelf_location', 'description', 'cover_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1800, 'max': 2100}),
            'total_copies': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'available_copies': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'shelf_location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        total_copies = cleaned_data.get('total_copies')
        available_copies = cleaned_data.get('available_copies')

        if total_copies is not None and total_copies < 1:
            self.add_error('total_copies', 'Total copies must be at least 1.')
        if available_copies is not None and available_copies < 0:
            self.add_error('available_copies', 'Available copies cannot be negative.')
        if (
            total_copies is not None
            and available_copies is not None
            and available_copies > total_copies
        ):
            self.add_error('available_copies', 'Available copies cannot exceed total copies.')
        return cleaned_data

    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        if not image:
            return image

        allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        content_type = getattr(image, 'content_type', '').lower()
        if content_type and content_type not in allowed_types:
            raise forms.ValidationError('Cover image must be a JPG, PNG, WEBP, or GIF file.')

        max_size = 5 * 1024 * 1024
        if image.size > max_size:
            raise forms.ValidationError('Cover image must be 5 MB or smaller.')
        return image


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['member_id', 'first_name', 'last_name', 'email', 'phone',
                  'address', 'membership_type', 'status', 'date_of_birth',
                  'membership_expiry', 'max_books_allowed']
        widgets = {
            'member_id': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'membership_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'membership_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_books_allowed': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        }


class BookIssueForm(forms.ModelForm):
    class Meta:
        model = BookIssue
        fields = ['member', 'book', 'due_date', 'remarks']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'book': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active members
        self.fields['member'].queryset = Member.objects.filter(status='active')
        # Only show available books
        self.fields['book'].queryset = Book.objects.filter(available_copies__gt=0)
        # Set default due date to 14 days from now
        self.fields['due_date'].initial = (
            timezone.now() + timedelta(days=getattr(settings, 'DEFAULT_LOAN_DAYS', 14))
        ).strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('member')
        book = cleaned_data.get('book')
        due_date = cleaned_data.get('due_date')
        today = timezone.localdate()

        if member and not member.can_borrow:
            raise forms.ValidationError(
                f"Member {member.full_name} cannot borrow more books. "
                f"They have reached their limit or have outstanding fines."
            )
        if book and not book.is_available:
            raise forms.ValidationError(f"Book '{book.title}' is not available.")
        if due_date and due_date < today:
            self.add_error('due_date', 'Due date cannot be in the past.')
        return cleaned_data


class ReturnBookForm(forms.Form):
    issue_id = forms.IntegerField(widget=forms.HiddenInput())
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        initial=timezone.now().date
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    fine_paid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, issue=None, **kwargs):
        self.issue = issue
        super().__init__(*args, **kwargs)

    def clean_return_date(self):
        return_date = self.cleaned_data['return_date']
        today = timezone.localdate()

        if return_date > today:
            raise forms.ValidationError('Return date cannot be in the future.')
        if self.issue and return_date < self.issue.issue_date:
            raise forms.ValidationError('Return date cannot be earlier than the issue date.')
        return return_date

    def clean(self):
        cleaned_data = super().clean()
        issue_id = cleaned_data.get('issue_id')

        if self.issue and issue_id != self.issue.pk:
            raise forms.ValidationError('Invalid return request.')
        return cleaned_data


class BookSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title, author, ISBN...'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    available_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class RegisterForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['first_name', 'last_name', 'email', 'phone']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
