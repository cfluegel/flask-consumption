"""Pytest fixtures for flask-consumption tests."""

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app import create_app
from app.extensions import db
from app.models import Meter, MeterReading, Tariff, User, WeatherData


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('config.TestingConfig')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def sample_meters(app):
    """Create sample meters for testing."""
    with app.app_context():
        meters = [
            Meter(name='Strom', unit='kWh', serial_number='STROM-001'),
            Meter(name='Gas', unit='m³', serial_number='GAS-001'),
            Meter(name='Wasser', unit='Liter', serial_number='WASSER-001'),
        ]
        for m in meters:
            db.session.add(m)
        db.session.commit()

        # Return IDs for reference
        return {m.name: m.id for m in meters}


@pytest.fixture
def sample_readings(app, sample_meters):
    """Create sample readings spanning several months."""
    with app.app_context():
        strom_id = sample_meters['Strom']
        gas_id = sample_meters['Gas']
        wasser_id = sample_meters['Wasser']

        today = date.today()

        # Create readings for the past 6 months
        readings = []

        # Strom readings (monthly increases of ~300 kWh)
        base_strom = 10000.0
        for i in range(6, -1, -1):
            reading_date = today - relativedelta(months=i)
            reading_date = reading_date.replace(day=1)
            value = base_strom + (6 - i) * 300
            readings.append(MeterReading(
                meter_id=strom_id,
                reading_date=reading_date,
                value=value
            ))

        # Gas readings (monthly increases of ~50 m³)
        base_gas = 5000.0
        for i in range(6, -1, -1):
            reading_date = today - relativedelta(months=i)
            reading_date = reading_date.replace(day=1)
            value = base_gas + (6 - i) * 50
            readings.append(MeterReading(
                meter_id=gas_id,
                reading_date=reading_date,
                value=value
            ))

        # Wasser readings (monthly increases of ~5000 Liter)
        base_wasser = 100000.0
        for i in range(6, -1, -1):
            reading_date = today - relativedelta(months=i)
            reading_date = reading_date.replace(day=1)
            value = base_wasser + (6 - i) * 5000
            readings.append(MeterReading(
                meter_id=wasser_id,
                reading_date=reading_date,
                value=value
            ))

        for r in readings:
            db.session.add(r)
        db.session.commit()

        return sample_meters


@pytest.fixture
def sample_tariffs(app, sample_meters):
    """Create tariffs: Strom has a price change 3 months ago, Gas one tariff."""
    with app.app_context():
        today = date.today()
        old_start = (today - relativedelta(months=24)).replace(day=1)
        new_start = (today - relativedelta(months=3)).replace(day=1)

        tariffs = [
            Tariff(meter_id=sample_meters['Strom'], name='Strom Alt',
                   price_per_unit=0.30, base_price_monthly=10.0,
                   valid_from=old_start),
            Tariff(meter_id=sample_meters['Strom'], name='Strom Neu',
                   price_per_unit=0.35, base_price_monthly=12.0,
                   valid_from=new_start),
            Tariff(meter_id=sample_meters['Gas'], name='Gas Basis',
                   price_per_unit=1.10, base_price_monthly=15.0,
                   valid_from=old_start),
        ]
        for t in tariffs:
            db.session.add(t)
        db.session.commit()

        return sample_meters


@pytest.fixture
def sample_weather(app):
    """Create weather data for the past 6 months (one station)."""
    with app.app_context():
        today = date.today()
        temps = [2.0, 4.5, 8.0, 12.5, 16.0, 18.5, 20.0]
        for i in range(6, -1, -1):
            month_date = today - relativedelta(months=i)
            db.session.add(WeatherData(
                station_id=1975,
                year_month=f"{month_date.year}{month_date.month:02d}",
                temp_min=temps[6 - i] - 8,
                temp_avg=temps[6 - i],
                temp_max=temps[6 - i] + 10,
            ))
        db.session.commit()


@pytest.fixture
def sample_user(app):
    """Create a sample user for authentication tests."""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        return {'id': user.id, 'username': 'testuser', 'password': 'testpassword123'}


@pytest.fixture
def api_headers():
    """Return headers for API authentication."""
    return {'X-API-Key': 'default-api-key'}
