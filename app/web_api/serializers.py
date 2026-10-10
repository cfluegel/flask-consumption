"""JSON-Serialisierung für die UI-API (/ui-api)."""


def meter_to_dict(meter) -> dict:
    return {
        'id': meter.id,
        'name': meter.name,
        'unit': meter.unit,
        'serial_number': meter.serial_number,
        'weather_overlay': meter.weather_overlay,
    }


def reading_to_dict(reading) -> dict:
    return {
        'id': reading.id,
        'meter_id': reading.meter_id,
        'reading_date': reading.reading_date.isoformat(),
        'value': reading.value,
    }


def tariff_to_dict(tariff) -> dict:
    return {
        'id': tariff.id,
        'meter_id': tariff.meter_id,
        'name': tariff.name,
        'price_per_unit': tariff.price_per_unit,
        'base_price_monthly': tariff.base_price_monthly,
        'valid_from': tariff.valid_from.isoformat(),
    }
