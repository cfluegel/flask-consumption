"""Tests for SPA serving (catch-all) and route precedence.

The old Jinja web UI was replaced by the React SPA; its CRUD and
statistics behavior is covered by tests/test_web_api.py.
"""

import os

import pytest


DIST_INDEX = os.path.join(
    os.path.dirname(__file__), '..', 'frontend', 'dist', 'index.html'
)
frontend_built = os.path.isfile(DIST_INDEX)


class TestSpaServing:
    def test_root_serves_spa_or_hint(self, client):
        response = client.get('/')
        if frontend_built:
            assert response.status_code == 200
            assert b'<div id="root">' in response.data
        else:
            assert response.status_code == 503
            assert 'npm run build' in response.get_data(as_text=True)

    @pytest.mark.skipif(not frontend_built, reason='frontend/dist fehlt')
    def test_client_routes_serve_index_html(self, client):
        """Client-side routes get index.html via the catch-all."""
        for path in ('/kosten', '/tarife', '/vergleich', '/zaehler/1', '/einstellungen'):
            response = client.get(path)
            assert response.status_code == 200
            assert b'<div id="root">' in response.data

    @pytest.mark.skipif(not frontend_built, reason='frontend/dist fehlt')
    def test_static_assets_served_directly(self, client):
        index = client.get('/').get_data(as_text=True)
        # Vite injects hashed asset paths like /assets/index-abc123.js
        assert '/assets/' in index


class TestRoutePrecedence:
    """The SPA catch-all must not swallow API, PWA or admin routes."""

    def test_api_status_not_swallowed(self, client):
        response = client.get('/api/status')
        assert response.status_code == 200
        assert response.get_json() is not None

    def test_api_v1_requires_key(self, client):
        response = client.get('/api/v1/meters')
        assert response.status_code == 401

    def test_ui_api_not_swallowed(self, client):
        response = client.get('/ui-api/dashboard')
        assert response.status_code == 200
        assert response.get_json() == {'meters': []}

    def test_admin_not_swallowed(self, client):
        response = client.get('/admin/')
        assert response.status_code == 200
        assert b'Export' in response.data

    def test_pwa_not_swallowed(self, client):
        response = client.get('/pwa/')
        assert response.status_code == 200
