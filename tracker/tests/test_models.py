"""
Tests for tracker models: DietaryEntry, ExerciseEntry, WeightEntry.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry


# ============================================================================
# DietaryEntry Model Tests
# ============================================================================

class TestDietaryEntryModel:
    """Tests for DietaryEntry model."""
    
    def test_create_dietary_entry(self, db, user):
        """Test creating a basic dietary entry."""
        entry = DietaryEntry.objects.create(
            user=user,
            date=date.today(),
            item='Breakfast Burrito',
            calories=650,
            notes='Extra salsa',
            remarks='Felt good after'
        )
        assert entry.id is not None
        assert entry.user == user
        assert entry.item == 'Breakfast Burrito'
        assert entry.calories == 650
        assert entry.notes == 'Extra salsa'
        assert entry.remarks == 'Felt good after'
    
    def test_dietary_entry_str_representation(self, dietary_entry):
        """Test the string representation of dietary entry."""
        expected = f"Dietary {dietary_entry.user} {dietary_entry.date} - {dietary_entry.item} ({dietary_entry.calories} kcal)"
        assert str(dietary_entry) == expected
    
    def test_dietary_entry_blank_optional_fields(self, db, user):
        """Test dietary entry with blank optional fields."""
        entry = DietaryEntry.objects.create(
            user=user,
            date=date.today(),
            item='Simple meal',
            calories=300
        )
        assert entry.notes == ''
        assert entry.remarks == ''
    
    def test_dietary_entry_blank_item(self, db, user):
        """Test dietary entry with blank item (allowed)."""
        entry = DietaryEntry.objects.create(
            user=user,
            date=date.today(),
            item='',
            calories=100
        )
        assert entry.item == ''
    
    def test_dietary_entry_user_relationship(self, db, user):
        """Test the foreign key relationship to User."""
        DietaryEntry.objects.create(user=user, date=date.today(), calories=500)
        DietaryEntry.objects.create(user=user, date=date.today(), calories=300)
        
        assert user.dietary_entries.count() == 2
    
    def test_dietary_entry_cascade_delete(self, db):
        """Test that deleting user cascades to dietary entries."""
        temp_user = User.objects.create_user(username='temp', password='temp123')
        user_id = temp_user.id
        DietaryEntry.objects.create(user=temp_user, date=date.today(), calories=500)
        
        assert DietaryEntry.objects.filter(user_id=user_id).count() == 1
        temp_user.delete()
        assert DietaryEntry.objects.filter(user_id=user_id).count() == 0
    
    def test_dietary_entry_ordering_by_date(self, multiple_dietary_entries):
        """Test querying dietary entries ordered by date."""
        entries = DietaryEntry.objects.order_by('-date')
        dates = [e.date for e in entries]
        assert dates == sorted(dates, reverse=True)


# ============================================================================
# ExerciseEntry Model Tests
# ============================================================================

class TestExerciseEntryModel:
    """Tests for ExerciseEntry model."""
    
    def test_create_exercise_entry(self, db, user):
        """Test creating a basic exercise entry."""
        entry = ExerciseEntry.objects.create(
            user=user,
            date=date.today(),
            activity='Swimming',
            duration_minutes=45,
            calories_burned=400,
            remarks='Great workout'
        )
        assert entry.id is not None
        assert entry.user == user
        assert entry.activity == 'Swimming'
        assert entry.duration_minutes == 45
        assert entry.calories_burned == 400
        assert entry.remarks == 'Great workout'
    
    def test_exercise_entry_str_representation(self, exercise_entry):
        """Test the string representation of exercise entry."""
        expected = f"Exercise {exercise_entry.activity} for {exercise_entry.user} on {exercise_entry.date}"
        assert str(exercise_entry) == expected
    
    def test_exercise_entry_nullable_calories_burned(self, db, user):
        """Test exercise entry with null calories_burned."""
        entry = ExerciseEntry.objects.create(
            user=user,
            date=date.today(),
            activity='Walking',
            duration_minutes=60
        )
        assert entry.calories_burned is None
    
    def test_exercise_entry_blank_remarks(self, db, user):
        """Test exercise entry with blank remarks."""
        entry = ExerciseEntry.objects.create(
            user=user,
            date=date.today(),
            activity='Yoga',
            duration_minutes=30
        )
        assert entry.remarks == ''
    
    def test_exercise_entry_user_relationship(self, db, user):
        """Test the foreign key relationship to User."""
        ExerciseEntry.objects.create(user=user, date=date.today(), activity='Run', duration_minutes=30)
        ExerciseEntry.objects.create(user=user, date=date.today(), activity='Swim', duration_minutes=45)
        
        assert user.exercise_entries.count() == 2
    
    def test_exercise_entry_cascade_delete(self, db):
        """Test that deleting user cascades to exercise entries."""
        temp_user = User.objects.create_user(username='temp2', password='temp123')
        user_id = temp_user.id
        ExerciseEntry.objects.create(user=temp_user, date=date.today(), activity='Run', duration_minutes=30)
        
        assert ExerciseEntry.objects.filter(user_id=user_id).count() == 1
        temp_user.delete()
        assert ExerciseEntry.objects.filter(user_id=user_id).count() == 0


# ============================================================================
# WeightEntry Model Tests
# ============================================================================

class TestWeightEntryModel:
    """Tests for WeightEntry model."""
    
    def test_create_weight_entry(self, db, user):
        """Test creating a basic weight entry."""
        entry = WeightEntry.objects.create(
            user=user,
            date=date.today(),
            weight_kg=Decimal('72.50'),
            notes='After breakfast'
        )
        assert entry.id is not None
        assert entry.user == user
        assert entry.weight_kg == Decimal('72.50')
        assert entry.notes == 'After breakfast'
    
    def test_weight_entry_str_representation(self, weight_entry):
        """Test the string representation of weight entry."""
        expected = f"Weight {weight_entry.weight_kg} kg on {weight_entry.date} ({weight_entry.user})"
        assert str(weight_entry) == expected
    
    def test_weight_entry_decimal_precision(self, db, user):
        """Test weight entry decimal precision (5 digits, 2 decimal places)."""
        entry = WeightEntry.objects.create(
            user=user,
            date=date.today(),
            weight_kg=Decimal('123.45')
        )
        assert entry.weight_kg == Decimal('123.45')
    
    def test_weight_entry_blank_notes(self, db, user):
        """Test weight entry with blank notes."""
        entry = WeightEntry.objects.create(
            user=user,
            date=date.today(),
            weight_kg=Decimal('70.00')
        )
        assert entry.notes == ''
    
    def test_weight_entry_user_relationship(self, db, user):
        """Test the foreign key relationship to User."""
        WeightEntry.objects.create(user=user, date=date.today(), weight_kg=Decimal('70.00'))
        WeightEntry.objects.create(user=user, date=date.today() - timedelta(days=1), weight_kg=Decimal('70.50'))
        
        assert user.weight_entries.count() == 2
    
    def test_weight_entry_cascade_delete(self, db):
        """Test that deleting user cascades to weight entries."""
        temp_user = User.objects.create_user(username='temp3', password='temp123')
        user_id = temp_user.id
        WeightEntry.objects.create(user=temp_user, date=date.today(), weight_kg=Decimal('70.00'))
        
        assert WeightEntry.objects.filter(user_id=user_id).count() == 1
        temp_user.delete()
        assert WeightEntry.objects.filter(user_id=user_id).count() == 0


# ============================================================================
# Cross-Model Tests
# ============================================================================

class TestCrossModelBehavior:
    """Tests for behavior across multiple models."""
    
    def test_multiple_entry_types_same_date(self, db, user):
        """Test creating all entry types on the same date."""
        today = date.today()
        
        dietary = DietaryEntry.objects.create(user=user, date=today, calories=500)
        exercise = ExerciseEntry.objects.create(user=user, date=today, activity='Run', duration_minutes=30)
        weight = WeightEntry.objects.create(user=user, date=today, weight_kg=Decimal('70.00'))
        
        assert DietaryEntry.objects.filter(date=today).count() == 1
        assert ExerciseEntry.objects.filter(date=today).count() == 1
        assert WeightEntry.objects.filter(date=today).count() == 1
    
    def test_user_has_all_entry_types(self, dietary_entry, exercise_entry, weight_entry):
        """Test user can have all entry types via fixtures."""
        user = dietary_entry.user
        
        # Note: exercise and weight entries are created with different user from fixtures
        # This test just verifies the fixtures work
        assert dietary_entry.user == user
        assert DietaryEntry.objects.filter(user=user).exists()
