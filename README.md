# Vorgangswerk

**Digitale Vorgangsbearbeitung für die öffentliche Verwaltung**

Vorgangswerk ist eine quelloffene Plattform zur digitalen Bearbeitung von Verwaltungsvorgängen. Sie ermöglicht es Behörden und Organisationen, Antragsformulare, Workflows, Dokumente und Kommunikation in einer einheitlichen Anwendung zu verwalten – OZG-konform und selbst gehostet.

Lizenz: [EUPL-1.2](LICENSE) · Sprache: Deutsch · Stack: Django · PostgreSQL · Docker

---

## Screenshots

**Visueller Pfad-Editor** – Verzweigte Antragsformulare per Drag & Drop

![Pfad-Editor](docs/screenshots/editor_graph.png)

**Prozesszentrale** – Überfällige Tasks, laufende Workflows, Sachbearbeiter-Übersicht

![Prozesszentrale](docs/screenshots/prozesszentrale.png)

**Bürgerseitige Antragsstrecke** – Mit Fortschrittsbalken, Breadcrumb-Navigation und mobilem Layout

![Antragsstrecke](docs/screenshots/buerger_formular.png)

---

## Funktionsübersicht

### Formulare & Antragsstrecken
- Visueller **Pfad-Editor** zum Aufbau mehrstufiger Antragsformulare (Drag & Drop, Verzweigungen, Transitionen)
- Über 20 Feldtypen: Text, Auswahl, Datum, Datei-Upload, Unterschrift, Tabelle, Adresse, IBAN u. v. m.
- **Bedingte Felder** (`zeige_wenn`) – Felder ein-/ausblenden abhängig von anderen Eingaben
- **Öffentliche Antragsstrecken** – ohne Login, mit Tracking-Link für Antragsteller
- **Quiz & Prüfbögen** – Multiple-Choice-Tests mit automatischer Auswertung und Zertifikat (geeignet für Einweisungen, Schulungen, Einbürgerungstest)
- PDF-Ausgabe ausgefüllter Anträge (WeasyPrint)
- Webhook-Benachrichtigungen bei Abschluss (JSON-POST an externe Systeme)

### Workflow-Engine
- Modellierung von Geschäftsprozessen als visuelle Workflows (Knoten, Transitionen, Bedingungen)
- Aufgabenverwaltung mit Zuweisung an Benutzer und Teams
- Arbeitsstapel-Übersicht für Sachbearbeiter
- Prozesszentrale mit Gesamtüberblick aller laufenden Instanzen

### Dokumentenmanagementsystem (DMS)
- Verwaltung von Dokumenten mit Versionierung und Zugriffsschutz
- Integration von **OnlyOffice** (WOPI) zur direkten Bearbeitung im Browser
- Klassifizierung als öffentlich, intern oder sensibel
- Zeitlich begrenzte Zugriffsschlüssel für sensible Dokumente (AES-256-GCM)
- Automatisches Backup (täglich/wöchentlich/monatlich)

### Kommunikation
- IMAP-basierter **E-Mail-Worker** für eingehende Nachrichten
- Postfach-Ansicht mit Zuordnung zu Vorgängen
- E-Mail-Benachrichtigungen bei Workflow-Ereignissen

### Digitale Signatur
- **FES** (Fortgeschrittene Elektronische Signatur) intern via pyHanko
- **QES** (Qualifizierte Elektronische Signatur) via sign.me (Bundesdruckerei)
- Signaturstatus, Validierung und Zertifikatsverwaltung

### Portal (KI-gestützter Formular-Import)
- Prepaid-Portal für externe Nutzer
- PDF-Formular hochladen → Claude KI analysiert Struktur → fertiger Pfad wird automatisch angelegt
- Stripe-Integration für Credit-Kauf
- BentoPDF / Stirling-PDF Integration als PDF-Werkzeug

### BundID-Anbindung ✓ BundID-ready
- **SAML SP-Integration implementiert** – Anbindung an `test.id.bund.de` / `id.bund.de` ohne Codeänderungen möglich
- HTTP-POST-Binding, ACS-Callback, SP-Metadaten-Endpoint
- Benutzeranlage und -aktualisierung anhand des bPK2 (Bereichsspezifisches Personenkennzeichen)
- Getestet mit offiziellem BundID-Simulator (`ghcr.io/ba-itsys/bundid-simulator`)
- Für Produktivbetrieb: SP-Registrierung beim ITZBund + SP-Zertifikat (kein Codeaufwand)
- OZG-Anforderung erfüllt: Kommunen benötigen kein eigenes Identity-Management

### Core & Administration
- Benutzerverwaltung mit MFA (TOTP), Brute-Force-Schutz (django-axes)
- REST-API via django-ninja
- Dashboard mit Live-Daten aus allen Apps
- Profilverwaltung mit Benachrichtigungseinstellungen

---

## Technischer Stack

| Komponente | Technologie |
|---|---|
| Backend | Django 5.x, Python 3.12 |
| Datenbank | PostgreSQL 16 |
| PDF-Generierung | WeasyPrint |
| Dokumenteneditor | OnlyOffice (WOPI) |
| Statische Dateien | Whitenoise |
| Webserver | Gunicorn |
| Deployment | Docker / Docker Compose |
| KI-Analyse | Anthropic Claude API |
| Zahlung | Stripe |
| Signatur | pyHanko, sign.me |

---

## Demo

Eine öffentliche Demo-Instanz ist verfügbar unter:

**https://vorgangswerk.georg-klein.com**

| Feld | Wert |
|---|---|
| Benutzer | `demo@vorgangswerk.de` |
| Passwort | `Demo1234!` |
| Rolle | Sachbearbeiter (kein Admin, keine Benutzerverwaltung) |

---

## Schnellstart (Docker)

**Voraussetzungen:** Docker und Docker Compose

```bash
# Repository klonen
git clone https://github.com/<org>/vorgangswerk.git
cd vorgangswerk

# Umgebungsvariablen anlegen
cp .env.example .env
# .env anpassen (SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS)

# Starten
docker compose up -d

# Datenbank initialisieren
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
```

Die Anwendung ist danach unter `http://localhost:8100` erreichbar.

### Optionale Dienste

```bash
# Mit eigenem OnlyOffice-Container
docker compose --profile onlyoffice up -d
```

---

## Umgebungsvariablen

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `SECRET_KEY` | Ja | Django Secret Key |
| `DB_PASSWORD` | Ja | PostgreSQL-Passwort |
| `ALLOWED_HOSTS` | Ja | Kommagetrennte Hostnamen |
| `ANTHROPIC_API_KEY` | Nein | Für KI-Formularanalyse (Portal) |
| `ONLYOFFICE_URL` | Nein | URL des OnlyOffice-Servers |
| `ONLYOFFICE_JWT_SECRET` | Nein | JWT-Secret für OnlyOffice |
| `SIGNME_API_KEY` | Nein | Für QES via sign.me |
| `EMAIL_HOST` | Nein | SMTP für ausgehende E-Mails |
| `IMAP_HOST` | Nein | IMAP für eingehende E-Mails |
| `STRIPE_PUBLIC_KEY` | Nein | Stripe (Portal-Zahlungen) |
| `STRIPE_SECRET_KEY` | Nein | Stripe Secret |
| `VERSCHLUESSEL_KEY` | Nein | AES-Key für sensible Dokumente |
| `BENTOPDF_URL` | Nein | URL zu BentoPDF/Stirling-PDF |

Eine vollständige Vorlage: `.env.example`

---

## Projektstruktur

```
vorgangswerk/
├── core/           – Benutzerverwaltung, Dashboard, API
├── formulare/      – Pfad-Editor, Antragsstrecken, Quizmodul
├── workflow/       – Workflow-Engine, Arbeitsstapel
├── dokumente/      – DMS, OnlyOffice-Integration
├── kommunikation/  – E-Mail-Worker, Postfach
├── korrespondenz/  – Briefvorlagen, Schreiben
├── signatur/       – FES/QES-Integration
├── portal/         – KI-Portal, Stripe, PDF-Analyse
├── quiz/           – Fragenpools, BAMF-Einbürgerungstest
├── config/         – Django-Einstellungen, URLs
├── static/         – JavaScript, CSS
├── templates/      – Basis-Templates
└── docker-compose.yml
```

---

## Mitmachen

Beiträge sind willkommen. Bitte:

1. Fork erstellen
2. Feature-Branch anlegen (`git checkout -b feature/mein-feature`)
3. Änderungen committen
4. Pull Request öffnen

Für größere Änderungen, Fragen oder Fehlerberichte bitte ein [GitHub Issue](https://github.com/geolohmar-star/vorgangswerk/issues) anlegen.

---

## Lizenz

Veröffentlicht unter der [European Union Public Licence 1.2 (EUPL-1.2)](LICENSE).

Die EUPL-1.2 ist eine von der EU-Kommission entwickelte Open-Source-Lizenz, die speziell für Software der öffentlichen Verwaltung konzipiert wurde und mit anderen gängigen Open-Source-Lizenzen kompatibel ist.

---

## Kontakt

Georg Klein · [vorgangswerk@georg-klein.com](mailto:vorgangswerk@georg-klein.com)

Für Bugs und Feature-Anfragen bitte [GitHub Issues](https://github.com/geolohmar-star/vorgangswerk/issues) verwenden.
