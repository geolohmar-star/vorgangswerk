# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Quiz-Services: Auswertungslogik und Zertifikat-Generierung.

Bewertungsmodelle:
  prozent       – Prozentueller Schwellenwert
  noten         – Schulnoten 1–6 (konfigurierbare Grenzen)
  punkte        – Absolute Mindestpunktzahl
  fuehrerschein – Max. Fehlerpunkte (TÜV/DEKRA-Prinzip)
"""
import datetime
import logging

from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger("vorgangswerk.quiz")

# Noten-Standardgrenzen (Prozentwert ab dem die Note gilt)
_STANDARD_NOTEN = {
    "1": 90,
    "2": 76,
    "3": 63,
    "4": 50,
    "5": 30,
}
_NOTEN_TEXT = {
    "1": "Sehr gut",
    "2": "Gut",
    "3": "Befriedigend",
    "4": "Ausreichend",
    "5": "Mangelhaft",
    "6": "Ungenügend",
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _sammle_quizfragen(sitzung):
    """
    Gibt eine geordnete Liste aller quizfrage-Felder zurück,
    die in besuchten Schritten vorkommen.
    Quizpool-Felder werden automatisch aus gesammelte_daten expandiert.
    """
    from formulare.models import AntrSchritt
    fragen = []
    for node_id in sitzung.besuchte_schritte:
        try:
            schritt = sitzung.pfad.schritte.get(node_id=node_id)
        except AntrSchritt.DoesNotExist:
            continue
        for feld in schritt.felder():
            if feld.get("typ") == "quizfrage":
                fragen.append(feld)
            elif feld.get("typ") == "quizpool":
                # Pool wurde beim Schritt-Rendern in gesammelte_daten gespeichert
                pool_key = f"__pool__{feld.get('id', '')}"
                pool = sitzung.gesammelte_daten.get(pool_key, [])
                fragen.extend(pool)
    return fragen


def _finde_ergebnis_config(sitzung):
    """
    Sucht das quizergebnis-Feld in einem der besuchten Schritte
    und gibt dessen Konfiguration zurück (oder ein leeres Dict).
    """
    from formulare.models import AntrSchritt
    for node_id in reversed(sitzung.besuchte_schritte):
        try:
            schritt = sitzung.pfad.schritte.get(node_id=node_id)
        except AntrSchritt.DoesNotExist:
            continue
        for feld in schritt.felder():
            if feld.get("typ") == "quizergebnis":
                return feld
    return {}


def _ist_antwort_korrekt(feld, gegebene_antwort):
    """
    Prüft ob die gegebene Antwort korrekt ist.
    Bei multiple: alle korrekten müssen gewählt sein, keine falschen.
    Gibt (korrekt: bool, teilweise_korrekt: bool) zurück.
    """
    antwort_typ = feld.get("antwort_typ", "single")
    antworten   = feld.get("antworten", [])
    korrekte    = {a["text"] for a in antworten if a.get("korrekt")}

    if antwort_typ == "multiple":
        gewaehlte = {s.strip() for s in str(gegebene_antwort).split(",") if s.strip()}
        falsch_gewaehlt = gewaehlte - korrekte
        nicht_gewaehlt  = korrekte - gewaehlte
        voll_korrekt    = (not falsch_gewaehlt and not nicht_gewaehlt)
        teilweise       = bool(gewaehlte & korrekte) and not voll_korrekt
        return voll_korrekt, teilweise
    else:
        korrekt = gegebene_antwort.strip() in korrekte
        return korrekt, False


def berechne_ergebnis(fragen, gesammelte_daten, ergebnis_config):
    """
    Berechnet das Quiz-Ergebnis ohne DB-Zugriff (für Vorschau und Speichern).

    Gibt ein Dict zurück:
      punkte_erreicht, punkte_gesamt, fehlerpunkte,
      prozent, bestanden, note, note_text,
      bewertungsmodell, antworten_detail
    """
    modell            = ergebnis_config.get("bewertungsmodell", "prozent")
    bestanden_ab      = float(ergebnis_config.get("bestanden_ab", 50))
    max_fehlerpunkte  = float(ergebnis_config.get("max_fehlerpunkte", 0))
    noten_grenzen_raw = ergebnis_config.get("noten_grenzen") or {}
    noten_grenzen     = {k: float(v) for k, v in noten_grenzen_raw.items()} if noten_grenzen_raw else {k: float(v) for k, v in _STANDARD_NOTEN.items()}
    teilpunkte_global = ergebnis_config.get("teilpunkte", False)

    punkte_gesamt    = 0.0
    punkte_erreicht  = 0.0
    fehlerpunkte_sum = 0.0
    sofort_fail      = False
    antworten_detail = {}

    for feld in fragen:
        fid         = feld.get("id", "")
        max_punkte  = float(feld.get("punkte", 1))
        fehlp       = float(feld.get("fehlerpunkte", max_punkte))
        pflicht_ok  = feld.get("pflicht_korrekt", False)
        teilpunkte  = feld.get("teilpunkte", teilpunkte_global)
        gegebene    = str(gesammelte_daten.get(fid, "")).strip()

        punkte_gesamt += max_punkte
        korrekt, teilweise = _ist_antwort_korrekt(feld, gegebene)

        if korrekt:
            p_f = max_punkte
            fp  = 0.0
        elif teilweise and teilpunkte:
            antworten  = feld.get("antworten", [])
            korrekte   = [a for a in antworten if a.get("korrekt")]
            gewaehlte  = {s.strip() for s in gegebene.split(",") if s.strip()}
            richtig_gew = sum(1 for a in korrekte if a["text"] in gewaehlte)
            p_f = round(max_punkte * richtig_gew / max(len(korrekte), 1), 2)
            fp  = round(fehlp * (1 - richtig_gew / max(len(korrekte), 1)), 2)
        else:
            p_f = 0.0
            fp  = fehlp if not korrekt else 0.0

        punkte_erreicht  += p_f
        fehlerpunkte_sum += fp

        if pflicht_ok and not korrekt:
            sofort_fail = True

        antworten_detail[fid] = {
            "label":      feld.get("label", fid),
            "antwort":    gegebene,
            "korrekt":    korrekt,
            "teilweise":  teilweise,
            "punkte":     p_f,
            "max_punkte": max_punkte,
            "erklaerung": feld.get("erklaerung", ""),
        }

    # Prozent
    prozent = round((punkte_erreicht / punkte_gesamt * 100) if punkte_gesamt > 0 else 0, 2)

    # Bestanden?
    if sofort_fail:
        bestanden = False
    elif modell == "fuehrerschein":
        bestanden = fehlerpunkte_sum <= max_fehlerpunkte
    elif modell == "punkte":
        bestanden = punkte_erreicht >= bestanden_ab
    else:
        bestanden = prozent >= bestanden_ab  # prozent + noten

    # Note
    note = ""
    note_text = ""
    if modell == "noten":
        for n in ["1", "2", "3", "4", "5"]:
            grenze = noten_grenzen.get(n, _STANDARD_NOTEN.get(n, 0))
            if prozent >= grenze:
                note = n
                note_text = _NOTEN_TEXT.get(n, "")
                break
        if not note:
            note = "6"
            note_text = _NOTEN_TEXT["6"]

    # Fragen-Liste mit gegebener Antwort + Korrektheit für Template-Rendering
    fragen_auswertung = []
    for feld in fragen:
        fid = feld.get("id", "")
        detail = antworten_detail.get(fid, {})
        gegebene = str(gesammelte_daten.get(fid, "")).strip()
        gewaehlte_set = {s.strip() for s in gegebene.split(",") if s.strip()}
        antworten_markiert = []
        for a in feld.get("antworten", []):
            gewaehlt = a["text"] in gewaehlte_set
            antworten_markiert.append({
                "text":      a["text"],
                "korrekt":   a.get("korrekt", False),
                "gewaehlt":  gewaehlt,
            })
        fragen_auswertung.append({
            "id":         fid,
            "label":      feld.get("label", fid),
            "korrekt":    detail.get("korrekt", False),
            "teilweise":  detail.get("teilweise", False),
            "punkte":     detail.get("punkte", 0),
            "max_punkte": detail.get("max_punkte", 1),
            "erklaerung": detail.get("erklaerung", ""),
            "antworten":  antworten_markiert,
        })

    return {
        "punkte_erreicht":  round(punkte_erreicht, 2),
        "punkte_gesamt":    round(punkte_gesamt, 2),
        "fehlerpunkte":     round(fehlerpunkte_sum, 2),
        "prozent":          prozent,
        "prozent_int":      int(prozent),
        "bestanden":        bestanden,
        "note":             note,
        "note_text":        note_text,
        "bewertungsmodell": modell,
        "sofort_fail":      sofort_fail,
        "antworten_detail": antworten_detail,
        "fragen_auswertung": fragen_auswertung,
    }


# ---------------------------------------------------------------------------
# Vorschau (ohne DB-Schreiben)
# ---------------------------------------------------------------------------

def vorschau_ergebnis(sitzung):
    """
    Berechnet das Quiz-Ergebnis ohne es zu speichern.
    Wird beim Rendern des quizergebnis-Schritts (GET) aufgerufen.
    Gibt None zurück wenn keine quizfrage-Felder gefunden.
    """
    fragen = _sammle_quizfragen(sitzung)
    if not fragen:
        return None
    config = _finde_ergebnis_config(sitzung)
    return berechne_ergebnis(fragen, sitzung.gesammelte_daten, config)


# ---------------------------------------------------------------------------
# Auswertung + Speichern (nach sitzung.abschliessen())
# ---------------------------------------------------------------------------

def auswerte_quiz(sitzung):
    """
    Wertet das Quiz aus, speichert QuizErgebnis und ggf. QuizZertifikat.
    Gibt QuizErgebnis-Instanz zurück oder None wenn kein Quiz vorhanden.
    """
    from .models import QuizErgebnis, QuizZertifikat

    # Schon ausgewertet?
    if hasattr(sitzung, "quiz_ergebnis"):
        return sitzung.quiz_ergebnis

    fragen = _sammle_quizfragen(sitzung)
    if not fragen:
        return None

    config = _finde_ergebnis_config(sitzung)
    if not config:
        return None

    ergebnis_data = berechne_ergebnis(fragen, sitzung.gesammelte_daten, config)

    ergebnis = QuizErgebnis.objects.create(
        sitzung          = sitzung,
        punkte_erreicht  = ergebnis_data["punkte_erreicht"],
        punkte_gesamt    = ergebnis_data["punkte_gesamt"],
        fehlerpunkte     = ergebnis_data["fehlerpunkte"],
        prozent          = ergebnis_data["prozent"],
        bestanden        = ergebnis_data["bestanden"],
        note             = ergebnis_data["note"],
        note_text        = ergebnis_data["note_text"],
        bewertungsmodell = ergebnis_data["bewertungsmodell"],
        antworten_json   = ergebnis_data["antworten_detail"],
        config_snapshot  = config,
    )
    logger.info("QuizErgebnis %d erstellt: %s %% – %s",
                ergebnis.pk, ergebnis_data["prozent"],
                "bestanden" if ergebnis_data["bestanden"] else "nicht bestanden")

    # Zertifikat generieren wenn bestanden und konfiguriert
    if ergebnis_data["bestanden"] and config.get("zertifikat"):
        try:
            _erstelle_zertifikat(ergebnis, config, sitzung)
        except Exception:
            logger.exception("Zertifikat-Generierung fehlgeschlagen für Ergebnis %d", ergebnis.pk)

    return ergebnis


def _erstelle_zertifikat(ergebnis, config, sitzung):
    """Generiert das Zertifikat-PDF und speichert QuizZertifikat."""
    from weasyprint import HTML
    from .models import QuizZertifikat

    # Ablaufdatum berechnen
    monate = config.get("zertifikat_gueltig_monate", 0)
    ablauf = None
    if monate:
        heute = datetime.date.today()
        monat = heute.month - 1 + int(monate)
        jahr  = heute.year + monat // 12
        monat = monat % 12 + 1
        tag   = min(heute.day, [31,29,31,30,31,30,31,31,30,31,30,31][monat-1])
        ablauf = datetime.date(jahr, monat, tag)

    # Name aus Sitzungsdaten ermitteln
    daten     = sitzung.gesammelte_daten
    vorname   = daten.get("vorname") or daten.get("F60000003") or ""
    nachname  = daten.get("nachname") or daten.get("name") or daten.get("F60000004") or ""
    if sitzung.user:
        vollname = sitzung.user.get_full_name() or sitzung.user.username
    else:
        vollname = f"{vorname} {nachname}".strip() or sitzung.email_anonym or "Teilnehmer/in"

    titel = config.get("zertifikat_titel") or sitzung.pfad.name

    html_string = render_to_string("quiz/zertifikat_pdf.html", {
        "ergebnis":  ergebnis,
        "sitzung":   sitzung,
        "vollname":  vollname,
        "titel":     titel,
        "ablauf":    ablauf,
        "heute":     datetime.date.today(),
    })
    pdf_bytes = HTML(string=html_string).write_pdf()

    QuizZertifikat.objects.create(
        ergebnis    = ergebnis,
        pdf_inhalt  = pdf_bytes,
        ablaufdatum = ablauf,
    )
    logger.info("QuizZertifikat für Ergebnis %d erstellt (gültig bis %s)", ergebnis.pk, ablauf)
