# Docker Deployment Guide

This guide explains how to deploy the Flask Consumption Tracker using Docker.

## Prerequisites

- Docker and Docker Compose installed
- (Optional) Docker Hub account for pushing images

## Quick Start

### Using Pre-built Image

```bash
# SQLite (simplest setup)
docker compose -f docker-compose.sqlite.yml up -d

# PostgreSQL (recommended for production)
docker compose -f docker-compose.postgres.yml up -d
```

The application will be available at `http://localhost:5000`

### Building Locally

```bash
# Build the image
docker build -t cfluegel/flask-consumption:latest .

# Run with SQLite
docker compose -f docker-compose.sqlite.yml up -d
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `change-me-in-production` |
| `API_KEY` | API key for mobile app authentication | `change-me-in-production` |
| `DATABASE_URL` | Database connection string | (set by compose file) |
| `FLASK_CONFIG` | Configuration class | `config.ProductionConfig` |

### PostgreSQL-specific Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | `consumption` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `consumption` |
| `POSTGRES_DB` | PostgreSQL database name | `consumption` |

## Configuration

### Using an .env File

Create a `.env` file in the project directory:

```bash
# .env
SECRET_KEY=your-secure-secret-key-here
API_KEY=your-secure-api-key-here

# For PostgreSQL setup
POSTGRES_USER=consumption
POSTGRES_PASSWORD=a-secure-database-password
POSTGRES_DB=consumption
```

Docker Compose automatically loads this file.

### Generating Secure Keys

```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate an API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Deployment Options

### Option 1: SQLite (Simple)

Best for single-user or low-traffic deployments.

```bash
docker compose -f docker-compose.sqlite.yml up -d
```

Data is stored in a Docker volume (`app-data`).

### Option 2: PostgreSQL (Production)

Recommended for production deployments.

```bash
# Start the stack
docker compose -f docker-compose.postgres.yml up -d

# View logs
docker compose -f docker-compose.postgres.yml logs -f app
```

## Database Migrations

Migrations run automatically when the container starts. To run them manually:

```bash
# SQLite setup
docker compose -f docker-compose.sqlite.yml exec app flask db upgrade

# PostgreSQL setup
docker compose -f docker-compose.postgres.yml exec app flask db upgrade
```

## Seeding Initial Data

Create the default meters (Strom, Gas, Wasser):

```bash
# SQLite setup
docker compose -f docker-compose.sqlite.yml exec app flask seed-meters

# PostgreSQL setup
docker compose -f docker-compose.postgres.yml exec app flask seed-meters
```

## Creating a User

```bash
# SQLite setup
docker compose -f docker-compose.sqlite.yml exec app flask create-user \
    --username admin \
    --email admin@example.com

# PostgreSQL setup
docker compose -f docker-compose.postgres.yml exec app flask create-user \
    --username admin \
    --email admin@example.com
```

You will be prompted to enter a password.

## Useful Commands

```bash
# View running containers
docker compose -f docker-compose.sqlite.yml ps

# View application logs
docker compose -f docker-compose.sqlite.yml logs -f app

# Stop the application
docker compose -f docker-compose.sqlite.yml down

# Stop and remove volumes (WARNING: deletes data)
docker compose -f docker-compose.sqlite.yml down -v

# Restart the application
docker compose -f docker-compose.sqlite.yml restart

# Execute a command in the container
docker compose -f docker-compose.sqlite.yml exec app flask --help
```

## Pushing to Docker Hub

```bash
# Login to Docker Hub
docker login

# Build and tag
docker build -t cfluegel/flask-consumption:latest .

# Push to Docker Hub
docker push cfluegel/flask-consumption:latest

# Tag a specific version
docker tag cfluegel/flask-consumption:latest cfluegel/flask-consumption:1.0.0
docker push cfluegel/flask-consumption:1.0.0
```

## Example: Complete Production Setup

1. Create project directory:
   ```bash
   mkdir consumption-tracker && cd consumption-tracker
   ```

2. Download compose file:
   ```bash
   curl -O https://raw.githubusercontent.com/cfluegel/flask-consumption/main/docker-compose.postgres.yml
   ```

3. Create `.env` file:
   ```bash
   cat > .env << 'EOF'
   SECRET_KEY=your-secure-secret-key-here
   API_KEY=your-secure-api-key-here
   POSTGRES_PASSWORD=secure-database-password
   EOF
   ```

4. Start the application:
   ```bash
   docker compose -f docker-compose.postgres.yml up -d
   ```

5. Initialize the database:
   ```bash
   docker compose -f docker-compose.postgres.yml exec app flask seed-meters
   docker compose -f docker-compose.postgres.yml exec app flask create-user \
       --username admin --email admin@example.com
   ```

6. Access the application at `http://localhost:5000`

## API Access

The REST API is available at `/api/v1/`. All endpoints require the `X-API-Key` header:

```bash
# List all meters
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/v1/meters

# Get latest reading for a meter
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/v1/meters/1/latest

# Add a new reading
curl -X POST \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"meter_id": 1, "reading_date": "2026-01-15", "value": 12345.67}' \
     http://localhost:5000/api/v1/readings
```

## Troubleshooting

### Container won't start

Check the logs:
```bash
docker compose -f docker-compose.postgres.yml logs app
```

### Database connection errors (PostgreSQL)

Ensure the database container is healthy:
```bash
docker compose -f docker-compose.postgres.yml ps
```

Wait for the `db` service to show `healthy` status.

### Permission errors with SQLite

The data directory must be writable. The container runs as non-root user `appuser`.

### Reset everything

```bash
docker compose -f docker-compose.postgres.yml down -v
docker compose -f docker-compose.postgres.yml up -d
```

Warning: This deletes all data!
