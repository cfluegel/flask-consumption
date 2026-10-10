# Flask Consumption Tracker

A web application for tracking utility consumption (electricity, natural gas, water). Record monthly meter readings, visualize consumption trends, track costs with tariff history, and access data via REST API. The main UI is a mobile-first React single-page app served by Flask.

## Features

- Track multiple utility meters (Strom/Electricity, Gas, Wasser/Water)
- Record and manage monthly meter readings
- **Mobile-first React SPA** with sand-colored theme and German UI
- **Cost tracking** with per-meter tariff history (Arbeitspreis + Grundpreis, valid-from dates)
- **Cost dashboard** with monthly cost charts and current-month cost forecast
- **Year-over-year comparison** per month with deviation percentages
- **Weather analysis** for gas meters: temperature overlay and weather-adjusted consumption (heating degree days, base 15 °C)
- Consumption predictions (calculated from current month, trend, seasonal)
- **Progressive Web App (PWA)** for mobile devices (iOS/Android)
- **Admin area** with web-based data export and import (JSON, includes tariffs)
- REST API for mobile app integration
- Docker deployment support (SQLite or PostgreSQL)

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/cfluegel/flask-consumption.git
cd flask-consumption

# Backend: create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
flask db upgrade
flask seed-meters

# Frontend: build the React SPA (required once for production serving)
cd frontend
npm install
npm run build
cd ..

# Run development server
python run.py
```

The application will be available at `http://127.0.0.1:5000`.

**Frontend development with hot reload:** run `python run.py` in one terminal and `cd frontend && npm run dev` in another. The Vite dev server on `http://127.0.0.1:5173` proxies `/ui-api`, `/api`, `/admin`, `/pwa` and `/apidocs` to Flask.

### Web UI (React SPA)

Served at `/` from `frontend/dist`. Pages:

| Route | Page |
|---|---|
| `/` | Dashboard with per-meter cards (readings, statistics, predictions, costs) |
| `/zaehler/:id` | Meter detail with readings management |
| `/ablesung/neu` | Add a new reading |
| `/kosten` | Cost dashboard (monthly costs, yearly cost, forecast) |
| `/tarife` | Tariff management (price history per meter) |
| `/vergleich` | Year-over-year comparison |
| `/grafiken/:id` | Consumption chart, optional temperature overlay and weather-adjusted view |
| `/einstellungen` | Meter settings (name, serial number, weather overlay) and links |

The SPA talks to the unauthenticated same-origin JSON API under `/ui-api` (dashboard, consumption, readings/tariffs CRUD, costs, year-comparison, weather).

### Progressive Web App (PWA)

The PWA is available at `/pwa/` and provides a mobile-optimized interface for viewing meters and adding readings.

**Setup on iOS:**
1. Open `http://your-server:5000/pwa/` in Safari
2. Enter your API key (default: `default-api-key`)
3. Tap Share → "Add to Home Screen"
4. Open from home screen for standalone app experience

**PWA Features:**
- Mobile-optimized meter dashboard
- View reading history per meter
- Add new readings with German number format support
- Works as standalone app on iOS and Android
- API key stored locally (persists across sessions)

### Admin Area

The admin area is available at `/admin/` and provides web-based data management:

- **Export** — Download all meters, readings and tariffs as a timestamped JSON file
- **Import** — Upload a previously exported JSON file to merge data (duplicates are skipped). Exports from older versions (without tariffs) import fine.

No authentication is required for the admin area.

### Docker Deployment

The Docker image builds the React frontend in a Node stage automatically and runs `flask db upgrade` on startup — updating an existing installation is just a rebuild/pull and restart.

```bash
# Simple setup with SQLite
docker compose -f docker-compose.sqlite.yml up -d

# Production setup with PostgreSQL
docker compose -f docker-compose.postgres.yml up -d

# Initialize meters
docker compose -f docker-compose.sqlite.yml exec app flask seed-meters

# Enable the temperature overlay for the gas meter
docker compose -f docker-compose.sqlite.yml exec app flask set-weather-overlay --meter-id 2
```

**Note on bind mounts:** The container runs as `appuser` which is typically assigned UID/GID 1000:1000 (not explicitly pinned in the Dockerfile). When using bind mounts, ensure the host directory is owned by the matching UID/GID.

See [README-docker.md](README-docker.md) for detailed Docker deployment instructions.

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `dev-secret` |
| `API_KEY` | API key for REST API authentication | `default-api-key` |
| `DATABASE_URL` | Database connection string | `sqlite:///app.db` |
| `FLASK_CONFIG` | Configuration class | `config.Config` |
| `FLASK_DEBUG` | Enable debug mode | `false` |

## API Usage

Two authenticated API versions are available for external clients:
- **Base API** (`/api`) - Core functionality
- **Extended API** (`/api/v1`) - Additional features like latest reading and pagination

All endpoints (except `/api/status` and `/api/openapi.json`) require the `X-API-Key` header. (The SPA uses the separate unauthenticated `/ui-api` intended for same-origin use only.)

```bash
# Health check
curl http://localhost:5000/api/status

# OpenAPI 3.0 specification
curl http://localhost:5000/api/openapi.json

# List all meters
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/v1/meters

# Get latest reading for a meter (v1 only)
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/v1/meters/1/latest

# Get readings for a meter (with optional limit in v1)
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/v1/meters/1/readings?limit=5

# Add a new reading
curl -X POST \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"meter_id": 1, "reading_date": "2026-01-15", "value": 12345.67}' \
     http://localhost:5000/api/v1/readings
```

## CLI Commands

```bash
# Database
flask db upgrade              # Apply database migrations
flask db migrate -m "msg"     # Generate new migration

# Data management
flask seed-meters             # Create default meters (Strom, Gas, Wasser)
flask create-user             # Create a new user account
flask export-data data.json   # Export all data (meters, readings, tariffs) to JSON
flask import-data data.json   # Import data from JSON
flask import-data data.json --replace  # Replace all data

# Meters & weather
flask list-meters             # List meters with IDs and serial numbers
flask update-meter-serial --meter-id 1 --serial NEW-SERIAL
flask set-weather-overlay --meter-id 2         # Enable temperature overlay
flask set-weather-overlay --meter-id 2 --off   # Disable it
flask import-weather          # Import monthly DWD weather data
flask show-weather            # Display stored weather data

# Debugging
flask debug-readings          # Display readings and computed consumption
```

## Project Structure

```
flask-consumption/
├── app/
│   ├── __init__.py          # Application factory, CLI commands
│   ├── models.py            # SQLAlchemy models (User, Meter, MeterReading, Tariff, WeatherData)
│   ├── extensions.py        # Flask extensions
│   ├── services/            # Business logic
│   │   ├── costs.py         # Tariff selection, monthly/yearly costs, cost forecast
│   │   └── weather.py       # Heating degree days, weather series
│   ├── web_api/             # UI API blueprint (/ui-api) for the React SPA
│   │   ├── routes.py        # Dashboard, CRUD, costs, comparison, weather endpoints
│   │   └── serializers.py   # JSON serializers
│   ├── spa/                 # Serves the built React SPA (catch-all routing)
│   ├── api/                 # Base REST API blueprint (/api)
│   │   ├── routes.py        # API endpoints
│   │   └── openapi.json     # OpenAPI 3.0 specification
│   ├── api_v1/              # Extended REST API blueprint (/api/v1)
│   │   └── routes.py        # Additional endpoints (latest, pagination)
│   ├── pwa/                 # Progressive Web App blueprint (/pwa)
│   └── admin/               # Admin blueprint (/admin, export/import)
├── frontend/                # React SPA (Vite + React 18 + TypeScript)
│   ├── src/
│   │   ├── api/             # Typed API client
│   │   ├── lib/             # Formatting (German numbers), chart defaults
│   │   ├── components/      # Layout, cards, tables, dialogs
│   │   └── pages/           # One component per route
│   └── dist/                # Production build (served by Flask, not committed)
├── migrations/              # Alembic database migrations
├── tests/                   # Pytest test suite
├── config.py                # Configuration classes
├── run.py                   # Application entry point
├── Dockerfile               # Multi-stage build (Node frontend + Python app)
├── docker-compose.*.yml     # Docker Compose configurations
└── requirements.txt         # Python dependencies
```

## Tech Stack

- **Backend:** Flask, SQLAlchemy, Flask-WTF
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** React 18, TypeScript, Vite, Chart.js (react-chartjs-2), React Router
- **Testing:** pytest (backend), Vitest (frontend)
- **Deployment:** Docker (multi-stage), Gunicorn

## License

MIT License
