"""
Pytest configuration and fixtures for Avicenna Tracker tests.
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
def user2(db):
    """Create a second test user (for couples mode testing)."""
    user = User.objects.create_user(
        username='partner',
        email='partner@example.com',
        password='partnerpass123'
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
def special_group(db):
    """Create the 'special' group for FOR_HER mode."""
    group, _ = Group.objects.get_or_create(name='special')
    return group


@pytest.fixture
def special_user(db, special_group):
    """Create a user in the 'special' group."""
    user = User.objects.create_user(
        username='specialuser',
        email='special@example.com',
        password='specialpass123'
    )
    user.groups.add(special_group)
    return user


@pytest.fixture
def linked_partners(db, user, user2):
    """Create two users linked as partners."""
    # Link user -> user2
    user.profile.partner = user2
    user.profile.save()
    # Link user2 -> user (bidirectional)
    user2.profile.partner = user
    user2.profile.save()
    return user, user2


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
def dietary_entries(db, user):
    """Create multiple dietary entries across several days."""
    entries = []
    today = date.today()
    foods = [
        ('Breakfast', 400),
        ('Lunch', 600),
        ('Dinner', 700),
        ('Snack', 200),
    ]
    for i in range(7):
        entry_date = today - timedelta(days=i)
        for item, calories in foods:
            entry = DietaryEntry.objects.create(
                user=user,
                date=entry_date,
                item=f'{item} Day {i}',
                calories=calories,
                notes=f'Notes for {item}',
                remarks=f'Day {i} remarks'
            )
            entries.append(entry)
    return entries


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
def exercise_entries(db, user):
    """Create multiple exercise entries across several days."""
    entries = []
    today = date.today()
    activities = [
        ('Running', 30, 300),
        ('Walking', 45, 150),
        ('Cycling', 60, 400),
    ]
    for i in range(7):
        entry_date = today - timedelta(days=i)
        for activity, duration, calories in activities:
            entry = ExerciseEntry.objects.create(
                user=user,
                date=entry_date,
                activity=f'{activity} Day {i}',
                duration_minutes=duration,
                calories_burned=calories,
                remarks=f'Day {i} exercise'
            )
            entries.append(entry)
    return entries


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
def weight_entries(db, user):
    """Create multiple weight entries across several days."""
    entries = []
    today = date.today()
    base_weight = Decimal('70.0')
    for i in range(10):
        entry_date = today - timedelta(days=i)
        # Simulate slight weight fluctuations
        weight = base_weight + Decimal(str(i * 0.1))
        entry = WeightEntry.objects.create(
            user=user,
            date=entry_date,
            weight_kg=weight,
            notes=f'Day {i} weight'
        )
        entries.append(entry)
    return entries


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
def partner_with_data(db, user2):
    """Create partner user with their own data."""
    today = date.today()

    # Partner's dietary entries
    DietaryEntry.objects.create(
        user=user2,
        date=today,
        item='Partner Breakfast',
        calories=350,
        notes='Partner food'
    )

    # Partner's exercise
    ExerciseEntry.objects.create(
        user=user2,
        date=today,
        activity='Yoga',
        duration_minutes=45,
        calories_burned=200
    )

    # Partner's weight
    WeightEntry.objects.create(
        user=user2,
        date=today,
        weight_kg=Decimal('55.0'),
        notes='Partner weight'
    )

    return user2
