"""
Tests for Avicenna Tracker views.
"""
import pytest
import json
from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.contrib.auth import get_user_model

from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry

User = get_user_model()


class TestDashboardView:
    """Tests for the dashboard view."""

    def test_dashboard_requires_login(self, client):
        """Dashboard should redirect unauthenticated users."""
        response = client.get(reverse('tracker:dashboard'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_dashboard_accessible_when_logged_in(self, authenticated_client):
        """Dashboard should be accessible to logged-in users."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        assert response.status_code == 200

    def test_dashboard_contains_expected_context(self, authenticated_client):
        """Dashboard should contain expected context variables."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        assert 'dietary_recent' in response.context
        assert 'exercise_recent' in response.context
        assert 'weight_recent' in response.context
        assert 'cal_dates' in response.context
        assert 'cal_values' in response.context
        assert 'heatmap_data' in response.context
        assert 'viewing_partner' in response.context
        assert 'partner' in response.context

    def test_dashboard_shows_user_data(self, authenticated_client, dietary_entry):
        """Dashboard should show the user's dietary entries."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        assert dietary_entry in response.context['dietary_recent']

    def test_dashboard_shows_exercise_data(self, authenticated_client, exercise_entry):
        """Dashboard should show the user's exercise entries."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        assert exercise_entry in response.context['exercise_recent']

    def test_dashboard_shows_weight_data(self, authenticated_client, weight_entry):
        """Dashboard should show the user's weight entries."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        assert weight_entry in response.context['weight_recent']

    def test_dashboard_calculates_totals(self, authenticated_client, dietary_entries):
        """Dashboard should calculate calorie totals."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        assert response.context['total_calories'] > 0

    def test_dashboard_no_partner_shown_when_not_linked(self, authenticated_client):
        """Dashboard should not show partner when not linked."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        assert response.context['partner'] is None
        assert response.context['viewing_partner'] is False

    def test_dashboard_caching_disabled(self, authenticated_client):
        """Dashboard should have no-cache headers."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        # Check cache-control headers
        cache_control = response.get('Cache-Control', '')
        assert 'no-cache' in cache_control or 'no-store' in cache_control


class TestPartnerDashboardView:
    """Tests for partner dashboard view."""

    def test_partner_dashboard_requires_login(self, client):
        """Partner dashboard should redirect unauthenticated users."""
        response = client.get(reverse('tracker:partner_dashboard'))
        assert response.status_code == 302

    def test_partner_dashboard_without_partner(self, authenticated_client):
        """Partner dashboard should work even without partner (shows own data)."""
        response = authenticated_client.get(reverse('tracker:partner_dashboard'))
        assert response.status_code == 200
        # When no partner, viewing_partner should be False
        assert response.context['viewing_partner'] is False

    def test_partner_dashboard_with_partner(self, client, linked_partners, partner_with_data):
        """Partner dashboard should show partner's data."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))
        assert response.status_code == 200
        assert response.context['viewing_partner'] is True
        assert response.context['target_user'] == partner

    def test_partner_dashboard_shows_partner_name(self, client, linked_partners):
        """Partner dashboard should display partner's name."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))
        assert response.context['partner_name'] == 'partner'


class TestDailyRecapView:
    """Tests for daily recap API endpoint."""

    def test_daily_recap_requires_login(self, client):
        """Daily recap should redirect unauthenticated users."""
        today = date.today().strftime('%Y-%m-%d')
        response = client.get(f'/tracker/daily-recap/{today}/')
        assert response.status_code == 302

    def test_daily_recap_returns_json(self, authenticated_client):
        """Daily recap should return JSON."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_daily_recap_success_response(self, authenticated_client, dietary_entry):
        """Daily recap should return success with data."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/')

        data = json.loads(response.content)
        assert data['success'] is True
        assert 'dietary' in data
        assert 'exercise' in data
        assert 'weight' in data
        assert 'summary' in data

    def test_daily_recap_contains_dietary_data(self, authenticated_client, dietary_entry):
        """Daily recap should include dietary entries."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/')

        data = json.loads(response.content)
        assert len(data['dietary']) == 1
        assert data['dietary'][0]['item'] == 'Test Food'
        assert data['dietary'][0]['calories'] == 500

    def test_daily_recap_contains_exercise_data(self, authenticated_client, exercise_entry):
        """Daily recap should include exercise entries."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/')

        data = json.loads(response.content)
        assert len(data['exercise']) == 1
        assert data['exercise'][0]['activity'] == 'Running'

    def test_daily_recap_contains_weight_data(self, authenticated_client, weight_entry):
        """Daily recap should include weight entries."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/')

        data = json.loads(response.content)
        assert len(data['weight']) == 1
        assert data['weight'][0]['weight_kg'] == 70.5

    def test_daily_recap_calculates_summary(self, authenticated_client, dietary_entry, exercise_entry):
        """Daily recap should calculate summary totals."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/')

        data = json.loads(response.content)
        assert data['summary']['total_calories_in'] == 500
        assert data['summary']['total_calories_burned'] == 300
        assert data['summary']['net_calories'] == 200

    def test_daily_recap_empty_day(self, authenticated_client):
        """Daily recap should handle days with no entries."""
        yesterday = (date.today() - timedelta(days=100)).strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{yesterday}/')

        data = json.loads(response.content)
        assert data['success'] is True
        assert len(data['dietary']) == 0
        assert len(data['exercise']) == 0
        assert len(data['weight']) == 0

    def test_daily_recap_partner_access(self, client, linked_partners, partner_with_data):
        """User should be able to access partner's daily recap."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        today = date.today().strftime('%Y-%m-%d')
        response = client.get(f'/tracker/daily-recap/{today}/user/{partner.id}/')

        data = json.loads(response.content)
        assert data['success'] is True
        # Should show partner's data
        assert len(data['dietary']) == 1
        assert data['dietary'][0]['item'] == 'Partner Breakfast'

    def test_daily_recap_unauthorized_partner_access(self, authenticated_client, user2):
        """User should not access non-partner's data."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/user/{user2.id}/')

        data = json.loads(response.content)
        assert data['success'] is False
        assert 'Unauthorized' in data['error']


class TestAddWeightView:
    """Tests for add weight endpoint."""

    def test_add_weight_requires_login(self, client):
        """Add weight should require authentication."""
        response = client.post('/tracker/add-weight/', {'weight_kg': '70.0'})
        assert response.status_code == 302

    def test_add_weight_requires_post(self, authenticated_client):
        """Add weight should only accept POST requests."""
        response = authenticated_client.get('/tracker/add-weight/')
        assert response.status_code == 405

    def test_add_weight_success(self, authenticated_client, user):
        """Add weight should create a new weight entry."""
        response = authenticated_client.post('/tracker/add-weight/', {
            'weight_kg': '72.5',
            'date': date.today().strftime('%Y-%m-%d'),
            'notes': 'After workout'
        })

        data = json.loads(response.content)
        assert data['success'] is True

        # Verify entry was created
        entry = WeightEntry.objects.filter(user=user).latest('id')
        assert entry.weight_kg == Decimal('72.5')
        assert entry.notes == 'After workout'

    def test_add_weight_missing_weight(self, authenticated_client):
        """Add weight should fail without weight value."""
        response = authenticated_client.post('/tracker/add-weight/', {
            'date': date.today().strftime('%Y-%m-%d'),
        })

        data = json.loads(response.content)
        assert data['success'] is False
        assert 'required' in data['error'].lower()

    def test_add_weight_default_date(self, authenticated_client, user):
        """Add weight should use today's date if not provided."""
        response = authenticated_client.post('/tracker/add-weight/', {
            'weight_kg': '73.0',
        })

        data = json.loads(response.content)
        assert data['success'] is True

        entry = WeightEntry.objects.filter(user=user).latest('id')
        assert entry.date == date.today()


class TestImportJsonView:
    """Tests for JSON import endpoint."""

    def test_import_json_requires_login(self, client):
        """Import JSON should require authentication."""
        response = client.post('/tracker/import-json/', {'json_data': '[]'})
        assert response.status_code == 302

    def test_import_json_requires_post(self, authenticated_client):
        """Import JSON should only accept POST requests."""
        response = authenticated_client.get('/tracker/import-json/')
        assert response.status_code == 405

    def test_import_json_empty_data(self, authenticated_client):
        """Import JSON should fail with empty data."""
        response = authenticated_client.post('/tracker/import-json/', {
            'json_data': ''
        })

        data = json.loads(response.content)
        assert data['success'] is False

    def test_import_json_invalid_json(self, authenticated_client):
        """Import JSON should fail with invalid JSON."""
        response = authenticated_client.post('/tracker/import-json/', {
            'json_data': 'not valid json'
        })

        data = json.loads(response.content)
        assert data['success'] is False
        assert 'JSON' in data['error']

    def test_import_json_valid_dietary(self, authenticated_client, user):
        """Import JSON should create dietary entries."""
        json_data = json.dumps([{
            'date': date.today().strftime('%Y-%m-%d'),
            'dietary': [
                {'item': 'Imported Food', 'calories': 450}
            ]
        }])

        response = authenticated_client.post('/tracker/import-json/', {
            'json_data': json_data
        })

        data = json.loads(response.content)
        assert data['success'] is True
        assert '1 dietary' in data['message']

        # Verify entry was created
        entry = DietaryEntry.objects.filter(user=user, item='Imported Food').first()
        assert entry is not None
        assert entry.calories == 450

    def test_import_json_valid_exercise(self, authenticated_client, user):
        """Import JSON should create exercise entries."""
        json_data = json.dumps([{
            'date': date.today().strftime('%Y-%m-%d'),
            'exercise': [
                {'activity': 'Imported Exercise', 'duration_minutes': 30, 'calories_burned': 250}
            ]
        }])

        response = authenticated_client.post('/tracker/import-json/', {
            'json_data': json_data
        })

        data = json.loads(response.content)
        assert data['success'] is True
        assert '1 exercise' in data['message']

        # Verify entry was created
        entry = ExerciseEntry.objects.filter(user=user, activity='Imported Exercise').first()
        assert entry is not None
        assert entry.duration_minutes == 30

    def test_import_json_alternative_field_names(self, authenticated_client, user):
        """Import JSON should accept alternative field names (food, duration_min)."""
        json_data = json.dumps([{
            'date': date.today().strftime('%Y-%m-%d'),
            'food': [
                {'item': 'Alt Food', 'calories': 300}
            ],
            'exercise': [
                {'activity': 'Alt Exercise', 'duration_min': 20}
            ]
        }])

        response = authenticated_client.post('/tracker/import-json/', {
            'json_data': json_data
        })

        data = json.loads(response.content)
        assert data['success'] is True

        dietary = DietaryEntry.objects.filter(user=user, item='Alt Food').first()
        exercise = ExerciseEntry.objects.filter(user=user, activity='Alt Exercise').first()

        assert dietary is not None
        assert exercise is not None
        assert exercise.duration_minutes == 20

    def test_import_json_skips_invalid_dates(self, authenticated_client):
        """Import JSON should skip entries with invalid dates."""
        json_data = json.dumps([
            {'date': 'invalid-date', 'dietary': [{'item': 'Food', 'calories': 100}]},
            {'date': date.today().strftime('%Y-%m-%d'), 'dietary': [{'item': 'Valid Food', 'calories': 200}]}
        ])

        response = authenticated_client.post('/tracker/import-json/', {
            'json_data': json_data
        })

        data = json.loads(response.content)
        assert data['success'] is True
        assert 'Skipped 1' in data['message']


class TestGuideView:
    """Tests for the guide page."""

    def test_guide_accessible_without_login(self, client):
        """Guide page should be publicly accessible."""
        response = client.get(reverse('tracker:guide'))
        assert response.status_code == 200

    def test_guide_uses_correct_template(self, client):
        """Guide page should use the guide template."""
        response = client.get(reverse('tracker:guide'))
        assert 'tracker/guide.html' in [t.name for t in response.templates]


class TestAuthenticationViews:
    """Tests for authentication-related views."""

    def test_logout_clears_session(self, authenticated_client):
        """Logout should clear the session."""
        response = authenticated_client.get('/accounts/logout/')

        # Should redirect to login page
        assert response.status_code == 302

        # Session should be cleared - subsequent dashboard request should redirect
        response = authenticated_client.get(reverse('tracker:dashboard'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
