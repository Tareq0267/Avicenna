from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile - appears on User edit page."""
    model = UserProfile
    can_delete = False
    verbose_name = 'Profile'
    verbose_name_plural = 'Profile'
    fk_name = 'user'


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
