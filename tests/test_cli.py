"""Tests for CLI commands."""

import pytest
import json
import os
from datetime import date

from app.extensions import db
from app.models import Meter, MeterReading, User


class TestSeedMetersCommand:
    """Tests for seed-meters CLI command."""

    def test_seed_meters_creates_meters(self, runner, app):
        """Test seed-meters creates the standard meters."""
        result = runner.invoke(args=['seed-meters'])
        assert result.exit_code == 0
        assert 'Strom' in result.output
        assert 'Gas' in result.output
        assert 'Wasser' in result.output

        with app.app_context():
            meters = Meter.query.all()
            assert len(meters) == 3

    def test_seed_meters_idempotent(self, runner, app):
        """Test seed-meters doesn't duplicate existing meters."""
        # First run
        runner.invoke(args=['seed-meters'])

        # Second run
        result = runner.invoke(args=['seed-meters'])
        assert 'existiert bereits' in result.output

        with app.app_context():
            meters = Meter.query.all()
            assert len(meters) == 3


class TestListMetersCommand:
    """Tests for list-meters CLI command."""

    def test_list_meters_empty(self, runner, app):
        """Test list-meters with no meters."""
        result = runner.invoke(args=['list-meters'])
        assert result.exit_code == 0
        assert 'Keine Zähler' in result.output

    def test_list_meters(self, runner, sample_meters, app):
        """Test list-meters shows all meters."""
        result = runner.invoke(args=['list-meters'])
        assert result.exit_code == 0
        assert 'Strom' in result.output
        assert 'Gas' in result.output
        assert 'Wasser' in result.output
        assert 'STROM-001' in result.output


class TestUpdateMeterSerialCommand:
    """Tests for update-meter-serial CLI command."""

    def test_update_serial(self, runner, sample_meters, app):
        """Test updating meter serial number."""
        with app.app_context():
            meter = Meter.query.filter_by(name='Strom').first()
            meter_id = meter.id

        result = runner.invoke(args=[
            'update-meter-serial',
            '--meter-id', str(meter_id),
            '--serial', 'NEW-SERIAL-123'
        ])

        assert result.exit_code == 0
        assert 'NEW-SERIAL-123' in result.output

        with app.app_context():
            meter = Meter.query.get(meter_id)
            assert meter.serial_number == 'NEW-SERIAL-123'

    def test_update_serial_not_found(self, runner, app):
        """Test error when meter doesn't exist."""
        result = runner.invoke(args=[
            'update-meter-serial',
            '--meter-id', '99999',
            '--serial', 'NEW-SERIAL'
        ])

        assert 'nicht gefunden' in result.output


class TestCreateUserCommand:
    """Tests for create-user CLI command."""

    def test_create_user(self, runner, app):
        """Test creating a new user."""
        result = runner.invoke(args=[
            'create-user',
            '--username', 'newuser',
            '--email', 'new@example.com',
            '--password', 'testpass123'
        ])

        assert result.exit_code == 0
        assert 'erfolgreich erstellt' in result.output

        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'new@example.com'
            assert user.check_password('testpass123')

    def test_create_user_duplicate_username(self, runner, sample_user, app):
        """Test error when username exists."""
        result = runner.invoke(args=[
            'create-user',
            '--username', 'testuser',  # Same as sample_user
            '--email', 'different@example.com',
            '--password', 'testpass123'
        ])

        assert 'existiert bereits' in result.output

    def test_create_user_duplicate_email(self, runner, sample_user, app):
        """Test error when email exists."""
        result = runner.invoke(args=[
            'create-user',
            '--username', 'differentuser',
            '--email', 'test@example.com',  # Same as sample_user
            '--password', 'testpass123'
        ])

        assert 'existiert bereits' in result.output


class TestDebugReadingsCommand:
    """Tests for debug-readings CLI command."""

    def test_debug_readings_all(self, runner, sample_readings, app):
        """Test debug-readings shows all meters."""
        result = runner.invoke(args=['debug-readings'])
        assert result.exit_code == 0
        assert 'Strom' in result.output
        assert 'Gas' in result.output
        assert 'Wasser' in result.output

    def test_debug_readings_single_meter(self, runner, sample_readings, app):
        """Test debug-readings for specific meter."""
        with app.app_context():
            meter = Meter.query.filter_by(name='Strom').first()
            meter_id = meter.id

        result = runner.invoke(args=['debug-readings', '--meter-id', str(meter_id)])
        assert result.exit_code == 0
        assert 'Strom' in result.output
        # Should not show other meters
        assert 'Gas' not in result.output

    def test_debug_readings_not_found(self, runner, app):
        """Test debug-readings with non-existent meter."""
        result = runner.invoke(args=['debug-readings', '--meter-id', '99999'])
        assert 'nicht gefunden' in result.output


class TestExportImportCommands:
    """Tests for export-data and import-data CLI commands."""

    def test_export_data(self, runner, sample_readings, app, tmp_path):
        """Test exporting data to JSON file."""
        export_file = tmp_path / 'export.json'

        result = runner.invoke(args=['export-data', str(export_file)])
        assert result.exit_code == 0
        assert 'Exportiert' in result.output

        # Verify file contents
        with open(export_file, 'r') as f:
            data = json.load(f)

        assert 'meters' in data
        assert 'readings' in data
        assert len(data['meters']) == 3
        assert len(data['readings']) > 0

    def test_import_data(self, runner, app, tmp_path):
        """Test importing data from JSON file."""
        import_file = tmp_path / 'import.json'
        data = {
            'exported_at': '2025-01-01T00:00:00',
            'meters': [
                {'id': 1, 'name': 'ImportedMeter', 'unit': 'kWh', 'serial_number': 'IMP-001'}
            ],
            'readings': [
                {'meter_id': 1, 'reading_date': '2025-01-15', 'value': 1000.0}
            ]
        }
        with open(import_file, 'w') as f:
            json.dump(data, f)

        result = runner.invoke(args=['import-data', str(import_file)])
        assert result.exit_code == 0
        assert 'Import abgeschlossen' in result.output

        with app.app_context():
            meter = Meter.query.filter_by(name='ImportedMeter').first()
            assert meter is not None
            reading = MeterReading.query.filter_by(meter_id=meter.id).first()
            assert reading is not None
            assert reading.value == 1000.0

    def test_import_data_skips_duplicates(self, runner, sample_meters, app, tmp_path):
        """Test import skips existing meters."""
        import_file = tmp_path / 'import.json'
        data = {
            'exported_at': '2025-01-01T00:00:00',
            'meters': [
                {'id': 1, 'name': 'Strom', 'unit': 'kWh', 'serial_number': 'NEW-001'}
            ],
            'readings': []
        }
        with open(import_file, 'w') as f:
            json.dump(data, f)

        result = runner.invoke(args=['import-data', str(import_file)])
        assert result.exit_code == 0
        assert 'übersprungen' in result.output

        # Original serial number should be preserved
        with app.app_context():
            meter = Meter.query.filter_by(name='Strom').first()
            assert meter.serial_number == 'STROM-001'

    def test_export_import_roundtrip(self, runner, sample_readings, app, tmp_path):
        """Test data survives export/import roundtrip."""
        export_file = tmp_path / 'roundtrip.json'

        # Count original data
        with app.app_context():
            original_meter_count = Meter.query.count()
            original_reading_count = MeterReading.query.count()

        # Export
        runner.invoke(args=['export-data', str(export_file)])

        # Clear database
        with app.app_context():
            MeterReading.query.delete()
            Meter.query.delete()
            db.session.commit()

        # Import with replace flag
        result = runner.invoke(args=['import-data', str(export_file), '--replace'], input='y\n')

        # Verify counts match
        with app.app_context():
            assert Meter.query.count() == original_meter_count
            assert MeterReading.query.count() == original_reading_count
