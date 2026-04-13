# Architektur – Vorgangswerk

Dieses Dokument beschreibt den technischen Aufbau von Vorgangswerk für Entwickler und technisch interessierte Administratoren.

---

## Überblick

Vorgangswerk ist eine **Django-Monolith-Anwendung** mit PostgreSQL als Datenbank. Kein Microservice-Overhead, keine Message-Broker-Abhängigkeit – der gesamte Anwendungslogik läuft in einem Python-Prozess (Gunicorn mit mehreren Workern).

```
Browser / BundID / Externe Systeme
           │
           ▼
    Reverse Proxy (Nginx / Cloudflare Tunnel)
           │
           ▼
    Gunicorn (9 Worker, Port 8000)
           │
    ┌──────┴──────┐
    │   Django    │
    │  WSGI-App   │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │ PostgreSQL  │
    └─────────────┘
```

Neben dem Web-Prozess laufen zwei eigenständige Container:

| Container | Aufgabe |
|---|---|
| `web` | Django + Gunicorn, bedient alle HTTP-Requests |
| `worker` | IMAP-Polling-Loop (E-Mail-Eingang alle 60 s) |
| `backup` | Zeitgesteuertes Backup (täglich/wöchentlich/monatlich) |
| `db` | PostgreSQL 16 |

---

## App-Struktur

Vorgangswerk folgt Djangos App-Prinzip: jede fachliche Domäne ist eine eigenständige App mit eigenen Models, Views, URLs und Templates.

```
vorgangswerk/
├── config/          Django-Einstellungen, Root-URLs, WSGI/ASGI
│
├── core/            Querschnitt
│   ├── models.py    Benutzerprofil, Roadmap-Einträge
│   ├── views.py     Dashboard, Profil
│   └── api.py       REST-API (django-ninja)
│
├── formulare/       Antragsformulare (Kern-App)
├── workflow/        Workflow-Engine
├── dokumente/       Dokumentenmanagementsystem
├── kommunikation/   E-Mail-Postfach + Benachrichtigungen
├── korrespondenz/   Briefvorlagen + Bescheide
├── signatur/        FES / QES
├── portal/          KI-Formularanalyse + Stripe
├── quiz/            Fragenpools + Einbürgerungstest
├── bundid/          SAML SP für BundID
├── post/            Postbuch + Organisationsverzeichnis
├── sicherung/       Backup-Worker
└── datenschutz/     DSGVO-Werkzeuge
```

---

## Kern-App: Formulare

Die Formulare-App ist das Herzstück. Sie modelliert Antragsformulare als **gerichteten Graph**:

```
AntrPfad          (Formular-Definition, "Blueprint")
  ├── AntrSchritt (Knoten  = eine Formularseite mit Feldern als JSON)
  └── AntrTransition (Kante = bedingte Verbindung zwischen Schritten)

AntrSitzung       (laufende Instanz eines Pfads für einen Nutzer)
  └── gesammelte_daten_json  (alle bisherigen Eingaben als JSON)
```

### Feldtypen

Felder sind **keine eigenen Datenbankzeilen** – sie werden als JSON-Array in `AntrSchritt.felder_json` gespeichert. Das ermöglicht flexible Formulare ohne Schema-Migrationen.

Jedes Feld hat mindestens:
```json
{"id": "vorname", "typ": "text", "label": "Vorname", "pflicht": true}
```

Verfügbare Typen: `text`, `mehrzeil`, `zahl`, `datum`, `uhrzeit`, `email`, `telefon`, `plz`, `iban`, `bic`, `kfz`, `steuernummer`, `radio`, `auswahl`, `checkboxen`, `bool`, `datei`, `bild`, `signatur`, `einwilligung`, `abschnitt`, `textblock`, `berechnung`, `systemfeld`, `gruppe`, `bankverbindung`, `pdf_email`, `zahlung`, `zusammenfassung`, `link`, `leerblock`, `trennlinie`

### Bedingte Transitionen

Übergänge zwischen Schritten können bedingt sein:
```
{{nutzung}} == 'gewerblich'   →  Schritt "Gewerbedetails"
(leer)                        →  Standard-Weiterleitung
```

Die Engine wertet beim Absenden eines Schritts alle ausgehenden Transitionen in der Reihenfolge aus und nimmt die erste, deren Bedingung zutrifft.

---

## Kern-App: Workflow

Die Workflow-Engine modelliert Geschäftsprozesse ebenfalls als Graph:

```
WorkflowTemplate     (Blueprint eines Prozesses)
  ├── WorkflowStep       (Knoten = Aufgabe oder automatische Aktion)
  └── WorkflowTransition (Kante = Übergang nach Entscheidung oder Bedingung)

WorkflowInstance     (laufende Instanz, verknüpft mit einem Antrag oder Dokument)
  └── WorkflowTask       (konkrete Aufgabe im Arbeitsstapel eines Bearbeiters)
```

Ein Pfad kann nach Abschluss automatisch eine Workflow-Instanz starten (`AntrPfad.workflow_template`).

---

## REST-API

Die API wird mit **django-ninja** umgesetzt – typsicher, automatisch dokumentiert.

Erreichbar unter: `/api/`  
Swagger-UI: `/api/docs`

Authentifizierung: Session-Cookie (gleiche Auth wie die Web-UI) oder Token.

---

## Authentifizierung & Sicherheit

| Mechanismus | Umsetzung |
|---|---|
| Login | Django-Auth, Session-Cookie |
| MFA / TOTP | django-otp |
| Brute-Force-Schutz | django-axes (5 Versuche → 1h Sperre) |
| BundID / SAML | eigene `bundid`-App, python3-saml |
| HTTPS-Header | `SECURE_PROXY_SSL_HEADER`, HSTS, CSP via Middleware |
| Sensible Dokumente | AES-256-GCM (cryptography), zeitlich begrenzte Zugriffsschlüssel |

---

## Datenbankstrategie

- **Keine Raw-SQL-Queries** – ausschließlich Django ORM
- **Migrationen niemals squashen** – bestehende Installationen würden brechen
- JSON-Felder (`JSONField`) für flexible Strukturen (Felddefinitionen, gesammelte Formulardaten, Workflow-Konfiguration)
- Alle ForeignKeys mit `on_delete=CASCADE` oder `SET_NULL` je nach fachlicher Anforderung

---

## Templates & Frontend

- **Bootstrap 5** – kein eigenes CSS-Framework
- **HTMX** – für partielle Seitenaktualisierungen (Benachrichtigungs-Badge, etc.)
- **Vanilla JavaScript** – kein Build-Schritt, kein npm, kein Webpack
- **Vis.js** – für den visuellen Graph-Editor (Pfad-Editor, Workflow-Editor)
- **WeasyPrint** – serverseitige PDF-Generierung aus HTML-Templates

Statische Dateien werden von **Whitenoise** ausgeliefert – kein separater Nginx für Static nötig.

---

## Datenstrom: Öffentlicher Antrag

```
1. Bürger ruft /antrag/<pfad_pk>/ auf
2. Neue AntrSitzung wird angelegt (mit Token für Tracking)
3. Pro Schritt: POST → Validierung → gesammelte_daten_json erweitert
4. Transition-Engine bestimmt nächsten Schritt
5. Bei Abschluss:
   a. AntrSitzung.status = "abgeschlossen"
   b. Optional: PDF generieren + E-Mail versenden
   c. Optional: Webhook-POST an externes System
   d. Optional: WorkflowInstance starten
```

---

## Datenstrom: Eingehende E-Mail

```
1. email_worker pollt IMAP-Postfach alle 60 Sekunden
2. Neue E-Mail → EingehendeEmail-Objekt in DB
3. Sachbearbeiter sieht E-Mail im Postfach-Modul
4. Kann E-Mail einem Vorgang / einer Sitzung zuordnen
5. Optional: Benachrichtigung an zuständigen Bearbeiter
```

---

## Erweiterungspunkte

| Was | Wo |
|---|---|
| Neuer Feldtyp | `formulare/views.py` (Rendering + Validierung) + Templates |
| Neue Workflow-Aktion | `workflow/models.py` `AKTION_CHOICES` + `workflow/services.py` |
| Neuer API-Endpoint | `core/api.py` |
| Neues Management-Command | `<app>/management/commands/<name>.py` |
| Neuer Webhook-Event | `formulare/models.py` `WebhookKonfiguration` |
