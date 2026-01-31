from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from .models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile, AIUsage

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile - appears on User edit page."""
    model = UserProfile
    can_delete = False
    verbose_name = 'Profile'
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = (
        'partner',
        'ai_enabled',
        ('fitness_goal', 'daily_calorie_goal'),
        ('age', 'gender'),
        ('height_cm', 'activity_level'),
        'calorie_profile_complete',
    )


class UserAdmin(BaseUserAdmin):
    """Extended User admin with profile inline."""
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


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


@admin.register(AIUsage)
class AIUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'request_type', 'success_badge', 'tokens_used')
    list_filter = ('request_type', 'success', 'timestamp')
    search_fields = ('user__username', 'error_message')
    readonly_fields = ('user', 'timestamp', 'request_type', 'success', 'error_message', 'tokens_used')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    def success_badge(self, obj):
        """Display success status with color badge."""
        if obj.success:
            return format_html(
                '<span style="background-color: #10b981; color: white; padding: 3px 8px; border-radius: 4px;">✓ Success</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 4px;">✗ Failed</span>'
            )
    success_badge.short_description = 'Status'

    def has_add_permission(self, request):
        """Prevent manual creation of usage records."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make records read-only."""
        return False
