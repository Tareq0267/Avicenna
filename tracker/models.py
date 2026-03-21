from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


# Fitness Goal Choices
GOAL_CHOICES = [
    ('lose', 'Lose Weight'),
    ('gain', 'Gain Weight'),
    ('maintain', 'Maintain Weight'),
]

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
]

ACTIVITY_CHOICES = [
    ('sedentary', 'Sedentary (little or no exercise)'),
    ('light', 'Lightly Active (1-3 days/week)'),
    ('moderate', 'Moderately Active (3-5 days/week)'),
    ('active', 'Very Active (6-7 days/week)'),
    ('extra', 'Extra Active (very active + physical job)'),
]


class UserProfile(models.Model):
    """Extended user profile for couples mode, AI settings, and fitness goals."""
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

    # Fitness Profile Fields
    fitness_goal = models.CharField(
        max_length=10,
        choices=GOAL_CHOICES,
        null=True,
        blank=True,
        help_text="Weight management goal"
    )
    age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="User's age in years"
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True
    )
    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Height in centimeters"
    )
    activity_level = models.CharField(
        max_length=20,
        choices=ACTIVITY_CHOICES,
        null=True,
        blank=True,
        help_text="Daily activity level"
    )
    daily_calorie_goal = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calculated daily calorie target"
    )
    calorie_profile_complete = models.BooleanField(
        default=False,
        help_text="Whether user has completed calorie goal setup"
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

    def is_calorie_profile_ready(self):
        """Check if all required fields for calorie calculation are set."""
        return all([
            self.fitness_goal,
            self.age,
            self.gender,
            self.height_cm,
            self.activity_level,
        ])


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
    remarks = models.TextField(blank=True)  # AI coach feedback / meal context

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


class Routine(models.Model):
    """A recurring habit or task the user wants to track."""
    SCHEDULE_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routines')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    schedule_type = models.CharField(max_length=10, choices=SCHEDULE_TYPE_CHOICES, default='daily')
    # Flexible scheduling via JSON:
    # daily: {"time": "05:30"}
    # weekly: {"days": [0,2,4], "time": "07:00"}  (0=Mon, 6=Sun)
    # monthly: {"dates": [1, 15], "time": "09:00"}
    schedule_config = models.JSONField(default=dict, blank=True)
    preset_key = models.CharField(max_length=50, blank=True, help_text="Key of the preset this was created from")
    points_value = models.PositiveIntegerField(default=10)
    icon = models.CharField(max_length=50, default='bi-check-circle', help_text="Bootstrap icon class")
    color = models.CharField(max_length=20, default='#6366f1', help_text="Hex color for display")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def is_scheduled_for(self, date):
        """Check if this routine is due on the given date."""
        if not self.is_active:
            return False
        if self.schedule_type == 'daily':
            return True
        elif self.schedule_type == 'weekly':
            days = self.schedule_config.get('days', [])
            return date.weekday() in days if days else True
        elif self.schedule_type == 'monthly':
            dates = self.schedule_config.get('dates', [])
            return date.day in dates if dates else True
        return False

    def get_scheduled_time(self):
        """Return the scheduled time string, or None."""
        return self.schedule_config.get('time')


class CompletionRecord(models.Model):
    """Records each time a routine is completed."""
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name='completions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routine_completions')
    date = models.DateField()
    completed_at = models.DateTimeField(auto_now_add=True)
    points_earned = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['routine', 'date']
        ordering = ['-completed_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['routine', 'date']),
        ]

    def __str__(self):
        return f"{self.routine.name} completed by {self.user.username} on {self.date}"


class UserPoints(models.Model):
    """Cached gamification data per user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points')
    total_points = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_completion_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}: {self.total_points} pts, {self.current_streak} streak"

    def record_completion(self, points, date):
        """Add points and update streak on completion."""
        self.total_points += points
        if self.last_completion_date is None:
            self.current_streak = 1
        elif self.last_completion_date == date:
            pass  # same day, no streak change
        elif (date - self.last_completion_date).days == 1:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_completion_date = date
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        self.save()

    def record_undo(self, points, date):
        """Remove points when a completion is undone."""
        self.total_points = max(0, self.total_points - points)
        # Recalculate streak if undoing today's last completion
        if self.last_completion_date == date:
            remaining = CompletionRecord.objects.filter(user=self.user, date=date).exists()
            if not remaining:
                self._recalculate_streak()
        self.save()

    def _recalculate_streak(self):
        """Walk backwards through completion dates to find current streak."""
        from datetime import timedelta
        dates = (
            CompletionRecord.objects.filter(user=self.user)
            .values_list('date', flat=True)
            .distinct()
            .order_by('-date')
        )
        streak = 0
        expected = None
        for d in dates:
            if expected is None:
                expected = d
            if d == expected:
                streak += 1
                expected = d - timedelta(days=1)
            else:
                break
        self.current_streak = streak
        self.last_completion_date = dates[0] if dates else None
