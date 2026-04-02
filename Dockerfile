# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein

FROM python:3.12-slim

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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhaengigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode kopieren
COPY . .

# Statische Dateien einsammeln
RUN python manage.py collectstatic --noinput

# Migrations + Server starten
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
