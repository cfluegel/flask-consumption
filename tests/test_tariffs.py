"""Tests for the Tariff model and the cost service (app/services/costs.py)."""

from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from app.extensions import db
from app.models import Meter, MeterReading, Tariff
from app.services.costs import (
    forecast_cost_current_month,
    format_month_label,
    monthly_costs,
    parse_month_label,
    tariff_for_month,
    yearly_cost,
)


class TestMonthLabelHelpers:
    def test_roundtrip(self, app):
        assert parse_month_label('Mär 2024') == (2024, 3)
        assert format_month_label(2024, 3) == 'Mär 2024'
        assert parse_month_label(format_month_label(2025, 12)) == (2025, 12)


class TestTariffForMonth:
    def test_no_tariff_returns_none(self, sample_meters, app):
        meter = db.session.get(Meter, sample_meters['Strom'])
        assert tariff_for_month(meter, 2024, 1) is None

    def test_picks_latest_applicable_tariff(self, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Strom'])
        today = date.today()

        current = tariff_for_month(meter, today.year, today.month)
        assert current.name == 'Strom Neu'
        assert current.price_per_unit == 0.35

        old_month = today - relativedelta(months=6)
        old = tariff_for_month(meter, old_month.year, old_month.month)
        assert old.name == 'Strom Alt'
        assert old.price_per_unit == 0.30

    def test_month_before_first_tariff_returns_none(self, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Strom'])
        before = date.today() - relativedelta(months=30)
        assert tariff_for_month(meter, before.year, before.month) is None

    def test_unique_constraint_meter_valid_from(self, sample_tariffs, app):
        meter_id = sample_tariffs['Strom']
        existing = Tariff.query.filter_by(meter_id=meter_id).first()
        db.session.add(Tariff(meter_id=meter_id, price_per_unit=0.4,
                              base_price_monthly=5.0,
                              valid_from=existing.valid_from))
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()


class TestMonthlyCosts:
    def test_costs_use_applicable_tariff_per_month(self, sample_readings, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Strom'])
        entries = monthly_costs(meter, months=6, newest_first=True)

        for e in entries:
            if e['consumption'] is None:
                assert e['cost'] is None
            else:
                expected = e['consumption'] * e['price_per_unit'] + e['base_price_monthly']
                assert e['cost'] == pytest.approx(expected)

        # Price change 3 months ago: older months use the old tariff
        old_entry = entries[-1]
        assert old_entry['price_per_unit'] == 0.30
        new_entry = entries[0]
        assert new_entry['price_per_unit'] == 0.35

    def test_no_tariff_means_no_cost(self, sample_readings, app):
        meter = db.session.get(Meter, sample_readings['Wasser'])
        entries = monthly_costs(meter, months=3, newest_first=True)
        assert all(e['cost'] is None for e in entries)
        assert any(e['consumption'] is not None for e in entries)

    def test_entry_shape(self, sample_readings, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Gas'])
        entry = monthly_costs(meter, months=2, newest_first=True)[0]
        assert set(entry) == {'year', 'month', 'label', 'consumption', 'cost',
                              'tariff_id', 'price_per_unit', 'base_price_monthly'}


class TestYearlyCost:
    def test_yearly_cost_sums_complete_months(self, sample_readings, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Strom'])
        total = yearly_cost(meter)
        assert total is not None
        # 6 months of ~300 kWh at 0.30-0.35 €/kWh plus Grundpreis: plausible range
        assert 400 < total < 800

    def test_yearly_cost_none_without_tariff(self, sample_readings, app):
        meter = db.session.get(Meter, sample_readings['Wasser'])
        assert yearly_cost(meter) is None

    def test_yearly_cost_none_without_readings(self, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Gas'])
        MeterReading.query.filter_by(meter_id=meter.id).delete()
        db.session.commit()
        assert yearly_cost(meter) is None


class TestForecastCost:
    def test_forecast_uses_fallback_chain(self, sample_readings, sample_tariffs, app):
        meter = db.session.get(Meter, sample_tariffs['Strom'])
        forecast = forecast_cost_current_month(meter)
        assert forecast is not None
        assert forecast['method'] in ('calculated', 'seasonal', 'weighted')
        assert forecast['consumption'] is not None
        tariff = tariff_for_month(meter, date.today().year, date.today().month)
        expected = forecast['consumption'] * tariff.price_per_unit + tariff.base_price_monthly
        assert forecast['cost'] == pytest.approx(expected)

    def test_forecast_calculated_preferred(self, sample_tariffs, app):
        """Two readings in the current month -> method 'calculated'."""
        meter = db.session.get(Meter, sample_tariffs['Gas'])
        today = date.today()
        if today.day < 2:
            pytest.skip('Monat gerade erst begonnen')
        first = date(today.year, today.month, 1)
        db.session.add(MeterReading(meter_id=meter.id, reading_date=first, value=1000.0))
        db.session.add(MeterReading(meter_id=meter.id, reading_date=today, value=1000.0 + (today.day - 1) * 2.0))
        db.session.commit()

        forecast = forecast_cost_current_month(meter)
        assert forecast['method'] == 'calculated'

    def test_forecast_none_without_data(self, sample_meters, app):
        meter = db.session.get(Meter, sample_meters['Strom'])
        assert forecast_cost_current_month(meter) is None

    def test_forecast_cost_none_without_tariff(self, sample_readings, app):
        meter = db.session.get(Meter, sample_readings['Wasser'])
        forecast = forecast_cost_current_month(meter)
        assert forecast is not None
        assert forecast['cost'] is None
        assert forecast['consumption'] is not None
