# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Portal-Services: Claude-API-Integration für Formular-Analyse.

Sicherheitshinweise:
- PDF wird als natives Dokument an Claude übergeben (Base64).
- AcroForm-Feldnamen werden zusätzlich via pypdf extrahiert.
- Felder werden auf max. 200 Einträge begrenzt.
- Dateinamen werden sanitisiert.
"""
import base64
import io
import json
import logging
import re
import html

import anthropic
from django.conf import settings
from django.utils import timezone

from .models import FormularAnalyse

logger = logging.getLogger("vorgangswerk.portal")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _extrahiere_acroform_felder(pdf_bytes: bytes) -> tuple[list[str], int]:
    """Gibt (acroform_feldnamen, seitenanzahl) zurück. Nur technische Metadaten via pypdf."""
    try:
        import pypdf
    except ImportError:
        return [], 0

    felder: list[str] = []

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        seitenanzahl = len(reader.pages)

        # Textfelder
        for name in (reader.get_form_text_fields() or {}).keys():
            sauber = _sanitize_text(name)
            if sauber:
                felder.append(sauber)

        # Checkboxen, Radio etc.
        try:
            annots = reader.trailer.get("/Root", {}).get("/AcroForm", {}).get("/Fields", [])
            for f in annots:
                try:
                    obj = f.get_object()
                    name = obj.get("/T", "")
                    if name:
                        sauber = _sanitize_text(str(name))
                        if sauber and sauber not in felder:
                            felder.append(sauber)
                except Exception:
                    pass
        except Exception:
            pass

    except Exception as e:
        logger.warning("PDF-Lesefehler (AcroForm): %s", e)
        return [], 0

    return felder[:200], seitenanzahl


def _sanitize_text(text: str) -> str:
    """Bereinigt Text: HTML-Entities escapen, Steuerzeichen entfernen."""
    if not isinstance(text, str):
        text = str(text)
    text = html.escape(text)
    # Steuerzeichen entfernen (außer \n, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def _erstelle_prompt(dateiname: str, felder: list[str], seitenanzahl: int) -> str:
    """Erstellt den Claude-Analyse-Prompt (ohne Seitentext – Claude liest PDF nativ)."""
    felder_str = "\n".join(f"  - {f}" for f in felder) if felder else "  (keine AcroForm-Felder erkannt)"
    dateiname_sauber = _sanitize_text(dateiname)[:100]

    return f"""Du analysierst ein deutsches Verwaltungsformular (das PDF siehst du direkt) und erzeugst eine strukturierte Pfad-Definition für das System "Vorgangswerk".

Formularname: {dateiname_sauber}
Seiten: {seitenanzahl}

Technische AcroForm-Feldnamen aus dem Dokument (zur Orientierung):
{felder_str}

## Marker-Konvention im PDF

Das PDF kann handschriftlich oder digital mit folgenden Markierungen vorbereitet sein:

### LOOP-Marker (Rechteck mit "LOOP: Name")
Felder innerhalb eines "LOOP: Kind"- oder "LOOP: Bewohner"-Rahmens sind wiederholende Eingaben.
So baust du die Struktur:
1. Einen Schritt für die Felder VOR dem Loop (Pre-Loop, z.B. Familienname) – normale Felder, pdf_gruppe setzen.
2. Einen Schritt für die Loop-Felder (z.B. "Kind-Daten") mit pdf_gruppe = Loop-Name, node_id z.B. "s_loop_body".
3. Einen Schritt "Weiteres [Name]?" mit einem radio-Feld (optionen: ["ja","nein"]), pdf_ausblenden: true gesetzt (erscheint nicht in PDF).
4. Einen Loop-Trigger-Schritt mit loop_bezeichnung = Loop-Name (z.B. "Kind"), loop_titel_feld = erstes Namensfeld im Loop (z.B. "vorname"), und einem systemfeld (systemwert: "loop_zaehler").
5. Transitionen: Loop-Body → Weiter-Schritt → (ja) → Loop-Trigger → Loop-Body; (nein) → Abschluss.

Schritt-Attribute für Loop-Schritte:
- "loop_bezeichnung": "Kind" (nur am Loop-Trigger-Schritt)
- "loop_titel_feld": "vorname" (Feld-ID dessen Wert als Untertitel erscheint, nur am Loop-Trigger-Schritt)
- "pdf_gruppe": "Kinder" (an Loop-Body- und Weiter-Schritt)

### GRUPPE-Marker (Rechteck mit "GRUPPE: Name")
Alle Felder im markierten Bereich gehören zur gleichen PDF-Gruppe.
Setze am jeweiligen Schritt: "pdf_gruppe": "Name" (z.B. "Wohnort", "Persönliche Daten").

### Entscheidungswege (Rechteck mit Zahl)
1. Jede visuell abgegrenzte Gruppe bekommt einen EIGENEN Schritt. Die Gruppennummer (z.B. "3", "4", "5") steht sichtbar im oder am Rahmen.
2. Eine Ziffernreihe im Abschnitts-Header (z.B. "3 4 5 6 7 8 9 10") ist das AUSWAHLFELD: Erstelle daraus ein checkboxen-Feld mit den Ziffern als Optionen und einem passenden label.
3. Der Schritt mit diesem Auswahlfeld ist der Verzweigungsschritt (node_id: "s_auswahl").
4. Jede Transition vom Auswahlschritt zu einem Gruppenschritt erhält eine Bedingung: {{{{auswahl_feld_id}}}} == 'N'.
5. Alle Gruppenschritte münden in denselben Abschluss-Schritt.
6. pos_x der Gruppenschritte: 600, pos_y staffeln (80, 230, 380, ...). Auswahlschritt: pos_x=300. Abschluss: pos_x=1000, pos_y=80.

## JSON-Struktur

Erstelle eine JSON-Pfad-Definition mit exakt dieser Struktur:
{{
  "name": "Vollständiger Formularname auf Deutsch",
  "beschreibung": "Kurze Beschreibung wofür das Formular ist",
  "kuerzel": "3-5 Großbuchstaben",
  "leika_schluessel": "14-stelliger LeiKa-Schlüssel oder leer",
  "schritte": [
    {{
      "node_id": "s01",
      "titel": "Abschnittstitel",
      "ist_start": true,
      "ist_ende": false,
      "pos_x": 300,
      "pos_y": 80,
      "pdf_gruppe": "",
      "loop_bezeichnung": "",
      "loop_titel_feld": "",
      "felder_json": [
        {{"id": "eindeutige_feld_id", "typ": "text", "label": "Feldbeschriftung", "pflicht": true, "fim_id": "F60000003"}}
      ]
    }}
  ],
  "transitionen": [
    {{"von": "s01", "zu": "s02", "bedingung": "", "label": "", "reihenfolge": 0}}
  ]
}}

## Verfügbare Feldtypen
- text: Einzeiliges Textfeld
- mehrzeil: Mehrzeiliges Textfeld
- zahl: Zahlenfeld
- datum: Datumsfeld (TT.MM.JJJJ)
- email: E-Mail-Adresse
- telefon: Telefonnummer
- plz: Postleitzahl (5 Stellen)
- gemeindekennzahl: 8-stelliger AGS – füllt automatisch Gemeinde, Kreis und Bundesland aus. Verwende diesen Typ immer wenn das Formular nach "Gemeindekennzahl", "AGS" fragt ODER wenn Felder für Gemeinde + Kreis + Bundesland zusammen vorkommen. Lege KEINE separaten Felder für Gemeinde, Kreis oder Bundesland an.
- radio: Einfachauswahl (Pflicht: "optionen": ["Option A", "Option B"])
- checkboxen: Mehrfachauswahl (Pflicht: "optionen": ["Option A", "Option B"])
- bool: Einzelne Checkbox (ja/nein)
- signatur: Unterschriftsfeld
- einwilligung: Zustimmungstext (Pflicht: "text": "Ich stimme zu...")
- textblock: Informationstext (Pflicht: "text": "Hinweistext...")
- abschnitt: Abschnittsüberschrift (Pflicht: "text": "Überschrift")
- systemfeld: Internes Steuerungsfeld, nicht vom Nutzer ausfüllbar (Pflicht: "systemwert": "loop_zaehler"). Nur für Loop-Trigger-Schritte.
- zusammenfassung: Zusammenfassung aller Angaben (genau einmal im letzten Schritt)
- quizfrage: Multiple-Choice-Frage (Pflicht: "antwort_typ": "single"|"multiple", "antworten": [{{"text": "...", "korrekt": true|false}}], optional "erklaerung": "...", "punkte": 1)
- quizergebnis: Auswertungsfeld (Pflicht: "bewertungsmodell": "prozent", "bestanden_ab": 50) – genau einmal im letzten Schritt statt zusammenfassung

## Feld-Attribute
- "pflicht": true/false – Pflichtfeld
- "pdf_ausblenden": true – Feld erscheint nicht in der PDF-Zusammenfassung (z.B. Loop-Steuerungsfelder wie "Weiteres Kind?")

## Quiz-Erkennung
Falls das PDF ein Test, eine Prüfung oder eine Einweisung mit Wissensfragen ist:
1. Jede Frage mit Antwortoptionen wird als quizfrage erfasst.
2. Die korrekte Antwort markierst du mit "korrekt": true.
3. Gruppiere 5-10 Fragen pro Schritt.
4. Der letzte Schritt enthält ein quizergebnis-Feld statt zusammenfassung.

## Wichtige Regeln
- Verwende sprechende, einzigartige IDs (z.B. "vorname", "geburtsdatum", "kfz_kennzeichen")
- Markiere echte Pflichtfelder mit pflicht:true
- FIM-IDs: F60000003=Vorname, F60000004=Nachname, F60000022=Straße, F60000024=PLZ, F60000025=Ort, F60000030=E-Mail, F60000031=Telefon, F60000060=Datum
- Der letzte Schritt (ist_ende:true) enthält ein "zusammenfassung"-Feld und optional "signatur"
- Ohne visuelle Gruppen: 3-8 Schritte nach Themen, pos_y +150 pro Schritt

Antworte AUSSCHLIESSLICH mit dem JSON-Objekt. Kein Text davor oder danach."""


def _parse_json_antwort(antwort: str) -> dict:
    """Extrahiert und validiert das JSON aus der Claude-Antwort.

    Nutzt json_repair fuer robuste Verarbeitung von LLM-Ausgaben
    (unescapte Zeichen, trailing commas, fehlende Kommas etc.).
    """
    from json_repair import repair_json

    antwort = antwort.strip()

    # Codeblock entfernen falls vorhanden
    if antwort.startswith("```"):
        antwort = re.sub(r"^```(?:json)?\n?", "", antwort)
        antwort = re.sub(r"\n?```$", "", antwort.strip())

    # Direkt versuchen
    try:
        daten = json.loads(antwort)
    except json.JSONDecodeError:
        # json_repair repariert alle gaengigen LLM-JSON-Fehler
        repariert = repair_json(antwort, return_objects=False)
        daten = json.loads(repariert)

    # Pflichtfelder prüfen
    assert "name" in daten, "name fehlt"
    assert "schritte" in daten, "schritte fehlt"
    assert isinstance(daten["schritte"], list) and len(daten["schritte"]) > 0
    # transitionen ist optional – bei fehlendem Feld lineare Kette erzeugen
    if "transitionen" not in daten or not isinstance(daten["transitionen"], list):
        schritte = daten["schritte"]
        daten["transitionen"] = [
            {"von": schritte[i].get("node_id", schritte[i].get("id", f"s{i+1:02d}")),
             "zu":  schritte[i + 1].get("node_id", schritte[i + 1].get("id", f"s{i+2:02d}")),
             "bedingung": "", "label": "", "reihenfolge": i}
            for i in range(len(schritte) - 1)
        ]

    return daten


# ---------------------------------------------------------------------------
# Haupt-Analyse-Funktion
# ---------------------------------------------------------------------------

def analysiere_formular(analyse_id: int) -> None:
    """
    Wird in einem separaten Thread ausgeführt.
    Liest FormularAnalyse aus DB, ruft Claude auf, speichert Ergebnis.
    """
    try:
        analyse = FormularAnalyse.objects.get(pk=analyse_id)
    except FormularAnalyse.DoesNotExist:
        logger.error("FormularAnalyse %d nicht gefunden", analyse_id)
        return

    analyse.status = FormularAnalyse.STATUS_VERARBEITUNG
    analyse.save(update_fields=["status"])

    try:
        pdf_bytes = bytes(analyse.pdf_inhalt)
        dateiname = analyse.dateiname

        # 1. AcroForm-Feldnamen via pypdf (technische Metadaten)
        felder, seitenanzahl = _extrahiere_acroform_felder(pdf_bytes)
        logger.info("Analyse %d: %d AcroForm-Felder, %d Seiten",
                    analyse_id, len(felder), seitenanzahl)

        # 2. Claude API aufrufen – PDF nativ als Dokument übergeben
        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY nicht konfiguriert")

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _erstelle_prompt(dateiname, felder, seitenanzahl)
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

        nachricht = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }],
        )

        antwort_text = nachricht.content[0].text

        # 3. JSON parsen
        ergebnis = _parse_json_antwort(antwort_text)

        # 4. Ergebnis speichern
        analyse.ergebnis_json = ergebnis
        analyse.status = FormularAnalyse.STATUS_FERTIG
        analyse.fertig_am = timezone.now()
        analyse.save(update_fields=["ergebnis_json", "status", "fertig_am"])
        logger.info("Analyse %d erfolgreich abgeschlossen", analyse_id)

    except Exception as e:
        logger.exception("Analyse %d fehlgeschlagen: %s", analyse_id, e)
        analyse.status = FormularAnalyse.STATUS_FEHLER
        analyse.fehler_meldung = str(e)[:1000]
        analyse.fertig_am = timezone.now()
        analyse.save(update_fields=["status", "fehler_meldung", "fertig_am"])


# ---------------------------------------------------------------------------
# Import-Funktion: Analyse-JSON → Vorgangswerk-Pfad
# ---------------------------------------------------------------------------

def importiere_pfad_aus_analyse(analyse: FormularAnalyse) -> int:
    """
    Erstellt AntrPfad + Schritte + Transitionen aus dem Analyse-JSON.
    Gibt die PK des neuen Pfades zurück.
    """
    from formulare.models import AntrPfad, AntrSchritt, AntrTransition

    daten = analyse.ergebnis_json
    pfad = AntrPfad.objects.create(
        name=daten.get("name", analyse.dateiname),
        beschreibung=daten.get("beschreibung", ""),
        kuerzel=daten.get("kuerzel", "")[:10],
        leika_schluessel=daten.get("leika_schluessel", "")[:20],
        aktiv=True,
        oeffentlich=False,  # Erstmal nicht öffentlich
    )

    schritt_map = {}
    for sd in daten.get("schritte", []):
        felder = sd.pop("felder_json", [])
        obj = AntrSchritt.objects.create(
            pfad=pfad,
            felder_json=felder,
            node_id=sd.get("node_id", ""),
            titel=sd.get("titel", ""),
            ist_start=sd.get("ist_start", False),
            ist_ende=sd.get("ist_ende", False),
            pos_x=sd.get("pos_x", 300),
            pos_y=sd.get("pos_y", 80),
            pdf_gruppe=sd.get("pdf_gruppe", ""),
            loop_bezeichnung=sd.get("loop_bezeichnung", ""),
            loop_titel_feld=sd.get("loop_titel_feld", ""),
        )
        schritt_map[obj.node_id] = obj

    for td in daten.get("transitionen", []):
        von = schritt_map.get(td.get("von", ""))
        zu = schritt_map.get(td.get("zu", ""))
        if not von or not zu:
            continue
        AntrTransition.objects.create(
            pfad=pfad,
            von_schritt=von,
            zu_schritt=zu,
            bedingung=td.get("bedingung", ""),
            label=td.get("label", ""),
            reihenfolge=td.get("reihenfolge", 0),
        )

    analyse.status = FormularAnalyse.STATUS_IMPORTIERT
    analyse.importierter_pfad_pk = pfad.pk
    analyse.save(update_fields=["status", "importierter_pfad_pk"])

    return pfad.pk
