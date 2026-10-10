"""Kostenberechnung auf Basis von Verbräuchen und Tarifhistorie.

Vereinfachung: Pro Monat gilt genau ein Tarif — der jüngste Tarif, dessen
valid_from vor oder am Monatsanfang liegt. Ein Tarifwechsel mitten im Monat
wird nicht tagesanteilig aufgeteilt.
"""
from datetime import date

from ..models import Tariff

MONTH_NAMES = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
               'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']


def parse_month_label(label: str) -> tuple[int, int]:
    """'Mär 2024' -> (2024, 3)."""
    name, year = label.split()
    return int(year), MONTH_NAMES.index(name) + 1


def format_month_label(year: int, month: int) -> str:
    """(2024, 3) -> 'Mär 2024'."""
    return f"{MONTH_NAMES[month - 1]} {year}"


def tariff_for_month(meter, year: int, month: int) -> 'Tariff | None':
    first_of_month = date(year, month, 1)
    return (Tariff.query
            .filter_by(meter_id=meter.id)
            .filter(Tariff.valid_from <= first_of_month)
            .order_by(Tariff.valid_from.desc())
            .first())


def _cost_entry(meter, year: int, month: int, consumption: float | None) -> dict:
    tariff = tariff_for_month(meter, year, month)
    cost = None
    if consumption is not None and tariff is not None:
        cost = consumption * tariff.price_per_unit + tariff.base_price_monthly
    return {
        'year': year,
        'month': month,
        'label': format_month_label(year, month),
        'consumption': consumption,
        'cost': cost,
        'tariff_id': tariff.id if tariff else None,
        'price_per_unit': tariff.price_per_unit if tariff else None,
        'base_price_monthly': tariff.base_price_monthly if tariff else None,
    }


def monthly_costs(meter, months: int | None = None, newest_first: bool = True) -> list[dict]:
    """Monatliche Kosten je Monat aus Verbrauch × anwendbarem Tarif."""
    result = []
    for label, consumption in meter.get_monthly_consumption(months=months, newest_first=newest_first):
        year, month = parse_month_label(label)
        result.append(_cost_entry(meter, year, month, consumption))
    return result


def yearly_cost(meter) -> float | None:
    """Summe der Kosten der letzten 12 vollständigen Monate.

    Analog zu Meter.get_yearly_consumption(): laufender Monat wird
    übersprungen, wenn genug Daten vorhanden sind. Monate ohne Verbrauch
    oder ohne Tarif fließen nicht ein.
    """
    entries = [e for e in monthly_costs(meter, months=13, newest_first=True)
               if e['consumption'] is not None]

    if len(entries) > 12:
        entries = entries[1:13]
    elif len(entries) > 1:
        entries = entries[:12]
    else:
        return None

    costs = [e['cost'] for e in entries if e['cost'] is not None]
    if not costs:
        return None
    return sum(costs)


def forecast_cost_current_month(meter) -> dict | None:
    """Kostenprognose für den laufenden Monat.

    Verbrauchsprognose: calculated -> seasonal -> weighted (erste verfügbare).
    """
    for method, fn in (('calculated', meter.get_prediction_calculated),
                       ('seasonal', meter.get_prediction_seasonal),
                       ('weighted', meter.get_prediction_weighted)):
        consumption = fn()
        if consumption is not None:
            break
    else:
        return None

    today = date.today()
    tariff = tariff_for_month(meter, today.year, today.month)
    cost = None
    if tariff is not None:
        cost = consumption * tariff.price_per_unit + tariff.base_price_monthly

    return {'method': method, 'consumption': consumption, 'cost': cost}
