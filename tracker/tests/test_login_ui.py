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

    # Not logged in: navbar does not show Import/Weight/Logout, shows Login
    resp = client.get('/')
    html = resp.content.decode()
    assert 'Import' not in html
    assert 'Weight' not in html
    assert 'Logout' not in html
    assert 'Login' in html

    # Login
    login_url = reverse('login')
    resp = client.post(login_url, {'username': username, 'password': password}, follow=True)
    assert resp.status_code == 200
    assert resp.context['user'].is_authenticated

    # After login: dashboard loads, Import/Weight/Logout visible, Login hidden
    resp = client.get('/')
    html = resp.content.decode()
    assert 'Import' in html
    assert 'Weight' in html
    assert f'Logout ({username})' in html
    assert 'Login' not in html

    # Logout
    logout_url = reverse('logout')
    resp = client.get(logout_url, follow=True)
    assert resp.status_code == 200
    # After logout: Import/Weight/Logout hidden, Login visible
    html = resp.content.decode()
    assert 'Import' not in html
    assert 'Weight' not in html
    assert 'Logout' not in html
    assert 'Login' in html

@pytest.mark.django_db
def test_superuser_admin_link(client):
    # Superuser sees Admin link
    user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
    client.login(username='admin', password='adminpass')
    resp = client.get('/')
    html = resp.content.decode()
    assert 'Admin' in html
    # Normal user does not see Admin link
    client.logout()
    user2 = User.objects.create_user('normal', password='normalpass')
    client.login(username='normal', password='normalpass')
    resp = client.get('/')
    html = resp.content.decode()
    assert 'Admin' not in html
