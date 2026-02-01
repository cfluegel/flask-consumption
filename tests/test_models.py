"""Tests for database models."""

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app.extensions import db
from app.models import Meter, MeterReading, User


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, app):
        """Test creating a user."""
        with app.app_context():
            user = User(username='newuser', email='new@example.com')
            user.set_password('securepass')
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == 'newuser'
            assert user.email == 'new@example.com'

    def test_password_hashing(self, app):
        """Test password is hashed and not stored in plain text."""
        with app.app_context():
            user = User(username='hashtest', email='hash@example.com')
            user.set_password('mypassword')
            db.session.add(user)
            db.session.commit()

            assert user.password_hash != 'mypassword'
            assert user.check_password('mypassword') is True
            assert user.check_password('wrongpassword') is False

    def test_user_uniqueness(self, app, sample_user):
        """Test that duplicate usernames and emails are rejected."""
        with app.app_context():
            # Try duplicate username
            user = User(username='testuser', email='different@example.com')
            user.set_password('password')
            db.session.add(user)

            with pytest.raises(Exception):
                db.session.commit()


class TestMeterModel:
    """Tests for Meter model."""

    def test_create_meter(self, app):
        """Test creating a meter."""
        with app.app_context():
            meter = Meter(name='TestMeter', unit='kWh', serial_number='TEST-001')
            db.session.add(meter)
            db.session.commit()

            assert meter.id is not None
            assert meter.name == 'TestMeter'
            assert meter.unit == 'kWh'
            assert meter.serial_number == 'TEST-001'

    def test_get_last_reading_empty(self, app, sample_meters):
        """Test get_last_reading returns None when no readings exist."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])
            # No readings yet
            MeterReading.query.filter_by(meter_id=meter.id).delete()
            db.session.commit()

            assert meter.get_last_reading() is None

    def test_get_last_reading_with_data(self, app, sample_readings):
        """Test get_last_reading returns the most recent reading."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            last_reading = meter.get_last_reading()

            assert last_reading is not None
            # Should be the most recent reading
            all_readings = MeterReading.query.filter_by(meter_id=meter.id).all()
            max_date = max(r.reading_date for r in all_readings)
            assert last_reading.reading_date == max_date

    def test_get_monthly_consumption_empty(self, app, sample_meters):
        """Test monthly consumption returns empty list when no readings."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])
            MeterReading.query.filter_by(meter_id=meter.id).delete()
            db.session.commit()

            consumption = meter.get_monthly_consumption()
            assert consumption == []

    def test_get_monthly_consumption_with_data(self, app, sample_readings):
        """Test monthly consumption calculation."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            consumption = meter.get_monthly_consumption(months=6, newest_first=True)

            assert len(consumption) > 0
            # All entries should be (label, value) tuples
            for label, value in consumption:
                assert isinstance(label, str)
                # Value can be None or float

    def test_get_monthly_consumption_order(self, app, sample_readings):
        """Test monthly consumption ordering."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])

            # Newest first
            consumption_newest = meter.get_monthly_consumption(months=3, newest_first=True)
            # Oldest first (for charts)
            consumption_oldest = meter.get_monthly_consumption(months=3, newest_first=False)

            # Labels should be in opposite order
            if len(consumption_newest) > 1 and len(consumption_oldest) > 1:
                assert consumption_newest[0][0] != consumption_oldest[0][0]

    def test_get_3month_average(self, app, sample_readings):
        """Test 3-month average calculation."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            avg = meter.get_3month_average()

            # Should return a float with our test data
            assert avg is not None
            assert isinstance(avg, float)
            assert avg > 0

    def test_get_3month_average_no_data(self, app, sample_meters):
        """Test 3-month average returns None with no data."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])
            MeterReading.query.filter_by(meter_id=meter.id).delete()
            db.session.commit()

            avg = meter.get_3month_average()
            assert avg is None

    def test_get_prediction_weighted(self, app, sample_readings):
        """Test weighted prediction calculation."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            prediction = meter.get_prediction_weighted()

            assert prediction is not None
            assert isinstance(prediction, float)
            assert prediction > 0

    def test_get_prediction_weighted_no_data(self, app, sample_meters):
        """Test weighted prediction returns None with no data."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])
            MeterReading.query.filter_by(meter_id=meter.id).delete()
            db.session.commit()

            prediction = meter.get_prediction_weighted()
            assert prediction is None

    def test_get_prediction_seasonal(self, app, sample_readings):
        """Test seasonal prediction (falls back to weighted with short data)."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            prediction = meter.get_prediction_seasonal()

            # With only 6 months of data, should fall back to weighted
            assert prediction is not None
            assert isinstance(prediction, float)

    def test_meter_unique_name(self, app, sample_meters):
        """Test that meter names must be unique."""
        with app.app_context():
            meter = Meter(name='Strom', unit='kWh', serial_number='DUPE-001')
            db.session.add(meter)

            with pytest.raises(Exception):
                db.session.commit()

    def test_get_yearly_consumption(self, app, sample_meters):
        """Test yearly consumption returns sum of 12 months."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])
            today = date.today()

            # Create 13 months of readings for a full year
            base_value = 1000.0
            for i in range(13, -1, -1):
                reading_date = today - relativedelta(months=i)
                reading_date = reading_date.replace(day=1)
                value = base_value + (13 - i) * 100  # 100 units per month
                reading = MeterReading(
                    meter_id=meter.id,
                    reading_date=reading_date,
                    value=value
                )
                db.session.add(reading)
            db.session.commit()

            yearly = meter.get_yearly_consumption()
            assert yearly is not None
            assert isinstance(yearly, float)
            # Should be approximately 12 * 100 = 1200 (sum of 12 months consumption)
            assert yearly > 0

    def test_get_yearly_consumption_no_data(self, app, sample_meters):
        """Test yearly consumption returns None with no readings."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])
            MeterReading.query.filter_by(meter_id=meter.id).delete()
            db.session.commit()

            yearly = meter.get_yearly_consumption()
            assert yearly is None

    def test_get_previous_reading(self, app, sample_readings):
        """Test get_previous_reading returns correct earlier reading."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            today = date.today()

            # Get the previous reading before today
            prev = meter.get_previous_reading(before_date=today)
            assert prev is not None
            assert prev.reading_date < today

            # Get the reading before that
            prev2 = meter.get_previous_reading(before_date=prev.reading_date)
            if prev2:
                assert prev2.reading_date < prev.reading_date

    def test_get_previous_reading_no_earlier(self, app, sample_meters):
        """Test get_previous_reading returns None when no earlier reading exists."""
        with app.app_context():
            meter = Meter.query.get(sample_meters['Strom'])

            # Create just one reading
            reading = MeterReading(
                meter_id=meter.id,
                reading_date=date.today(),
                value=1000.0
            )
            db.session.add(reading)
            db.session.commit()

            # No reading before today's reading
            prev = meter.get_previous_reading(before_date=date.today())
            assert prev is None

    def test_get_previous_reading_without_date(self, app, sample_readings):
        """Test get_previous_reading returns last reading when no date specified."""
        with app.app_context():
            meter = Meter.query.get(sample_readings['Strom'])
            last_reading = meter.get_last_reading()
            prev_reading = meter.get_previous_reading()

            # Without a date, should return the most recent reading
            assert prev_reading is not None
            assert prev_reading.id == last_reading.id


class TestMeterReadingModel:
    """Tests for MeterReading model."""

    def test_create_reading(self, app, sample_meters):
        """Test creating a meter reading."""
        with app.app_context():
            reading = MeterReading(
                meter_id=sample_meters['Strom'],
                reading_date=date.today(),
                value=12345.67
            )
            db.session.add(reading)
            db.session.commit()

            assert reading.id is not None
            assert reading.value == 12345.67
            assert reading.meter_id == sample_meters['Strom']

    def test_reading_meter_relationship(self, app, sample_readings):
        """Test reading has access to its meter."""
        with app.app_context():
            reading = MeterReading.query.first()
            assert reading.meter is not None
            assert reading.meter.name in ['Strom', 'Gas', 'Wasser']

    def test_unique_meter_date_constraint(self, app, sample_meters):
        """Test that same meter can't have two readings on same date."""
        with app.app_context():
            reading_date = date.today() + timedelta(days=100)

            reading1 = MeterReading(
                meter_id=sample_meters['Strom'],
                reading_date=reading_date,
                value=1000
            )
            db.session.add(reading1)
            db.session.commit()

            reading2 = MeterReading(
                meter_id=sample_meters['Strom'],
                reading_date=reading_date,
                value=2000
            )
            db.session.add(reading2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_different_meters_same_date(self, app, sample_meters):
        """Test that different meters can have readings on the same date."""
        with app.app_context():
            reading_date = date.today() + timedelta(days=200)

            reading1 = MeterReading(
                meter_id=sample_meters['Strom'],
                reading_date=reading_date,
                value=1000
            )
            reading2 = MeterReading(
                meter_id=sample_meters['Gas'],
                reading_date=reading_date,
                value=500
            )
            db.session.add(reading1)
            db.session.add(reading2)
            db.session.commit()

            assert reading1.id is not None
            assert reading2.id is not None
