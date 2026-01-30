"""
Tests for Couples Mode functionality.
"""
import json
from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.contrib.auth import get_user_model

from tracker.models import DietaryEntry, WeightEntry

User = get_user_model()


class TestPartnerLinking:
    """Tests for partner linking functionality."""

    def test_users_start_without_partners(self, user, user2):
        """New users should not have partners by default."""
        assert user.profile.partner is None
        assert user2.profile.partner is None

    def test_one_way_partner_link(self, user, user2):
        """Partner linking can be one-way."""
        user.profile.partner = user2
        user.profile.save()

        assert user.profile.partner == user2
        assert user2.profile.partner is None

    def test_bidirectional_partner_link(self, linked_partners):
        """Partners can be linked bidirectionally."""
        user, partner = linked_partners

        assert user.profile.partner == partner
        assert partner.profile.partner == user

    def test_partner_can_be_changed(self, user, user2, admin_user):
        """Partner link can be changed to different user."""
        user.profile.partner = user2
        user.profile.save()

        user.profile.partner = admin_user
        user.profile.save()

        assert user.profile.partner == admin_user

    def test_partner_can_be_removed(self, linked_partners):
        """Partner link can be removed."""
        user, partner = linked_partners

        user.profile.partner = None
        user.profile.save()

        user.profile.refresh_from_db()
        assert user.profile.partner is None
        # Other partner should still have link
        assert partner.profile.partner == user


class TestPartnerDashboardView:
    """Tests for viewing partner's dashboard."""

    def test_partner_dashboard_shows_partner_data(self, client, linked_partners, partner_with_data):
        """Partner dashboard should show partner's entries."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))

        # Should be viewing partner's data
        assert response.context['viewing_partner'] is True
        assert response.context['target_user'] == partner

    def test_partner_dashboard_hides_own_data(self, client, linked_partners, dietary_entry):
        """Partner dashboard should not show user's own data."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))

        # Own data should not appear (dietary_entry belongs to user)
        assert dietary_entry not in response.context['dietary_recent']

    def test_partner_dashboard_redirects_without_partner(self, authenticated_client):
        """Partner dashboard without partner shows own data."""
        response = authenticated_client.get(reverse('tracker:partner_dashboard'))

        # Should still work but show own data
        assert response.status_code == 200
        assert response.context['viewing_partner'] is False

    def test_partner_banner_visible_when_viewing_partner(self, client, linked_partners):
        """Partner banner should be visible when viewing partner dashboard."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))

        content = response.content.decode()
        assert 'partner-banner' in content
        assert partner.username in content

    def test_partner_toggle_visible_on_own_dashboard(self, client, linked_partners):
        """Partner toggle card should be visible on own dashboard."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:dashboard'))

        content = response.content.decode()
        assert 'partner-toggle-card' in content
        assert partner.username in content

    def test_partner_toggle_hidden_without_partner(self, authenticated_client):
        """Partner toggle should not appear when no partner is linked."""
        response = authenticated_client.get(reverse('tracker:dashboard'))

        content = response.content.decode()
        assert 'partner-toggle-card' not in content

    def test_back_to_mine_link_works(self, client, linked_partners):
        """Back to Mine link should return to own dashboard."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        # View partner dashboard
        response = client.get(reverse('tracker:partner_dashboard'))
        assert response.context['viewing_partner'] is True

        # Click back to mine (view own dashboard)
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['viewing_partner'] is False


class TestPartnerDailyRecap:
    """Tests for viewing partner's daily recap."""

    def test_can_view_partner_daily_recap(self, client, linked_partners, partner_with_data):
        """User can view their partner's daily recap."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        today = date.today().strftime('%Y-%m-%d')
        response = client.get(f'/tracker/daily-recap/{today}/user/{partner.id}/')

        data = json.loads(response.content)
        assert data['success'] is True
        assert data['dietary'][0]['item'] == 'Partner Breakfast'

    def test_cannot_view_non_partner_daily_recap(self, authenticated_client, user2):
        """User cannot view daily recap of non-partner."""
        today = date.today().strftime('%Y-%m-%d')
        response = authenticated_client.get(f'/tracker/daily-recap/{today}/user/{user2.id}/')

        data = json.loads(response.content)
        assert data['success'] is False
        assert 'Unauthorized' in data['error']

    def test_partner_recap_shows_correct_summary(self, client, linked_partners, partner_with_data):
        """Partner's daily recap should show correct summary."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        today = date.today().strftime('%Y-%m-%d')
        response = client.get(f'/tracker/daily-recap/{today}/user/{partner.id}/')

        data = json.loads(response.content)
        assert data['summary']['total_calories_in'] == 350
        assert data['summary']['total_calories_burned'] == 200


class TestPartnerDataIsolation:
    """Tests to ensure data isolation between partners."""

    def test_partner_cannot_see_other_users_data(self, client, user, user2, admin_user):
        """Users should not see data from users who aren't their partner."""
        # Create data for admin_user
        DietaryEntry.objects.create(
            user=admin_user,
            date=date.today(),
            item='Admin Food',
            calories=1000
        )

        # Link user to user2 (not admin)
        user.profile.partner = user2
        user.profile.save()

        client.login(username='testuser', password='testpass123')

        # Try to access admin's data via partner endpoint
        today = date.today().strftime('%Y-%m-%d')
        response = client.get(f'/tracker/daily-recap/{today}/user/{admin_user.id}/')

        data = json.loads(response.content)
        assert data['success'] is False

    def test_own_dashboard_unaffected_by_partner_data(self, client, linked_partners, partner_with_data, dietary_entry):
        """Own dashboard should only show own data."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:dashboard'))

        # Should show own data
        assert dietary_entry in response.context['dietary_recent']

        # Should NOT show partner's data
        partner_entries = DietaryEntry.objects.filter(user=partner)
        for entry in partner_entries:
            assert entry not in response.context['dietary_recent']

    def test_partner_actions_disabled(self, client, linked_partners):
        """User should not be able to add data for partner."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        # Try to add weight (should add to own account, not partner's)
        response = client.post('/tracker/add-weight/', {
            'weight_kg': '100.0',
            'date': date.today().strftime('%Y-%m-%d'),
        })

        data = json.loads(response.content)
        assert data['success'] is True

        # Verify it was added to user's account, not partner's
        user_entry = WeightEntry.objects.filter(user=user, weight_kg=Decimal('100.0'))
        partner_entry = WeightEntry.objects.filter(user=partner, weight_kg=Decimal('100.0'))

        assert user_entry.exists()
        assert not partner_entry.exists()


class TestPartnerCharts:
    """Tests for partner's chart data."""

    def test_partner_chart_data_correct(self, client, linked_partners, partner_with_data):
        """Partner dashboard should have correct chart data."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))

        # Chart data should be for partner
        cal_values = json.loads(response.context['cal_values'])
        # Partner has 350 calorie breakfast
        assert 350 in cal_values or sum(cal_values) >= 350

    def test_partner_heatmap_data_correct(self, client, linked_partners, partner_with_data):
        """Partner's heatmap should show their activity."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))

        heatmap_data = json.loads(response.context['heatmap_data'])
        today_str = date.today().strftime('%Y-%m-%d')

        # Find today's entry in heatmap
        today_count = None
        for entry in heatmap_data:
            if entry[0] == today_str:
                today_count = entry[1]
                break

        # Partner has 3 entries today (dietary, exercise, weight)
        assert today_count == 3

    def test_partner_latest_weight_shown(self, client, linked_partners, partner_with_data):
        """Partner's latest weight should be shown."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('tracker:partner_dashboard'))

        # Partner's weight is 55.0
        assert response.context['latest_weight'] == 55.0


class TestOneWayPartnerLink:
    """Tests for one-way partner linking scenarios."""

    def test_user_can_view_partner_without_reciprocal(self, client, user, user2):
        """User can view partner even if partner hasn't linked back."""
        # One-way link: user -> user2
        user.profile.partner = user2
        user.profile.save()

        # Create some data for user2
        DietaryEntry.objects.create(
            user=user2,
            date=date.today(),
            item='One Way Food',
            calories=400
        )

        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('tracker:partner_dashboard'))

        assert response.context['viewing_partner'] is True
        assert response.context['target_user'] == user2

    def test_partner_without_link_cannot_view_back(self, client, user, user2):
        """User2 cannot view user1 if they haven't linked."""
        # One-way link: user -> user2
        user.profile.partner = user2
        user.profile.save()

        # user2 hasn't linked to user
        assert user2.profile.partner is None

        client.login(username='partner', password='partnerpass123')
        response = client.get(reverse('tracker:partner_dashboard'))

        # Should show own data since no partner linked
        assert response.context['viewing_partner'] is False


class TestPartnerDeletionHandling:
    """Tests for handling partner account deletion."""

    def test_partner_deletion_clears_link(self, linked_partners):
        """When partner is deleted, link should be cleared."""
        user, partner = linked_partners
        partner.delete()

        user.profile.refresh_from_db()
        assert user.profile.partner is None

    def test_dashboard_works_after_partner_deleted(self, client, linked_partners):
        """Dashboard should work after partner is deleted."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        # Delete partner
        partner.delete()

        # Dashboard should still work
        response = client.get(reverse('tracker:dashboard'))
        assert response.status_code == 200
        assert response.context['partner'] is None

    def test_partner_dashboard_after_partner_deleted(self, client, linked_partners):
        """Partner dashboard should fallback to own data after deletion."""
        user, partner = linked_partners
        client.login(username='testuser', password='testpass123')

        # Delete partner
        partner.delete()

        # Partner dashboard should show own data
        response = client.get(reverse('tracker:partner_dashboard'))
        assert response.status_code == 200
        assert response.context['viewing_partner'] is False
