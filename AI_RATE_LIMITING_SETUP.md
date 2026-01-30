# AI Rate Limiting Setup Guide

## Overview
This guide will help you set up rate limiting for your AI food logging feature to protect your OpenAI API costs.

## What Was Implemented

### 1. **AIUsage Model**
- Tracks every AI API call per user
- Records: timestamp, request type (text/image), success status, error messages, tokens used
- Provides methods to query usage counts (hourly, daily, monthly)

### 2. **Rate Limiting System**
- **Hourly Limit**: 10 requests per hour (default)
- **Daily Limit**: 30 requests per day (default)
- **Monthly Limit**: 200 requests per month (default)

### 3. **User-Facing Features**
- Quota display on AI food log page showing remaining requests
- Color-coded warnings (yellow at 70%, red at 90%)
- Clear error messages when limits are exceeded

### 4. **Admin Interface**
- View all API usage in Django admin
- Filter by user, request type, success/failure
- Read-only records (cannot be manually created or edited)

---

## Setup Instructions

### Step 1: Create Database Migration

Run the following commands to create the new AIUsage table:

```bash
python manage.py makemigrations tracker
python manage.py migrate
```

### Step 2: Configure Rate Limits (Optional)

You can customize the rate limits by adding these settings to your `settings.py`:

```python
# AI Food Logging Rate Limits
AI_HOURLY_LIMIT = 10    # Requests per hour per user
AI_DAILY_LIMIT = 30     # Requests per day per user
AI_MONTHLY_LIMIT = 200  # Requests per month per user
```

**Cost Estimation Example:**
- GPT-4o with vision: ~$0.01-0.05 per request (varies by image size)
- 200 requests/month = $2-10/month per user
- Adjust limits based on your budget!

### Step 3: Test the System

1. **Test Rate Limiting:**
   - Log in as a regular user
   - Go to the AI Food Log page
   - Try to make 11 requests within an hour
   - You should see the rate limit error on the 11th request

2. **Check Quota Display:**
   - The page should show "9/10" for today after first request
   - Numbers should update after each request

3. **Test Admin Interface:**
   - Go to Django admin (`/admin/`)
   - Navigate to "Tracker > AI Usages"
   - You should see all your test requests logged

### Step 4: Monitor Usage

#### Via Django Admin:
1. Go to `/admin/tracker/aiusage/`
2. Filter by user, date, or success status
3. Export to CSV if needed

#### Via Database Query (for reporting):
```python
from tracker.models import AIUsage
from django.contrib.auth.models import User

# Get total usage for all users this month
this_month_total = AIUsage.get_monthly_count_all()

# Get top users by usage
from django.db.models import Count
top_users = AIUsage.objects.values('user__username').annotate(
    total=Count('id')
).order_by('-total')[:10]
```

---

## Adjusting Limits

### Increase Limits for Specific Users

If you want to give some users higher limits (e.g., premium users), you can:

1. **Option A: Modify `rate_limit.py`** to check user groups:
```python
def get_rate_limits(user=None):
    """Get rate limits from settings, with premium user support."""
    if user and user.groups.filter(name='Premium').exists():
        return {
            'hourly': 50,
            'daily': 150,
            'monthly': 1000,
        }
    # Default limits for regular users
    return {
        'hourly': getattr(settings, 'AI_HOURLY_LIMIT', 10),
        'daily': getattr(settings, 'AI_DAILY_LIMIT', 30),
        'monthly': getattr(settings, 'AI_MONTHLY_LIMIT', 200),
    }
```

2. **Option B: Add a field to UserProfile**:
```python
# In models.py
class UserProfile(models.Model):
    ...
    ai_daily_limit = models.IntegerField(default=30)
    ai_monthly_limit = models.IntegerField(default=200)
```

### Temporarily Disable Limits

To temporarily disable rate limiting (e.g., during testing):

```python
# In settings.py
AI_HOURLY_LIMIT = 9999
AI_DAILY_LIMIT = 9999
AI_MONTHLY_LIMIT = 9999
```

---

## Cost Monitoring

### Estimate Costs

```python
# In Django shell
from tracker.models import AIUsage
from datetime import datetime

# This month's usage
month_usage = AIUsage.objects.filter(
    timestamp__year=datetime.now().year,
    timestamp__month=datetime.now().month,
    success=True
).count()

# Image vs Text requests
image_count = AIUsage.objects.filter(
    timestamp__month=datetime.now().month,
    request_type='image',
    success=True
).count()

text_count = AIUsage.objects.filter(
    timestamp__month=datetime.now().month,
    request_type='text',
    success=True
).count()

# Rough cost estimate (adjust based on actual OpenAI pricing)
estimated_cost = (text_count * 0.01) + (image_count * 0.03)
print(f"Estimated cost: ${estimated_cost:.2f}")
```

### Set Up Alerts

Consider setting up alerts when usage exceeds thresholds:

```python
# Example: Send email when monthly usage > 80%
from django.core.mail import send_mail
from django.conf import settings

def check_and_alert_high_usage():
    total = AIUsage.get_monthly_count_all()
    limit = settings.AI_MONTHLY_LIMIT * User.objects.count()

    if total > (limit * 0.8):
        send_mail(
            'AI Usage Alert',
            f'Usage is at {total}/{limit} ({total/limit*100:.1f}%)',
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
        )
```

---

## Troubleshooting

### Issue: Rate limit not working
- Check that you ran migrations: `python manage.py migrate`
- Verify the view imports are correct
- Check for any errors in browser console

### Issue: Quota not displaying
- Ensure the URL pattern is registered: `path('ai/quota/', ...)`
- Check browser console for JavaScript errors
- Verify CSRF token is present

### Issue: Users hitting limits too quickly
- Review and adjust limits in settings
- Check for any automated/bot usage
- Consider implementing CAPTCHA for suspicious activity

---

## Security Recommendations

1. **Monitor for Abuse**: Regularly check the admin panel for unusual patterns
2. **IP-Based Limiting**: Consider adding IP-based rate limiting for additional protection
3. **CAPTCHA**: Add CAPTCHA for users who fail requests repeatedly
4. **API Key Rotation**: Rotate your OpenAI API key periodically

---

## Files Modified

1. `tracker/models.py` - Added AIUsage model
2. `tracker/rate_limit.py` - New file with rate limiting logic
3. `tracker/views.py` - Updated AI endpoints with rate limiting
4. `tracker/admin.py` - Added AIUsage admin interface
5. `tracker/urls.py` - Added quota status endpoint
6. `templates/tracker/ai_food_log.html` - Added quota display UI

---

## Next Steps

1. ✅ Run migrations
2. ✅ Test rate limiting
3. ✅ Configure limits in settings
4. ✅ Monitor usage for the first week
5. ✅ Adjust limits based on actual usage patterns
6. ✅ Set up cost alerts if needed

---

## Support

If you encounter any issues, check:
- Django logs for errors
- Browser console for JavaScript errors
- Database to verify AIUsage records are being created

For questions, review the code comments in `rate_limit.py` and `views.py`.
