"""
Pytest configuration and fixtures for tracker app tests.
These fixtures include proper authentication for views that require login.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a standard test user."""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin/superuser."""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )
    return user


@pytest.fixture
def authenticated_client(client, user):
    """Return a logged-in test client."""
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Return a logged-in admin client."""
    client.login(username='admin', password='adminpass123')
    return client


@pytest.fixture
def dietary_entry(db, user):
    """Create a single dietary entry."""
    return DietaryEntry.objects.create(
        user=user,
        date=date.today(),
        item='Test Food',
        calories=500,
        notes='Test notes',
        remarks='Test remarks'
    )


@pytest.fixture
def exercise_entry(db, user):
    """Create a single exercise entry."""
    return ExerciseEntry.objects.create(
        user=user,
        date=date.today(),
        activity='Running',
        duration_minutes=30,
        calories_burned=300,
        remarks='Morning run'
    )


@pytest.fixture
def weight_entry(db, user):
    """Create a single weight entry."""
    return WeightEntry.objects.create(
        user=user,
        date=date.today(),
        weight_kg=Decimal('70.5'),
        notes='Morning weight'
    )


@pytest.fixture
def multiple_dietary_entries(db, user, authenticated_client):
    """Create multiple dietary entries across several days."""
    entries = []
    today = date.today()
    for i in range(7):
        entry_date = today - timedelta(days=i)
        entry = DietaryEntry.objects.create(
            user=user,
            date=entry_date,
            item=f'Food Day {i}',
            calories=400 + (i * 50),
            notes=f'Notes for day {i}'
        )
        entries.append(entry)
    return entries


@pytest.fixture
def multiple_exercise_entries(db, user, authenticated_client):
    """Create multiple exercise entries across several days."""
    entries = []
    today = date.today()
    for i in range(7):
        entry_date = today - timedelta(days=i)
        entry = ExerciseEntry.objects.create(
            user=user,
            date=entry_date,
            activity=f'Activity Day {i}',
            duration_minutes=30 + (i * 5),
            calories_burned=200 + (i * 20)
        )
        entries.append(entry)
    return entries


@pytest.fixture
def multiple_weight_entries(db, user, authenticated_client):
    """Create multiple weight entries across several days."""
    entries = []
    today = date.today()
    base_weight = Decimal('70.0')
    for i in range(10):
        entry_date = today - timedelta(days=i)
        weight = base_weight + Decimal(str(i * 0.1))
        entry = WeightEntry.objects.create(
            user=user,
            date=entry_date,
            weight_kg=weight,
            notes=f'Day {i} weight'
        )
        entries.append(entry)
    return entries
