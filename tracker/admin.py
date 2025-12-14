from django.contrib import admin
from .models import DietaryEntry, ExerciseEntry, WeightEntry

@admin.register(DietaryEntry)
class DietaryEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'item', 'calories', 'notes')
    list_filter = ('date', 'user')
    search_fields = ('item', 'notes', 'remarks')

@admin.register(ExerciseEntry)
class ExerciseEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'activity', 'duration_minutes', 'calories_burned')
    list_filter = ('date', 'user')
    search_fields = ('activity', 'remarks')

@admin.register(WeightEntry)
class WeightEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight_kg')
    list_filter = ('date', 'user')
