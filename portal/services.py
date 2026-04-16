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
from typing import Any

import anthropic
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, model_validator, field_validator

from .models import FormularAnalyse


# ---------------------------------------------------------------------------
# Pydantic-Modelle für KI-Output-Validierung
# ---------------------------------------------------------------------------

class FeldDefinition(BaseModel):
    """Ein einzelnes Formularfeld – extra-Felder (typ-spezifisch) bleiben erhalten."""
    id: str = ""
    typ: str = "text"
    label: str = ""
    pflicht: bool = False
    pdf_ausblenden: bool = False
    versteckt: bool = False
    fim_id: str = ""
    hilfetext: str = ""

    model_config = {"extra": "allow"}  # typ-spezifische Felder (optionen, text, ...) durchreichen


class TransitionDefinition(BaseModel):
    von: str
    zu: str
    bedingung: str = ""
    label: str = ""
    reihenfolge: int = 0

    @field_validator("von", "zu", mode="before")
    @classmethod
    def leere_strings_abfangen(cls, v: Any) -> str:
        return str(v) if v is not None else ""


class SchrittDefinition(BaseModel):
    node_id: str
    titel: str = "Schritt"
    ist_start: bool = False
    ist_ende: bool = False
    pos_x: int = 300
    pos_y: int = 80
    pdf_gruppe: str = ""
    loop_bezeichnung: str = ""
    loop_titel_feld: str = ""
    felder_json: list[FeldDefinition] = []

    model_config = {"extra": "ignore"}


class PfadDefinition(BaseModel):
    name: str
    beschreibung: str = ""
    kuerzel: str = ""
    leika_schluessel: str = ""
    schritte: list[SchrittDefinition]
    transitionen: list[TransitionDefinition] = []

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def erzeuge_transitionen_wenn_leer(self) -> "PfadDefinition":
        """Lineare Kette erzeugen wenn die KI keine Transitionen geliefert hat."""
        if not self.transitionen and len(self.schritte) > 1:
            self.transitionen = [
                TransitionDefinition(von=self.schritte[i].node_id, zu=self.schritte[i + 1].node_id, reihenfolge=i)
                for i in range(len(self.schritte) - 1)
            ]
        return self

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


def _parse_json_antwort(antwort: str) -> PfadDefinition:
    """Extrahiert, repariert und validiert den KI-Output als PfadDefinition.

    json_repair korrigiert LLM-typische Fehler (trailing commas, unescapte
    Zeichen, fehlende Kommas). Pydantic validiert Struktur und Typen,
    setzt Defaults und erzeugt ggf. lineare Transitionen.
    """
    from json_repair import repair_json
    from pydantic import ValidationError

    antwort = antwort.strip()

    # Markdown-Codeblock entfernen falls vorhanden
    if antwort.startswith("```"):
        antwort = re.sub(r"^```(?:json)?\n?", "", antwort)
        antwort = re.sub(r"\n?```$", "", antwort.strip())

    # JSON parsen – mit Reparatur als Fallback
    try:
        roh = json.loads(antwort)
    except json.JSONDecodeError:
        roh = json.loads(repair_json(antwort, return_objects=False))

    # Pydantic-Validierung
    try:
        return PfadDefinition.model_validate(roh)
    except ValidationError as e:
        raise ValueError(f"KI-Antwort ungültig: {e}") from e


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

        # 3. JSON parsen + Pydantic-Validierung
        pfad_def = _parse_json_antwort(antwort_text)

        # 4. Ergebnis speichern (als dict für JSONField)
        analyse.ergebnis_json = pfad_def.model_dump()
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

    pfad_def = PfadDefinition.model_validate(analyse.ergebnis_json)

    pfad = AntrPfad.objects.create(
        name=pfad_def.name,
        beschreibung=pfad_def.beschreibung,
        kuerzel=pfad_def.kuerzel[:10],
        leika_schluessel=pfad_def.leika_schluessel[:20],
        aktiv=True,
        oeffentlich=False,
    )

    schritt_map = {}
    for sd in pfad_def.schritte:
        felder_dicts = [
            f.model_dump(exclude_defaults=True)
            for f in sd.felder_json
        ]
        obj = AntrSchritt.objects.create(
            pfad=pfad,
            felder_json=felder_dicts,
            node_id=sd.node_id,
            titel=sd.titel,
            ist_start=sd.ist_start,
            ist_ende=sd.ist_ende,
            pos_x=sd.pos_x,
            pos_y=sd.pos_y,
            pdf_gruppe=sd.pdf_gruppe,
            loop_bezeichnung=sd.loop_bezeichnung,
            loop_titel_feld=sd.loop_titel_feld,
        )
        schritt_map[obj.node_id] = obj

    for td in pfad_def.transitionen:
        von = schritt_map.get(td.von)
        zu = schritt_map.get(td.zu)
        if not von or not zu:
            continue
        AntrTransition.objects.create(
            pfad=pfad,
            von_schritt=von,
            zu_schritt=zu,
            bedingung=td.bedingung,
            label=td.label,
            reihenfolge=td.reihenfolge,
        )

    analyse.status = FormularAnalyse.STATUS_IMPORTIERT
    analyse.importierter_pfad_pk = pfad.pk
    analyse.save(update_fields=["status", "importierter_pfad_pk"])

    return pfad.pk
