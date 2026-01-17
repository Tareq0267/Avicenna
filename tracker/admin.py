from django.contrib import admin
from .models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'partner', 'get_partner_status')
    list_filter = ('partner',)
    search_fields = ('user__username', 'partner__username')
    raw_id_fields = ['partner']

    def get_partner_status(self, obj):
        if obj.partner:
            return f"Linked with {obj.partner.username}"
        return "No partner"
    get_partner_status.short_description = 'Status'


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
