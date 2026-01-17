from django.conf import settings


def for_her(request):
    """Make FOR_HER setting available in all templates."""
    return {
        'FOR_HER': getattr(settings, 'FOR_HER', False)
    }
