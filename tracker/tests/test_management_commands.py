"""
Tests for tracker management commands.
"""
import pytest
from io import StringIO
from datetime import date
from decimal import Decimal
from django.core.management import call_command
from django.contrib.auth.models import User
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry


# ============================================================================
# clear_data Command Tests
# ============================================================================

class TestClearDataCommand:
    """Tests for the clear_data management command."""
    
    @pytest.fixture
    def populated_db(self, db):
        """Create sample data in all tables."""
        user = User.objects.create_user(username='testuser', password='test123')
        
        DietaryEntry.objects.create(user=user, date=date.today(), calories=500)
        DietaryEntry.objects.create(user=user, date=date.today(), calories=300)
        ExerciseEntry.objects.create(user=user, date=date.today(), activity='Run', duration_minutes=30)
        WeightEntry.objects.create(user=user, date=date.today(), weight_kg=Decimal('70.00'))
        
        return user
    
    def test_clear_data_with_force_flag(self, populated_db):
        """Test clear_data command with --force flag."""
        out = StringIO()
        
        # Verify data exists
        assert DietaryEntry.objects.count() == 2
        assert ExerciseEntry.objects.count() == 1
        assert WeightEntry.objects.count() == 1
        
        # Run command
        call_command('clear_data', '--force', stdout=out)
        
        # Verify all data cleared
        assert DietaryEntry.objects.count() == 0
        assert ExerciseEntry.objects.count() == 0
        assert WeightEntry.objects.count() == 0
        
        # Check output message
        output = out.getvalue()
        assert 'Deleted 2 dietary entries' in output
        assert '1 exercise entries' in output
        assert '1 weight entries' in output
    
    def test_clear_data_empty_database(self, db):
        """Test clear_data command on empty database."""
        out = StringIO()
        
        call_command('clear_data', '--force', stdout=out)
        
        output = out.getvalue()
        assert 'Deleted 0 dietary entries' in output
        assert '0 exercise entries' in output
        assert '0 weight entries' in output
    
    def test_clear_data_preserves_users(self, populated_db):
        """Test clear_data does not delete users."""
        out = StringIO()
        user_count_before = User.objects.count()
        
        call_command('clear_data', '--force', stdout=out)
        
        # Users should still exist
        assert User.objects.count() == user_count_before
    
    def test_clear_data_clears_only_tracker_data(self, populated_db):
        """Test clear_data only affects tracker models."""
        out = StringIO()
        
        # User should still exist after clear
        call_command('clear_data', '--force', stdout=out)
        
        assert User.objects.filter(username='testuser').exists()
