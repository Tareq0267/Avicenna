"""
Rate limiting utilities for AI food logging features.
Protects against API abuse and controls costs.
"""
from functools import wraps
from django.http import JsonResponse
from django.conf import settings
from .models import AIUsage


# Configurable limits - adjust these based on your budget
DEFAULT_HOURLY_LIMIT = 10  # 10 requests per hour per user
DEFAULT_DAILY_LIMIT = 30   # 30 requests per day per user
DEFAULT_MONTHLY_LIMIT = 200  # 200 requests per month per user


def get_rate_limits():
    """Get rate limits from settings or use defaults."""
    return {
        'hourly': getattr(settings, 'AI_HOURLY_LIMIT', DEFAULT_HOURLY_LIMIT),
        'daily': getattr(settings, 'AI_DAILY_LIMIT', DEFAULT_DAILY_LIMIT),
        'monthly': getattr(settings, 'AI_MONTHLY_LIMIT', DEFAULT_MONTHLY_LIMIT),
    }


def is_special_user(user):
    """Check if user is in the 'special' group (unlimited AI access)."""
    return user.groups.filter(name='special').exists()


def check_rate_limit(user):
    """
    Check if user has exceeded rate limits.
    Special users (in 'special' group) have unlimited access.

    Returns:
        tuple: (allowed: bool, error_message: str or None, remaining: dict)
    """
    # Special users have unlimited access
    if is_special_user(user):
        return True, None, {
            'hourly_remaining': 999999,
            'daily_remaining': 999999,
            'monthly_remaining': 999999,
            'unlimited': True,
        }

    limits = get_rate_limits()

    # Check hourly limit
    hourly_count = AIUsage.get_usage_count(user, hours=1)
    if hourly_count >= limits['hourly']:
        return False, f"Rate limit exceeded: {limits['hourly']} requests per hour. Please try again later.", {
            'hourly_remaining': 0,
            'daily_remaining': max(0, limits['daily'] - AIUsage.get_daily_count(user)),
            'monthly_remaining': max(0, limits['monthly'] - AIUsage.get_monthly_count(user)),
        }

    # Check daily limit
    daily_count = AIUsage.get_daily_count(user)
    if daily_count >= limits['daily']:
        return False, f"Daily limit exceeded: {limits['daily']} requests per day. Reset at midnight.", {
            'hourly_remaining': max(0, limits['hourly'] - hourly_count),
            'daily_remaining': 0,
            'monthly_remaining': max(0, limits['monthly'] - AIUsage.get_monthly_count(user)),
        }

    # Check monthly limit
    monthly_count = AIUsage.get_monthly_count(user)
    if monthly_count >= limits['monthly']:
        return False, f"Monthly limit exceeded: {limits['monthly']} requests per month. Reset next month.", {
            'hourly_remaining': max(0, limits['hourly'] - hourly_count),
            'daily_remaining': max(0, limits['daily'] - daily_count),
            'monthly_remaining': 0,
        }

    # All checks passed
    remaining = {
        'hourly_remaining': max(0, limits['hourly'] - hourly_count),
        'daily_remaining': max(0, limits['daily'] - daily_count),
        'monthly_remaining': max(0, limits['monthly'] - monthly_count),
    }

    return True, None, remaining


def ai_rate_limit(view_func):
    """
    Decorator to enforce rate limits on AI endpoints.
    Must be used with @login_required.

    Usage:
        @login_required
        @ai_rate_limit
        @require_POST
        def my_ai_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check rate limit
        allowed, error_msg, remaining = check_rate_limit(request.user)

        if not allowed:
            return JsonResponse({
                'success': False,
                'error': error_msg,
                'rate_limit': True,
                'remaining': remaining
            }, status=429)

        # Add remaining quota to request for view to use
        request.ai_quota_remaining = remaining

        return view_func(request, *args, **kwargs)

    return wrapper


def log_ai_usage(user, request_type, success=True, error_message='', tokens_used=0):
    """
    Log AI API usage for tracking and analytics.

    Args:
        user: Django User instance
        request_type: 'text' or 'image'
        success: Whether the request succeeded
        error_message: Error message if failed
        tokens_used: Number of tokens consumed (if available)
    """
    AIUsage.objects.create(
        user=user,
        request_type=request_type,
        success=success,
        error_message=error_message,
        tokens_used=tokens_used
    )


def get_user_quota_info(user):
    """
    Get user's current quota information.
    Special users get unlimited access with a cute reminder.

    Returns:
        dict with usage counts and remaining quota
    """
    # Special users have unlimited access
    if is_special_user(user):
        hourly_count = AIUsage.get_usage_count(user, hours=1)
        daily_count = AIUsage.get_daily_count(user)
        monthly_count = AIUsage.get_monthly_count(user)
        return {
            'unlimited': True,
            'special_message': "You have unlimited AI access, sayang! But remember not to overuse it okay~ ",
            'limits': {'hourly': '∞', 'daily': '∞', 'monthly': '∞'},
            'usage': {
                'hourly': hourly_count,
                'daily': daily_count,
                'monthly': monthly_count,
            },
            'remaining': {
                'hourly': '∞',
                'daily': '∞',
                'monthly': '∞',
            },
            'percentage_used': {
                'daily': 0,
                'monthly': 0,
            }
        }

    limits = get_rate_limits()

    hourly_count = AIUsage.get_usage_count(user, hours=1)
    daily_count = AIUsage.get_daily_count(user)
    monthly_count = AIUsage.get_monthly_count(user)

    return {
        'unlimited': False,
        'limits': limits,
        'usage': {
            'hourly': hourly_count,
            'daily': daily_count,
            'monthly': monthly_count,
        },
        'remaining': {
            'hourly': max(0, limits['hourly'] - hourly_count),
            'daily': max(0, limits['daily'] - daily_count),
            'monthly': max(0, limits['monthly'] - monthly_count),
        },
        'percentage_used': {
            'daily': round((daily_count / limits['daily']) * 100, 1) if limits['daily'] > 0 else 0,
            'monthly': round((monthly_count / limits['monthly']) * 100, 1) if limits['monthly'] > 0 else 0,
        }
    }
