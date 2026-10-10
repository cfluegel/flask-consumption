import json
from datetime import datetime, date

from flask import render_template, Response, request, flash, redirect, url_for

from . import admin_bp
from ..extensions import db
from ..models import Meter, MeterReading, Tariff, WeatherData
from ..services.weather_import import WeatherImportError, import_weather_data


@admin_bp.route('/')
def index():
    weather_count = WeatherData.query.count()
    latest = (WeatherData.query
              .order_by(WeatherData.year_month.desc())
              .first())
    latest_month = None
    if latest:
        latest_month = f"{latest.year_month[4:]}/{latest.year_month[:4]}"
    return render_template('admin/index.html',
                           weather_count=weather_count,
                           weather_latest_month=latest_month)


@admin_bp.route('/import-weather', methods=['POST'])
def import_weather():
    try:
        result = import_weather_data()
    except WeatherImportError as e:
        flash(f'Wetterdaten-Abruf fehlgeschlagen: {e}', 'danger')
        return redirect(url_for('admin.index'))

    flash(
        f"Wetterdaten aktualisiert: {result['created']} neue Monate, "
        f"{result['skipped']} bereits vorhanden.",
        'success',
    )
    return redirect(url_for('admin.index'))


@admin_bp.route('/export')
def export_data():
    meters = Meter.query.all()
    readings = MeterReading.query.order_by(
        MeterReading.meter_id, MeterReading.reading_date
    ).all()
    tariffs = Tariff.query.order_by(Tariff.meter_id, Tariff.valid_from).all()

    data = {
        'exported_at': datetime.utcnow().isoformat(),
        'meters': [
            {
                'id': m.id,
                'name': m.name,
                'unit': m.unit,
                'serial_number': m.serial_number,
                'weather_overlay': m.weather_overlay,
            }
            for m in meters
        ],
        'readings': [
            {
                'meter_id': r.meter_id,
                'reading_date': r.reading_date.isoformat(),
                'value': r.value,
            }
            for r in readings
        ],
        'tariffs': [
            {
                'meter_id': t.meter_id,
                'name': t.name,
                'price_per_unit': t.price_per_unit,
                'base_price_monthly': t.base_price_monthly,
                'valid_from': t.valid_from.isoformat(),
            }
            for t in tariffs
        ],
    }

    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    filename = f"verbrauchstracker_export_{date.today().isoformat()}.json"

    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@admin_bp.route('/import', methods=['POST'])
def import_data():
    file = request.files.get('file')
    if not file or not file.filename:
        flash('Keine Datei ausgewählt.', 'danger')
        return redirect(url_for('admin.index'))

    try:
        data = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError):
        flash('Ungültige JSON-Datei.', 'danger')
        return redirect(url_for('admin.index'))

    if 'meters' not in data or 'readings' not in data:
        flash('Ungültiges Dateiformat. Erwartet: meters und readings.', 'danger')
        return redirect(url_for('admin.index'))

    # Import meters
    meter_id_map = {}
    meters_created = 0
    meters_skipped = 0

    for meter_data in data['meters']:
        existing = Meter.query.filter_by(name=meter_data['name']).first()
        if existing:
            meter_id_map[meter_data['id']] = existing.id
            meters_skipped += 1
        else:
            meter = Meter(
                name=meter_data['name'],
                unit=meter_data['unit'],
                serial_number=meter_data['serial_number'],
                weather_overlay=meter_data.get('weather_overlay', False),
            )
            db.session.add(meter)
            db.session.flush()
            meter_id_map[meter_data['id']] = meter.id
            meters_created += 1

    db.session.commit()

    # Import readings
    readings_created = 0
    readings_skipped = 0

    for reading_data in data['readings']:
        old_meter_id = reading_data['meter_id']
        if old_meter_id not in meter_id_map:
            readings_skipped += 1
            continue

        new_meter_id = meter_id_map[old_meter_id]
        reading_date = datetime.fromisoformat(reading_data['reading_date']).date()

        existing = MeterReading.query.filter_by(
            meter_id=new_meter_id,
            reading_date=reading_date,
        ).first()

        if existing:
            readings_skipped += 1
        else:
            reading = MeterReading(
                meter_id=new_meter_id,
                reading_date=reading_date,
                value=reading_data['value'],
            )
            db.session.add(reading)
            readings_created += 1

    db.session.commit()

    # Import tariffs (optional key, abwärtskompatibel zu alten Exporten)
    tariffs_created = 0
    tariffs_skipped = 0

    for tariff_data in data.get('tariffs', []):
        old_meter_id = tariff_data['meter_id']
        if old_meter_id not in meter_id_map:
            tariffs_skipped += 1
            continue

        new_meter_id = meter_id_map[old_meter_id]
        valid_from = datetime.fromisoformat(tariff_data['valid_from']).date()

        existing = Tariff.query.filter_by(
            meter_id=new_meter_id,
            valid_from=valid_from,
        ).first()

        if existing:
            tariffs_skipped += 1
        else:
            tariff = Tariff(
                meter_id=new_meter_id,
                name=tariff_data.get('name'),
                price_per_unit=tariff_data['price_per_unit'],
                base_price_monthly=tariff_data.get('base_price_monthly', 0.0),
                valid_from=valid_from,
            )
            db.session.add(tariff)
            tariffs_created += 1

    db.session.commit()

    flash(
        f'Import abgeschlossen: '
        f'Zähler: {meters_created} erstellt, {meters_skipped} übersprungen. '
        f'Ablesungen: {readings_created} erstellt, {readings_skipped} übersprungen. '
        f'Tarife: {tariffs_created} erstellt, {tariffs_skipped} übersprungen.',
        'success',
    )
    return redirect(url_for('admin.index'))
