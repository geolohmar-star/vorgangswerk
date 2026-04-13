# Betriebsanleitung – Vorgangswerk

Dieser Leitfaden richtet sich an Administratoren, die eine Vorgangswerk-Instanz selbst betreiben.

---

## Inhaltsverzeichnis

1. [Erstes Setup](#erstes-setup)
2. [Updates einspielen](#updates-einspielen)
3. [Backup & Restore](#backup--restore)
4. [Logs & Monitoring](#logs--monitoring)
5. [Benutzerverwaltung](#benutzerverwaltung)
6. [E-Mail konfigurieren](#e-mail-konfigurieren)
7. [OnlyOffice anbinden](#onlyoffice-anbinden)
8. [BundID-Anbindung](#bundid-anbindung)
9. [Reverse Proxy / HTTPS](#reverse-proxy--https)
10. [Troubleshooting](#troubleshooting)

---

## Erstes Setup

```bash
# 1. Repository klonen
git clone https://github.com/geolohmar-star/vorgangswerk.git
cd vorgangswerk

# 2. Umgebungsvariablen anlegen
make setup
# .env öffnen und mindestens SECRET_KEY + DB_PASSWORD setzen:
# SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")

# 3. Image laden und starten (fertiges Image – empfohlen)
make pull

# 4. Superuser anlegen
make superuser

# 5. Optional: Demo-Daten für erste Orientierung
make demo
```

Die Anwendung ist unter **http://localhost:8100** erreichbar.

---

## Updates einspielen

### Option A – Fertiges Image (empfohlen)

```bash
make pull
# Lädt das neue Image von ghcr.io, startet neu und migriert automatisch
```

### Option B – Selbst bauen

```bash
make update
# git pull + docker build + migrate in einem Schritt
```

### Was passiert beim Update?

1. Neues Image wird geladen
2. Container werden neu gestartet (kurze Downtime ~10 Sekunden)
3. Datenbankmigrationen laufen automatisch beim Start
4. Statische Dateien werden neu eingesammelt

> **Hinweis:** Vor größeren Updates (neue Hauptversion) empfiehlt sich ein manuelles Backup.

---

## Backup & Restore

Vorgangswerk enthält einen eingebauten Backup-Worker, der automatisch sichert:

| Zeitplan | Aufbewahrung |
|---|---|
| Täglich 02:00 Uhr | 7 Tage |
| Sonntags | 4 Wochen |
| 1. des Monats | 12 Monate |

Sicherungen liegen im Volume `sicherungen` → gemountet unter `/app/sicherungen` im Container.

### Backup manuell auslösen

```bash
docker compose exec web python manage.py backup_erstellen
```

### Backup-Dateien einsehen

```bash
docker compose exec web ls -lh /app/sicherungen/
```

### Sicherungen auf den Host kopieren

```bash
docker cp $(docker compose ps -q web):/app/sicherungen ./meine-sicherungen
```

### Restore

```bash
# 1. Container stoppen
make stop

# 2. Sicherungsdatei in den Container kopieren
docker cp ./sicherung-2026-04-01.json.gz $(docker compose ps -q web):/app/sicherungen/

# 3. Container starten
make start

# 4. Restore ausführen
docker compose exec web python manage.py backup_wiederherstellen sicherung-2026-04-01.json.gz
```

---

## Logs & Monitoring

### Logs live verfolgen

```bash
make logs                          # Web-Container
docker compose logs -f worker      # E-Mail-Worker
docker compose logs -f backup      # Backup-Worker
docker compose logs -f db          # PostgreSQL
```

### Einzelne Fehler finden

```bash
docker compose logs web | grep ERROR
docker compose logs web | grep "500"
```

### Container-Status

```bash
docker compose ps
```

### Ressourcenverbrauch

```bash
docker stats
```

### Healthcheck

```bash
curl -f http://localhost:8100/health/ && echo "OK"
```

---

## Benutzerverwaltung

### Superuser anlegen

```bash
make superuser
```

### Benutzer per Shell verwalten

```bash
make shell
# In der Django-Shell:
from django.contrib.auth import get_user_model
User = get_user_model()

# Neuen Benutzer anlegen
u = User.objects.create_user('max.mustermann', 'max@beispiel.de', 'Passwort123!')
u.first_name = 'Max'
u.last_name = 'Mustermann'
u.save()

# Passwort zurücksetzen
u = User.objects.get(email='max@beispiel.de')
u.set_password('NeuesPasswort!')
u.save()

# Zum Admin machen
u.is_staff = True
u.save()
```

### MFA / TOTP

Benutzer können unter **Mein Profil → Sicherheit** einen TOTP-Authenticator einrichten (Google Authenticator, Aegis etc.).

Brute-Force-Schutz ist über `django-axes` aktiv (5 Fehlversuche → 1 Stunde Sperre).

Gesperrte IP entsperren:
```bash
docker compose exec web python manage.py axes_reset
```

---

## E-Mail konfigurieren

### Ausgehende E-Mails (SMTP)

In `.env`:
```env
EMAIL_HOST=smtp.beispiel.de
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@beispiel.de
EMAIL_HOST_PASSWORD=geheimes-passwort
DEFAULT_FROM_EMAIL=Vorgangswerk <noreply@beispiel.de>
```

### Eingehende E-Mails (IMAP-Worker)

```env
IMAP_HOST=imap.beispiel.de
IMAP_PORT=993
IMAP_USER=eingang@beispiel.de
IMAP_PASSWORD=geheimes-passwort
```

Der `worker`-Container pollt das Postfach alle 60 Sekunden und legt eingegangene E-Mails im Postfach-Modul ab.

### E-Mail-Versand testen

```bash
docker compose exec web python manage.py sendtestemail admin@beispiel.de
```

---

## OnlyOffice anbinden

Vorgangswerk nutzt OnlyOffice über das WOPI-Protokoll für die Dokumentenbearbeitung im Browser.

### Externe OnlyOffice-Instanz (empfohlen)

```env
ONLYOFFICE_URL=https://office.beispiel.de
ONLYOFFICE_INTERNAL_URL=http://office.intern:80
ONLYOFFICE_JWT_SECRET=geheimes-jwt-secret
```

### Eigener OnlyOffice-Container (lokal)

```bash
docker compose --profile onlyoffice up -d
```

```env
ONLYOFFICE_URL=http://localhost:8016
ONLYOFFICE_INTERNAL_URL=http://onlyoffice:80
ONLYOFFICE_JWT_SECRET=vorgangswerk-oo-secret
ONLYOFFICE_PORT=8016
```

> **Wichtig:** `WOPI_BASE_URL` muss die URL sein, unter der der OnlyOffice-Container den Vorgangswerk-Server erreicht (nicht `localhost` wenn OnlyOffice im Docker-Netz läuft → `http://host.docker.internal:8100`).

---

## BundID-Anbindung

Vorgangswerk implementiert einen SAML 2.0 Service Provider für die BundID-Anmeldung.

### Testumgebung (BundID-Simulator)

```bash
docker compose --profile bundid up -d
```

```env
BUNDID_SP_ENTITY_ID=vorgangswerk-test
BUNDID_IDP_SSO_URL=http://bundid-sim:8080/saml
```

Simulator-UI: http://localhost:8089 (Testnutzer U01–U07)

### Produktivbetrieb

1. SP-Metadaten abrufen: `https://deine-instanz.de/bundid/metadata/`
2. SP-Registrierung beim ITZBund beantragen
3. SP-Zertifikat hinterlegen (Details: [BundID-Dokumentation](https://www.bundid.de))
4. `.env` anpassen:
```env
BUNDID_SP_ENTITY_ID=https://deine-instanz.de/bundid/
BUNDID_IDP_SSO_URL=https://id.bund.de/idp/profile/SAML2/Redirect/SSO
```

---

## Reverse Proxy / HTTPS

### Cloudflare Tunnel (empfohlen für einfaches HTTPS)

```bash
cloudflared tunnel --url http://localhost:8100
```

In `.env`:
```env
ALLOWED_HOSTS=deine-subdomain.trycloudflare.com
VORGANGSWERK_BASE_URL=https://deine-subdomain.trycloudflare.com
```

### Nginx (klassisch)

```nginx
server {
    listen 443 ssl;
    server_name vorgangswerk.beispiel.de;

    location / {
        proxy_pass http://localhost:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }
}
```

In `.env`:
```env
ALLOWED_HOSTS=vorgangswerk.beispiel.de
VORGANGSWERK_BASE_URL=https://vorgangswerk.beispiel.de
```

> **Hinweis:** `SECURE_PROXY_SSL_HEADER` ist bereits gesetzt – Vorgangswerk erkennt HTTPS automatisch wenn der Proxy `X-Forwarded-Proto: https` sendet.

---

## Troubleshooting

### Container startet nicht

```bash
docker compose logs web | tail -50
```

Häufige Ursachen:
- `SECRET_KEY` nicht gesetzt → `bitte-aendern` in `.env` ersetzen
- `DB_PASSWORD` nicht gesetzt
- Port 8100 bereits belegt → `lsof -i :8100`

### Datenbank nicht erreichbar

```bash
docker compose ps db          # Läuft der DB-Container?
docker compose logs db        # Fehler in den DB-Logs?
```

Wenn die DB nicht healthy ist: `docker compose restart db`

### Migrationen fehlgeschlagen

```bash
docker compose exec web python manage.py showmigrations | grep "\[ \]"
docker compose exec web python manage.py migrate --verbosity 2
```

### Statische Dateien fehlen (CSS/JS lädt nicht)

```bash
docker compose exec web python manage.py collectstatic --noinput
docker compose restart web
```

### Datei-Upload schlägt fehl

Maximale Upload-Größe prüfen. In Nginx: `client_max_body_size 50M;` setzen.

### E-Mail wird nicht versandt

```bash
docker compose exec web python manage.py sendtestemail test@beispiel.de
docker compose logs worker | grep ERROR
```

SMTP-Einstellungen in `.env` prüfen. Port 587 (STARTTLS) oder 465 (SSL) verwenden.

### OnlyOffice öffnet Dokumente nicht

1. `WOPI_BASE_URL` muss von OnlyOffice-Container erreichbar sein
2. JWT-Secret in `.env` und OnlyOffice-Konfiguration müssen übereinstimmen
3. Logs: `docker compose logs web | grep WOPI`

### Speicherplatz voll

```bash
docker system df                        # Verbrauch anzeigen
docker system prune -f                  # Ungenutzte Images/Container löschen
docker compose exec web du -sh /app/sicherungen/  # Backup-Größe
```

Alte Sicherungen werden automatisch rotiert, aber bei knappem Speicher manuell prüfen.

---

## Nützliche Befehle

```bash
make start       # Starten
make stop        # Stoppen
make restart     # Web-Container neu starten
make logs        # Logs live
make shell       # Django-Shell
make migrate     # Migrationen ausführen
make superuser   # Superuser anlegen
make demo        # Demo-Daten laden
make pull        # Neues Image laden + neu starten
make update      # Code + Build + Migrate
```

---

## Support

Bugs und Fragen: [GitHub Issues](https://github.com/geolohmar-star/vorgangswerk/issues)

E-Mail: [vorgangswerk@georg-klein.com](mailto:vorgangswerk@georg-klein.com)
