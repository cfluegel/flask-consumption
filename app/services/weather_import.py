"""Import monatlicher DWD-Wetterdaten (Hamburg-Fuhlsbüttel).

Gemeinsame Logik für CLI (flask import-weather) und Admin-Weboberfläche.
"""
import urllib.request

from ..extensions import db
from ..models import WeatherData

DEFAULT_DWD_URL = 'https://www.dwd.de/DE/leistungen/_config/leistungsteckbriefPublication.txt?view=nasPublication&nn=16102&imageFilePath=8524108716561010473591414984380285860348440627905136707616031491601294722759953476578874542442119146105183517945099480938740343906988335742522410754862714750285564712567437754031667430876202844830680654990991014883769890983300283888580251123815305533&download=true'

# DWD-Spalten -> Modellfelder
FIELD_MAPPING = {
    'STAT': 'station_id',
    'JJJJMM': 'year_month',
    'QN': 'quality_level',
    'TNN': 'temp_min',
    'TNM': 'temp_min_avg',
    'TMM': 'temp_avg',
    'TXM': 'temp_max_avg',
    'TXX': 'temp_max',
    'SOS': 'sunshine_hours',
    'NMM': 'cloud_cover_avg',
    'RSS': 'precipitation_sum',
    'RSX': 'precipitation_max',
    'FMM': 'wind_speed_avg',
    'FXX': 'wind_gust_max',
}


class WeatherImportError(Exception):
    """Download oder Parsing der DWD-Daten fehlgeschlagen."""


def fetch_dwd_content(url: str | None = None, timeout: int = 60) -> str:
    """Lädt die DWD-Datei (optional ZIP) und liefert den Textinhalt."""
    data_url = url or DEFAULT_DWD_URL

    try:
        if data_url.endswith('.zip'):
            import io
            import zipfile

            with urllib.request.urlopen(data_url, timeout=timeout) as response:
                zip_data = response.read()

            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                data_file = next(
                    (name for name in zf.namelist()
                     if name.startswith('produkt_') and name.endswith('.txt')),
                    None,
                )
                if not data_file:
                    raise WeatherImportError('Keine Datendatei im ZIP gefunden.')
                content = zf.read(data_file).decode('latin-1')
        else:
            with urllib.request.urlopen(data_url, timeout=timeout) as response:
                content = response.read().decode('latin-1')
    except WeatherImportError:
        raise
    except Exception as e:
        raise WeatherImportError(f'Fehler beim Download: {e}') from e

    # <pre>-Tags entfernen, falls vorhanden
    content = content.strip()
    if content.startswith('<pre>'):
        content = content[5:]
    if content.endswith('</pre>'):
        content = content[:-6]
    return content.strip()


def parse_and_store(content: str, replace: bool = False) -> dict:
    """Parst den DWD-Festbreiten-Text und speichert neue Monatseinträge.

    Returns: {'created': int, 'skipped': int, 'deleted': int}
    """
    lines = content.strip().split('\n')
    if not lines or not content:
        raise WeatherImportError('Keine Daten gefunden.')

    # Header- und Trennzeile finden
    header_idx = None
    separator_idx = None
    for i, line in enumerate(lines):
        if 'STAT' in line and 'JJJJMM' in line:
            header_idx = i
        elif header_idx is not None and line.strip().startswith('-----'):
            separator_idx = i
            break

    if header_idx is None or separator_idx is None:
        raise WeatherImportError('Header oder Trennzeile nicht gefunden.')

    # Spaltengrenzen aus der Trennzeile (-----  ------ ...) ableiten
    separator = lines[separator_idx]
    header = lines[header_idx]

    col_positions = []
    in_col = False
    col_start = 0
    for i, char in enumerate(separator):
        if char == '-' and not in_col:
            col_start = i
            in_col = True
        elif char != '-' and in_col:
            col_positions.append((col_start, i))
            in_col = False
    if in_col:
        col_positions.append((col_start, len(separator)))

    columns = [header[start:end].strip() for start, end in col_positions]

    deleted = 0
    if replace:
        deleted = WeatherData.query.count()
        if deleted:
            WeatherData.query.delete()
            db.session.commit()

    created = 0
    skipped = 0

    for line in lines[separator_idx + 1:]:
        if not line.strip() or line.strip().startswith('-'):
            continue

        values = {}
        for col_name, (start, end) in zip(columns, col_positions):
            if end <= len(line):
                val = line[start:end].strip()
            elif start < len(line):
                val = line[start:].strip()
            else:
                val = ''
            values[col_name] = val

        try:
            station_id = int(values.get('STAT', ''))
            year_month = values.get('JJJJMM', '')
        except (ValueError, TypeError):
            continue

        if not year_month or len(year_month) != 6:
            continue

        existing = WeatherData.query.filter_by(
            station_id=station_id,
            year_month=year_month,
        ).first()
        if existing:
            skipped += 1
            continue

        weather = WeatherData(station_id=station_id, year_month=year_month)

        for dwd_col, model_field in FIELD_MAPPING.items():
            if dwd_col in ('STAT', 'JJJJMM'):
                continue
            val = values.get(dwd_col, '').strip()
            if val and val not in ('-999', '-999.0'):
                try:
                    if model_field == 'quality_level':
                        setattr(weather, model_field, int(val))
                    else:
                        setattr(weather, model_field, float(val))
                except ValueError:
                    pass  # bleibt NULL

        db.session.add(weather)
        created += 1

    db.session.commit()
    return {'created': created, 'skipped': skipped, 'deleted': deleted}


def import_weather_data(url: str | None = None, replace: bool = False) -> dict:
    """Download + Parsen + Speichern in einem Schritt."""
    content = fetch_dwd_content(url)
    return parse_and_store(content, replace=replace)
