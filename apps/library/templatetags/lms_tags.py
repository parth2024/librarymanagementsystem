from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def rupees(value):
    """Format a number as Indian rupees: ₹1,23,456.00"""
    try:
        value = float(value)
        if value == int(value):
            return f"₹{int(value):,}"
        return f"₹{value:,.2f}"
    except (TypeError, ValueError):
        return "₹0"


@register.filter
def days_since(date_value):
    """Return number of days since a given date."""
    if not date_value:
        return 0
    today = timezone.localdate()
    delta = today - date_value
    return delta.days


@register.filter
def days_until(date_value):
    """Return number of days until a given date (negative if past)."""
    if not date_value:
        return 0
    today = timezone.localdate()
    delta = date_value - today
    return delta.days


@register.filter
def overdue_class(issue):
    """Return a CSS class string based on issue overdue status."""
    if issue.status == 'returned':
        return 'badge-green'
    if issue.days_overdue > 14:
        return 'badge-red'
    if issue.days_overdue > 0:
        return 'badge-amber'
    return 'badge-gold'


@register.filter
def percentage(value, total):
    """Return value as a percentage of total, rounded to 1 decimal."""
    try:
        if int(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0


@register.simple_tag
def active_if(request, url_name):
    """Return 'active' if the current URL matches url_name."""
    if request.resolver_match and request.resolver_match.url_name == url_name:
        return 'active'
    return ''


@register.inclusion_tag('library/partials/stat_card.html')
def stat_card(label, value, sub, color, icon):
    return {'label': label, 'value': value, 'sub': sub, 'color': color, 'icon': icon}
