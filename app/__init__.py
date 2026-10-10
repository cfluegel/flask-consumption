import json
from pathlib import Path

import click
from flask import Flask
from flasgger import Swagger
from .extensions import db, migrate, login_manager, csrf
from .api import api_bp
from .api_v1 import api_v1_bp
from .pwa import pwa_bp
from .admin import admin_bp
from .web_api import web_api_bp

def create_app(config_object='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Extensions initialisieren
    db.init_app(app)
    migrate.init_app(app, db)
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
    app.register_blueprint(api_bp, url_prefix='/api')
    csrf.exempt(api_bp)  # API uses API key auth instead of CSRF
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    csrf.exempt(api_v1_bp)
    app.register_blueprint(pwa_bp)
    csrf.exempt(pwa_bp)  # PWA uses API key auth
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(web_api_bp, url_prefix='/ui-api')
    csrf.exempt(web_api_bp)  # Same-origin UI-API, gleiches Vertrauensniveau wie Web-UI

    # React-SPA zuletzt registrieren, damit /api, /pwa, /admin etc. Vorrang haben.
    from .spa import spa_bp
    app.register_blueprint(spa_bp)

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

    @app.cli.command('set-weather-overlay')
    @click.option('--meter-id', required=True, type=int, help='ID des Zählers')
    @click.option('--off', is_flag=True, help='Temperatur-Overlay deaktivieren')
    def set_weather_overlay(meter_id, off):
        """Aktiviert/deaktiviert das Temperatur-Overlay für einen Zähler."""
        from .models import Meter

        meter = Meter.query.get(meter_id)
        if not meter:
            click.echo(f"Fehler: Zähler mit ID {meter_id} nicht gefunden.")
            return

        meter.weather_overlay = not off
        db.session.commit()
        status = 'deaktiviert' if off else 'aktiviert'
        click.echo(f"Temperatur-Overlay für '{meter.name}' {status}.")

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
        from .models import Meter, MeterReading, Tariff

        meters = Meter.query.all()
        readings = MeterReading.query.order_by(MeterReading.meter_id, MeterReading.reading_date).all()
        tariffs = Tariff.query.order_by(Tariff.meter_id, Tariff.valid_from).all()

        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'meters': [
                {
                    'id': m.id,
                    'name': m.name,
                    'unit': m.unit,
                    'serial_number': m.serial_number,
                    'weather_overlay': m.weather_overlay
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
            ],
            'tariffs': [
                {
                    'meter_id': t.meter_id,
                    'name': t.name,
                    'price_per_unit': t.price_per_unit,
                    'base_price_monthly': t.base_price_monthly,
                    'valid_from': t.valid_from.isoformat()
                }
                for t in tariffs
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        click.echo(f"Exportiert: {len(meters)} Zähler, {len(readings)} Ablesungen, {len(tariffs)} Tarife")
        click.echo(f"Datei: {filename}")

    @app.cli.command('import-data')
    @click.argument('filename', type=click.Path(exists=True))
    @click.option('--replace', is_flag=True, help='Alle bestehenden Daten löschen vor dem Import')
    def import_data(filename, replace):
        """Importiert Zähler und Ablesungen aus einer JSON-Datei."""
        import json
        from datetime import datetime
        from .models import Meter, MeterReading, Tariff

        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'meters' not in data or 'readings' not in data:
            click.echo('Fehler: Ungültiges Dateiformat. Erwartet: meters und readings.')
            return

        if replace:
            # Confirm destructive operation
            reading_count = MeterReading.query.count()
            meter_count = Meter.query.count()
            tariff_count = Tariff.query.count()
            click.echo(f"WARNUNG: Dies löscht {meter_count} Zähler, {reading_count} Ablesungen und {tariff_count} Tarife!")
            if not click.confirm('Wirklich alle Daten ersetzen?'):
                click.echo('Abgebrochen.')
                return

            # Delete all existing data (readings/tariffs first due to foreign key)
            MeterReading.query.delete()
            Tariff.query.delete()
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
                    serial_number=meter_data['serial_number'],
                    weather_overlay=meter_data.get('weather_overlay', False)
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

        # Import tariffs (optional key, abwärtskompatibel zu alten Exporten)
        tariffs_created = 0
        tariffs_skipped = 0

        for tariff_data in data.get('tariffs', []):
            old_meter_id = tariff_data['meter_id']
            if old_meter_id not in meter_id_map:
                click.echo(f"Warnung: Zähler-ID {old_meter_id} nicht gefunden, überspringe Tarif.")
                tariffs_skipped += 1
                continue

            new_meter_id = meter_id_map[old_meter_id]
            valid_from = datetime.fromisoformat(tariff_data['valid_from']).date()

            existing = Tariff.query.filter_by(
                meter_id=new_meter_id,
                valid_from=valid_from
            ).first()

            if existing:
                tariffs_skipped += 1
            else:
                tariff = Tariff(
                    meter_id=new_meter_id,
                    name=tariff_data.get('name'),
                    price_per_unit=tariff_data['price_per_unit'],
                    base_price_monthly=tariff_data.get('base_price_monthly', 0.0),
                    valid_from=valid_from
                )
                db.session.add(tariff)
                tariffs_created += 1

        db.session.commit()

        click.echo(f"\nImport abgeschlossen:")
        click.echo(f"  Zähler:     {meters_created} erstellt, {meters_skipped} übersprungen")
        click.echo(f"  Ablesungen: {readings_created} erstellt, {readings_skipped} übersprungen")
        click.echo(f"  Tarife:     {tariffs_created} erstellt, {tariffs_skipped} übersprungen")

    @app.cli.command('import-weather')
    @click.option('--url', default=None, help='Override default DWD URL')
    @click.option('--replace', is_flag=True, help='Replace all existing weather data')
    def import_weather(url, replace):
        """Importiert monatliche Wetterdaten vom DWD (Hamburg-Fuhlsbüttel)."""
        from .services.weather_import import DEFAULT_DWD_URL, WeatherImportError, import_weather_data

        click.echo('Downloading weather data from DWD...')
        click.echo(f'URL: {url or DEFAULT_DWD_URL}')

        try:
            result = import_weather_data(url=url, replace=replace)
        except WeatherImportError as e:
            click.echo(f'Fehler: {e}')
            return

        if result['deleted']:
            click.echo(f"Gelöscht (--replace): {result['deleted']}")
        click.echo(f'\nImport abgeschlossen:')
        click.echo(f"  Neue Einträge: {result['created']}")
        click.echo(f"  Übersprungen (bereits vorhanden): {result['skipped']}")

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
