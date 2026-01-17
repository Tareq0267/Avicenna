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
