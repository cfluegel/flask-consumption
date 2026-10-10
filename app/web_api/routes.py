"""UI-API für das React-Frontend (same-origin, ohne Auth wie das Web-UI)."""

from datetime import date, datetime

from flask import jsonify, request
from sqlalchemy.exc import IntegrityError

from . import web_api_bp
from ..extensions import db
from ..models import Meter, MeterReading, Tariff
from ..services import costs as costs_service
from ..services.weather import weather_series_for_meter
from .serializers import meter_to_dict, reading_to_dict, tariff_to_dict


def _parse_iso_date(value):
    try:
        return datetime.fromisoformat(value).date()
    except (TypeError, ValueError):
        return None


def _month_entry(label: str, consumption):
    year, month = costs_service.parse_month_label(label)
    return {'year': year, 'month': month, 'label': label, 'consumption': consumption}


# --- Dashboard -------------------------------------------------------------

@web_api_bp.route('/dashboard')
def dashboard():
    meters = Meter.query.order_by(Meter.id).all()
    result = []
    today = date.today()
    for meter in meters:
        last = meter.get_last_reading()
        current_tariff = costs_service.tariff_for_month(meter, today.year, today.month)
        result.append({
            **meter_to_dict(meter),
            'last_reading': reading_to_dict(last) if last else None,
            'stats': {
                'avg_3month': meter.get_3month_average(),
                'pred_weighted': meter.get_prediction_weighted(),
                'pred_seasonal': meter.get_prediction_seasonal(),
                'pred_calculated': meter.get_prediction_calculated(),
                'yearly_consumption': meter.get_yearly_consumption(),
                'yearly_cost': costs_service.yearly_cost(meter),
                'forecast_cost': costs_service.forecast_cost_current_month(meter),
            },
            'current_tariff': tariff_to_dict(current_tariff) if current_tariff else None,
        })
    return jsonify({'meters': result})


# --- Meters ----------------------------------------------------------------

@web_api_bp.route('/meters/<int:meter_id>', methods=['PATCH'])
def update_meter(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    data = request.get_json(silent=True) or {}

    if 'weather_overlay' in data:
        if not isinstance(data['weather_overlay'], bool):
            return jsonify({'error': 'weather_overlay muss ein Boolean sein'}), 400
        meter.weather_overlay = data['weather_overlay']
    if 'name' in data:
        if not data['name'] or not isinstance(data['name'], str):
            return jsonify({'error': 'name darf nicht leer sein'}), 400
        meter.name = data['name']
    if 'serial_number' in data:
        if not data['serial_number'] or not isinstance(data['serial_number'], str):
            return jsonify({'error': 'serial_number darf nicht leer sein'}), 400
        meter.serial_number = data['serial_number']

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Zählername bereits vergeben'}), 409

    return jsonify(meter_to_dict(meter))


@web_api_bp.route('/meters/<int:meter_id>/consumption')
def meter_consumption(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    months = request.args.get('months', default=12, type=int)
    series = [_month_entry(label, value)
              for label, value in meter.get_monthly_consumption(months=months, newest_first=False)]
    return jsonify({'meter': meter_to_dict(meter), 'series': series})


@web_api_bp.route('/meters/<int:meter_id>/readings')
def meter_readings(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)

    query = MeterReading.query.filter_by(meter_id=meter.id).order_by(
        MeterReading.reading_date.desc())
    total = query.count()
    readings = query.offset(offset).limit(limit).all()

    return jsonify({
        'meter': meter_to_dict(meter),
        'total': total,
        'readings': [reading_to_dict(r) for r in readings],
    })


# --- Readings CRUD ---------------------------------------------------------

@web_api_bp.route('/readings', methods=['POST'])
def create_reading():
    data = request.get_json(silent=True) or {}

    meter = Meter.query.get(data.get('meter_id') or 0)
    if not meter:
        return jsonify({'error': 'Zähler nicht gefunden'}), 404

    reading_date = _parse_iso_date(data.get('reading_date'))
    if reading_date is None:
        return jsonify({'error': 'Ungültiges Datum (erwartet YYYY-MM-DD)'}), 400

    value = data.get('value')
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return jsonify({'error': 'Ungültiger Zählerstand'}), 400

    reading = MeterReading(meter_id=meter.id, reading_date=reading_date, value=float(value))
    db.session.add(reading)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Für dieses Datum existiert bereits eine Ablesung'}), 409

    return jsonify(reading_to_dict(reading)), 201


@web_api_bp.route('/readings/<int:reading_id>', methods=['PUT'])
def update_reading(reading_id):
    reading = db.get_or_404(MeterReading, reading_id)
    data = request.get_json(silent=True) or {}

    if 'reading_date' in data:
        reading_date = _parse_iso_date(data['reading_date'])
        if reading_date is None:
            return jsonify({'error': 'Ungültiges Datum (erwartet YYYY-MM-DD)'}), 400
        reading.reading_date = reading_date

    if 'value' in data:
        value = data['value']
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return jsonify({'error': 'Ungültiger Zählerstand'}), 400
        reading.value = float(value)

    if 'meter_id' in data:
        meter = Meter.query.get(data['meter_id'])
        if not meter:
            return jsonify({'error': 'Zähler nicht gefunden'}), 404
        reading.meter_id = meter.id

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Für dieses Datum existiert bereits eine Ablesung'}), 409

    return jsonify(reading_to_dict(reading))


@web_api_bp.route('/readings/<int:reading_id>', methods=['DELETE'])
def delete_reading(reading_id):
    reading = db.get_or_404(MeterReading, reading_id)
    db.session.delete(reading)
    db.session.commit()
    return '', 204


# --- Tariffs CRUD ----------------------------------------------------------

@web_api_bp.route('/meters/<int:meter_id>/tariffs')
def meter_tariffs(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    tariffs = meter.tariffs.all()
    return jsonify([tariff_to_dict(t) for t in tariffs])


def _validate_tariff_payload(data, partial=False):
    """Returns (fields, error_response)."""
    fields = {}

    if 'price_per_unit' in data or not partial:
        price = data.get('price_per_unit')
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price < 0:
            return None, (jsonify({'error': 'Ungültiger Arbeitspreis'}), 400)
        fields['price_per_unit'] = float(price)

    if 'base_price_monthly' in data:
        base = data.get('base_price_monthly')
        if not isinstance(base, (int, float)) or isinstance(base, bool) or base < 0:
            return None, (jsonify({'error': 'Ungültiger Grundpreis'}), 400)
        fields['base_price_monthly'] = float(base)
    elif not partial:
        fields['base_price_monthly'] = 0.0

    if 'valid_from' in data or not partial:
        valid_from = _parse_iso_date(data.get('valid_from'))
        if valid_from is None:
            return None, (jsonify({'error': 'Ungültiges Datum (erwartet YYYY-MM-DD)'}), 400)
        fields['valid_from'] = valid_from

    if 'name' in data:
        fields['name'] = data['name'] or None

    return fields, None


@web_api_bp.route('/meters/<int:meter_id>/tariffs', methods=['POST'])
def create_tariff(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    data = request.get_json(silent=True) or {}

    fields, error = _validate_tariff_payload(data, partial=False)
    if error:
        return error

    tariff = Tariff(meter_id=meter.id, **fields)
    db.session.add(tariff)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Für dieses Gültigkeitsdatum existiert bereits ein Tarif'}), 409

    return jsonify(tariff_to_dict(tariff)), 201


@web_api_bp.route('/tariffs/<int:tariff_id>', methods=['PUT'])
def update_tariff(tariff_id):
    tariff = db.get_or_404(Tariff, tariff_id)
    data = request.get_json(silent=True) or {}

    fields, error = _validate_tariff_payload(data, partial=True)
    if error:
        return error

    for key, value in fields.items():
        setattr(tariff, key, value)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Für dieses Gültigkeitsdatum existiert bereits ein Tarif'}), 409

    return jsonify(tariff_to_dict(tariff))


@web_api_bp.route('/tariffs/<int:tariff_id>', methods=['DELETE'])
def delete_tariff(tariff_id):
    tariff = db.get_or_404(Tariff, tariff_id)
    db.session.delete(tariff)
    db.session.commit()
    return '', 204


# --- Costs / comparison / weather ------------------------------------------

@web_api_bp.route('/meters/<int:meter_id>/costs')
def meter_costs(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    months = request.args.get('months', default=24, type=int)
    series = costs_service.monthly_costs(meter, months=months, newest_first=False)
    return jsonify({
        'meter': meter_to_dict(meter),
        'series': series,
        'yearly_cost': costs_service.yearly_cost(meter),
        'forecast': costs_service.forecast_cost_current_month(meter),
    })


@web_api_bp.route('/meters/<int:meter_id>/year-comparison')
def year_comparison(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    today = date.today()
    year = request.args.get('year', default=today.year, type=int)
    previous_year = year - 1

    # Alle Monate beider Jahre über die Kosten-Serie einsammeln
    entries = {(e['year'], e['month']): e
               for e in costs_service.monthly_costs(meter, months=None, newest_first=False)}

    months = []
    for month in range(1, 13):
        current = entries.get((year, month))
        previous = entries.get((previous_year, month))
        cur_consumption = current['consumption'] if current else None
        prev_consumption = previous['consumption'] if previous else None

        deviation_pct = None
        if cur_consumption is not None and prev_consumption:
            deviation_pct = (cur_consumption - prev_consumption) / prev_consumption * 100

        months.append({
            'month': month,
            'label_short': costs_service.MONTH_NAMES[month - 1],
            'current': {
                'consumption': cur_consumption,
                'cost': current['cost'] if current else None,
            },
            'previous': {
                'consumption': prev_consumption,
                'cost': previous['cost'] if previous else None,
            },
            'deviation_pct': deviation_pct,
            'is_current_month': year == today.year and month == today.month,
        })

    # Summen nur über Monate, in denen beide Jahre Daten haben (fairer Vergleich)
    paired = [(m['current']['consumption'], m['previous']['consumption'])
              for m in months
              if m['current']['consumption'] is not None
              and m['previous']['consumption'] is not None]
    total_current = sum(c for c, _ in paired) if paired else None
    total_previous = sum(p for _, p in paired) if paired else None
    total_deviation = None
    if total_current is not None and total_previous:
        total_deviation = (total_current - total_previous) / total_previous * 100

    return jsonify({
        'meter': meter_to_dict(meter),
        'year': year,
        'previous_year': previous_year,
        'months': months,
        'totals': {
            'current': total_current,
            'previous': total_previous,
            'deviation_pct': total_deviation,
        },
    })


@web_api_bp.route('/meters/<int:meter_id>/weather')
def meter_weather(meter_id):
    meter = db.get_or_404(Meter, meter_id)
    months = request.args.get('months', default=24, type=int)
    series = weather_series_for_meter(meter, months=months)
    return jsonify({'meter': meter_to_dict(meter), 'series': series})
