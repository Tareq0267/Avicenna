from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class UserProfile(models.Model):
    """Extended user profile for couples mode and other settings."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    partner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='partner_of',
        help_text="Link to partner's account for couples mode"
    )
    ai_enabled = models.BooleanField(
        default=False,
        help_text="Allow this user to access AI food logging features"
    )

    def __str__(self):
        partner_name = self.partner.username if self.partner else "No partner"
        return f"{self.user.username}'s profile (Partner: {partner_name})"

    def get_partner_profile(self):
        """Get partner's profile if linked."""
        if self.partner:
            try:
                return self.partner.profile
            except UserProfile.DoesNotExist:
                return None
        return None


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile when User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Auto-save UserProfile when User is saved."""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

class DietaryEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dietary_entries')
    date = models.DateField()
    item = models.CharField(max_length=200, blank=True, default='')  # food item name
    calories = models.IntegerField()
    notes = models.TextField(blank=True)  # per-item note (e.g. "vomited roughly half")
    remarks = models.TextField(blank=True)  # daily remarks

    def __str__(self):
        return f"Dietary {self.user} {self.date} - {self.item} ({self.calories} kcal)"

class ExerciseEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_entries')
    date = models.DateField()
    activity = models.CharField(max_length=100)
    duration_minutes = models.IntegerField()
    calories_burned = models.IntegerField(blank=True, null=True)
    remarks = models.TextField(blank=True)  # daily remarks

    def __str__(self):
        return f"Exercise {self.activity} for {self.user} on {self.date}"

class WeightEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_entries')
    date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Weight {self.weight_kg} kg on {self.date} ({self.user})"


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
