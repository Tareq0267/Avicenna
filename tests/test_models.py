"""
Tests for Avicenna Tracker models.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError

from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile

User = get_user_model()


class TestUserProfile:
    """Tests for UserProfile model."""

    def test_profile_created_on_user_creation(self, db):
        """Profile should be auto-created when user is created."""
        user = User.objects.create_user(
            username='newuser',
            password='password123'
        )
        assert hasattr(user, 'profile')
        assert isinstance(user.profile, UserProfile)

    def test_profile_str_without_partner(self, user):
        """String representation without partner."""
        assert 'testuser' in str(user.profile)
        assert 'No partner' in str(user.profile)

    def test_profile_str_with_partner(self, linked_partners):
        """String representation with partner."""
        user, partner = linked_partners
        profile_str = str(user.profile)
        assert 'testuser' in profile_str
        assert 'partner' in profile_str

    def test_partner_linking(self, user, user2):
        """Test partner can be linked."""
        user.profile.partner = user2
        user.profile.save()

        user.profile.refresh_from_db()
        assert user.profile.partner == user2

    def test_partner_unlinking(self, linked_partners):
        """Test partner can be unlinked."""
        user, partner = linked_partners
        user.profile.partner = None
        user.profile.save()

        user.profile.refresh_from_db()
        assert user.profile.partner is None

    def test_get_partner_profile(self, linked_partners):
        """Test get_partner_profile method."""
        user, partner = linked_partners
        partner_profile = user.profile.get_partner_profile()
        assert partner_profile == partner.profile

    def test_get_partner_profile_no_partner(self, user):
        """Test get_partner_profile with no partner."""
        result = user.profile.get_partner_profile()
        assert result is None

    def test_partner_deletion_sets_null(self, linked_partners):
        """When partner is deleted, profile.partner should be set to NULL."""
        user, partner = linked_partners
        partner_id = partner.id
        partner.delete()

        user.profile.refresh_from_db()
        assert user.profile.partner is None


class TestDietaryEntry:
    """Tests for DietaryEntry model."""

    def test_create_dietary_entry(self, user):
        """Test creating a dietary entry."""
        entry = DietaryEntry.objects.create(
            user=user,
            date=date.today(),
            item='Pizza',
            calories=800,
            notes='Lunch',
            remarks='Cheat day'
        )
        assert entry.pk is not None
        assert entry.item == 'Pizza'
        assert entry.calories == 800

    def test_dietary_entry_str(self, dietary_entry):
        """Test string representation."""
        assert 'Test Food' in str(dietary_entry)
        assert '500' in str(dietary_entry)

    def test_dietary_entry_user_cascade_delete(self, dietary_entry):
        """Entries should be deleted when user is deleted."""
        user = dietary_entry.user
        entry_id = dietary_entry.id
        user.delete()

        assert not DietaryEntry.objects.filter(id=entry_id).exists()

    def test_dietary_entry_blank_fields(self, user):
        """Test that item and notes can be blank."""
        entry = DietaryEntry.objects.create(
            user=user,
            date=date.today(),
            item='',
            calories=100,
            notes='',
            remarks=''
        )
        assert entry.pk is not None
        assert entry.item == ''

    def test_dietary_entry_ordering(self, dietary_entries):
        """Test that entries can be ordered by date."""
        entries = DietaryEntry.objects.filter(
            user=dietary_entries[0].user
        ).order_by('-date')

        # Most recent first
        assert entries[0].date >= entries[1].date


class TestExerciseEntry:
    """Tests for ExerciseEntry model."""

    def test_create_exercise_entry(self, user):
        """Test creating an exercise entry."""
        entry = ExerciseEntry.objects.create(
            user=user,
            date=date.today(),
            activity='Swimming',
            duration_minutes=45,
            calories_burned=400,
            remarks='Great workout'
        )
        assert entry.pk is not None
        assert entry.activity == 'Swimming'
        assert entry.duration_minutes == 45

    def test_exercise_entry_str(self, exercise_entry):
        """Test string representation."""
        assert 'Running' in str(exercise_entry)

    def test_exercise_entry_nullable_calories(self, user):
        """Test that calories_burned can be null."""
        entry = ExerciseEntry.objects.create(
            user=user,
            date=date.today(),
            activity='Walking',
            duration_minutes=30,
            calories_burned=None,
            remarks=''
        )
        assert entry.pk is not None
        assert entry.calories_burned is None

    def test_exercise_entry_user_cascade_delete(self, exercise_entry):
        """Entries should be deleted when user is deleted."""
        user = exercise_entry.user
        entry_id = exercise_entry.id
        user.delete()

        assert not ExerciseEntry.objects.filter(id=entry_id).exists()


class TestWeightEntry:
    """Tests for WeightEntry model."""

    def test_create_weight_entry(self, user):
        """Test creating a weight entry."""
        entry = WeightEntry.objects.create(
            user=user,
            date=date.today(),
            weight_kg=Decimal('75.5'),
            notes='After breakfast'
        )
        assert entry.pk is not None
        assert entry.weight_kg == Decimal('75.5')

    def test_weight_entry_str(self, weight_entry):
        """Test string representation."""
        assert '70.5' in str(weight_entry)

    def test_weight_entry_decimal_precision(self, user):
        """Test decimal precision for weight."""
        entry = WeightEntry.objects.create(
            user=user,
            date=date.today(),
            weight_kg=Decimal('65.75'),
            notes=''
        )
        assert entry.weight_kg == Decimal('65.75')

    def test_weight_entry_user_cascade_delete(self, weight_entry):
        """Entries should be deleted when user is deleted."""
        user = weight_entry.user
        entry_id = weight_entry.id
        user.delete()

        assert not WeightEntry.objects.filter(id=entry_id).exists()

    def test_weight_trend(self, weight_entries):
        """Test that weight entries can track a trend."""
        user = weight_entries[0].user
        entries = WeightEntry.objects.filter(user=user).order_by('date')

        weights = [e.weight_kg for e in entries]
        # Verify we have multiple entries with different weights
        assert len(set(weights)) > 1


class TestModelRelationships:
    """Tests for relationships between models."""

    def test_user_dietary_entries_related_name(self, dietary_entries):
        """Test user.dietary_entries related name."""
        user = dietary_entries[0].user
        assert user.dietary_entries.count() == len(dietary_entries)

    def test_user_exercise_entries_related_name(self, exercise_entries):
        """Test user.exercise_entries related name."""
        user = exercise_entries[0].user
        assert user.exercise_entries.count() == len(exercise_entries)

    def test_user_weight_entries_related_name(self, weight_entries):
        """Test user.weight_entries related name."""
        user = weight_entries[0].user
        assert user.weight_entries.count() == len(weight_entries)

    def test_multiple_entries_same_day(self, user):
        """Test multiple entries can exist for same day."""
        today = date.today()

        DietaryEntry.objects.create(user=user, date=today, item='Breakfast', calories=400)
        DietaryEntry.objects.create(user=user, date=today, item='Lunch', calories=600)
        DietaryEntry.objects.create(user=user, date=today, item='Dinner', calories=700)

        assert DietaryEntry.objects.filter(user=user, date=today).count() == 3

    def test_entries_isolated_between_users(self, user, user2):
        """Test that entries are isolated between users."""
        today = date.today()

        DietaryEntry.objects.create(user=user, date=today, item='User1 Food', calories=500)
        DietaryEntry.objects.create(user=user2, date=today, item='User2 Food', calories=600)

        user1_entries = DietaryEntry.objects.filter(user=user)
        user2_entries = DietaryEntry.objects.filter(user=user2)

        assert user1_entries.count() == 1
        assert user2_entries.count() == 1
        assert user1_entries.first().item == 'User1 Food'
        assert user2_entries.first().item == 'User2 Food'
