import json
from datetime import datetime, date

from flask import render_template, Response, request, flash, redirect, url_for

from . import admin_bp
from ..extensions import db
from ..models import Meter, MeterReading


@admin_bp.route('/')
def index():
    return render_template('admin/index.html')


@admin_bp.route('/export')
def export_data():
    meters = Meter.query.all()
    readings = MeterReading.query.order_by(
        MeterReading.meter_id, MeterReading.reading_date
    ).all()

    data = {
        'exported_at': datetime.utcnow().isoformat(),
        'meters': [
            {
                'id': m.id,
                'name': m.name,
                'unit': m.unit,
                'serial_number': m.serial_number,
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

    flash(
        f'Import abgeschlossen: '
        f'Zähler: {meters_created} erstellt, {meters_skipped} übersprungen. '
        f'Ablesungen: {readings_created} erstellt, {readings_skipped} übersprungen.',
        'success',
    )
    return redirect(url_for('admin.index'))
