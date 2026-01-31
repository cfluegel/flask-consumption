# Flask Consumption Tracker

A Flask-based web application for tracking utility consumption (electricity, natural gas, water). Record monthly meter readings, visualize consumption trends with charts, and access data via REST API.

## Features

- Track multiple utility meters (Strom/Electricity, Gas, Wasser/Water)
- Record and manage monthly meter readings
- Visualize consumption data with Chart.js
- REST API for mobile app integration
- Docker deployment support (SQLite or PostgreSQL)
- Data import/export functionality
- German language UI with sand-colored theme

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/cfluegel/flask-consumption.git
cd flask-consumption

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade
flask seed-meters

# Create a user
flask create-user --username admin --email admin@example.com

# Run development server
python run.py
```

The application will be available at `http://127.0.0.1:5000`

### Docker Deployment

```bash
# Simple setup with SQLite
docker compose -f docker-compose.sqlite.yml up -d

# Production setup with PostgreSQL
docker compose -f docker-compose.postgres.yml up -d

# Initialize meters and create user
docker compose -f docker-compose.sqlite.yml exec app flask seed-meters
docker compose -f docker-compose.sqlite.yml exec app flask create-user --username admin --email admin@example.com
```

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

Two API versions are available:
- **Base API** (`/api`) - Core functionality
- **Extended API** (`/api/v1`) - Additional features like latest reading and pagination

All endpoints (except `/api/status` and `/api/openapi.json`) require the `X-API-Key` header.

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
flask export-data data.json   # Export all data to JSON
flask import-data data.json   # Import data from JSON
flask import-data data.json --replace  # Replace all data

# Utilities
flask list-readings           # Display all readings
flask show-consumption        # Show consumption statistics
```

## Project Structure

```
flask-consumption/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models.py            # SQLAlchemy models (User, Meter, MeterReading)
│   ├── extensions.py        # Flask extensions
│   ├── main/                # Web UI blueprint
│   │   ├── routes.py        # View functions
│   │   ├── forms.py         # WTForms
│   │   └── templates/       # Jinja2 templates
│   ├── api/                 # Base REST API blueprint (/api)
│   │   ├── routes.py        # API endpoints
│   │   └── openapi.json     # OpenAPI 3.0 specification
│   └── api_v1/              # Extended REST API blueprint (/api/v1)
│       └── routes.py        # Additional endpoints (latest, pagination)
├── migrations/              # Alembic database migrations
├── config.py                # Configuration classes
├── run.py                   # Application entry point
├── Dockerfile               # Docker image definition
├── docker-compose.*.yml     # Docker Compose configurations
└── requirements.txt         # Python dependencies
```

## Tech Stack

- **Backend:** Flask, SQLAlchemy, Flask-Login, Flask-WTF
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** Jinja2 templates, Chart.js
- **Deployment:** Docker, Gunicorn

## License

MIT License
