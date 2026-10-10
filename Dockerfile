# Frontend-Build (React-SPA)
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py run.py docker-entrypoint.sh ./
COPY app ./app
COPY migrations ./migrations
COPY --from=frontend /frontend/dist ./frontend/dist

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Create non-root user and data directory
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

# Environment variables
ENV FLASK_CONFIG=config.ProductionConfig
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]
