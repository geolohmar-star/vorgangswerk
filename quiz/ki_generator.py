# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Quiz-KI-Generator: Erzeugt quizfrage-Felder aus einem Dokument via Claude.
"""
import io
import json
import logging
import re

logger = logging.getLogger("vorgangswerk.quiz")


def _extrahiere_text(pdf_bytes: bytes) -> str:
    """Extrahiert Text aus PDF-Bytes (erste 5 Seiten, max. 6000 Zeichen)."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        texte = []
        for seite in reader.pages[:5]:
            try:
                texte.append(seite.extract_text() or "")
            except Exception:
                pass
        text = "\n".join(texte)
        # Steuerzeichen bereinigen
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text[:6000]
    except Exception as e:
        logger.warning("PDF-Extraktion fehlgeschlagen: %s", e)
        return ""


def _erstelle_prompt(text: str, anzahl: int, sprache: str = "de") -> str:
    return f"""Du analysierst einen deutschen Fachtext und erzeugst daraus {anzahl} Multiple-Choice-Quizfragen.

TEXT:
{text}

Erstelle exakt {anzahl} Quizfragen als JSON-Array. Jede Frage hat folgende Struktur:
{{
  "label": "Vollständiger Fragetext als Frage formuliert",
  "antwort_typ": "single",
  "punkte": 1,
  "erklaerung": "Kurze Begründung der richtigen Antwort (1-2 Sätze)",
  "antworten": [
    {{"text": "Richtige Antwort", "korrekt": true}},
    {{"text": "Falsche Antwort 1", "korrekt": false}},
    {{"text": "Falsche Antwort 2", "korrekt": false}},
    {{"text": "Falsche Antwort 3", "korrekt": false}}
  ]
}}

Regeln:
- Fragen müssen aus dem Text ableitbar sein
- Falsche Antworten müssen plausibel klingen, aber eindeutig falsch sein
- Keine Fragen wie "Was ist NICHT..." (negativ formulierte Fragen)
- Antworten in zufälliger Reihenfolge (nicht immer die erste richtig)
- Sprache: Deutsch, sachlich und präzise

Antworte AUSSCHLIESSLICH mit dem JSON-Array. Kein Text davor oder danach."""


def generiere_fragen_aus_text(text: str, anzahl: int = 10) -> list[dict]:
    """
    Ruft Claude auf und gibt eine Liste von quizfrage-kompatiblen Dicts zurück.
    """
    from django.conf import settings
    import anthropic
    from json_repair import repair_json

    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nicht konfiguriert")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _erstelle_prompt(text, anzahl)

    nachricht = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    antwort = nachricht.content[0].text.strip()

    # Codeblock entfernen
    if antwort.startswith("```"):
        antwort = re.sub(r"^```(?:json)?\n?", "", antwort)
        antwort = re.sub(r"\n?```$", "", antwort.strip())

    try:
        fragen = json.loads(antwort)
    except json.JSONDecodeError:
        fragen = json.loads(repair_json(antwort))

    if not isinstance(fragen, list):
        raise ValueError("KI hat kein Array zurückgegeben")

    # Felder normalisieren + IDs vergeben
    result = []
    for i, f in enumerate(fragen):
        if not isinstance(f, dict) or not f.get("label"):
            continue
        result.append({
            "typ":         "quizfrage",
            "id":          f"ki_frage_{i + 1}",
            "label":       f.get("label", ""),
            "antwort_typ": f.get("antwort_typ", "single"),
            "punkte":      float(f.get("punkte", 1)),
            "erklaerung":  f.get("erklaerung", ""),
            "antworten":   f.get("antworten", []),
            "pflicht":     True,
        })
    return result


def generiere_fragen_aus_pdf(pdf_bytes: bytes, anzahl: int = 10) -> list[dict]:
    """Wrapper: PDF → Text → KI → quizfrage-Liste."""
    text = _extrahiere_text(pdf_bytes)
    if not text.strip():
        raise ValueError("Kein Text aus PDF extrahierbar")
    return generiere_fragen_aus_text(text, anzahl)
