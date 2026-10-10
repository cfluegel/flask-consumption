"""Tests for the UI API blueprint (/ui-api) used by the React frontend."""

from datetime import date

from dateutil.relativedelta import relativedelta

from app.extensions import db
from app.models import MeterReading, Tariff


class TestDashboard:
    def test_dashboard_structure(self, client, sample_readings, sample_tariffs):
        response = client.get('/ui-api/dashboard')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['meters']) == 3

        strom = next(m for m in data['meters'] if m['name'] == 'Strom')
        assert strom['last_reading'] is not None
        assert strom['stats']['avg_3month'] is not None
        assert strom['stats']['yearly_cost'] is not None
        assert strom['current_tariff']['name'] == 'Strom Neu'

        wasser = next(m for m in data['meters'] if m['name'] == 'Wasser')
        assert wasser['current_tariff'] is None
        assert wasser['stats']['yearly_cost'] is None

    def test_dashboard_empty_db(self, client, app):
        response = client.get('/ui-api/dashboard')
        assert response.status_code == 200
        assert response.get_json() == {'meters': []}

    def test_no_api_key_required(self, client, sample_meters):
        """UI API must work without X-API-Key (same-origin trust)."""
        assert client.get('/ui-api/dashboard').status_code == 200


class TestConsumption:
    def test_consumption_series(self, client, sample_readings):
        meter_id = sample_readings['Strom']
        response = client.get(f'/ui-api/meters/{meter_id}/consumption?months=6')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['series']) == 6
        entry = data['series'][0]
        assert set(entry) == {'year', 'month', 'label', 'consumption'}
        # oldest first
        first, last = data['series'][0], data['series'][-1]
        assert (first['year'], first['month']) < (last['year'], last['month'])

    def test_consumption_unknown_meter(self, client, app):
        assert client.get('/ui-api/meters/999/consumption').status_code == 404


class TestReadings:
    def test_list_readings_paginated(self, client, sample_readings):
        meter_id = sample_readings['Strom']
        response = client.get(f'/ui-api/meters/{meter_id}/readings?limit=3&offset=0')
        data = response.get_json()
        assert data['total'] == 7
        assert len(data['readings']) == 3
        # newest first
        assert data['readings'][0]['reading_date'] > data['readings'][-1]['reading_date']

    def test_create_reading(self, client, sample_meters, app):
        response = client.post('/ui-api/readings', json={
            'meter_id': sample_meters['Strom'],
            'reading_date': '2025-06-15',
            'value': 1234.5,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['value'] == 1234.5
        assert data['reading_date'] == '2025-06-15'

    def test_create_reading_duplicate_date_409(self, client, sample_meters, app):
        payload = {'meter_id': sample_meters['Gas'],
                   'reading_date': '2025-06-15', 'value': 100.0}
        assert client.post('/ui-api/readings', json=payload).status_code == 201
        response = client.post('/ui-api/readings', json=payload)
        assert response.status_code == 409
        assert 'error' in response.get_json()

    def test_create_reading_validation(self, client, sample_meters, app):
        meter_id = sample_meters['Strom']
        assert client.post('/ui-api/readings', json={
            'meter_id': 999, 'reading_date': '2025-06-15', 'value': 1.0}).status_code == 404
        assert client.post('/ui-api/readings', json={
            'meter_id': meter_id, 'reading_date': 'kein-datum', 'value': 1.0}).status_code == 400
        assert client.post('/ui-api/readings', json={
            'meter_id': meter_id, 'reading_date': '2025-06-15', 'value': 'abc'}).status_code == 400

    def test_update_reading(self, client, sample_readings, app):
        reading = MeterReading.query.filter_by(meter_id=sample_readings['Strom']).first()
        response = client.put(f'/ui-api/readings/{reading.id}', json={'value': 99999.0})
        assert response.status_code == 200
        assert response.get_json()['value'] == 99999.0

    def test_update_reading_duplicate_date_409(self, client, sample_readings, app):
        readings = (MeterReading.query
                    .filter_by(meter_id=sample_readings['Strom'])
                    .order_by(MeterReading.reading_date.asc())
                    .limit(2).all())
        response = client.put(f'/ui-api/readings/{readings[0].id}',
                              json={'reading_date': readings[1].reading_date.isoformat()})
        assert response.status_code == 409

    def test_delete_reading(self, client, sample_readings, app):
        reading = MeterReading.query.filter_by(meter_id=sample_readings['Strom']).first()
        assert client.delete(f'/ui-api/readings/{reading.id}').status_code == 204
        assert db.session.get(MeterReading, reading.id) is None

    def test_delete_unknown_reading(self, client, app):
        assert client.delete('/ui-api/readings/999').status_code == 404


class TestTariffs:
    def test_list_tariffs(self, client, sample_tariffs):
        meter_id = sample_tariffs['Strom']
        response = client.get(f'/ui-api/meters/{meter_id}/tariffs')
        data = response.get_json()
        assert len(data) == 2
        # newest valid_from first
        assert data[0]['valid_from'] > data[1]['valid_from']

    def test_create_tariff(self, client, sample_meters, app):
        meter_id = sample_meters['Wasser']
        response = client.post(f'/ui-api/meters/{meter_id}/tariffs', json={
            'name': 'Wasser 2026',
            'price_per_unit': 0.002,
            'base_price_monthly': 8.5,
            'valid_from': '2026-01-01',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['price_per_unit'] == 0.002
        assert data['valid_from'] == '2026-01-01'

    def test_create_tariff_duplicate_valid_from_409(self, client, sample_tariffs, app):
        meter_id = sample_tariffs['Strom']
        existing = Tariff.query.filter_by(meter_id=meter_id).first()
        response = client.post(f'/ui-api/meters/{meter_id}/tariffs', json={
            'price_per_unit': 0.5,
            'valid_from': existing.valid_from.isoformat(),
        })
        assert response.status_code == 409

    def test_create_tariff_validation(self, client, sample_meters, app):
        meter_id = sample_meters['Strom']
        assert client.post(f'/ui-api/meters/{meter_id}/tariffs', json={
            'price_per_unit': -1, 'valid_from': '2026-01-01'}).status_code == 400
        assert client.post(f'/ui-api/meters/{meter_id}/tariffs', json={
            'price_per_unit': 0.3, 'valid_from': 'ungueltig'}).status_code == 400

    def test_update_tariff(self, client, sample_tariffs, app):
        tariff = Tariff.query.filter_by(meter_id=sample_tariffs['Gas']).first()
        response = client.put(f'/ui-api/tariffs/{tariff.id}',
                              json={'price_per_unit': 1.25})
        assert response.status_code == 200
        assert response.get_json()['price_per_unit'] == 1.25

    def test_delete_tariff(self, client, sample_tariffs, app):
        tariff = Tariff.query.filter_by(meter_id=sample_tariffs['Gas']).first()
        assert client.delete(f'/ui-api/tariffs/{tariff.id}').status_code == 204
        assert db.session.get(Tariff, tariff.id) is None


class TestCosts:
    def test_costs_series(self, client, sample_readings, sample_tariffs):
        meter_id = sample_tariffs['Strom']
        response = client.get(f'/ui-api/meters/{meter_id}/costs?months=6')
        data = response.get_json()
        assert len(data['series']) == 6
        assert data['yearly_cost'] is not None
        assert data['forecast'] is not None

        # Tarifwechsel vor 3 Monaten: ältester Monat alter Preis, neuester neuer Preis
        with_tariff = [e for e in data['series'] if e['price_per_unit'] is not None]
        assert with_tariff[0]['price_per_unit'] == 0.30
        assert with_tariff[-1]['price_per_unit'] == 0.35

    def test_costs_without_tariff(self, client, sample_readings):
        meter_id = sample_readings['Wasser']
        data = client.get(f'/ui-api/meters/{meter_id}/costs?months=3').get_json()
        assert all(e['cost'] is None for e in data['series'])
        assert data['yearly_cost'] is None


class TestYearComparison:
    def test_year_comparison_structure(self, client, sample_readings, sample_tariffs):
        meter_id = sample_tariffs['Strom']
        today = date.today()
        response = client.get(f'/ui-api/meters/{meter_id}/year-comparison?year={today.year}')
        data = response.get_json()

        assert data['year'] == today.year
        assert data['previous_year'] == today.year - 1
        assert len(data['months']) == 12

        current_month_entry = data['months'][today.month - 1]
        assert current_month_entry['is_current_month'] is True
        assert sum(1 for m in data['months'] if m['is_current_month']) == 1

    def test_deviation_null_without_previous_year(self, client, sample_readings):
        """Sample data spans only ~7 months, so most previous-year values are missing."""
        meter_id = sample_readings['Strom']
        today = date.today()
        data = client.get(f'/ui-api/meters/{meter_id}/year-comparison?year={today.year}').get_json()
        months_without_prev = [m for m in data['months']
                               if m['previous']['consumption'] is None]
        assert all(m['deviation_pct'] is None for m in months_without_prev)

    def test_deviation_with_both_years(self, client, sample_meters, app):
        """Two full years of linear readings -> deviation computable."""
        meter_id = sample_meters['Strom']
        start = date(date.today().year - 3, 12, 1)
        for i in range(31):
            db.session.add(MeterReading(
                meter_id=meter_id,
                reading_date=start + relativedelta(months=i),
                value=1000.0 + i * 100,
            ))
        db.session.commit()

        year = date.today().year - 1
        data = client.get(f'/ui-api/meters/{meter_id}/year-comparison?year={year}').get_json()
        june = data['months'][5]
        assert june['current']['consumption'] is not None
        assert june['previous']['consumption'] is not None
        assert june['deviation_pct'] is not None
        assert data['totals']['deviation_pct'] is not None


class TestWeather:
    def test_weather_series_with_data(self, client, sample_readings, sample_weather):
        meter_id = sample_readings['Gas']
        response = client.get(f'/ui-api/meters/{meter_id}/weather?months=6')
        data = response.get_json()
        assert len(data['series']) == 6

        entry = data['series'][0]
        assert set(entry) == {'year', 'month', 'label', 'consumption', 'temp_min',
                              'temp_avg', 'temp_max', 'hgt', 'consumption_per_hgt'}
        # Fixture liefert Temperaturen für alle Monate
        assert entry['temp_avg'] is not None
        assert entry['hgt'] is not None

    def test_weather_series_without_weather_data(self, client, sample_readings):
        meter_id = sample_readings['Gas']
        data = client.get(f'/ui-api/meters/{meter_id}/weather?months=3').get_json()
        assert len(data['series']) == 3
        assert all(e['temp_avg'] is None and e['hgt'] is None for e in data['series'])


class TestMeterPatch:
    def test_patch_weather_overlay(self, client, sample_meters, app):
        meter_id = sample_meters['Gas']
        response = client.patch(f'/ui-api/meters/{meter_id}',
                                json={'weather_overlay': True})
        assert response.status_code == 200
        assert response.get_json()['weather_overlay'] is True

    def test_patch_validation(self, client, sample_meters, app):
        meter_id = sample_meters['Gas']
        assert client.patch(f'/ui-api/meters/{meter_id}',
                            json={'weather_overlay': 'ja'}).status_code == 400
        assert client.patch(f'/ui-api/meters/{meter_id}',
                            json={'name': ''}).status_code == 400

    def test_patch_duplicate_name_409(self, client, sample_meters, app):
        meter_id = sample_meters['Gas']
        assert client.patch(f'/ui-api/meters/{meter_id}',
                            json={'name': 'Strom'}).status_code == 409
