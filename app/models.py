from calendar import monthrange
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

# Beispiel-Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Meter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    weather_overlay = db.Column(db.Boolean, nullable=False, default=False,
                                server_default='0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    readings = db.relationship('MeterReading', backref='meter', lazy='dynamic',
                               order_by='desc(MeterReading.reading_date)')
    tariffs = db.relationship('Tariff', backref='meter', lazy='dynamic',
                              order_by='desc(Tariff.valid_from)',
                              cascade='all, delete-orphan')

    def get_last_reading(self) -> 'MeterReading | None':
        return self.readings.first()

    def get_monthly_consumption(self, months: int | None = None, newest_first: bool = True) -> list[tuple[str, float | None]]:
        """Returns list of (month_label, consumption).

        Args:
            months: Number of months to return. If None, returns all months from first reading.
            newest_first: If True, returns newest month first. If False, oldest first (for charts).

        Uses pro-rata distribution: consumption between readings is spread
        across months proportionally based on days in each month.
        """
        month_names = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

        # Use direct query to override relationship's default desc ordering
        readings = MeterReading.query.filter_by(meter_id=self.id).order_by(MeterReading.reading_date.asc()).all()

        if not readings:
            return []

        # Accumulate consumption per month using pro-rata distribution
        consumption_by_month: dict[tuple[int, int], float] = {}

        prev_reading = None
        for reading in readings:
            if prev_reading:
                total_consumption = reading.value - prev_reading.value
                total_days = (reading.reading_date - prev_reading.reading_date).days

                if total_days > 0:
                    # Distribute consumption across months the period spans
                    current = prev_reading.reading_date
                    while current < reading.reading_date:
                        month_key = (current.year, current.month)
                        # Days in this month within the reading period
                        month_end = date(current.year, current.month,
                                         monthrange(current.year, current.month)[1])
                        period_end = min(month_end, reading.reading_date)
                        days_in_month = (period_end - current).days + (1 if current == prev_reading.reading_date else 0)

                        # Pro-rata share for this month
                        share = (days_in_month / total_days) * total_consumption
                        consumption_by_month[month_key] = consumption_by_month.get(month_key, 0) + share

                        # Move to first day of next month
                        current = month_end + relativedelta(days=1)

            prev_reading = reading

        # Determine date range
        today = date.today()
        if months is None:
            # Start from the month of the first reading
            first_reading_date = readings[0].reading_date
            start_date = date(first_reading_date.year, first_reading_date.month, 1)
            total_months = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
        else:
            total_months = months

        # Generate months
        result = []
        if newest_first:
            # Newest to oldest (for tables)
            started = False
            for i in range(total_months):
                month_date = today - relativedelta(months=i)
                month_key = (month_date.year, month_date.month)
                month_label = f"{month_names[month_date.month - 1]} {month_date.year}"
                consumption = consumption_by_month.get(month_key)
                # Skip leading months with no data
                if not started and consumption is None:
                    continue
                started = True
                result.append((month_label, consumption))
        else:
            # Oldest to newest (for charts)
            for i in range(total_months - 1, -1, -1):
                month_date = today - relativedelta(months=i)
                month_key = (month_date.year, month_date.month)
                month_label = f"{month_names[month_date.month - 1]} {month_date.year}"
                consumption = consumption_by_month.get(month_key)
                result.append((month_label, consumption))

        return result

    def get_3month_average(self) -> float | None:
        """Returns average consumption of last 3 complete months.

        Returns None if less than 1 month of consumption data available.
        """
        consumption = self.get_monthly_consumption(months=4, newest_first=True)

        # Filter out months with no data
        values = [v for _, v in consumption if v is not None]

        # Skip current (potentially incomplete) month if we have enough data
        if len(values) > 3:
            values = values[1:4]  # Skip most recent, take next 3
        elif len(values) > 1:
            values = values[:3]  # Take what we have

        if not values:
            return None

        return sum(values) / len(values)

    def get_prediction_weighted(self) -> float | None:
        """Returns weighted moving average prediction.

        Uses weights: most recent month * 0.5, second * 0.33, third * 0.17
        Adapts to changing consumption patterns faster than simple average.
        Returns None if insufficient data.
        """
        consumption = self.get_monthly_consumption(months=4, newest_first=True)

        # Filter out months with no data
        values = [v for _, v in consumption if v is not None]

        # Skip current (potentially incomplete) month if we have enough data
        if len(values) > 3:
            values = values[1:4]
        elif len(values) > 1:
            values = values[:3]

        if not values:
            return None

        # Apply weights based on available data
        weights = [0.5, 0.33, 0.17]
        if len(values) == 1:
            return values[0]
        elif len(values) == 2:
            # Normalize weights for 2 values
            w1, w2 = 0.6, 0.4
            return values[0] * w1 + values[1] * w2
        else:
            return values[0] * weights[0] + values[1] * weights[1] + values[2] * weights[2]

    def get_prediction_seasonal(self) -> float | None:
        """Returns seasonal prediction based on same month last year.

        Calculates: last_year_same_month * (recent_3mo_avg / last_year_3mo_avg)
        This captures seasonal patterns (heating in winter, etc.) while
        accounting for overall consumption changes.

        Falls back to weighted prediction if no yearly data available.
        """
        today = date.today()
        target_month = today.month
        target_year = today.year - 1

        # Get consumption data going back at least 15 months
        consumption = self.get_monthly_consumption(months=15, newest_first=True)

        # Build a dict for easy lookup: (year, month) -> value
        month_names = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        consumption_dict = {}
        for label, value in consumption:
            if value is not None:
                # Parse "Mär 2024" format
                parts = label.split()
                if len(parts) == 2:
                    month_idx = month_names.index(parts[0]) + 1 if parts[0] in month_names else None
                    year = int(parts[1])
                    if month_idx:
                        consumption_dict[(year, month_idx)] = value

        # Get same month last year
        last_year_value = consumption_dict.get((target_year, target_month))

        if last_year_value is None:
            # Fall back to weighted prediction
            return self.get_prediction_weighted()

        # Calculate recent 3-month average (excluding current month)
        recent_values = []
        for i in range(1, 4):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            val = consumption_dict.get((y, m))
            if val is not None:
                recent_values.append(val)

        # Calculate last year's 3-month average (same period)
        last_year_values = []
        for i in range(1, 4):
            m = today.month - i
            y = today.year - 1
            if m <= 0:
                m += 12
                y -= 1
            val = consumption_dict.get((y, m))
            if val is not None:
                last_year_values.append(val)

        if not recent_values or not last_year_values:
            # Not enough data for adjustment, use last year value directly
            return last_year_value

        recent_avg = sum(recent_values) / len(recent_values)
        last_year_avg = sum(last_year_values) / len(last_year_values)

        if last_year_avg == 0:
            return last_year_value

        # Apply adjustment factor
        adjustment = recent_avg / last_year_avg
        return last_year_value * adjustment

    def get_prediction_calculated(self) -> float | None:
        """Returns calculated prediction based on actual readings in the current month.

        Uses the daily consumption rate between the earliest and latest reading
        of the current month, extrapolated to the full month.
        Requires >= 2 readings in the current month on different days.
        """
        today = date.today()
        first_of_month = date(today.year, today.month, 1)
        _, days_in_month = monthrange(today.year, today.month)

        readings = (MeterReading.query
                    .filter_by(meter_id=self.id)
                    .filter(MeterReading.reading_date >= first_of_month)
                    .filter(MeterReading.reading_date <= today)
                    .order_by(MeterReading.reading_date.asc())
                    .all())

        if len(readings) < 2:
            return None

        baseline = readings[0]
        latest = readings[-1]
        days_between = (latest.reading_date - baseline.reading_date).days

        if days_between <= 0:
            return None

        daily_rate = (latest.value - baseline.value) / days_between
        return daily_rate * days_in_month

    def get_yearly_consumption(self) -> float | None:
        """Returns total consumption from the last 12 complete months.

        Returns None if insufficient data (less than 2 readings spanning at least 1 month).
        """
        consumption = self.get_monthly_consumption(months=13, newest_first=True)

        # Filter out months with no data and skip current (potentially incomplete) month
        values = [v for _, v in consumption if v is not None]

        if len(values) > 12:
            values = values[1:13]  # Skip most recent, take next 12
        elif len(values) > 1:
            values = values[:12]  # Take what we have (up to 12)
        else:
            return None

        if not values:
            return None

        return sum(values)

    def get_previous_reading(self, before_date: date | None = None) -> 'MeterReading | None':
        """Returns the reading before the given date, or the last reading if no date specified.

        Args:
            before_date: If provided, returns the most recent reading before this date.
                        If None, returns the most recent reading overall.

        Returns:
            MeterReading or None if no reading exists.
        """
        query = MeterReading.query.filter_by(meter_id=self.id)

        if before_date is not None:
            query = query.filter(MeterReading.reading_date < before_date)

        return query.order_by(MeterReading.reading_date.desc()).first()


class MeterReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey('meter.id'), nullable=False)
    reading_date = db.Column(db.Date, nullable=False)
    value = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('meter_id', 'reading_date', name='unique_meter_date'),
    )


class Tariff(db.Model):
    """Preistarif für einen Zähler, gültig ab einem Stichtag.

    Bei mehreren Tarifen gilt pro Monat der jüngste Tarif, dessen
    valid_from vor oder am Monatsanfang liegt (ganzer Monat, keine
    tagesanteilige Aufteilung bei Wechsel mitten im Monat).
    """
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey('meter.id'), nullable=False)
    name = db.Column(db.String(120), nullable=True)
    price_per_unit = db.Column(db.Float, nullable=False)  # Arbeitspreis €/Einheit
    base_price_monthly = db.Column(db.Float, nullable=False, default=0.0)  # Grundpreis €/Monat
    valid_from = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('meter_id', 'valid_from', name='unique_meter_tariff_date'),
    )


class WeatherData(db.Model):
    """Monthly weather data from DWD (Deutscher Wetterdienst)."""
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, nullable=False)
    year_month = db.Column(db.String(6), nullable=False)  # YYYYMM format
    quality_level = db.Column(db.Integer, nullable=True)

    # Temperature fields (°C)
    temp_min = db.Column(db.Float, nullable=True)  # Lowest temperature
    temp_min_avg = db.Column(db.Float, nullable=True)  # Avg daily minimum
    temp_avg = db.Column(db.Float, nullable=True)  # Mean temperature
    temp_max_avg = db.Column(db.Float, nullable=True)  # Avg daily maximum
    temp_max = db.Column(db.Float, nullable=True)  # Highest temperature

    # Other weather fields
    sunshine_hours = db.Column(db.Float, nullable=True)  # Total sunshine duration (hours)
    cloud_cover_avg = db.Column(db.Float, nullable=True)  # Mean cloud cover (eighths)

    # Precipitation fields (mm)
    precipitation_sum = db.Column(db.Float, nullable=True)  # Total precipitation
    precipitation_max = db.Column(db.Float, nullable=True)  # Max daily precipitation

    # Wind fields
    wind_speed_avg = db.Column(db.Float, nullable=True)  # Mean wind force (Beaufort)
    wind_gust_max = db.Column(db.Float, nullable=True)  # Peak wind gust (m/s)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('station_id', 'year_month', name='unique_station_month'),
    )


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    # Flask-Login erwartet hier die Rückgabe eines User-Objekts oder None
    return User.query.get(int(user_id))

