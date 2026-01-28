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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    readings = db.relationship('MeterReading', backref='meter', lazy='dynamic',
                               order_by='desc(MeterReading.reading_date)')

    def get_last_reading(self) -> 'MeterReading | None':
        return self.readings.first()

    def get_monthly_consumption(self, months: int = 12) -> list[tuple[str, float | None]]:
        """Returns list of (month_label, consumption) for last N months.

        Uses pro-rata distribution: consumption between readings is spread
        across months proportionally based on days in each month.
        """
        month_names = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

        # Use direct query to override relationship's default desc ordering
        readings = MeterReading.query.filter_by(meter_id=self.id).order_by(MeterReading.reading_date.asc()).all()

        # Accumulate consumption per month using pro-rata distribution
        consumption_by_month: dict[tuple[int, int], float] = {}

        prev_reading = None
        for reading in readings:
            if prev_reading and reading.serial_number == prev_reading.serial_number:
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

        # Generate last N months
        today = date.today()
        result = []
        for i in range(months - 1, -1, -1):
            month_date = today - relativedelta(months=i)
            month_key = (month_date.year, month_date.month)
            month_label = f"{month_names[month_date.month - 1]} {month_date.year}"
            consumption = consumption_by_month.get(month_key)
            result.append((month_label, consumption))

        return result


class MeterReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey('meter.id'), nullable=False)
    reading_date = db.Column(db.Date, nullable=False)
    value = db.Column(db.Float, nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('meter_id', 'reading_date', name='unique_meter_date'),
    )


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    # Flask-Login erwartet hier die Rückgabe eines User-Objekts oder None
    return User.query.get(int(user_id))

