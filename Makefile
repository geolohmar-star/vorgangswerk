# Vorgangswerk – Makefile
# Kurzformen für häufige Docker-Befehle

.PHONY: start stop restart build logs shell migrate superuser update

## Starten (im Hintergrund)
start:
	docker compose up -d

## Stoppen
stop:
	docker compose down

## Neu starten
restart:
	docker compose restart web

## Image neu bauen und starten
build:
	docker compose up -d --build

## Logs live verfolgen
logs:
	docker compose logs -f web

## Django-Shell öffnen
shell:
	docker compose exec web python manage.py shell

## Migrationen ausführen
migrate:
	docker compose exec web python manage.py migrate

## Superuser anlegen
superuser:
	docker compose exec web python manage.py createsuperuser

## Update: Code holen, Image neu bauen, neu starten
update:
	git pull
	docker compose up -d --build
	docker compose exec web python manage.py migrate

## Erstes Setup: .env anlegen + starten
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ""; \
		echo "✓ .env wurde angelegt."; \
		echo "  Bitte SECRET_KEY und DB_PASSWORD in .env setzen:"; \
		echo "  SECRET_KEY: python -c \"import secrets; print(secrets.token_urlsafe(50))\""; \
		echo ""; \
	else \
		echo ".env existiert bereits."; \
	fi
