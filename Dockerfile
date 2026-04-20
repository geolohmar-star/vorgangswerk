# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein

FROM python:3.12-slim-bookworm

# Systemabhaengigkeiten (WeasyPrint + psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7 \
    postgresql-client \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhaengigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode kopieren
COPY . .

# Migrations + Server starten
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-9} --timeout 120 --max-requests 1000 --max-requests-jitter 100"]
