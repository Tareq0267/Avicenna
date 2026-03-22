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

TIER_CHOICES = [
    ('free', 'Free'),
    ('plus', 'Plus'),
    ('pro', 'Pro'),
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
        help_text="(Deprecated) Use subscription_tier instead"
    )

    # Subscription Tier
    subscription_tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default='free',
        help_text="Current subscription tier"
    )
    tier_override = models.BooleanField(
        default=False,
        help_text="Admin manually granted this tier (bypasses payment)"
    )
    tier_override_note = models.TextField(
        blank=True,
        help_text="Admin note for why tier was overridden"
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

    def has_ai_access(self):
        """Check if user's tier grants AI access (Plus or Pro)."""
        return self.subscription_tier in ('plus', 'pro')

    def has_image_ai(self):
        """Check if user's tier grants image AI (Pro only)."""
        return self.subscription_tier == 'pro'

    def show_ads(self):
        """Free tier users see ads."""
        return self.subscription_tier == 'free'

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
