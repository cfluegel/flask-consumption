"""Wetter-Auswertung: Heizgradtage und Verbrauchs-/Temperatur-Serien.

Heizgradtage (HGT) nach vereinfachter Methode mit Heizgrenze 15 °C auf
Monatsmittelbasis: HGT = max(0, 15 − Monatsmitteltemperatur) × Tage im Monat.
(VDI 3807 mit 20/15 bräuchte Tageswerte, die als Monatsdaten nicht vorliegen.)
"""
from calendar import monthrange

from ..models import WeatherData
from .costs import parse_month_label

HEATING_BASE_TEMP = 15.0


def heating_degree_days(year: int, month: int, temp_avg: float | None,
                        base: float = HEATING_BASE_TEMP) -> float | None:
    if temp_avg is None:
        return None
    _, days = monthrange(year, month)
    return max(0.0, base - temp_avg) * days


def weather_series_for_meter(meter, months: int | None = None) -> list[dict]:
    """Monatsverbrauch kombiniert mit Wetterdaten, oldest-first.

    Join über year_month (YYYYMM); bei mehreren Stationen pro Monat wird
    der zuletzt angelegte Datensatz verwendet.
    """
    weather_by_month: dict[str, WeatherData] = {}
    for w in WeatherData.query.order_by(WeatherData.created_at.asc()).all():
        weather_by_month[w.year_month] = w

    series = []
    for label, consumption in meter.get_monthly_consumption(months=months, newest_first=False):
        year, month = parse_month_label(label)
        w = weather_by_month.get(f"{year}{month:02d}")
        temp_avg = w.temp_avg if w else None
        hgt = heating_degree_days(year, month, temp_avg)
        consumption_per_hgt = None
        if consumption is not None and hgt:
            consumption_per_hgt = consumption / hgt
        series.append({
            'year': year,
            'month': month,
            'label': label,
            'consumption': consumption,
            'temp_min': w.temp_min if w else None,
            'temp_avg': temp_avg,
            'temp_max': w.temp_max if w else None,
            'hgt': hgt,
            'consumption_per_hgt': consumption_per_hgt,
        })
    return series
