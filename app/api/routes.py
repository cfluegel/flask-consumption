from datetime import datetime

from flask import jsonify, request

from . import api_bp, require_api_key
from ..extensions import db
from ..models import Meter, MeterReading


@api_bp.route('/status')
def status():
    return jsonify({'status': 'ok'})


@api_bp.route('/meters')
@require_api_key
def list_meters():
    meters = Meter.query.all()
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'unit': m.unit,
        'serial_number': m.serial_number
    } for m in meters])


@api_bp.route('/meters/<int:meter_id>/readings')
@require_api_key
def get_readings(meter_id):
    meter = Meter.query.get_or_404(meter_id)
    readings = meter.readings.all()
    return jsonify({
        'meter': {
            'id': meter.id,
            'name': meter.name,
            'unit': meter.unit,
            'serial_number': meter.serial_number
        },
        'readings': [{
            'id': r.id,
            'reading_date': r.reading_date.isoformat(),
            'value': r.value,
            'serial_number': r.serial_number
        } for r in readings]
    })


@api_bp.route('/readings', methods=['POST'])
@require_api_key
def create_reading():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    required_fields = ['meter_id', 'reading_date', 'value']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    meter = Meter.query.get(data['meter_id'])
    if not meter:
        return jsonify({'error': 'Meter not found'}), 404

    try:
        reading_date = datetime.strptime(data['reading_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    serial_number = data.get('serial_number', meter.serial_number)

    reading = MeterReading(
        meter_id=data['meter_id'],
        reading_date=reading_date,
        value=float(data['value']),
        serial_number=serial_number
    )

    db.session.add(reading)

    if serial_number != meter.serial_number:
        meter.serial_number = serial_number

    db.session.commit()

    return jsonify({
        'id': reading.id,
        'meter_id': reading.meter_id,
        'reading_date': reading.reading_date.isoformat(),
        'value': reading.value,
        'serial_number': reading.serial_number
    }), 201
