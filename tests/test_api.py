"""Tests for API endpoints."""

import pytest
from datetime import date, timedelta

from app.extensions import db
from app.models import Meter, MeterReading


class TestApiStatus:
    """Tests for /api/status endpoint."""

    def test_status_endpoint(self, client):
        """Test status endpoint returns ok."""
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'

    def test_status_no_auth_required(self, client):
        """Test status endpoint doesn't require authentication."""
        response = client.get('/api/status')
        assert response.status_code == 200


class TestApiMeters:
    """Tests for /api/meters endpoint."""

    def test_list_meters_unauthorized(self, client):
        """Test meters endpoint requires API key."""
        response = client.get('/api/meters')
        assert response.status_code == 401

    def test_list_meters_empty(self, client, api_headers, app):
        """Test listing meters when none exist."""
        response = client.get('/api/meters', headers=api_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_meters(self, client, api_headers, sample_meters):
        """Test listing all meters."""
        response = client.get('/api/meters', headers=api_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

        names = [m['name'] for m in data]
        assert 'Strom' in names
        assert 'Gas' in names
        assert 'Wasser' in names

    def test_list_meters_fields(self, client, api_headers, sample_meters):
        """Test meter response contains required fields."""
        response = client.get('/api/meters', headers=api_headers)
        data = response.get_json()

        for meter in data:
            assert 'id' in meter
            assert 'name' in meter
            assert 'unit' in meter
            assert 'serial_number' in meter


class TestApiReadings:
    """Tests for /api/meters/<id>/readings endpoint."""

    def test_get_readings_unauthorized(self, client, sample_meters, app):
        """Test readings endpoint requires API key."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/meters/{meter.id}/readings')
            assert response.status_code == 401

    def test_get_readings_empty(self, client, api_headers, sample_meters, app):
        """Test getting readings for meter with no readings."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/meters/{meter.id}/readings', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert 'meter' in data
            assert 'readings' in data
            assert data['readings'] == []

    def test_get_readings(self, client, api_headers, sample_readings, app):
        """Test getting readings for a meter."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/meters/{meter.id}/readings', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()

            assert data['meter']['id'] == meter.id
            assert data['meter']['name'] == meter.name
            assert len(data['readings']) > 0

    def test_get_readings_not_found(self, client, api_headers, app):
        """Test 404 for non-existent meter."""
        response = client.get('/api/meters/99999/readings', headers=api_headers)
        assert response.status_code == 404


class TestApiCreateReading:
    """Tests for POST /api/readings endpoint."""

    def test_create_reading_unauthorized(self, client, sample_meters):
        """Test creating reading requires API key."""
        response = client.post('/api/readings', json={
            'meter_id': 1,
            'reading_date': date.today().isoformat(),
            'value': 1000
        })
        assert response.status_code == 401

    def test_create_reading(self, client, api_headers, sample_meters, app):
        """Test creating a new reading via API."""
        with app.app_context():
            meter = Meter.query.first()
            reading_date = (date.today() + timedelta(days=50)).isoformat()

            response = client.post('/api/readings', headers=api_headers, json={
                'meter_id': meter.id,
                'reading_date': reading_date,
                'value': 99999.99
            })

            assert response.status_code == 201
            data = response.get_json()
            assert data['meter_id'] == meter.id
            assert data['value'] == 99999.99
            assert 'id' in data

    def test_create_reading_empty_json(self, client, api_headers):
        """Test error when empty JSON object provided."""
        response = client.post('/api/readings', headers=api_headers, json={})
        assert response.status_code == 400
        # Empty dict is falsy in Python, so API returns "No JSON data"
        assert 'No JSON data' in response.get_json()['error']

    def test_create_reading_missing_field(self, client, api_headers, sample_meters):
        """Test error when required field missing."""
        response = client.post('/api/readings', headers=api_headers, json={
            'meter_id': 1,
            'value': 1000
            # missing reading_date
        })
        assert response.status_code == 400
        assert 'Missing required field' in response.get_json()['error']

    def test_create_reading_invalid_meter(self, client, api_headers):
        """Test error when meter doesn't exist."""
        response = client.post('/api/readings', headers=api_headers, json={
            'meter_id': 99999,
            'reading_date': date.today().isoformat(),
            'value': 1000
        })
        assert response.status_code == 404
        assert 'Meter not found' in response.get_json()['error']

    def test_create_reading_invalid_date(self, client, api_headers, sample_meters, app):
        """Test error with invalid date format."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.post('/api/readings', headers=api_headers, json={
                'meter_id': meter.id,
                'reading_date': '31-01-2025',  # Wrong format
                'value': 1000
            })
            assert response.status_code == 400
            assert 'Invalid date format' in response.get_json()['error']


class TestApiV1Meters:
    """Tests for /api/v1/meters endpoints."""

    def test_list_meters(self, client, api_headers, sample_meters):
        """Test listing all meters via v1 API."""
        response = client.get('/api/v1/meters', headers=api_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

    def test_get_meter(self, client, api_headers, sample_meters, app):
        """Test getting single meter."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/v1/meters/{meter.id}', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert data['id'] == meter.id
            assert data['name'] == meter.name

    def test_get_meter_not_found(self, client, api_headers):
        """Test 404 for non-existent meter."""
        response = client.get('/api/v1/meters/99999', headers=api_headers)
        assert response.status_code == 404


class TestApiV1LatestReading:
    """Tests for /api/v1/meters/<id>/latest endpoint."""

    def test_get_latest_reading(self, client, api_headers, sample_readings, app):
        """Test getting latest reading for a meter."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/v1/meters/{meter.id}/latest', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()

            assert 'meter' in data
            assert 'reading' in data
            assert data['meter']['id'] == meter.id

            if data['reading']:
                assert 'id' in data['reading']
                assert 'date' in data['reading']
                assert 'value' in data['reading']

    def test_get_latest_reading_empty(self, client, api_headers, sample_meters, app):
        """Test latest reading when no readings exist."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/v1/meters/{meter.id}/latest', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert data['reading'] is None


class TestApiV1Readings:
    """Tests for /api/v1/meters/<id>/readings endpoint."""

    def test_get_readings(self, client, api_headers, sample_readings, app):
        """Test getting readings with default limit."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/v1/meters/{meter.id}/readings', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()

            assert 'meter' in data
            assert 'readings' in data
            # Default limit is 10
            assert len(data['readings']) <= 10

    def test_get_readings_with_limit(self, client, api_headers, sample_readings, app):
        """Test getting readings with custom limit."""
        with app.app_context():
            meter = Meter.query.first()
            response = client.get(f'/api/v1/meters/{meter.id}/readings?limit=3', headers=api_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['readings']) <= 3


class TestApiV1CreateReading:
    """Tests for POST /api/v1/readings endpoint."""

    def test_create_reading(self, client, api_headers, sample_meters, app):
        """Test creating reading via v1 API."""
        with app.app_context():
            meter = Meter.query.first()
            reading_date = (date.today() + timedelta(days=100)).isoformat()

            response = client.post('/api/v1/readings', headers=api_headers, json={
                'meter_id': meter.id,
                'reading_date': reading_date,
                'value': 55555.55
            })

            assert response.status_code == 201
            data = response.get_json()
            assert data['meter_id'] == meter.id
            assert data['value'] == 55555.55

    def test_create_reading_validates(self, client, api_headers):
        """Test validation for v1 readings endpoint."""
        # Missing meter_id
        response = client.post('/api/v1/readings', headers=api_headers, json={
            'reading_date': date.today().isoformat(),
            'value': 1000
        })
        assert response.status_code == 400


class TestApiKeyValidation:
    """Tests for API key authentication."""

    def test_invalid_api_key(self, client, sample_meters):
        """Test request with wrong API key is rejected."""
        response = client.get('/api/meters', headers={'X-API-Key': 'wrong-key'})
        assert response.status_code == 401

    def test_missing_api_key(self, client, sample_meters):
        """Test request without API key is rejected."""
        response = client.get('/api/meters')
        assert response.status_code == 401

    def test_valid_api_key(self, client, api_headers, sample_meters):
        """Test request with correct API key succeeds."""
        response = client.get('/api/meters', headers=api_headers)
        assert response.status_code == 200
