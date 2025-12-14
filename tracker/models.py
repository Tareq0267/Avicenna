from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

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
