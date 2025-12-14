"""
Tests for tracker views: dashboard, import_json, add_weight, daily_recap.
"""
import pytest
import json
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry


# ============================================================================
# Dashboard View Tests
# ============================================================================

class TestDashboardView:
    """Tests for the dashboard view."""
    
    def test_dashboard_loads_successfully(self, client, db):
        """Test dashboard view returns 200."""
        response = client.get(reverse('tracker:dashboard'))
        assert response.status_code == 200
    
    def test_dashboard_root_url_loads(self, client, db):
        """Test dashboard is accessible via root tracker URL."""
        response = client.get('/tracker/')
        assert response.status_code == 200
    
    def test_dashboard_uses_correct_template(self, client, db):
        """Test dashboard uses the correct template."""
        response = client.get(reverse('tracker:dashboard'))
        assert 'tracker/dashboard.html' in [t.name for t in response.templates]
    
    def test_dashboard_context_keys(self, client, db):
        """Test dashboard context contains all expected keys."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        expected_keys = [
            'dietary_recent', 'exercise_recent', 'weight_recent',
            'dietary_count', 'exercise_count', 'weight_count',
            'cal_dates', 'cal_values', 'ex_dates', 'ex_values',
            'wt_dates', 'wt_values', 'heatmap_data',
            'heatmap_start', 'heatmap_end', 'today',
            'total_calories', 'total_exercise_min', 'latest_weight'
        ]
        for key in expected_keys:
            assert key in context
    
    def test_dashboard_with_no_data(self, client, db):
        """Test dashboard handles empty database gracefully."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        assert context['dietary_count'] == 0
        assert context['exercise_count'] == 0
        assert context['weight_count'] == 0
        assert context['total_calories'] == 0
        assert context['total_exercise_min'] == 0
        assert context['latest_weight'] is None
    
    def test_dashboard_with_dietary_data(self, client, multiple_dietary_entries):
        """Test dashboard displays dietary entries."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        assert context['dietary_count'] == 7
        assert context['total_calories'] > 0
    
    def test_dashboard_with_exercise_data(self, client, multiple_exercise_entries):
        """Test dashboard displays exercise entries."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        assert context['exercise_count'] == 7
        assert context['total_exercise_min'] > 0
    
    def test_dashboard_with_weight_data(self, client, multiple_weight_entries):
        """Test dashboard displays weight entries."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        assert context['weight_count'] == 10
        assert context['latest_weight'] is not None
    
    def test_dashboard_chart_data_is_json(self, client, multiple_dietary_entries):
        """Test chart data is properly JSON encoded."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        # These should be JSON strings
        cal_dates = json.loads(context['cal_dates'])
        cal_values = json.loads(context['cal_values'])
        
        assert isinstance(cal_dates, list)
        assert isinstance(cal_values, list)
    
    def test_dashboard_heatmap_data_format(self, client, dietary_entry, exercise_entry):
        """Test heatmap data is in correct format."""
        response = client.get(reverse('tracker:dashboard'))
        context = response.context
        
        heatmap_data = json.loads(context['heatmap_data'])
        assert isinstance(heatmap_data, list)
        # Each item should be [date_string, count]
        if heatmap_data:
            assert len(heatmap_data[0]) == 2
    
    def test_dashboard_recent_entries_limit(self, client, db, user):
        """Test dashboard limits recent entries."""
        # Create more than the limit
        for i in range(30):
            DietaryEntry.objects.create(
                user=user,
                date=date.today(),
                calories=100
            )
        
        response = client.get(reverse('tracker:dashboard'))
        # Dashboard limits to 25 dietary entries
        assert response.context['dietary_count'] == 25


# ============================================================================
# Import JSON View Tests
# ============================================================================

class TestImportJsonView:
    """Tests for the import_json view."""
    
    def test_import_json_get_not_allowed(self, client, db):
        """Test GET request returns 405."""
        response = client.get(reverse('tracker:import_json'))
        assert response.status_code == 405
    
    def test_import_json_empty_data(self, client, db):
        """Test import with empty data returns error."""
        response = client.post(reverse('tracker:import_json'), {'json_data': ''})
        data = response.json()
        
        assert data['success'] is False
        assert 'No JSON data provided' in data['error']
    
    def test_import_json_invalid_json(self, client, db):
        """Test import with invalid JSON returns error."""
        response = client.post(reverse('tracker:import_json'), {'json_data': 'not valid json'})
        data = response.json()
        
        assert data['success'] is False
        assert 'Invalid JSON' in data['error']
    
    def test_import_json_valid_dietary(self, client, db, admin_user):
        """Test importing valid dietary entries."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [
                {"item": "Salad", "calories": 200, "notes": "Fresh"}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        data = response.json()
        
        assert data['success'] is True
        assert '1 dietary entries' in data['message']
        assert DietaryEntry.objects.filter(item='Salad').exists()
    
    def test_import_json_valid_exercise(self, client, db, admin_user):
        """Test importing valid exercise entries."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "exercise": [
                {"activity": "Running", "duration_minutes": 30, "calories_burned": 300}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        data = response.json()
        
        assert data['success'] is True
        assert '1 exercise entries' in data['message']
        assert ExerciseEntry.objects.filter(activity='Running').exists()
    
    def test_import_json_food_key_alias(self, client, db, admin_user):
        """Test import supports 'food' as alias for 'dietary'."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "food": [
                {"item": "Pizza", "calories": 800}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        data = response.json()
        
        assert data['success'] is True
        assert DietaryEntry.objects.filter(item='Pizza').exists()
    
    def test_import_json_note_key_alias(self, client, db, admin_user):
        """Test import supports 'note' as alias for 'notes'."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [
                {"item": "Soup", "calories": 150, "note": "Chicken noodle"}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        entry = DietaryEntry.objects.get(item='Soup')
        assert entry.notes == 'Chicken noodle'
    
    def test_import_json_duration_min_alias(self, client, db, admin_user):
        """Test import supports 'duration_min' as alias for 'duration_minutes'."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "exercise": [
                {"activity": "Yoga", "duration_min": 60, "calories_burned": 200}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        entry = ExerciseEntry.objects.get(activity='Yoga')
        assert entry.duration_minutes == 60
    
    def test_import_json_day_remarks_propagation(self, client, db, admin_user):
        """Test day-level remarks propagate to entries without their own."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "remarks": "Great day",
            "dietary": [
                {"item": "Apple", "calories": 80}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        entry = DietaryEntry.objects.get(item='Apple')
        assert entry.remarks == 'Great day'
    
    def test_import_json_entry_remarks_override(self, client, db, admin_user):
        """Test entry-level remarks override day-level remarks."""
        json_data = json.dumps([{
            "date": str(date.today()),
            "remarks": "Day remark",
            "dietary": [
                {"item": "Banana", "calories": 100, "remarks": "Item remark"}
            ]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        entry = DietaryEntry.objects.get(item='Banana')
        assert entry.remarks == 'Item remark'
    
    def test_import_json_multiple_days(self, client, db, admin_user):
        """Test importing data for multiple days."""
        json_data = json.dumps([
            {
                "date": str(date.today()),
                "dietary": [{"item": "Day1", "calories": 100}]
            },
            {
                "date": str(date.today() - timedelta(days=1)),
                "dietary": [{"item": "Day2", "calories": 200}]
            }
        ])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        data = response.json()
        
        assert data['success'] is True
        assert '2 dietary entries' in data['message']
    
    def test_import_json_creates_admin_user_if_needed(self, client, db):
        """Test import creates admin user if doesn't exist."""
        User.objects.filter(username='admin').delete()
        
        json_data = json.dumps([{
            "date": str(date.today()),
            "dietary": [{"item": "Test", "calories": 100}]
        }])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        assert User.objects.filter(username='admin').exists()
    
    def test_import_json_skips_entries_without_date(self, client, db, admin_user):
        """Test import skips entries without date field."""
        json_data = json.dumps([
            {
                "date": str(date.today()),
                "dietary": [{"item": "WithDate", "calories": 100}]
            },
            {
                "dietary": [{"item": "NoDate", "calories": 100}]
            }
        ])
        
        response = client.post(reverse('tracker:import_json'), {'json_data': json_data})
        
        assert DietaryEntry.objects.filter(item='WithDate').exists()
        assert not DietaryEntry.objects.filter(item='NoDate').exists()


# ============================================================================
# Add Weight View Tests
# ============================================================================

class TestAddWeightView:
    """Tests for the add_weight view."""
    
    def test_add_weight_get_not_allowed(self, client, db):
        """Test GET request returns 405."""
        response = client.get(reverse('tracker:add_weight'))
        assert response.status_code == 405
    
    def test_add_weight_missing_weight(self, client, db):
        """Test add weight with missing weight returns error."""
        response = client.post(reverse('tracker:add_weight'), {'weight_kg': ''})
        data = response.json()
        
        assert data['success'] is False
        assert 'Weight is required' in data['error']
    
    def test_add_weight_valid(self, client, db, admin_user):
        """Test adding valid weight entry."""
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': '75.5',
            'date': str(date.today()),
            'notes': 'Morning weight'
        })
        data = response.json()
        
        assert data['success'] is True
        assert '75.5 kg' in data['message']
        assert WeightEntry.objects.filter(weight_kg=Decimal('75.5')).exists()
    
    def test_add_weight_without_date_uses_today(self, client, db, admin_user):
        """Test add weight without date uses today."""
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': '70.0',
            'date': ''
        })
        data = response.json()
        
        assert data['success'] is True
        entry = WeightEntry.objects.latest('id')
        assert entry.date == date.today()
    
    def test_add_weight_without_notes(self, client, db, admin_user):
        """Test add weight without notes."""
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': '72.0',
            'date': str(date.today())
        })
        
        entry = WeightEntry.objects.latest('id')
        assert entry.notes == ''
    
    def test_add_weight_creates_admin_user_if_needed(self, client, db):
        """Test add weight creates admin user if doesn't exist."""
        User.objects.filter(username='admin').delete()
        
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': '68.5',
            'date': str(date.today())
        })
        
        assert User.objects.filter(username='admin').exists()
    
    def test_add_weight_invalid_decimal(self, client, db, admin_user):
        """Test add weight with invalid decimal returns error."""
        response = client.post(reverse('tracker:add_weight'), {
            'weight_kg': 'invalid',
            'date': str(date.today())
        })
        data = response.json()
        
        assert data['success'] is False


# ============================================================================
# Daily Recap View Tests
# ============================================================================

class TestDailyRecapView:
    """Tests for the daily_recap view."""
    
    def test_daily_recap_returns_json(self, client, db):
        """Test daily recap returns JSON response."""
        response = client.get(reverse('tracker:daily_recap', args=[str(date.today())]))
        assert response['Content-Type'] == 'application/json'
    
    def test_daily_recap_empty_date(self, client, db):
        """Test daily recap for date with no entries."""
        response = client.get(reverse('tracker:daily_recap', args=['2020-01-01']))
        data = response.json()
        
        assert data['success'] is True
        assert data['date'] == '2020-01-01'
        assert data['dietary'] == []
        assert data['exercise'] == []
        assert data['weight'] == []
    
    def test_daily_recap_with_dietary(self, client, dietary_entry):
        """Test daily recap includes dietary entries."""
        response = client.get(reverse('tracker:daily_recap', args=[str(dietary_entry.date)]))
        data = response.json()
        
        assert data['success'] is True
        assert len(data['dietary']) == 1
        assert data['dietary'][0]['item'] == dietary_entry.item
        assert data['dietary'][0]['calories'] == dietary_entry.calories
    
    def test_daily_recap_with_exercise(self, client, exercise_entry):
        """Test daily recap includes exercise entries."""
        response = client.get(reverse('tracker:daily_recap', args=[str(exercise_entry.date)]))
        data = response.json()
        
        assert data['success'] is True
        assert len(data['exercise']) == 1
        assert data['exercise'][0]['activity'] == exercise_entry.activity
    
    def test_daily_recap_with_weight(self, client, weight_entry):
        """Test daily recap includes weight entries."""
        response = client.get(reverse('tracker:daily_recap', args=[str(weight_entry.date)]))
        data = response.json()
        
        assert data['success'] is True
        assert len(data['weight']) == 1
        assert data['weight'][0]['weight_kg'] == float(weight_entry.weight_kg)
    
    def test_daily_recap_summary_calculations(self, client, db, user):
        """Test daily recap calculates summary correctly."""
        today = date.today()
        
        DietaryEntry.objects.create(user=user, date=today, calories=500)
        DietaryEntry.objects.create(user=user, date=today, calories=300)
        ExerciseEntry.objects.create(user=user, date=today, activity='Run', duration_minutes=30, calories_burned=250)
        ExerciseEntry.objects.create(user=user, date=today, activity='Walk', duration_minutes=15, calories_burned=100)
        
        response = client.get(reverse('tracker:daily_recap', args=[str(today)]))
        data = response.json()
        
        assert data['summary']['total_calories_in'] == 800
        assert data['summary']['total_calories_burned'] == 350
        assert data['summary']['total_exercise_min'] == 45
        assert data['summary']['net_calories'] == 450
    
    def test_daily_recap_invalid_date_format(self, client, db):
        """Test daily recap with invalid date format."""
        response = client.get(reverse('tracker:daily_recap', args=['invalid-date']))
        data = response.json()
        
        assert data['success'] is False
    
    def test_daily_recap_handles_null_calories_burned(self, client, db, user):
        """Test daily recap handles null calories_burned in exercise."""
        today = date.today()
        ExerciseEntry.objects.create(
            user=user,
            date=today,
            activity='Yoga',
            duration_minutes=30,
            calories_burned=None
        )
        
        response = client.get(reverse('tracker:daily_recap', args=[str(today)]))
        data = response.json()
        
        assert data['success'] is True
        assert data['summary']['total_calories_burned'] == 0


# ============================================================================
# URL Routing Tests
# ============================================================================

class TestURLRouting:
    """Tests for URL routing."""
    
    def test_dashboard_url_name(self, client, db):
        """Test dashboard URL name resolves."""
        url = reverse('tracker:dashboard')
        assert url == '/tracker/dashboard/'
    
    def test_dashboard_root_url_name(self, client, db):
        """Test dashboard-root URL name resolves."""
        url = reverse('tracker:dashboard-root')
        assert url == '/tracker/'
    
    def test_import_json_url_name(self, client, db):
        """Test import_json URL name resolves."""
        url = reverse('tracker:import_json')
        assert url == '/tracker/import-json/'
    
    def test_add_weight_url_name(self, client, db):
        """Test add_weight URL name resolves."""
        url = reverse('tracker:add_weight')
        assert url == '/tracker/add-weight/'
    
    def test_daily_recap_url_name(self, client, db):
        """Test daily_recap URL name resolves."""
        url = reverse('tracker:daily_recap', args=['2024-01-15'])
        assert url == '/tracker/daily-recap/2024-01-15/'
