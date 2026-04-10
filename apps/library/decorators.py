from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    """
    Decorator for views that checks if the user is staff or superuser.
    If not, it redirects to the dashboard with an error message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Permission Denied: You do not have administrative privileges to perform this action.")
            return redirect('dashboard')
    return _wrapped_view
