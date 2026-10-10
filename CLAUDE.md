# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Web application for tracking consumption of utilities (electricity, natural gas, water). Users record monthly meter readings which are stored in a database and visualized with charts. Includes cost tracking via per-meter tariff history, consumption predictions, year-over-year comparison, and weather analysis (heating degree days).

**Architecture:** Flask backend serving a React SPA (main UI) plus a separate PWA, two authenticated REST APIs, and an admin area.

## Commands

**Always use the virtual environment:**
```bash
source venv/bin/activate
```

### Setup (first time)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
flask seed-meters
cd frontend && npm install && npm run build && cd ..
```

### Run Development Server
```bash
source venv/bin/activate
python run.py
```
Server runs on `127.0.0.1:5000` and serves the built SPA from `frontend/dist`.

**Frontend dev with hot reload:** additionally run `cd frontend && npm run dev` → Vite on `127.0.0.1:5173` proxies `/ui-api`, `/api`, `/admin`, `/pwa`, `/apidocs` to Flask.

Environment variables:
- `FLASK_CONFIG` - Config class (default: `config.Config`, options: `config.DevelopmentConfig`, `config.ProductionConfig`, `config.TestingConfig`)
- `FLASK_RUN_HOST` / `FLASK_RUN_PORT` - Host/port
- `FLASK_DEBUG` - Enable debug mode (`true`/`1`/`t`)
- `API_KEY` - API key for mobile API (default: `default-api-key`)

### Database Migrations
```bash
flask db migrate -m "Description"   # Generate migration
flask db upgrade                    # Apply migrations
```

### Seed Data & CLI
```bash
flask seed-meters                               # Create initial meters (Strom, Gas, Wasser)
flask set-weather-overlay --meter-id 2 [--off]  # Toggle temperature overlay per meter
flask export-data f.json / flask import-data f.json [--replace]  # incl. tariffs
flask import-weather                            # DWD monthly weather data
```

### Run Tests
```bash
pytest                          # Backend (needs venv)
cd frontend && npx vitest run   # Frontend unit tests
cd frontend && npm run build    # TypeScript check + production build
```

## Architecture

### Application Factory Pattern
- `run.py` - Entry point, creates app via factory
- `app/__init__.py` - `create_app()` factory function + CLI commands
- `config.py` - Environment configs (Development, Production, Testing)

### Blueprint Structure
```
app/
├── spa/            # Serves built React SPA from frontend/dist (/ + catch-all)
├── web_api/        # UI API for the SPA (/ui-api prefix, no auth, CSRF-exempt)
│   ├── routes.py   # Dashboard, readings/tariffs CRUD, costs, year-comparison, weather
│   └── serializers.py
├── services/       # Business logic shared by blueprints
│   ├── costs.py    # tariff_for_month, monthly_costs, yearly_cost, forecast_cost_current_month
│   └── weather.py  # heating_degree_days (base 15°C), weather_series_for_meter
├── api/            # Base REST API blueprint (/api prefix, X-API-Key)
├── api_v1/         # Extended REST API blueprint (/api/v1 prefix, X-API-Key)
├── pwa/            # Progressive Web App blueprint (/pwa prefix)
└── admin/          # Admin blueprint (/admin prefix): JSON export/import (standalone template)
```

The SPA blueprint is registered LAST so `/api`, `/ui-api`, `/pwa`, `/admin`, `/apidocs` take precedence over the catch-all. If `frontend/dist` is missing, it returns a 503 hint instead of failing (tests don't require a frontend build).

### Frontend (`frontend/`)
Vite + React 18 + TypeScript (strict), React Router, Chart.js via react-chartjs-2. No UI framework; plain CSS with sand-theme custom properties in `src/theme.css`. German UI, German number formatting in `src/lib/format.ts` (mirrors the `de_number` Jinja filter). Pages in `src/pages/`, typed API client in `src/api/`. Routes: `/` (dashboard cards), `/zaehler/:id`, `/ablesung/neu`, `/kosten`, `/tarife`, `/vergleich`, `/grafiken/:id`, `/einstellungen`.

### Models (`app/models.py`)
- `User` - Auth model (kept for CLI/user management; no login flow in the web UI anymore)
- `Meter` - Utility meter (name, unit, serial_number, weather_overlay) + consumption/prediction methods (`get_monthly_consumption` pro-rata engine, `get_3month_average`, `get_prediction_weighted/seasonal/calculated`, `get_yearly_consumption`)
- `MeterReading` - Meter reading (meter_id, reading_date, value); unique per (meter_id, reading_date)
- `Tariff` - Price history per meter (price_per_unit = Arbeitspreis €/unit, base_price_monthly = Grundpreis €/month, valid_from); unique per (meter_id, valid_from). One tariff applies per whole month (latest valid_from ≤ first of month); mid-month changes are not pro-rated.
- `WeatherData` - DWD monthly weather (station_id, year_month YYYYMM, temperatures etc.)

### API Endpoints

**UI API (`/ui-api`)** — same-origin JSON API for the SPA, no auth, CSRF-exempt. Months serialized as `{year, month, label}`; dates ISO. Returns 409 with `{error}` on duplicate reading dates / tariff valid_from.
- `GET /ui-api/dashboard` - All meters with last reading, stats, predictions, yearly/forecast costs, current tariff
- `GET /ui-api/meters/<id>/consumption|readings|tariffs|costs|weather`
- `GET /ui-api/meters/<id>/year-comparison?year=YYYY`
- `POST/PUT/DELETE /ui-api/readings[/<id>]`, `POST /ui-api/meters/<id>/tariffs`, `PUT/DELETE /ui-api/tariffs/<id>`
- `PATCH /ui-api/meters/<id>` - name, serial_number, weather_overlay

**Base API (`/api`)** and **Extended API (`/api/v1`)** — external clients (PWA, mobile); require `X-API-Key` header except `/api/status` and `/api/openapi.json`. Unchanged contract: meters list, readings (with `limit` pagination in v1), latest reading (v1), create reading.

**PWA (`/pwa`)** — mobile web app using `/api/v1` with localStorage API key. Unchanged.

**Admin (`/admin`)** — export/import UI. Export JSON contains `meters` (incl. `weather_overlay`), `readings`, `tariffs`; import accepts old exports without `tariffs`. No authentication.

## Deployment

Docker multi-stage build: Node stage builds `frontend/dist`, Python stage copies it in. `docker-entrypoint.sh` runs `flask db upgrade` on start, so upgrading a live installation (e.g. verbrauch.gt57d.de) is pull/rebuild + restart — migrations and frontend ship automatically.

## Tech Stack
- Flask, SQLAlchemy ORM (SQLite default, PostgreSQL via `DATABASE_URL`), Flask-Migrate, Flask-WTF (admin form CSRF)
- React 18 + TypeScript + Vite, Chart.js, React Router
- pytest (backend), Vitest (frontend)

## Design Specifications
- Sand-colored theme via CSS variables (--sand-light #f5e6c8, --sand-medium #e8d4a8, --sand-dark #d4a574, --sand-accent #b8860b)
- German language UI, German number format (1.234,56)
- Mobile-first: viewport meta, 44px touch targets, bottom tab navigation ≤768px, 16px inputs (prevents iOS zoom), tables in overflow containers or card layouts
