# Beitragen zu Vorgangswerk

Danke für dein Interesse! Vorgangswerk ist ein Open-Source-Projekt unter der [EUPL-1.2](LICENSE) und freut sich über Beiträge aus der Community – besonders von Menschen mit Verwaltungserfahrung.

---

## Womit du helfen kannst

- **Fehler melden** – du hast einen Bug gefunden
- **Feature-Ideen einbringen** – du kennst einen Verwaltungsprozess der fehlt
- **Code beisteuern** – du möchtest etwas umsetzen
- **Dokumentation verbessern** – Erklärungen, Übersetzungen, Beispiele
- **Testen** – du betreibst eine Instanz und gibst Feedback aus dem Alltag

---

## Fehler melden

Bitte [ein GitHub Issue öffnen](https://github.com/geolohmar-star/vorgangswerk/issues/new) mit:

- Kurze Beschreibung was passiert ist
- Was du erwartet hattest
- Schritte zur Reproduktion
- Version / Commit-Hash (`git log -1 --oneline`)
- Relevante Logs (`make logs`)

Keine persönlichen Daten oder Zugangsdaten in Issues einfügen.

---

## Entwicklungsumgebung aufsetzen

```bash
# 1. Repository forken und klonen
git clone https://github.com/DEIN-USERNAME/vorgangswerk.git
cd vorgangswerk

# 2. Python-Umgebung
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Datenbank starten (nur PostgreSQL via Docker)
docker compose up -d db

# 4. Umgebungsvariablen
cp .env.example .env
# SECRET_KEY und DB_PASSWORD in .env setzen

# 5. Migrationen + Superuser
python manage.py migrate
python manage.py createsuperuser

# 6. Demo-Daten laden (empfohlen)
python manage.py demo_daten

# 7. Entwicklungsserver starten
python manage.py runserver
```

Die Anwendung ist unter **http://localhost:8000** erreichbar.

---

## Workflow für Pull Requests

```bash
# 1. Feature-Branch anlegen (von master)
git checkout -b feature/mein-feature

# 2. Änderungen entwickeln und testen
# ...

# 3. Commit
git add .
git commit -m "Feat: kurze Beschreibung"

# 4. Push und Pull Request öffnen
git push origin feature/mein-feature
```

Dann auf GitHub einen Pull Request gegen `master` öffnen.

---

## Commit-Nachrichten

Wir verwenden ein einfaches Präfix-Schema:

| Präfix | Bedeutung |
|---|---|
| `Feat:` | Neue Funktion |
| `Fix:` | Fehlerbehebung |
| `Chore:` | Wartung, Dependencies, Konfiguration |
| `Docs:` | Dokumentation |
| `Perf:` | Performance-Verbesserung |
| `Security:` | Sicherheitsrelevante Änderung |
| `Refactor:` | Umstrukturierung ohne Funktionsänderung |

Beispiele:
```
Feat: Feldtyp "Adresse" mit PLZ-Autovervollständigung
Fix: ZIP-Export schlägt fehl wenn Pfad-Name Sonderzeichen enthält
Docs: Betriebsanleitung für Backup-Worker ergänzt
```

---

## Code-Stil

- **Python**: PEP 8, keine externen Linter-Konfigurationen nötig
- **Django**: Class-based Views wo sinnvoll, ansonsten Function-based Views
- **Templates**: Bootstrap 5, kein eigenes CSS-Framework einführen
- **JavaScript**: Vanilla JS, kein Build-Schritt, kein npm
- **Sprache im Code**: Deutsch für Kommentare, Variablen und UI-Texte; Englisch für technische Bezeichner (HTTP, MIME-Typen etc.) ist OK
- **SPDX-Header**: Jede neue `.py`-Datei bekommt:
  ```python
  # SPDX-License-Identifier: EUPL-1.2
  # Copyright (C) 2026 Georg Klein
  ```

---

## Projektstruktur verstehen

```
vorgangswerk/
├── core/           Benutzerverwaltung, Dashboard, REST-API
├── formulare/      Pfad-Editor, Antragsstrecken, Quiz-Modul
├── workflow/       Workflow-Engine, Arbeitsstapel, Prozesszentrale
├── dokumente/      DMS, OnlyOffice-WOPI-Integration
├── kommunikation/  IMAP-Worker, Postfach, Benachrichtigungen
├── korrespondenz/  Briefvorlagen, Bescheid-Erstellung
├── signatur/       FES (pyHanko) + QES (sign.me)
├── portal/         KI-Formularanalyse, Stripe-Integration
├── quiz/           Fragenpools, BAMF-Einbürgerungstest
├── bundid/         SAML-SP für BundID-Anbindung
├── post/           Postbuch, Organisationsverzeichnis
├── sicherung/      Automatisches Backup (täglich/wöchentlich/monatlich)
├── datenschutz/    DSGVO-Werkzeuge
├── config/         Django-Einstellungen, URLs, WSGI/ASGI
├── static/         JavaScript, CSS (Bootstrap 5)
└── templates/      Basis-Templates
```

Jede App ist eigenständig und folgt dem Standard-Django-Layout (`models.py`, `views.py`, `urls.py`, `admin.py`).

---

## Neue App hinzufügen

```bash
python manage.py startapp meine_app

# Danach:
# 1. In config/settings.py unter INSTALLED_APPS eintragen
# 2. URLs in config/urls.py einbinden
# 3. SPDX-Header in alle neuen .py-Dateien
# 4. Migration erstellen: python manage.py makemigrations meine_app
```

---

## Migrationen

```bash
# Neue Migration erstellen
python manage.py makemigrations

# Alle Migrationen anwenden
python manage.py migrate

# Migrationsstatus prüfen
python manage.py showmigrations
```

Migrationen **nicht** squashen oder umbenennen – das bricht bestehende Installationen.

---

## Lizenz

Mit deinem Beitrag stimmst du zu, dass er unter der [EUPL-1.2](LICENSE) veröffentlicht wird. Das ist eine von der EU-Kommission entwickelte Open-Source-Lizenz, die speziell für Verwaltungssoftware konzipiert wurde.

---

## Fragen?

- [GitHub Issues](https://github.com/geolohmar-star/vorgangswerk/issues) für Bugs und Features
- [vorgangswerk@georg-klein.com](mailto:vorgangswerk@georg-klein.com) für alles andere
