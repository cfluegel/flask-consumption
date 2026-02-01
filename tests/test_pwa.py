"""Tests for PWA blueprint routes and functionality."""

import json
import pytest

from app.models import Meter


class TestPWARoutes:
    """Tests for PWA page routes."""

    def test_pwa_index(self, client):
        """Test PWA index page loads."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'Verbrauchstracker' in response.data

    def test_pwa_setup(self, client):
        """Test PWA setup page loads."""
        response = client.get('/pwa/setup')
        assert response.status_code == 200
        assert b'API-Schl' in response.data  # "API-Schlüssel"

    def test_pwa_meter_detail(self, client, sample_meters):
        """Test PWA meter detail page loads."""
        meter_id = sample_meters['Strom']
        response = client.get(f'/pwa/meter/{meter_id}')
        assert response.status_code == 200
        assert b'Ablesungen' in response.data

    def test_pwa_add_reading(self, client, sample_meters):
        """Test PWA add reading page loads."""
        meter_id = sample_meters['Strom']
        response = client.get(f'/pwa/meter/{meter_id}/add')
        assert response.status_code == 200
        assert b'Neue Ablesung' in response.data

    def test_pwa_manifest(self, client):
        """Test PWA manifest.json is served."""
        response = client.get('/pwa/manifest.json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['name'] == 'Verbrauchstracker'
        assert data['short_name'] == 'Verbrauch'
        assert data['start_url'] == '/pwa/'
        assert data['display'] == 'standalone'


class TestPWAStaticFiles:
    """Tests for PWA static file accessibility."""

    def test_pwa_css(self, client):
        """Test PWA CSS file is accessible."""
        response = client.get('/pwa/static/pwa.css')
        assert response.status_code == 200
        assert b'--sand-light' in response.data

    def test_pwa_js(self, client):
        """Test PWA JavaScript file is accessible."""
        response = client.get('/pwa/static/pwa.js')
        assert response.status_code == 200
        assert b'PWA' in response.data
        assert b'getApiKey' in response.data

    def test_pwa_icon_192(self, client):
        """Test PWA 192x192 icon is accessible."""
        response = client.get('/pwa/static/icons/icon-192.png')
        assert response.status_code == 200
        assert response.content_type == 'image/png'

    def test_pwa_icon_512(self, client):
        """Test PWA 512x512 icon is accessible."""
        response = client.get('/pwa/static/icons/icon-512.png')
        assert response.status_code == 200
        assert response.content_type == 'image/png'

    def test_pwa_apple_touch_icon(self, client):
        """Test Apple touch icon is accessible."""
        response = client.get('/pwa/static/icons/apple-touch-icon.png')
        assert response.status_code == 200
        assert response.content_type == 'image/png'


class TestPWATemplateContent:
    """Tests for PWA template content and meta tags."""

    def test_pwa_has_viewport_meta(self, client):
        """Test PWA pages have mobile viewport meta tag."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'viewport' in response.data
        assert b'viewport-fit=cover' in response.data

    def test_pwa_has_apple_meta_tags(self, client):
        """Test PWA pages have iOS-specific meta tags."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'apple-mobile-web-app-capable' in response.data
        assert b'apple-mobile-web-app-status-bar-style' in response.data
        assert b'apple-mobile-web-app-title' in response.data

    def test_pwa_has_manifest_link(self, client):
        """Test PWA pages link to manifest."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'manifest' in response.data

    def test_pwa_has_theme_color(self, client):
        """Test PWA pages have theme color meta tag."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'theme-color' in response.data
        assert b'#b8860b' in response.data

    def test_pwa_index_has_meters_container(self, client):
        """Test PWA index has meters container for dynamic content."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'meters-container' in response.data

    def test_pwa_setup_has_form(self, client):
        """Test PWA setup page has API key form."""
        response = client.get('/pwa/setup')
        assert response.status_code == 200
        assert b'setup-form' in response.data
        assert b'api-key' in response.data

    def test_pwa_add_reading_has_form(self, client, sample_meters):
        """Test PWA add reading page has reading form."""
        meter_id = sample_meters['Strom']
        response = client.get(f'/pwa/meter/{meter_id}/add')
        assert response.status_code == 200
        assert b'reading-form' in response.data
        assert b'reading-date' in response.data
        assert b'reading-value' in response.data

    def test_pwa_meter_passes_meter_id(self, client, sample_meters):
        """Test PWA meter detail page passes meter ID to JavaScript."""
        meter_id = sample_meters['Strom']
        response = client.get(f'/pwa/meter/{meter_id}')
        assert response.status_code == 200
        assert f'meterId = {meter_id}'.encode() in response.data


class TestPWANavigation:
    """Tests for PWA navigation elements."""

    def test_pwa_has_bottom_nav(self, client):
        """Test PWA pages have bottom navigation."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'pwa-nav' in response.data
        assert b'nav-item' in response.data

    def test_pwa_nav_has_home_link(self, client):
        """Test PWA navigation has home link."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'/pwa/' in response.data
        assert b'Start' in response.data

    def test_pwa_nav_has_setup_link(self, client):
        """Test PWA navigation has setup link."""
        response = client.get('/pwa/')
        assert response.status_code == 200
        assert b'/pwa/setup' in response.data
        assert b'Einstellung' in response.data

    def test_pwa_meter_detail_has_back_button(self, client, sample_meters):
        """Test PWA meter detail has back navigation."""
        meter_id = sample_meters['Strom']
        response = client.get(f'/pwa/meter/{meter_id}')
        assert response.status_code == 200
        assert b'header-back' in response.data

    def test_pwa_add_reading_has_back_button(self, client, sample_meters):
        """Test PWA add reading page has back navigation."""
        meter_id = sample_meters['Strom']
        response = client.get(f'/pwa/meter/{meter_id}/add')
        assert response.status_code == 200
        assert b'header-back' in response.data


class TestPWAManifest:
    """Tests for PWA manifest.json content."""

    def test_manifest_has_required_fields(self, client):
        """Test manifest has all required PWA fields."""
        response = client.get('/pwa/manifest.json')
        assert response.status_code == 200

        data = json.loads(response.data)
        required_fields = ['name', 'short_name', 'start_url', 'display', 'icons']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_manifest_has_icons(self, client):
        """Test manifest defines app icons."""
        response = client.get('/pwa/manifest.json')
        data = json.loads(response.data)

        assert 'icons' in data
        assert len(data['icons']) >= 2

        # Check for required sizes
        sizes = [icon['sizes'] for icon in data['icons']]
        assert '192x192' in sizes
        assert '512x512' in sizes

    def test_manifest_scope(self, client):
        """Test manifest has correct scope."""
        response = client.get('/pwa/manifest.json')
        data = json.loads(response.data)

        assert data.get('scope') == '/pwa/'

    def test_manifest_colors(self, client):
        """Test manifest has theme and background colors."""
        response = client.get('/pwa/manifest.json')
        data = json.loads(response.data)

        assert 'theme_color' in data
        assert 'background_color' in data
        assert data['theme_color'] == '#b8860b'
        assert data['background_color'] == '#f5e6c8'


class TestPWAJavaScript:
    """Tests for PWA JavaScript API client."""

    def test_js_has_api_base(self, client):
        """Test JavaScript defines API base URL."""
        response = client.get('/pwa/static/pwa.js')
        assert response.status_code == 200
        assert b"API_BASE: '/api/v1'" in response.data

    def test_js_has_storage_key(self, client):
        """Test JavaScript defines storage key for API key."""
        response = client.get('/pwa/static/pwa.js')
        assert response.status_code == 200
        assert b'STORAGE_KEY' in response.data

    def test_js_has_api_methods(self, client):
        """Test JavaScript has required API methods."""
        response = client.get('/pwa/static/pwa.js')
        assert response.status_code == 200

        required_methods = [
            b'getApiKey',
            b'setApiKey',
            b'clearApiKey',
            b'validateApiKey',
            b'getMeters',
            b'getMeter',
            b'getLatestReading',
            b'getMeterReadings',
            b'createReading'
        ]
        for method in required_methods:
            assert method in response.data, f"Missing method: {method.decode()}"

    def test_js_has_ui_helpers(self, client):
        """Test JavaScript has UI helper functions."""
        response = client.get('/pwa/static/pwa.js')
        assert response.status_code == 200

        ui_helpers = [
            b'showLoading',
            b'hideLoading',
            b'showError',
            b'formatNumber',
            b'formatDate',
            b'escapeHtml'
        ]
        for helper in ui_helpers:
            assert helper in response.data, f"Missing UI helper: {helper.decode()}"


class TestPWACSS:
    """Tests for PWA CSS styles."""

    def test_css_has_sand_theme_variables(self, client):
        """Test CSS defines sand theme color variables."""
        response = client.get('/pwa/static/pwa.css')
        assert response.status_code == 200

        variables = [
            b'--sand-light',
            b'--sand-medium',
            b'--sand-dark',
            b'--sand-accent'
        ]
        for var in variables:
            assert var in response.data, f"Missing CSS variable: {var.decode()}"

    def test_css_has_pwa_components(self, client):
        """Test CSS defines PWA component styles."""
        response = client.get('/pwa/static/pwa.css')
        assert response.status_code == 200

        components = [
            b'.pwa-header',
            b'.pwa-main',
            b'.pwa-nav',
            b'.meter-card',
            b'.reading-item'
        ]
        for component in components:
            assert component in response.data, f"Missing CSS component: {component.decode()}"

    def test_css_has_safe_area_insets(self, client):
        """Test CSS handles iOS safe area insets."""
        response = client.get('/pwa/static/pwa.css')
        assert response.status_code == 200
        assert b'safe-area-inset' in response.data


class TestPWACSRFExemption:
    """Tests that PWA blueprint is CSRF exempt (uses API key auth)."""

    def test_pwa_routes_no_csrf(self, client):
        """Test PWA routes work without CSRF token."""
        # All PWA routes should load without requiring CSRF
        routes = ['/pwa/', '/pwa/setup', '/pwa/manifest.json']
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200, f"Route {route} failed"
