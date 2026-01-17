"""
Tests for Avicenna Tracker admin configuration.
"""
import pytest
from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite

from tracker.admin import (
    UserAdmin, UserProfileInline,
    DietaryEntryAdmin, ExerciseEntryAdmin, WeightEntryAdmin
)
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile

User = get_user_model()


class TestUserProfileInline:
    """Tests for UserProfile inline admin."""

    def test_user_edit_page_accessible(self, admin_client, user):
        """Admin should be able to access user edit page."""
        url = reverse('admin:auth_user_change', args=[user.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_user_edit_shows_profile_section(self, admin_client, user):
        """User edit page should show Profile section."""
        url = reverse('admin:auth_user_change', args=[user.pk])
        response = admin_client.get(url)

        content = response.content.decode()
        assert 'Profile' in content

    def test_user_edit_shows_partner_field(self, admin_client, user, user2):
        """User edit page should show partner field."""
        url = reverse('admin:auth_user_change', args=[user.pk])
        response = admin_client.get(url)

        content = response.content.decode()
        assert 'partner' in content.lower()

    def test_can_set_partner_via_admin(self, admin_client, user, user2):
        """Admin should be able to set partner via user edit page."""
        url = reverse('admin:auth_user_change', args=[user.pk])

        # Get the current form data
        response = admin_client.get(url)
        assert response.status_code == 200

        # Post with partner set
        data = {
            'username': user.username,
            'date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': user.date_joined.strftime('%H:%M:%S'),
            'profile-TOTAL_FORMS': '1',
            'profile-INITIAL_FORMS': '1',
            'profile-MIN_NUM_FORMS': '0',
            'profile-MAX_NUM_FORMS': '1',
            'profile-0-id': user.profile.pk,
            'profile-0-user': user.pk,
            'profile-0-partner': user2.pk,
        }

        response = admin_client.post(url, data)

        # Refresh and check
        user.profile.refresh_from_db()
        assert user.profile.partner == user2


class TestDietaryEntryAdmin:
    """Tests for DietaryEntry admin."""

    def test_dietary_entry_list_accessible(self, admin_client):
        """Dietary entry list should be accessible."""
        url = reverse('admin:tracker_dietaryentry_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_dietary_entry_add_accessible(self, admin_client):
        """Dietary entry add form should be accessible."""
        url = reverse('admin:tracker_dietaryentry_add')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_dietary_entry_list_displays_correct_columns(self, admin_client, dietary_entry):
        """Dietary entry list should display configured columns."""
        url = reverse('admin:tracker_dietaryentry_changelist')
        response = admin_client.get(url)

        content = response.content.decode()
        assert dietary_entry.item in content
        assert str(dietary_entry.calories) in content

    def test_dietary_entry_can_filter_by_date(self, admin_client, dietary_entries):
        """Dietary entry list should support date filtering."""
        url = reverse('admin:tracker_dietaryentry_changelist')
        today = date.today().strftime('%Y-%m-%d')
        response = admin_client.get(f'{url}?date__gte={today}')

        assert response.status_code == 200

    def test_dietary_entry_can_filter_by_user(self, admin_client, dietary_entries):
        """Dietary entry list should support user filtering."""
        user = dietary_entries[0].user
        url = reverse('admin:tracker_dietaryentry_changelist')
        response = admin_client.get(f'{url}?user__id__exact={user.pk}')

        assert response.status_code == 200

    def test_dietary_entry_searchable(self, admin_client, dietary_entry):
        """Dietary entry should be searchable by item."""
        url = reverse('admin:tracker_dietaryentry_changelist')
        response = admin_client.get(f'{url}?q=Test')

        assert response.status_code == 200
        content = response.content.decode()
        assert 'Test Food' in content


class TestExerciseEntryAdmin:
    """Tests for ExerciseEntry admin."""

    def test_exercise_entry_list_accessible(self, admin_client):
        """Exercise entry list should be accessible."""
        url = reverse('admin:tracker_exerciseentry_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_exercise_entry_add_accessible(self, admin_client):
        """Exercise entry add form should be accessible."""
        url = reverse('admin:tracker_exerciseentry_add')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_exercise_entry_list_displays_correct_columns(self, admin_client, exercise_entry):
        """Exercise entry list should display configured columns."""
        url = reverse('admin:tracker_exerciseentry_changelist')
        response = admin_client.get(url)

        content = response.content.decode()
        assert exercise_entry.activity in content
        assert str(exercise_entry.duration_minutes) in content

    def test_exercise_entry_searchable(self, admin_client, exercise_entry):
        """Exercise entry should be searchable by activity."""
        url = reverse('admin:tracker_exerciseentry_changelist')
        response = admin_client.get(f'{url}?q=Running')

        assert response.status_code == 200
        content = response.content.decode()
        assert 'Running' in content


class TestWeightEntryAdmin:
    """Tests for WeightEntry admin."""

    def test_weight_entry_list_accessible(self, admin_client):
        """Weight entry list should be accessible."""
        url = reverse('admin:tracker_weightentry_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_weight_entry_add_accessible(self, admin_client):
        """Weight entry add form should be accessible."""
        url = reverse('admin:tracker_weightentry_add')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_weight_entry_list_displays_correct_columns(self, admin_client, weight_entry):
        """Weight entry list should display configured columns."""
        url = reverse('admin:tracker_weightentry_changelist')
        response = admin_client.get(url)

        content = response.content.decode()
        assert '70.5' in content

    def test_weight_entry_can_filter_by_date(self, admin_client, weight_entries):
        """Weight entry list should support date filtering."""
        url = reverse('admin:tracker_weightentry_changelist')
        today = date.today().strftime('%Y-%m-%d')
        response = admin_client.get(f'{url}?date__gte={today}')

        assert response.status_code == 200


class TestAdminPermissions:
    """Tests for admin permission controls."""

    def test_non_admin_cannot_access_admin(self, client, user):
        """Non-admin users should not access admin."""
        client.login(username='testuser', password='testpass123')
        url = reverse('admin:index')
        response = client.get(url)

        # Should redirect to admin login
        assert response.status_code == 302

    def test_admin_can_access_admin(self, admin_client):
        """Admin users should access admin."""
        url = reverse('admin:index')
        response = admin_client.get(url)

        assert response.status_code == 200

    def test_admin_sees_tracker_models(self, admin_client):
        """Admin index should show tracker models."""
        url = reverse('admin:index')
        response = admin_client.get(url)

        content = response.content.decode()
        assert 'Dietary entry' in content or 'Dietary entrys' in content
        assert 'Exercise entry' in content or 'Exercise entrys' in content
        assert 'Weight entry' in content or 'Weight entrys' in content


class TestAdminCRUD:
    """Tests for admin CRUD operations."""

    def test_create_dietary_entry_via_admin(self, admin_client, user):
        """Admin should be able to create dietary entry."""
        url = reverse('admin:tracker_dietaryentry_add')
        data = {
            'user': user.pk,
            'date': date.today().strftime('%Y-%m-%d'),
            'item': 'Admin Created Food',
            'calories': 600,
            'notes': 'Created via admin',
            'remarks': 'Test remarks',
        }
        response = admin_client.post(url, data)

        # Should redirect on success
        assert response.status_code == 302

        # Verify entry was created
        entry = DietaryEntry.objects.filter(item='Admin Created Food').first()
        assert entry is not None
        assert entry.calories == 600

    def test_create_exercise_entry_via_admin(self, admin_client, user):
        """Admin should be able to create exercise entry."""
        url = reverse('admin:tracker_exerciseentry_add')
        data = {
            'user': user.pk,
            'date': date.today().strftime('%Y-%m-%d'),
            'activity': 'Admin Created Exercise',
            'duration_minutes': 45,
            'calories_burned': 350,
            'remarks': 'Test remarks',
        }
        response = admin_client.post(url, data)

        assert response.status_code == 302

        entry = ExerciseEntry.objects.filter(activity='Admin Created Exercise').first()
        assert entry is not None
        assert entry.duration_minutes == 45

    def test_create_weight_entry_via_admin(self, admin_client, user):
        """Admin should be able to create weight entry."""
        url = reverse('admin:tracker_weightentry_add')
        data = {
            'user': user.pk,
            'date': date.today().strftime('%Y-%m-%d'),
            'weight_kg': '68.5',
            'notes': 'Created via admin',
        }
        response = admin_client.post(url, data)

        assert response.status_code == 302

        entry = WeightEntry.objects.filter(weight_kg=Decimal('68.5')).first()
        assert entry is not None

    def test_delete_dietary_entry_via_admin(self, admin_client, dietary_entry):
        """Admin should be able to delete dietary entry."""
        url = reverse('admin:tracker_dietaryentry_delete', args=[dietary_entry.pk])
        response = admin_client.post(url, {'post': 'yes'})

        assert response.status_code == 302
        assert not DietaryEntry.objects.filter(pk=dietary_entry.pk).exists()

    def test_edit_dietary_entry_via_admin(self, admin_client, dietary_entry):
        """Admin should be able to edit dietary entry."""
        url = reverse('admin:tracker_dietaryentry_change', args=[dietary_entry.pk])
        data = {
            'user': dietary_entry.user.pk,
            'date': dietary_entry.date.strftime('%Y-%m-%d'),
            'item': 'Updated Food Name',
            'calories': 999,
            'notes': dietary_entry.notes,
            'remarks': dietary_entry.remarks,
        }
        response = admin_client.post(url, data)

        assert response.status_code == 302

        dietary_entry.refresh_from_db()
        assert dietary_entry.item == 'Updated Food Name'
        assert dietary_entry.calories == 999
