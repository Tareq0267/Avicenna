from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


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
