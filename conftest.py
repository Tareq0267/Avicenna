"""
Pytest configuration and fixtures for the Avicenna fitness tracker tests.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create or get the admin user (used by import/add_weight views)."""
    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@example.com'}
    )
    user.set_password('admin123')
    user.save()
    return user


@pytest.fixture
def dietary_entry(db, user):
    """Create a single dietary entry."""
    from tracker.models import DietaryEntry
    return DietaryEntry.objects.create(
        user=user,
        date=date.today(),
        item='Test Breakfast',
        calories=500,
        notes='Test notes',
        remarks='Test remarks'
    )


@pytest.fixture
def exercise_entry(db, user):
    """Create a single exercise entry."""
    from tracker.models import ExerciseEntry
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
    from tracker.models import WeightEntry
    return WeightEntry.objects.create(
        user=user,
        date=date.today(),
        weight_kg=Decimal('75.50'),
        notes='Morning weight'
    )


@pytest.fixture
def multiple_dietary_entries(db, user):
    """Create multiple dietary entries over several days."""
    from tracker.models import DietaryEntry
    entries = []
    for i in range(7):
        entry = DietaryEntry.objects.create(
            user=user,
            date=date.today() - timedelta(days=i),
            item=f'Food item {i}',
            calories=400 + (i * 50),
            notes=f'Notes for day {i}',
            remarks=f'Remarks for day {i}'
        )
        entries.append(entry)
    return entries


@pytest.fixture
def multiple_exercise_entries(db, user):
    """Create multiple exercise entries over several days."""
    from tracker.models import ExerciseEntry
    entries = []
    activities = ['Running', 'Swimming', 'Cycling', 'Walking', 'Yoga', 'Weights', 'HIIT']
    for i in range(7):
        entry = ExerciseEntry.objects.create(
            user=user,
            date=date.today() - timedelta(days=i),
            activity=activities[i],
            duration_minutes=20 + (i * 5),
            calories_burned=150 + (i * 25),
            remarks=f'Workout remarks {i}'
        )
        entries.append(entry)
    return entries


@pytest.fixture
def multiple_weight_entries(db, user):
    """Create multiple weight entries over several days."""
    from tracker.models import WeightEntry
    entries = []
    for i in range(10):
        entry = WeightEntry.objects.create(
            user=user,
            date=date.today() - timedelta(days=i),
            weight_kg=Decimal('75.00') - Decimal(str(i * 0.1)),
            notes=f'Weight notes {i}'
        )
        entries.append(entry)
    return entries


@pytest.fixture
def sample_import_json():
    """Sample JSON data for import testing."""
    return [
        {
            "date": str(date.today()),
            "remarks": "Good day overall",
            "dietary": [
                {"item": "Oatmeal", "calories": 300, "notes": "With berries"},
                {"item": "Chicken Salad", "calories": 450, "notes": "Light dressing"}
            ],
            "exercise": [
                {"activity": "Morning Jog", "duration_minutes": 30, "calories_burned": 250}
            ]
        },
        {
            "date": str(date.today() - timedelta(days=1)),
            "food": [  # Testing 'food' key alias
                {"item": "Eggs", "calories": 200, "note": "Scrambled"}  # Testing 'note' alias
            ],
            "exercise": [
                {"activity": "Yoga", "duration_min": 45, "calories_burned": 150}  # Testing 'duration_min' alias
            ]
        }
    ]


@pytest.fixture
def client():
    """Django test client."""
    from django.test import Client
    return Client()
