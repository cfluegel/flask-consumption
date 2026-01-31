"""Tests for main blueprint web routes."""

import pytest
from datetime import date

from app.extensions import db
from app.models import Meter, MeterReading


class TestIndexRoute:
    """Tests for index page."""

    def test_index_empty(self, client, app):
        """Test index page with no meters."""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_with_meters(self, client, sample_meters):
        """Test index page displays meters."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Strom' in response.data
        assert b'Gas' in response.data
        assert b'Wasser' in response.data

    def test_index_with_readings(self, client, sample_readings):
        """Test index page shows consumption data."""
        response = client.get('/')
        assert response.status_code == 200
        # Should show meters with data
        assert b'Strom' in response.data
        assert b'kWh' in response.data


class TestGraphsRoute:
    """Tests for graphs page."""

    def test_graphs_page(self, client, sample_meters):
        """Test graphs page loads."""
        response = client.get('/graphs')
        assert response.status_code == 200

    def test_graphs_with_data(self, client, sample_readings):
        """Test graphs page with consumption data."""
        response = client.get('/graphs')
        assert response.status_code == 200
        assert b'Strom' in response.data
        assert b'chart-' in response.data


class TestGraphDetailRoute:
    """Tests for individual graph detail page."""

    def test_graph_detail_page(self, client, sample_readings, app):
        """Test graph detail page loads."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/graph/{meter.id}')
            assert response.status_code == 200
            assert meter.name.encode() in response.data

    def test_graph_detail_not_found(self, client, app):
        """Test 404 for non-existent meter."""
        response = client.get('/graph/99999')
        assert response.status_code == 404


class TestMeterDetailRoute:
    """Tests for meter detail page."""

    def test_meter_detail(self, client, sample_readings, app):
        """Test meter detail page shows readings."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/meter/{meter.id}')
            assert response.status_code == 200
            assert meter.name.encode() in response.data

    def test_meter_detail_not_found(self, client, app):
        """Test 404 for non-existent meter."""
        response = client.get('/meter/99999')
        assert response.status_code == 404


class TestReadingCRUD:
    """Tests for reading create, edit, delete."""

    def test_new_reading_get(self, client, sample_meters):
        """Test new reading form displays."""
        response = client.get('/reading/new')
        assert response.status_code == 200
        assert b'Strom' in response.data
        assert b'Gas' in response.data

    def test_new_reading_get_with_meter_id(self, client, sample_meters, app):
        """Test new reading form pre-fills meter."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/reading/new?meter_id={meter.id}')
            assert response.status_code == 200

    def test_new_reading_post(self, client, sample_meters, app):
        """Test creating a new reading."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.post('/reading/new', data={
                'meter_id': meter.id,
                'reading_date': date.today().isoformat(),
                'value': '12345.67'
            }, follow_redirects=True)

            assert response.status_code == 200
            # Should redirect to meter detail
            assert b'erfolgreich gespeichert' in response.data or meter.name.encode() in response.data

            # Verify reading was created
            reading = MeterReading.query.filter_by(
                meter_id=meter.id,
                reading_date=date.today()
            ).first()
            assert reading is not None
            assert reading.value == 12345.67

    def test_edit_reading_get(self, client, sample_readings, app):
        """Test edit reading form displays."""
        with app.app_context():
            reading = MeterReading.query.first()
            response = client.get(f'/reading/{reading.id}/edit')
            assert response.status_code == 200

    def test_edit_reading_post(self, client, sample_readings, app):
        """Test updating a reading."""
        with app.app_context():
            reading = MeterReading.query.first()
            original_value = reading.value
            new_value = original_value + 100

            response = client.post(f'/reading/{reading.id}/edit', data={
                'meter_id': reading.meter_id,
                'reading_date': reading.reading_date.isoformat(),
                'value': str(new_value)
            }, follow_redirects=True)

            assert response.status_code == 200

            # Reload and verify
            db.session.refresh(reading)
            assert reading.value == new_value

    def test_edit_reading_not_found(self, client, app):
        """Test 404 for editing non-existent reading."""
        response = client.get('/reading/99999/edit')
        assert response.status_code == 404

    def test_delete_reading(self, client, sample_readings, app):
        """Test deleting a reading."""
        with app.app_context():
            reading = MeterReading.query.first()
            reading_id = reading.id
            meter_id = reading.meter_id

            response = client.post(f'/reading/{reading_id}/delete', follow_redirects=True)

            assert response.status_code == 200

            # Verify reading was deleted
            deleted = MeterReading.query.get(reading_id)
            assert deleted is None

    def test_delete_reading_not_found(self, client, app):
        """Test 404 for deleting non-existent reading."""
        response = client.post('/reading/99999/delete')
        assert response.status_code == 404


class TestAuthentication:
    """Tests for login/logout."""

    def test_login_page(self, client):
        """Test login page displays."""
        response = client.get('/login')
        assert response.status_code == 200

    def test_login_success(self, client, sample_user):
        """Test successful login."""
        response = client.post('/login', data={
            'username': sample_user['username'],
            'password': sample_user['password']
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Erfolgreich angemeldet' in response.data or b'Strom' in response.data

    def test_login_invalid_credentials(self, client, sample_user):
        """Test login with wrong password."""
        response = client.post('/login', data={
            'username': sample_user['username'],
            'password': 'wrongpassword'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Ung' in response.data  # "Ungültige Anmeldedaten"

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post('/login', data={
            'username': 'nobody',
            'password': 'somepassword'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Ung' in response.data  # "Ungültige Anmeldedaten"

    def test_logout(self, authenticated_client):
        """Test logout."""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'abgemeldet' in response.data

    def test_already_authenticated_redirect(self, authenticated_client):
        """Test that logged-in user is redirected from login page."""
        response = authenticated_client.get('/login', follow_redirects=False)
        assert response.status_code == 302
        assert '/' in response.location
