# CLAUDE.md – Vorgangswerk

## Deployment

**Immer vollständig neu bauen, niemals `docker cp`:**

```bash
docker compose build web && docker compose up -d
```

`docker cp` ist ephemer – Änderungen gehen beim nächsten `up -d` verloren.

## Stack

- Django 5 + PostgreSQL (psycopg2)
- Bootstrap 5 (lokal, kein CDN)
- Pydantic v2 für KI-Output-Validierung (`portal/services.py`)
- WeasyPrint für PDF-Generierung
- Gunicorn als WSGI-Server im Container

## Konventionen

- Deutsche Bezeichner in Models, Views und Templates (z.B. `pfad`, `schritt`, `sitzung`)
- Keine Mandantenfähigkeit – jeder Betreiber führt seine eigene Instanz
- Neue Migrations immer im Container ausführen: `docker compose exec web python manage.py migrate`
