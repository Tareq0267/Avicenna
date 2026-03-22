from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AIUsage(models.Model):
    """Track AI API usage per user for rate limiting and cost monitoring."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_usage')
    timestamp = models.DateTimeField(auto_now_add=True)
    request_type = models.CharField(max_length=20, choices=[
        ('text', 'Text Analysis'),
        ('image', 'Image Analysis')
    ])
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    tokens_used = models.IntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['user', 'request_type', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.request_type} at {self.timestamp}"

    @classmethod
    def get_usage_count(cls, user, hours=24):
        """Get usage count for a user in the last N hours."""
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(user=user, timestamp__gte=cutoff).count()

    @classmethod
    def get_daily_count(cls, user):
        """Get usage count for today."""
        from django.utils import timezone
        today = timezone.now().date()
        return cls.objects.filter(user=user, timestamp__date=today).count()

    @classmethod
    def get_monthly_count(cls, user):
        """Get usage count for current month."""
        from django.utils import timezone
        now = timezone.now()
        return cls.objects.filter(
            user=user,
            timestamp__year=now.year,
            timestamp__month=now.month
        ).count()
