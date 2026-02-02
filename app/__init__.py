import json
from pathlib import Path

import click
from flask import Flask
from flasgger import Swagger
from .extensions import db, migrate, login_manager, csrf
from .main import main_bp
from .api import api_bp
from .api_v1 import api_v1_bp
from .pwa import pwa_bp

def create_app(config_object='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Extensions initialisieren
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    csrf.init_app(app)

    # Load OpenAPI spec and configure Swagger UI
    openapi_path = Path(__file__).parent / 'api' / 'openapi.json'
    with open(openapi_path) as f:
        openapi_spec = json.load(f)

    swagger_config = {
        'headers': [],
        'specs': [
            {
                'endpoint': 'apispec',
                'route': '/apispec.json',
            }
        ],
        'static_url_path': '/flasgger_static',
        'swagger_ui': True,
        'specs_route': '/apidocs/'
    }

    Swagger(app, template=openapi_spec, config=swagger_config)

    # Blueprints registrieren
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    csrf.exempt(api_bp)  # API uses API key auth instead of CSRF
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    csrf.exempt(api_v1_bp)
    app.register_blueprint(pwa_bp)
    csrf.exempt(pwa_bp)  # PWA uses API key auth

    # Custom Jinja2 filters
    @app.template_filter('de_number')
    def de_number_filter(value, decimals=2):
        """Format number with German locale (comma as decimal separator)."""
        if value is None:
            return '-'
        formatted = f"{value:,.{decimals}f}"
        # Swap . and , for German format (1,234.56 -> 1.234,56)
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted

    # CLI commands registrieren
    register_commands(app)

    return app


def register_commands(app):
    @app.cli.command('seed-meters')
    def seed_meters():
        """Erstellt die Standard-Zähler (Strom, Gas, Wasser)."""
        from .models import Meter

        meters = [
            {'name': 'Strom', 'unit': 'kWh', 'serial_number': 'STROM-001'},
            {'name': 'Gas', 'unit': 'm³', 'serial_number': 'GAS-001'},
            {'name': 'Wasser', 'unit': 'Liter', 'serial_number': 'WASSER-001'},
        ]

        for meter_data in meters:
            existing = Meter.query.filter_by(name=meter_data['name']).first()
            if existing:
                click.echo(f"Zähler '{meter_data['name']}' existiert bereits.")
            else:
                meter = Meter(**meter_data)
                db.session.add(meter)
                click.echo(f"Zähler '{meter_data['name']}' erstellt.")

        db.session.commit()
        click.echo('Fertig.')

    @app.cli.command('list-meters')
    def list_meters():
        """Zeigt alle Zähler mit ID und Seriennummer an."""
        from .models import Meter

        meters = Meter.query.all()
        if not meters:
            click.echo('Keine Zähler vorhanden.')
            return

        click.echo(f"{'ID':<4} {'Name':<12} {'Einheit':<8} {'Seriennummer'}")
        click.echo('-' * 40)
        for meter in meters:
            click.echo(f"{meter.id:<4} {meter.name:<12} {meter.unit:<8} {meter.serial_number}")

    @app.cli.command('update-meter-serial')
    @click.option('--meter-id', required=True, type=int, help='ID des Zählers')
    @click.option('--serial', required=True, help='Neue Seriennummer')
    def update_meter_serial(meter_id, serial):
        """Aktualisiert die Seriennummer eines Zählers (z.B. bei Zählerwechsel)."""
        from .models import Meter

        meter = Meter.query.get(meter_id)
        if not meter:
            click.echo(f"Fehler: Zähler mit ID {meter_id} nicht gefunden.")
            return

        old_serial = meter.serial_number
        meter.serial_number = serial
        db.session.commit()
        click.echo(f"Seriennummer für '{meter.name}' aktualisiert: {old_serial} -> {serial}")

    @app.cli.command('create-user')
    @click.option('--username', required=True, help='Benutzername')
    @click.option('--email', required=True, help='E-Mail-Adresse')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Passwort')
    def create_user(username, email, password):
        """Erstellt einen neuen Benutzer."""
        from .models import User

        if User.query.filter_by(username=username).first():
            click.echo(f"Fehler: Benutzername '{username}' existiert bereits.")
            return

        if User.query.filter_by(email=email).first():
            click.echo(f"Fehler: E-Mail '{email}' existiert bereits.")
            return

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Benutzer '{username}' erfolgreich erstellt.")

    @app.cli.command('debug-readings')
    @click.option('--meter-id', type=int, help='ID eines bestimmten Zählers')
    def debug_readings(meter_id):
        """Zeigt alle Ablesungen und berechneten Verbrauch zur Fehlersuche."""
        from .models import Meter, MeterReading

        meters = [Meter.query.get(meter_id)] if meter_id else Meter.query.all()

        for meter in meters:
            if not meter:
                click.echo(f"Zähler mit ID {meter_id} nicht gefunden.")
                continue

            click.echo(f"\n=== {meter.name} (ID: {meter.id}) ===")
            click.echo(f"Aktuelle Seriennummer: {meter.serial_number}")

            readings = MeterReading.query.filter_by(meter_id=meter.id).order_by(MeterReading.reading_date.asc()).all()
            click.echo(f"\nAblesungen ({len(readings)} gesamt):")
            click.echo(f"{'Datum':<12} {'Wert':<15}")
            click.echo('-' * 30)
            for r in readings:
                click.echo(f"{r.reading_date}   {r.value:<15.2f}")

            click.echo(f"\nMonatlicher Verbrauch:")
            consumption = meter.get_monthly_consumption()
            for month, value in consumption:
                if value is not None:
                    click.echo(f"  {month}: {value:.2f} {meter.unit}")
                else:
                    click.echo(f"  {month}: -")

    @app.cli.command('export-data')
    @click.argument('filename', type=click.Path())
    def export_data(filename):
        """Exportiert alle Zähler und Ablesungen in eine JSON-Datei."""
        import json
        from datetime import datetime
        from .models import Meter, MeterReading

        meters = Meter.query.all()
        readings = MeterReading.query.order_by(MeterReading.meter_id, MeterReading.reading_date).all()

        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'meters': [
                {
                    'id': m.id,
                    'name': m.name,
                    'unit': m.unit,
                    'serial_number': m.serial_number
                }
                for m in meters
            ],
            'readings': [
                {
                    'meter_id': r.meter_id,
                    'reading_date': r.reading_date.isoformat(),
                    'value': r.value
                }
                for r in readings
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        click.echo(f"Exportiert: {len(meters)} Zähler, {len(readings)} Ablesungen")
        click.echo(f"Datei: {filename}")

    @app.cli.command('import-data')
    @click.argument('filename', type=click.Path(exists=True))
    @click.option('--replace', is_flag=True, help='Alle bestehenden Daten löschen vor dem Import')
    def import_data(filename, replace):
        """Importiert Zähler und Ablesungen aus einer JSON-Datei."""
        import json
        from datetime import datetime
        from .models import Meter, MeterReading

        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'meters' not in data or 'readings' not in data:
            click.echo('Fehler: Ungültiges Dateiformat. Erwartet: meters und readings.')
            return

        if replace:
            # Confirm destructive operation
            reading_count = MeterReading.query.count()
            meter_count = Meter.query.count()
            click.echo(f"WARNUNG: Dies löscht {meter_count} Zähler und {reading_count} Ablesungen!")
            if not click.confirm('Wirklich alle Daten ersetzen?'):
                click.echo('Abgebrochen.')
                return

            # Delete all existing data (readings first due to foreign key)
            MeterReading.query.delete()
            Meter.query.delete()
            db.session.commit()
            click.echo('Bestehende Daten gelöscht.')

        # Build meter ID mapping (old ID -> new meter)
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
                    serial_number=meter_data['serial_number']
                )
                db.session.add(meter)
                db.session.flush()  # Get the new ID
                meter_id_map[meter_data['id']] = meter.id
                meters_created += 1

        db.session.commit()

        # Import readings
        readings_created = 0
        readings_skipped = 0

        for reading_data in data['readings']:
            old_meter_id = reading_data['meter_id']
            if old_meter_id not in meter_id_map:
                click.echo(f"Warnung: Zähler-ID {old_meter_id} nicht gefunden, überspringe Ablesung.")
                readings_skipped += 1
                continue

            new_meter_id = meter_id_map[old_meter_id]
            reading_date = datetime.fromisoformat(reading_data['reading_date']).date()

            # Check for duplicate (same meter and date)
            existing = MeterReading.query.filter_by(
                meter_id=new_meter_id,
                reading_date=reading_date
            ).first()

            if existing:
                readings_skipped += 1
            else:
                reading = MeterReading(
                    meter_id=new_meter_id,
                    reading_date=reading_date,
                    value=reading_data['value']
                )
                db.session.add(reading)
                readings_created += 1

        db.session.commit()

        click.echo(f"\nImport abgeschlossen:")
        click.echo(f"  Zähler:     {meters_created} erstellt, {meters_skipped} übersprungen")
        click.echo(f"  Ablesungen: {readings_created} erstellt, {readings_skipped} übersprungen")

    @app.cli.command('import-weather')
    @click.option('--url', default=None, help='Override default DWD URL')
    @click.option('--replace', is_flag=True, help='Replace all existing weather data')
    def import_weather(url, replace):
        """Importiert monatliche Wetterdaten vom DWD (Hamburg-Fuhlsbüttel)."""
        import urllib.request
        from .models import WeatherData

        # Default URL for Hamburg-Fuhlsbüttel monthly data
        default_url = 'https://www.dwd.de/DE/leistungen/_config/leistungsteckbriefPublication.txt?view=nasPublication&nn=16102&imageFilePath=8524108716561010473591414984380285860348440627905136707616031491601294722759953476578874542442119146105183517945099480938740343906988335742522410754862714750285564712567437754031667430876202844830680654990991014883769890983300283888580251123815305533&download=true'
        data_url = url or default_url

        click.echo(f'Downloading weather data from DWD...')
        click.echo(f'URL: {data_url}')

        try:
            # Download the file
            if data_url.endswith('.zip'):
                import zipfile
                import io
                import tempfile

                with urllib.request.urlopen(data_url, timeout=60) as response:
                    zip_data = response.read()

                # Extract the data file from the zip
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    # Find the data file (starts with 'produkt_')
                    data_file = None
                    for name in zf.namelist():
                        if name.startswith('produkt_') and name.endswith('.txt'):
                            data_file = name
                            break

                    if not data_file:
                        click.echo('Fehler: Keine Datendatei im ZIP gefunden.')
                        return

                    click.echo(f'Extrahiere: {data_file}')
                    content = zf.read(data_file).decode('latin-1')
            else:
                with urllib.request.urlopen(data_url, timeout=60) as response:
                    content = response.read().decode('latin-1')

        except Exception as e:
            click.echo(f'Fehler beim Download: {e}')
            return

        # Strip <pre> tags if present
        content = content.strip()
        if content.startswith('<pre>'):
            content = content[5:]
        if content.endswith('</pre>'):
            content = content[:-6]
        content = content.strip()

        # Parse the content - fixed-width format from DWD
        lines = content.strip().split('\n')
        if not lines:
            click.echo('Fehler: Keine Daten gefunden.')
            return

        # Find header and separator lines
        header_idx = None
        separator_idx = None
        for i, line in enumerate(lines):
            if 'STAT' in line and 'JJJJMM' in line:
                header_idx = i
            elif header_idx is not None and line.strip().startswith('-----'):
                separator_idx = i
                break

        if header_idx is None or separator_idx is None:
            click.echo('Fehler: Header oder Trennzeile nicht gefunden.')
            return

        # Parse column positions from separator line (-----  ------  etc.)
        separator = lines[separator_idx]
        header = lines[header_idx]

        # Find column boundaries from dashes
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

        # Extract column names from header using positions
        columns = []
        for start, end in col_positions:
            col_name = header[start:end].strip()
            columns.append(col_name)

        click.echo(f'Gefundene Spalten: {columns}')

        # DWD column mapping to our model fields
        field_mapping = {
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

        # Map column names to positions
        col_map = {name: (pos, columns[i]) for i, (name, pos) in enumerate(zip(columns, col_positions))}

        if replace:
            count = WeatherData.query.count()
            if count > 0:
                click.echo(f'Lösche {count} bestehende Wetterdaten-Einträge...')
                WeatherData.query.delete()
                db.session.commit()

        records_created = 0
        records_skipped = 0

        # Process data lines (skip header and separator line)
        for line in lines[separator_idx + 1:]:
            if not line.strip() or line.strip().startswith('-'):
                continue

            # Extract values using fixed-width positions
            values = {}
            for col_name, (start, end) in zip(columns, col_positions):
                if end <= len(line):
                    val = line[start:end].strip()
                elif start < len(line):
                    val = line[start:].strip()
                else:
                    val = ''
                values[col_name] = val

            # Extract station_id and year_month
            try:
                station_id = int(values.get('STAT', ''))
                year_month = values.get('JJJJMM', '')
            except (ValueError, TypeError):
                continue

            if not year_month or len(year_month) != 6:
                continue

            # Check for existing record
            existing = WeatherData.query.filter_by(
                station_id=station_id,
                year_month=year_month
            ).first()

            if existing:
                records_skipped += 1
                continue

            # Build the record
            weather = WeatherData(station_id=station_id, year_month=year_month)

            # Map remaining fields
            for dwd_col, model_field in field_mapping.items():
                if dwd_col in ['STAT', 'JJJJMM']:
                    continue  # Already handled

                val = values.get(dwd_col, '').strip()
                if val and val != '-999' and val != '-999.0':
                    try:
                        if model_field == 'quality_level':
                            setattr(weather, model_field, int(val))
                        else:
                            setattr(weather, model_field, float(val))
                    except ValueError:
                        pass  # Leave as NULL

            db.session.add(weather)
            records_created += 1

        db.session.commit()

        click.echo(f'\nImport abgeschlossen:')
        click.echo(f'  Neue Einträge: {records_created}')
        click.echo(f'  Übersprungen (bereits vorhanden): {records_skipped}')

    @app.cli.command('show-weather')
    @click.option('--limit', default=12, help='Anzahl der Einträge (Standard: 12)')
    @click.option('--all', 'show_all', is_flag=True, help='Alle Einträge anzeigen')
    def show_weather(limit, show_all):
        """Zeigt Wetterdaten aus der Datenbank an."""
        from .models import WeatherData

        query = WeatherData.query.order_by(WeatherData.year_month.desc())
        if not show_all:
            query = query.limit(limit)

        records = query.all()

        if not records:
            click.echo('Keine Wetterdaten vorhanden.')
            return

        # Header
        click.echo(f"{'Monat':<8} {'QN':>3} {'Temp Ø':>7} {'TMin Ø':>7} {'TMax Ø':>7} {'TMin':>7} {'TMax':>7} {'Sonne':>6} {'Wolken':>6} {'Regen':>6} {'RMax':>6} {'Wind':>5} {'Böen':>7}")
        click.echo('-' * 100)

        for r in records:
            month = f"{r.year_month[:4]}-{r.year_month[4:]}"
            qn = f"{r.quality_level}" if r.quality_level is not None else '-'
            temp_avg = f"{r.temp_avg:.1f}" if r.temp_avg is not None else '-'
            temp_min_avg = f"{r.temp_min_avg:.1f}" if r.temp_min_avg is not None else '-'
            temp_max_avg = f"{r.temp_max_avg:.1f}" if r.temp_max_avg is not None else '-'
            temp_min = f"{r.temp_min:.1f}" if r.temp_min is not None else '-'
            temp_max = f"{r.temp_max:.1f}" if r.temp_max is not None else '-'
            sunshine = f"{r.sunshine_hours:.0f}h" if r.sunshine_hours is not None else '-'
            clouds = f"{r.cloud_cover_avg:.1f}/8" if r.cloud_cover_avg is not None else '-'
            rain = f"{r.precipitation_sum:.0f}mm" if r.precipitation_sum is not None else '-'
            rain_max = f"{r.precipitation_max:.0f}mm" if r.precipitation_max is not None else '-'
            wind_avg = f"{r.wind_speed_avg:.1f}" if r.wind_speed_avg is not None else '-'
            wind_gust = f"{r.wind_gust_max:.1f}" if r.wind_gust_max is not None else '-'

            click.echo(f"{month:<8} {qn:>3} {temp_avg:>7} {temp_min_avg:>7} {temp_max_avg:>7} {temp_min:>7} {temp_max:>7} {sunshine:>6} {clouds:>6} {rain:>6} {rain_max:>6} {wind_avg:>5} {wind_gust:>7}")

        click.echo(f'\nGesamt: {len(records)} Einträge')
