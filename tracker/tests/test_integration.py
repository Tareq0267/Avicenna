"""
Integration tests for the tracker app - testing full workflows.
"""
import pytest
import json
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry


# ============================================================================
# Full Workflow Integration Tests
# ============================================================================

class TestImportToDisplayWorkflow:
    """Test complete workflow from import to display."""
    
    def test_import_data_appears_on_dashboard(self, client, db):
        """Test that imported data appears on dashboard."""
        # Import data
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [{"item": "Integration Test Meal", "calories": 999}],
            "exercise": [{"activity": "Integration Test Run", "duration_minutes": 42, "calories_burned": 333}]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        assert response.json()['success'] is True
        
        # Check dashboard
        response = client.get(reverse('tracker:dashboard'))
        content = response.content.decode('utf-8')
        
        # Data should be in recent entries
        assert 'Integration Test Meal' in content
        assert 'Integration Test Run' in content
    
    def test_add_weight_appears_on_dashboard(self, client, db):
        """Test that added weight appears on dashboard."""
        # Add weight
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': '88.88',
            'date': str(date.today()),
            'notes': 'Integration test weight'
        })
        assert response.json()['success'] is True
        
        # Check dashboard
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        assert context['latest_weight'] == 88.88
    
    def test_imported_data_in_daily_recap(self, client, db):
        """Test imported data appears in daily recap."""
        today = str(date.today())
        
        # Import data
        json_data = json.dumps([{
            "date": today,
            "dietary": [
                {"item": "Recap Test Food 1", "calories": 400},
                {"item": "Recap Test Food 2", "calories": 600}
            ],
            "exercise": [
                {"activity": "Recap Test Exercise", "duration_minutes": 45, "calories_burned": 400}
            ]
        }])
        
        client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        # Get daily recap
        response = client.get(reverse('tracker:daily_recap', args=[today]))
        data = response.json()
        
        assert data['success'] is True
        assert len(data['dietary']) == 2
        assert len(data['exercise']) == 1
        assert data['summary']['total_calories_in'] == 1000
        assert data['summary']['total_calories_burned'] == 400


class TestMultiDayTracking:
    """Test tracking over multiple days."""
    
    def test_week_of_tracking(self, client, db):
        """Test a full week of tracking data."""
        entries = []
        for i in range(7):
            day = date.today() - timedelta(days=i)
            entries.append({
                "date": str(day),
                "dietary": [{"item": f"Day {i} food", "calories": 500 + i*100}],
                "exercise": [{"activity": f"Day {i} exercise", "duration_minutes": 30 + i*5}]
            })
        
        json_data = json.dumps(entries)
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        assert response.json()['success'] is True
        assert '7 dietary entries' in response.json()['message']
        assert '7 exercise entries' in response.json()['message']
        
        # Verify counts
        assert DietaryEntry.objects.count() == 7
        assert ExerciseEntry.objects.count() == 7
    
    def test_heatmap_data_with_week_entries(self, client, db, user):
        """Test heatmap reflects entries over time."""
        # Create entries over a week
        for i in range(7):
            day = date.today() - timedelta(days=i)
            DietaryEntry.objects.create(user=user, date=day, calories=500)
            ExerciseEntry.objects.create(user=user, date=day, activity='Test', duration_minutes=30)
        
        response = client.get(reverse('tracker:dashboard'))
        heatmap_data = json.loads(response.context['heatmap_data'])
        
        # Should have entries for each day
        assert len(heatmap_data) >= 7


class TestDataIsolation:
    """Test that data is properly isolated."""
    
    def test_daily_recap_only_shows_requested_date(self, client, db, user):
        """Test daily recap only shows data for the requested date."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Create entries for today
        DietaryEntry.objects.create(user=user, date=today, item='Today food', calories=500)
        
        # Create entries for yesterday
        DietaryEntry.objects.create(user=user, date=yesterday, item='Yesterday food', calories=400)
        
        # Request today's recap
        response = client.get(reverse('tracker:daily_recap', args=[str(today)]))
        data = response.json()
        
        assert len(data['dietary']) == 1
        assert data['dietary'][0]['item'] == 'Today food'
    
    def test_multiple_users_data_isolation(self, client, db):
        """Test that different users' data is separate."""
        user1 = User.objects.create_user(username='user1', password='pass1')
        user2 = User.objects.create_user(username='user2', password='pass2')
        
        DietaryEntry.objects.create(user=user1, date=date.today(), item='User1 food', calories=500)
        DietaryEntry.objects.create(user=user2, date=date.today(), item='User2 food', calories=600)
        
        # Both entries exist
        assert DietaryEntry.objects.count() == 2
        
        # But each user only has their own
        assert user1.dietary_entries.count() == 1
        assert user2.dietary_entries.count() == 1
        assert user1.dietary_entries.first().item == 'User1 food'


# ============================================================================
# Edge Case Integration Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_large_import(self, client, db):
        """Test importing a large amount of data."""
        entries = []
        for i in range(50):
            entries.append({
                "date": str(date.today() - timedelta(days=i % 30)),
                "dietary": [{"item": f"Item {i}", "calories": 100}],
                "exercise": [{"activity": f"Activity {i}", "duration_minutes": 10}]
            })
        
        json_data = json.dumps(entries)
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        assert response.json()['success'] is True
        assert DietaryEntry.objects.count() == 50
    
    def test_same_date_multiple_entries(self, client, db):
        """Test multiple entries on the same date."""
        today = str(date.today())
        
        # Import multiple items for same day
        json_data = json.dumps([{
            "date": today,
            "dietary": [
                {"item": "Breakfast", "calories": 300},
                {"item": "Lunch", "calories": 500},
                {"item": "Dinner", "calories": 700},
                {"item": "Snack 1", "calories": 100},
                {"item": "Snack 2", "calories": 150}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        assert response.json()['success'] is True
        
        # Check daily recap totals
        response = client.get(reverse('tracker:daily_recap', args=[today]))
        data = response.json()
        
        assert len(data['dietary']) == 5
        assert data['summary']['total_calories_in'] == 1750
    
    def test_zero_calorie_entries(self, client, db):
        """Test entries with zero calories."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [{"item": "Water", "calories": 0}],
            "exercise": [{"activity": "Stretching", "duration_minutes": 10, "calories_burned": 0}]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        assert response.json()['success'] is True
        
        entry = DietaryEntry.objects.get(item='Water')
        assert entry.calories == 0
    
    def test_high_calorie_day(self, client, db):
        """Test handling of high calorie values."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [
                {"item": "Feast", "calories": 5000},
                {"item": "Dessert", "calories": 2000}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        assert response.json()['success'] is True
        
        response = client.get(reverse('tracker:daily_recap', args=[str(date.today())]))
        data = response.json()
        
        assert data['summary']['total_calories_in'] == 7000
    
    def test_weight_with_many_decimal_places(self, client, db):
        """Test weight entry rounds to correct precision."""
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': '75.555',  # More decimals than model allows
            'date': str(date.today())
        })
        
        # Should succeed (decimal truncation)
        entry = WeightEntry.objects.latest('id')
        # Model has decimal_places=2, so should be 75.56 (rounded)
        assert entry.weight_kg == Decimal('75.56') or entry.weight_kg == Decimal('75.55')


# ============================================================================
# Clear Data Integration Tests
# ============================================================================

class TestClearDataIntegration:
    """Integration tests for clear_data command."""
    
    def test_clear_data_then_import_fresh(self, client, db):
        """Test clearing data then importing fresh."""
        from django.core.management import call_command
        from io import StringIO
        
        # First, create some data
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [{"item": "Old food", "calories": 500}]
        }])
        client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        assert DietaryEntry.objects.count() == 1
        
        # Clear all data
        call_command('clear_data', '--force', stdout=StringIO())
        
        assert DietaryEntry.objects.count() == 0
        
        # Import fresh data
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [{"item": "New food", "calories": 600}]
        }])
        client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        assert DietaryEntry.objects.count() == 1
        assert DietaryEntry.objects.first().item == 'New food'
