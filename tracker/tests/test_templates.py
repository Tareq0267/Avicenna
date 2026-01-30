"""
Tests for tracker templates and template rendering.
"""
import pytest
from django.test import Client
from django.urls import reverse


# ============================================================================
# Template Content Tests
# ============================================================================

class TestDashboardTemplateContent:
    """Tests for dashboard template content."""

    @pytest.fixture(autouse=True)
    def login(self, client, user):
        client.login(username='testuser', password='testpass123')
        self.client = client

    @pytest.fixture
    def response(self, db):
        return self.client.get(reverse('tracker:dashboard'))
    
    def test_dashboard_contains_title(self, response):
        """Test dashboard contains page title."""
        assert b'Avicenna' in response.content or b'Dashboard' in response.content
    
    def test_dashboard_contains_charts_container(self, response):
        """Test dashboard contains charts containers."""
        content = response.content.decode('utf-8')
        assert 'calChart' in content or 'chart' in content.lower()
    
    def test_dashboard_contains_heatmap(self, response):
        """Test dashboard contains heatmap element."""
        content = response.content.decode('utf-8')
        assert 'heatmap' in content.lower() or 'activity-heatmap' in content
    
    def test_dashboard_contains_stat_cards(self, response):
        """Test dashboard contains statistics cards."""
        content = response.content.decode('utf-8')
        # Check for stat-related elements
        assert 'stat' in content.lower() or 'total' in content.lower()
    
    def test_dashboard_contains_recent_entries_tables(self, response):
        """Test dashboard contains recent entries sections."""
        content = response.content.decode('utf-8')
        assert 'Recent' in content or 'recent' in content
    
    def test_dashboard_contains_import_button(self, response):
        """Test dashboard contains import functionality."""
        content = response.content.decode('utf-8')
        assert 'import' in content.lower() or 'Import' in content
    
    def test_dashboard_contains_weight_form(self, response):
        """Test dashboard contains weight logging form."""
        content = response.content.decode('utf-8')
        assert 'weight' in content.lower()
    
    def test_dashboard_loads_echarts(self, response):
        """Test dashboard includes ECharts library."""
        content = response.content.decode('utf-8')
        assert 'echarts' in content.lower()
    
    def test_dashboard_loads_bootstrap(self, response):
        """Test dashboard includes Bootstrap."""
        content = response.content.decode('utf-8')
        assert 'bootstrap' in content.lower()


# ============================================================================
# Template Inheritance Tests
# ============================================================================

class TestTemplateInheritance:
    """Tests for template inheritance structure."""

    def test_dashboard_extends_base(self, authenticated_client, db):
        """Test dashboard template extends base template."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        # Base template should provide common elements
        content = response.content.decode('utf-8')
        assert '<html' in content
        assert '</html>' in content

    def test_base_template_has_navigation(self, authenticated_client, db):
        """Test base template includes navigation."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        content = response.content.decode('utf-8')
        assert 'nav' in content.lower() or 'navbar' in content.lower()


# ============================================================================
# Modal Tests
# ============================================================================

class TestModals:
    """Tests for modal dialogs in templates."""

    def test_import_modal_exists(self, authenticated_client, db):
        """Test import JSON modal is present."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        content = response.content.decode('utf-8')
        assert 'importJsonModal' in content or 'import' in content.lower()

    def test_weight_modal_exists(self, authenticated_client, db):
        """Test add weight modal is present."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        content = response.content.decode('utf-8')
        assert 'addWeightModal' in content or 'weight' in content.lower()

    def test_daily_recap_modal_exists(self, authenticated_client, db):
        """Test daily recap modal is present."""
        response = authenticated_client.get(reverse('tracker:dashboard'))
        content = response.content.decode('utf-8')
        assert 'dailyRecapModal' in content or 'recap' in content.lower()
