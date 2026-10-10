"""Tests for the admin blueprint (export/import, weather import)."""

import io
import json
from datetime import date

import pytest

from app.extensions import db
from app.models import Meter, MeterReading, Tariff, WeatherData
from app.services.weather_import import WeatherImportError, parse_and_store

def _build_dwd_content(rows):
    """Builds fixed-width DWD-style content; rows are lists of column values."""
    columns = ['STAT', 'JJJJMM', 'QN', 'TNN', 'TNM', 'TMM', 'TXM', 'TXX',
               'SOS', 'NMM', 'RSS', 'RSX', 'FMM', 'FXX']
    width = 8
    header = ' '.join(f'{c:>{width}}' for c in columns)
    separator = ' '.join('-' * width for _ in columns)
    lines = ['Monatswerte Hamburg-Fuhlsbuettel', header, separator]
    for row in rows:
        lines.append(' '.join(f'{str(v):>{width}}' for v in row))
    return '\n'.join(lines) + '\n'


SAMPLE_DWD_CONTENT = _build_dwd_content([
    [1975, '202601', 3, -7.2, -1.0, 2.1, 5.3, 11.0, 45.0, 6.1, 62.4, 14.2, 3.1, 24.5],
    [1975, '202602', 3, -5.0, 0.2, 3.4, 6.8, 13.1, 70.3, 5.8, 48.0, 10.1, 2.9, 22.0],
    [1975, '202603', 3, -999, -999, 7.5, -999, -999, -999, -999, -999, -999, -999, -999],
])


class TestAdminIndex:
    def test_index_page(self, client):
        response = client.get('/admin/')
        assert response.status_code == 200


class TestExport:
    def test_export_contains_all_sections(self, client, sample_readings, sample_tariffs):
        response = client.get('/admin/export')
        assert response.status_code == 200
        assert 'attachment' in response.headers['Content-Disposition']

        data = json.loads(response.data)
        assert set(data) == {'exported_at', 'meters', 'readings', 'tariffs'}
        assert len(data['meters']) == 3
        assert len(data['tariffs']) == 3

        meter = data['meters'][0]
        assert set(meter) == {'id', 'name', 'unit', 'serial_number', 'weather_overlay'}

        tariff = data['tariffs'][0]
        assert set(tariff) == {'meter_id', 'name', 'price_per_unit',
                               'base_price_monthly', 'valid_from'}

    def test_export_empty_db(self, client, app):
        response = client.get('/admin/export')
        data = json.loads(response.data)
        assert data['meters'] == []
        assert data['readings'] == []
        assert data['tariffs'] == []


class TestImport:
    def _upload(self, client, payload):
        return client.post(
            '/admin/import',
            data={'file': (io.BytesIO(json.dumps(payload).encode()), 'export.json')},
            content_type='multipart/form-data',
            follow_redirects=True,
        )

    def test_import_roundtrip(self, client, sample_readings, sample_tariffs, app):
        export = json.loads(client.get('/admin/export').data)

        reading_count = MeterReading.query.count()
        tariff_count = Tariff.query.count()

        # Wipe and re-import
        MeterReading.query.delete()
        Tariff.query.delete()
        Meter.query.delete()
        db.session.commit()

        response = self._upload(client, export)
        assert response.status_code == 200

        assert Meter.query.count() == 3
        assert MeterReading.query.count() == reading_count
        assert Tariff.query.count() == tariff_count

    def test_import_legacy_format_without_tariffs(self, client, app):
        """Old exports (no tariffs key, no weather_overlay) must still import."""
        payload = {
            'exported_at': '2025-01-01T00:00:00',
            'meters': [{'id': 1, 'name': 'Strom', 'unit': 'kWh', 'serial_number': 'S-1'}],
            'readings': [{'meter_id': 1, 'reading_date': '2025-01-01', 'value': 100.0}],
        }
        response = self._upload(client, payload)
        assert response.status_code == 200

        meter = Meter.query.filter_by(name='Strom').first()
        assert meter is not None
        assert meter.weather_overlay is False
        assert MeterReading.query.count() == 1
        assert Tariff.query.count() == 0

    def test_import_skips_duplicate_tariffs(self, client, sample_tariffs, app):
        export = json.loads(client.get('/admin/export').data)
        before = Tariff.query.count()

        self._upload(client, export)
        assert Tariff.query.count() == before

    def test_import_invalid_json(self, client, app):
        response = client.post(
            '/admin/import',
            data={'file': (io.BytesIO(b'kein json'), 'broken.json')},
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Meter.query.count() == 0

    def test_import_missing_keys(self, client, app):
        response = self._upload(client, {'meters': []})
        assert response.status_code == 200
        assert Meter.query.count() == 0

    def test_import_no_file(self, client, app):
        response = client.post('/admin/import', data={}, follow_redirects=True)
        assert response.status_code == 200


class TestWeatherImportParser:
    def test_parse_and_store_creates_records(self, app):
        result = parse_and_store(SAMPLE_DWD_CONTENT)
        assert result == {'created': 3, 'skipped': 0, 'deleted': 0}

        jan = WeatherData.query.filter_by(year_month='202601').first()
        assert jan.station_id == 1975
        assert jan.temp_avg == 2.1
        assert jan.temp_min == -7.2
        assert jan.precipitation_sum == 62.4

        # -999 markiert fehlende Werte -> NULL
        maerz = WeatherData.query.filter_by(year_month='202603').first()
        assert maerz.temp_avg == 7.5
        assert maerz.temp_min is None
        assert maerz.sunshine_hours is None

    def test_parse_and_store_skips_existing(self, app):
        parse_and_store(SAMPLE_DWD_CONTENT)
        result = parse_and_store(SAMPLE_DWD_CONTENT)
        assert result == {'created': 0, 'skipped': 3, 'deleted': 0}
        assert WeatherData.query.count() == 3

    def test_parse_and_store_replace(self, app):
        parse_and_store(SAMPLE_DWD_CONTENT)
        result = parse_and_store(SAMPLE_DWD_CONTENT, replace=True)
        assert result == {'created': 3, 'skipped': 0, 'deleted': 3}

    def test_parse_invalid_content_raises(self, app):
        with pytest.raises(WeatherImportError):
            parse_and_store('kein dwd format\nnur text\n')


class TestWeatherImportRoute:
    def test_import_weather_success(self, client, app, monkeypatch):
        monkeypatch.setattr('app.admin.routes.import_weather_data',
                            lambda **kwargs: {'created': 5, 'skipped': 2, 'deleted': 0})
        response = client.post('/admin/import-weather', follow_redirects=True)
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert '5 neue Monate' in text
        assert '2 bereits vorhanden' in text

    def test_import_weather_download_error(self, client, app, monkeypatch):
        def fail(**kwargs):
            raise WeatherImportError('Fehler beim Download: timeout')
        monkeypatch.setattr('app.admin.routes.import_weather_data', fail)
        response = client.post('/admin/import-weather', follow_redirects=True)
        assert response.status_code == 200
        assert 'fehlgeschlagen' in response.get_data(as_text=True)

    def test_index_shows_weather_status(self, client, app):
        parse_and_store(SAMPLE_DWD_CONTENT)
        response = client.get('/admin/')
        text = response.get_data(as_text=True)
        assert '3 Monate gespeichert' in text
        assert '03/2026' in text

    def test_index_without_weather_data(self, client, app):
        response = client.get('/admin/')
        assert 'Noch keine Wetterdaten' in response.get_data(as_text=True)
