"""
Comprehensive tests for login/logout and navbar button visibility.
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_login_logout_flow(client):
    # Create user
    username = 'testuser'
    password = 'testpass123'
    user = User.objects.create_user(username=username, password=password)

    # Not logged in: dashboard redirects to login
    resp = client.get(reverse('tracker:dashboard'))
    assert resp.status_code == 302
    assert '/accounts/login/' in resp.url

    # Not logged in: follow redirect to login page, shows Login link in navbar
    resp = client.get('/', follow=True)
    html = resp.content.decode()
    # Check navbar doesn't have Logout link (user not logged in)
    assert 'Logout (' not in html
    # Check Login link is in navbar
    assert 'href="/accounts/login/">Login</a>' in html

    # Login
    client.login(username=username, password=password)

    # After login: dashboard loads, navbar shows Logout with username
    resp = client.get('/', follow=True)
    html = resp.content.decode()
    assert f'Logout ({username})' in html
    # Login link should not be visible when logged in
    assert 'href="/accounts/login/">Login</a>' not in html

    # Logout
    logout_url = reverse('logout')
    resp = client.get(logout_url, follow=True)
    assert resp.status_code == 200
    # After logout: Logout hidden, Login visible in navbar
    html = resp.content.decode()
    assert 'Logout (' not in html
    assert 'href="/accounts/login/">Login</a>' in html

@pytest.mark.django_db
def test_superuser_admin_link(client):
    # Superuser sees Admin link
    user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
    client.login(username='admin', password='adminpass')
    resp = client.get('/', follow=True)
    html = resp.content.decode()
    assert 'Admin' in html
    # Normal user does not see Admin link
    client.logout()
    user2 = User.objects.create_user('normal', password='normalpass')
    client.login(username='normal', password='normalpass')
    resp = client.get('/', follow=True)
    html = resp.content.decode()
    assert 'Admin' not in html
