"""
Tests for tracker admin configuration.
"""
import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry
from tracker.admin import DietaryEntryAdmin, ExerciseEntryAdmin, WeightEntryAdmin


# ============================================================================
# Admin Registration Tests
# ============================================================================

class TestAdminRegistration:
    """Tests for model admin registration."""

    @pytest.fixture(autouse=True)
    def login(self, admin_user, client):
        client.login(username='admin', password='admin123')
        self.client = client

    def test_dietary_entry_registered(self):
        assert DietaryEntry in admin.site._registry

    def test_exercise_entry_registered(self):
        assert ExerciseEntry in admin.site._registry

    def test_weight_entry_registered(self):
        assert WeightEntry in admin.site._registry


# ============================================================================
# DietaryEntry Admin Tests
# ============================================================================

class TestDietaryEntryAdmin:
    """Tests for DietaryEntryAdmin configuration."""
    
    @pytest.fixture
    def admin_instance(self):
        """Create admin instance."""
        site = AdminSite()
        return DietaryEntryAdmin(DietaryEntry, site)
    
    def test_list_display(self, admin_instance):
        """Test list_display configuration."""
        assert admin_instance.list_display == ('user', 'date', 'item', 'calories', 'notes')
    
    def test_list_filter(self, admin_instance):
        """Test list_filter configuration."""
        assert admin_instance.list_filter == ('date', 'user')
    
    def test_search_fields(self, admin_instance):
        """Test search_fields configuration."""
        assert admin_instance.search_fields == ('item', 'notes', 'remarks')


# ============================================================================
# ExerciseEntry Admin Tests
# ============================================================================

class TestExerciseEntryAdmin:
    """Tests for ExerciseEntryAdmin configuration."""
    
    @pytest.fixture
    def admin_instance(self):
        """Create admin instance."""
        site = AdminSite()
        return ExerciseEntryAdmin(ExerciseEntry, site)
    
    def test_list_display(self, admin_instance):
        """Test list_display configuration."""
        assert admin_instance.list_display == ('user', 'date', 'activity', 'duration_minutes', 'calories_burned')
    
    def test_list_filter(self, admin_instance):
        """Test list_filter configuration."""
        assert admin_instance.list_filter == ('date', 'user')
    
    def test_search_fields(self, admin_instance):
        """Test search_fields configuration."""
        assert admin_instance.search_fields == ('activity', 'remarks')


# ============================================================================
# WeightEntry Admin Tests
# ============================================================================

class TestWeightEntryAdmin:
    """Tests for WeightEntryAdmin configuration."""
    
    @pytest.fixture
    def admin_instance(self):
        """Create admin instance."""
        site = AdminSite()
        return WeightEntryAdmin(WeightEntry, site)
    
    def test_list_display(self, admin_instance):
        """Test list_display configuration."""
        assert admin_instance.list_display == ('user', 'date', 'weight_kg')
    
    def test_list_filter(self, admin_instance):
        """Test list_filter configuration."""
        assert admin_instance.list_filter == ('date', 'user')
