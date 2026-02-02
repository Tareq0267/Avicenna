import pytest
from django.urls import reverse
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_delete_dietary_entry(client):
    user = User.objects.create_user(username='deleteuser', password='pass')
    client.login(username='deleteuser', password='pass')
    entry = DietaryEntry.objects.create(user=user, date='2026-01-01', item='Test', calories=100)
    url = reverse('tracker:delete_dietary_entry', args=[entry.id])
    response = client.post(url, follow=True)
    assert response.status_code == 200 or response.status_code == 302
    assert not DietaryEntry.objects.filter(id=entry.id).exists()

@pytest.mark.django_db
def test_delete_exercise_entry(client):
    user = User.objects.create_user(username='deleteuser2', password='pass')
    client.login(username='deleteuser2', password='pass')
    entry = ExerciseEntry.objects.create(user=user, date='2026-01-01', activity='Test', duration_minutes=10)
    url = reverse('tracker:delete_exercise_entry', args=[entry.id])
    response = client.post(url, follow=True)
    assert response.status_code == 200 or response.status_code == 302
    assert not ExerciseEntry.objects.filter(id=entry.id).exists()

@pytest.mark.django_db
def test_delete_weight_entry(client):
    user = User.objects.create_user(username='deleteuser3', password='pass')
    client.login(username='deleteuser3', password='pass')
    entry = WeightEntry.objects.create(user=user, date='2026-01-01', weight_kg=70)
    url = reverse('tracker:delete_weight_entry', args=[entry.id])
    response = client.post(url, follow=True)
    assert response.status_code == 200 or response.status_code == 302
    assert not WeightEntry.objects.filter(id=entry.id).exists()
