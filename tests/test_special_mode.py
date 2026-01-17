"""
Tests for FOR_HER / Special Mode functionality.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class TestSpecialGroup:
    """Tests for the 'special' group functionality."""

    def test_special_group_exists_after_migration(self, db):
        """The 'special' group should exist after migrations."""
        group = Group.objects.filter(name='special').first()
        assert group is not None

    def test_user_not_special_by_default(self, user):
        """Regular users should not be in special group."""
        assert not user.groups.filter(name='special').exists()

    def test_user_can_be_added_to_special_group(self, user, special_group):
        """Users can be added to the special group."""
        user.groups.add(special_group)
        assert user.groups.filter(name='special').exists()

    def test_user_can_be_removed_from_special_group(self, special_user, special_group):
        """Users can be removed from the special group."""
        special_user.groups.remove(special_group)
        assert not special_user.groups.filter(name='special').exists()


class TestForHerContextProcessor:
    """Tests for the FOR_HER context processor."""

    def test_for_her_false_for_anonymous(self, client):
        """FOR_HER should be False for anonymous users."""
        response = client.get(reverse('tracker:guide'))
        assert response.context['FOR_HER'] is False

    def test_for_her_false_for_regular_user(self, authenticated_client):
        """FOR_HER should be False for regular users."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is False

    def test_for_her_true_for_special_user(self, client, special_user):
        """FOR_HER should be True for users in special group."""
        client.login(username='specialuser', password='specialpass123')
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is True

    def test_for_her_updates_when_group_added(self, client, user, special_group):
        """FOR_HER should update when user is added to group."""
        client.login(username='testuser', password='testpass123')

        # Before adding to group
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is False

        # Add to group
        user.groups.add(special_group)

        # After adding to group
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is True

    def test_for_her_updates_when_group_removed(self, client, special_user, special_group):
        """FOR_HER should update when user is removed from group."""
        client.login(username='specialuser', password='specialpass123')

        # Before removing from group
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is True

        # Remove from group
        special_user.groups.remove(special_group)

        # After removing from group
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is False


class TestSpecialModeAdmin:
    """Tests for managing special mode via admin."""

    def test_admin_can_add_user_to_special_group(self, admin_client, user, special_group):
        """Admin should be able to add user to special group."""
        url = reverse('admin:auth_user_change', args=[user.pk])

        # Get current form data
        response = admin_client.get(url)
        assert response.status_code == 200

        # Add user to special group via admin
        data = {
            'username': user.username,
            'date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': user.date_joined.strftime('%H:%M:%S'),
            'groups': [special_group.pk],
            'profile-TOTAL_FORMS': '1',
            'profile-INITIAL_FORMS': '1',
            'profile-MIN_NUM_FORMS': '0',
            'profile-MAX_NUM_FORMS': '1',
            'profile-0-id': user.profile.pk,
            'profile-0-user': user.pk,
            'profile-0-partner': '',
        }

        response = admin_client.post(url, data)

        # Refresh and check
        user.refresh_from_db()
        assert user.groups.filter(name='special').exists()

    def test_groups_visible_in_user_admin(self, admin_client, user):
        """Groups field should be visible in user admin."""
        url = reverse('admin:auth_user_change', args=[user.pk])
        response = admin_client.get(url)

        content = response.content.decode()
        assert 'groups' in content.lower()


class TestSpecialModeTemplateUsage:
    """Tests for template usage of FOR_HER variable."""

    def test_guide_accessible_for_special_user(self, client, special_user):
        """Special users should be able to access the guide."""
        client.login(username='specialuser', password='specialpass123')
        response = client.get(reverse('tracker:guide'))
        assert response.status_code == 200

    def test_dashboard_accessible_for_special_user(self, client, special_user):
        """Special users should be able to access the dashboard."""
        client.login(username='specialuser', password='specialpass123')
        response = client.get(reverse('tracker:dashboard'))
        assert response.status_code == 200


class TestMultipleSpecialUsers:
    """Tests for multiple users in special group."""

    def test_multiple_users_can_be_special(self, db, special_group):
        """Multiple users can be in the special group."""
        user1 = User.objects.create_user('special1', password='pass123')
        user2 = User.objects.create_user('special2', password='pass123')

        user1.groups.add(special_group)
        user2.groups.add(special_group)

        assert special_group.user_set.count() >= 2
        assert user1.groups.filter(name='special').exists()
        assert user2.groups.filter(name='special').exists()

    def test_special_users_independent(self, client, db, special_group):
        """Special users should have independent sessions."""
        user1 = User.objects.create_user('special1', password='pass123')
        user2 = User.objects.create_user('special2', password='pass123')

        user1.groups.add(special_group)
        # user2 is not special

        # Check user1
        client.login(username='special1', password='pass123')
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is True
        client.logout()

        # Check user2
        client.login(username='special2', password='pass123')
        response = client.get(reverse('tracker:dashboard'))
        assert response.context['FOR_HER'] is False
