from datetime import datetime

from flask import jsonify, request

from . import api_v1_bp, require_api_key
from ..extensions import db
from ..models import Meter, MeterReading


@api_v1_bp.route('/meters')
@require_api_key
def list_meters():
    """List all meters."""
    meters = Meter.query.all()
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'unit': m.unit,
        'serial_number': m.serial_number
    } for m in meters])


@api_v1_bp.route('/meters/<int:meter_id>')
@require_api_key
def get_meter(meter_id):
    """Get meter details."""
    meter = Meter.query.get_or_404(meter_id)
    return jsonify({
        'id': meter.id,
        'name': meter.name,
        'unit': meter.unit,
        'serial_number': meter.serial_number
    })


@api_v1_bp.route('/meters/<int:meter_id>/latest')
@require_api_key
def get_latest_reading(meter_id):
    """Get the latest reading for a meter (useful for sanity checks)."""
    meter = Meter.query.get_or_404(meter_id)
    latest = meter.get_last_reading()

    return jsonify({
        'meter': {
            'id': meter.id,
            'name': meter.name,
            'unit': meter.unit
        },
        'reading': {
            'id': latest.id,
            'date': latest.reading_date.isoformat(),
            'value': latest.value
        } if latest else None
    })


@api_v1_bp.route('/meters/<int:meter_id>/readings')
@require_api_key
def get_readings(meter_id):
    """Get recent readings for a meter with optional limit."""
    meter = Meter.query.get_or_404(meter_id)
    limit = request.args.get('limit', 10, type=int)

    # Get readings ordered by date descending (most recent first)
    readings = meter.readings.limit(limit).all()

    return jsonify({
        'meter': {
            'id': meter.id,
            'name': meter.name,
            'unit': meter.unit
        },
        'readings': [{
            'id': r.id,
            'date': r.reading_date.isoformat(),
            'value': r.value
        } for r in readings]
    })


@api_v1_bp.route('/readings', methods=['POST'])
@require_api_key
def create_reading():
    """Add a new meter reading."""
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

    reading = MeterReading(
        meter_id=data['meter_id'],
        reading_date=reading_date,
        value=float(data['value'])
    )

    db.session.add(reading)
    db.session.commit()

    return jsonify({
        'id': reading.id,
        'meter_id': reading.meter_id,
        'reading_date': reading.reading_date.isoformat(),
        'value': reading.value
    }), 201
