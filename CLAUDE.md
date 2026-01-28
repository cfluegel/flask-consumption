# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask-based web application for tracking consumption of utilities (electricity, natural gas, water). Users record monthly meter readings which are stored in a database and visualized with charts.

**Current state:** Core meter reading functionality implemented with web UI and mobile API.

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
```

### Run Development Server
```bash
source venv/bin/activate
python run.py
```
Server runs on `127.0.0.1:5000` by default.

Environment variables:
- `FLASK_CONFIG` - Config class (default: `config.Config`, options: `config.DevelopmentConfig`, `config.ProductionConfig`, `config.TestingConfig`)
- `FLASK_RUN_HOST` - Host address
- `FLASK_RUN_PORT` - Port number
- `FLASK_DEBUG` - Enable debug mode (`true`/`1`/`t`)
- `API_KEY` - API key for mobile API (default: `default-api-key`)

### Database Migrations
```bash
flask db migrate -m "Description"   # Generate migration
flask db upgrade                    # Apply migrations
```

### Seed Data
```bash
flask seed-meters    # Create initial meters (Strom, Gas, Wasser)
```

### Run Tests
```bash
pytest
```

## Architecture

### Application Factory Pattern
- `run.py` - Entry point, creates app via factory
- `app/__init__.py` - `create_app()` factory function
- `config.py` - Environment configs (Development, Production, Testing)

### Blueprint Structure
```
app/
├── main/           # Main web UI blueprint
│   ├── routes.py   # View functions (dashboard, meter detail, readings CRUD)
│   ├── forms.py    # WTForms (LoginForm, ReadingForm)
│   └── templates/  # Jinja2 templates
└── api/            # REST API blueprint (/api prefix)
    └── routes.py   # API endpoints with X-API-Key authentication
```

### Extensions (`app/extensions.py`)
- `db` - SQLAlchemy database
- `migrate` - Flask-Migrate for Alembic migrations
- `login_manager` - Flask-Login for authentication

### Models (`app/models.py`)
- `User` - Authentication model with password hashing
- `Meter` - Utility meter (name, unit, serial_number)
- `MeterReading` - Meter reading (meter_id, reading_date, value)

### API Endpoints
- `GET /api/status` - Health check (no auth)
- `GET /api/meters` - List all meters
- `GET /api/meters/<id>/readings` - Get readings for a meter
- `POST /api/readings` - Create a new reading

All API endpoints (except /status) require `X-API-Key` header.

## Tech Stack
- Flask with Jinja2 templates
- SQLAlchemy ORM (SQLite default, PostgreSQL planned via `DATABASE_URL`)
- Flask-Login for authentication
- Flask-WTF for forms with CSRF protection
- Chart.js for data visualization
- HTMX for dynamic UI (planned)

## Design Specifications
- Sand-colored theme with CSS variables (--sand-light, --sand-medium, --sand-dark, --sand-accent)
- German language UI
