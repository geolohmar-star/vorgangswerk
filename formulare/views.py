# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""formulare - Views: Formular-Editor, Ausfuellen, Auswertung.

Editor-Flow:
  pfad_liste            -> Uebersicht aller Pfade
  pfad_editor           -> visueller Graph-Editor (vis.js)
  pfad_editor_laden     -> GET JSON: Pfad-Daten fuer Editor
  pfad_editor_speichern -> POST JSON: Pfad speichern

Player-Flow:
  pfad_starten          -> neue Sitzung anlegen, zum Start-Schritt
  pfad_schritt          -> aktuellen Schritt anzeigen + POST verarbeiten
  pfad_abgeschlossen    -> Abschluss-Seite
"""
import ast
import csv
import datetime
import io
import json
import logging
import mimetypes
import operator
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AntrDatei, AntrPfad, AntrSchritt, AntrSitzung, AntrTransition, AntrVersion

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Berechtigungspruefung
# ---------------------------------------------------------------------------

def _ist_editor(user):
    """Darf Pfade anlegen/bearbeiten (Staff oder Gruppe prozessverantwortlich)."""
    if user.is_staff:
        return True
    return user.groups.filter(name__icontains="prozessverantwortlich").exists()


# ---------------------------------------------------------------------------
# Formel-Evaluator
# ---------------------------------------------------------------------------

_OPS = {
    ast.Add:   operator.add,
    ast.Sub:   operator.sub,
    ast.Mult:  operator.mul,
    ast.Div:   operator.truediv,
    ast.Eq:    operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt:    operator.lt,
    ast.LtE:   operator.le,
    ast.Gt:    operator.gt,
    ast.GtE:   operator.ge,
}


def _ast_eval(node, werte):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return werte.get(node.id, "")
    if isinstance(node, ast.BinOp):
        op = _OPS.get(type(node.op))
        if op is None:
            raise ValueError("Nicht erlaubter Operator")
        l, r = _ast_eval(node.left, werte), _ast_eval(node.right, werte)
        if isinstance(node.op, ast.Div) and r == 0:
            return None
        try:
            return op(float(l), float(r))
        except (TypeError, ValueError):
            return op(l, r)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        op = _OPS.get(type(node.ops[0]))
        if op is None:
            raise ValueError("Nicht erlaubter Vergleichsoperator")
        l = _ast_eval(node.left, werte)
        r = _ast_eval(node.comparators[0], werte)
        return op(l, r)
    if isinstance(node, ast.BoolOp):
        werte_liste = [_ast_eval(v, werte) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(werte_liste)
        if isinstance(node.op, ast.Or):
            return any(werte_liste)
        raise ValueError("Nicht erlaubter Bool-Operator")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -float(_ast_eval(node.operand, werte))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id.upper()
        args = [_ast_eval(a, werte) for a in node.args]
        if name == "WENN":
            return args[1] if args[0] else args[2]
        if name == "RUNDEN":
            return round(float(args[0]), int(args[1]))
        if name == "ABS":
            return abs(float(args[0]))
    raise ValueError(f"Nicht erlaubter Ausdruck: {ast.dump(node)}")


def _berechne_formel(formel, werte):
    """Wertet eine Berechnungsformel aus. Gibt int/float oder None zurueck."""
    if not formel or not formel.strip():
        return None

    def _var_zu_zahl(match):
        v = werte.get(match.group(1))
        if v in ("", None):
            return "0"
        try:
            return str(float(str(v).replace(",", ".")))
        except (ValueError, TypeError):
            return "0"

    ausdruck = re.sub(r"\{\{(\w+)\}\}", _var_zu_zahl, formel.replace(";", ","))
    try:
        tree = ast.parse(ausdruck, mode="eval")
        ergebnis = _ast_eval(tree.body, {})
        if ergebnis is None:
            return None
        ergebnis = float(ergebnis)
        if ergebnis == int(ergebnis):
            return int(ergebnis)
        return round(ergebnis, 2)
    except Exception:
        return None


def _pruefe_bedingung(bedingung, gesammelte_daten):
    """Wertet eine Bedingungsformel aus. Leer = immer wahr. Bei Fehler: False."""
    if not bedingung or not bedingung.strip():
        return True
    ausdruck = bedingung.replace(";", ",")
    ausdruck = re.sub(r"\{\{(\w+)\}\}", r"_F_\1", ausdruck)
    werte = {}
    for k, v in gesammelte_daten.items():
        try:
            werte["_F_" + k] = float(str(v).replace(",", ".")) if v not in ("", None) else ""
        except (ValueError, TypeError):
            werte["_F_" + k] = str(v) if v is not None else ""
    try:
        tree = ast.parse(ausdruck, mode="eval")
        ergebnis = _ast_eval(tree.body, werte)
        return bool(ergebnis)
    except Exception:
        return False


def _naechster_schritt(schritt, gesammelte_daten):
    """Gibt die erste passende Transition zurueck (nach Reihenfolge)."""
    for transition in schritt.ausgaende.select_related("zu_schritt").order_by("reihenfolge", "pk"):
        if _pruefe_bedingung(transition.bedingung, gesammelte_daten):
            return transition
    return None


# ---------------------------------------------------------------------------
# Hilfsfunktionen Player
# ---------------------------------------------------------------------------

_KEINE_EINGABE = {
    "textblock", "abschnitt", "trennlinie", "leerblock", "link",
    "berechnung", "zusammenfassung", "pdf_email", "systemfeld",
}
_KEINE_ANZEIGE = {
    "textblock", "abschnitt", "trennlinie", "leerblock", "link",
    "zusammenfassung", "pdf_email",
}
_DATEI_PRAEFX = "__datei__"


def _berechne_fortschritt_map(pfad):
    """BFS vom Start-Knoten: gibt {node_id: {tiefe, gesamt}} zurueck."""
    schritte = {s.node_id: s for s in pfad.schritte.all()}
    nachfolger = {nid: [] for nid in schritte}
    for t in pfad.transitionen.select_related("von_schritt", "zu_schritt"):
        von = t.von_schritt.node_id
        zu = t.zu_schritt.node_id
        if von in nachfolger and zu not in nachfolger[von]:
            nachfolger[von].append(zu)
    start = next((nid for nid, s in schritte.items() if s.ist_start), None)
    if not start:
        return {}
    tiefe = {start: 0}
    warteschlange = [start]
    while warteschlange:
        aktuell = warteschlange.pop(0)
        for kind in nachfolger.get(aktuell, []):
            if kind not in tiefe:
                tiefe[kind] = tiefe[aktuell] + 1
                warteschlange.append(kind)
    gesamt = max(tiefe.values()) if tiefe else 1
    return {nid: {"tiefe": t, "gesamt": gesamt} for nid, t in tiefe.items()}


def _variablen_werte(pfad):
    """Flaches Dict {var_name: wert} aus pfad.variablen_json."""
    return {name: info.get("wert", "") for name, info in (pfad.variablen_json or {}).items()}


def _substituiere_system_vars(felder_json, pfad):
    """Ersetzt {{kuerzel}} und Pfad-Variablen in Textblock-Feldern."""
    kuerzel = pfad.kuerzel or ""
    var_werte = _variablen_werte(pfad)
    result = []
    for feld in felder_json:
        if feld.get("typ") == "textblock":
            text = feld.get("text") or ""
            if "{{kuerzel}}" in text or any("{{" + n + "}}" in text for n in var_werte):
                feld = dict(feld)
                text = text.replace("{{kuerzel}}", kuerzel)
                for var_name, var_wert in var_werte.items():
                    text = text.replace("{{" + var_name + "}}", str(var_wert))
                feld["text"] = text
        result.append(feld)
    return result


def _eingabefelder(schritt):
    """Alle Eingabefelder eines Schritts (ohne Struktur-Typen)."""
    return [f for f in schritt.felder() if f.get("typ") not in _KEINE_EINGABE]


def _anzeigefelder(schritt):
    """Alle Felder fuer die Zusammenfassung."""
    return [f for f in schritt.felder() if f.get("typ") not in _KEINE_ANZEIGE]


def _loop_iterationen(gesammelte_daten):
    """Gibt archivierte Loop-Iterationen als Liste zurueck."""
    iterationen = []
    i = 0
    while True:
        praeffix = f"__loop_{i}__"
        iteration = {
            k[len(praeffix):]: v
            for k, v in gesammelte_daten.items()
            if k.startswith(praeffix)
        }
        if not iteration:
            break
        iterationen.append(iteration)
        i += 1
    aktuell = {k: v for k, v in gesammelte_daten.items() if not k.startswith("__")}
    iterationen.append(aktuell)
    return iterationen


def datei_referenz_parsen(wert):
    """Parst '__datei__:{pk}:{dateiname}'. Gibt (pk, name) oder (None, None)."""
    if not isinstance(wert, str) or not wert.startswith(f"{_DATEI_PRAEFX}:"):
        return None, None
    teile = wert.split(":", 2)
    if len(teile) < 3:
        return None, None
    try:
        return int(teile[1]), teile[2]
    except (ValueError, IndexError):
        return None, None


def _baue_zusammenfassung(sitzung):
    """Baut Label+Wert-Liste aus allen bisher gesammelten Daten."""
    gesammelte = sitzung.gesammelte_daten
    durchlauf_count = gesammelte.get("__loop_durchlauf", 0)

    def _zeilen(daten_dict, besuchte):
        zeilen = []
        for schritt_node_id in besuchte:
            try:
                schritt = sitzung.pfad.schritte.get(node_id=schritt_node_id)
            except AntrSchritt.DoesNotExist:
                continue
            for feld in _anzeigefelder(schritt):
                feld_id = feld.get("id", "")
                if feld_id.startswith("__"):
                    continue
                wert = daten_dict.get(feld_id, "")
                if wert == "" or wert is None:
                    continue
                typ = feld.get("typ", "text")
                if typ == "einwilligung":
                    einw_text = feld.get("text", "")
                    einw_label = (einw_text[:60] + "...") if len(einw_text) > 60 else einw_text
                    zeilen.append({
                        "label": einw_label or "Datenschutz-Einwilligung",
                        "wert":  "Einwilligung erteilt",
                        "typ":   "einwilligung",
                    })
                    continue
                if typ == "berechnung" and feld.get("einheit"):
                    wert = f"{wert} {feld['einheit']}"
                datei_pk = None
                if typ == "datei":
                    datei_pk, dateiname = datei_referenz_parsen(wert)
                    wert = dateiname or wert
                eintrag = {"label": feld.get("label", feld_id), "wert": wert, "typ": typ}
                if datei_pk:
                    eintrag["datei_pk"] = datei_pk
                zeilen.append(eintrag)
        return zeilen

    if durchlauf_count == 0:
        return _zeilen(gesammelte, sitzung.besuchte_schritte)

    zusammenfassung = []
    for nr, iteration_daten in enumerate(_loop_iterationen(gesammelte), start=1):
        zusammenfassung.append({"label": f"-- Eintrag {nr} --", "wert": "", "typ": "_abschnitt"})
        zusammenfassung.extend(_zeilen(iteration_daten, sitzung.besuchte_schritte))
    return zusammenfassung


# ---------------------------------------------------------------------------
# Datei-Speicherung (intern, ohne externe DMS-Abhaengigkeit)
# ---------------------------------------------------------------------------

def _speichere_datei(datei_obj, feld_id, sitzung):
    """Speichert eine hochgeladene Datei als AntrDatei. Gibt Referenz-String zurueck."""
    try:
        inhalt_bytes = datei_obj.read()
        mime = (
            datei_obj.content_type
            or mimetypes.guess_type(datei_obj.name)[0]
            or "application/octet-stream"
        )
        datei = AntrDatei.objects.create(
            sitzung=sitzung,
            feld_id=feld_id,
            dateiname=datei_obj.name,
            inhalt=inhalt_bytes,
            mime_type=mime,
        )
        return f"{_DATEI_PRAEFX}:{datei.pk}:{datei_obj.name}"
    except Exception:
        logger.exception("Datei-Upload fehlgeschlagen")
        return None


# ---------------------------------------------------------------------------
# Schritt-Validierung
# ---------------------------------------------------------------------------

def _normalisiere_uhrzeit(wert):
    wert = wert.strip().replace(".", ":").replace(" ", "")
    if re.match(r"^\d{4}$", wert):
        wert = wert[:2] + ":" + wert[2:]
    if not re.match(r"^\d{1,2}:\d{2}$", wert):
        return None
    h, m = wert.split(":")
    h, m = int(h), int(m)
    if h > 23 or m > 59:
        return None
    return f"{h:02d}:{m:02d}"


def _validiere_schritt(schritt, post_data, vorige_daten=None, files_data=None, sitzung=None, pfad=None):
    """Prueft Pflichtfelder und gibt (daten_dict, fehler_liste) zurueck."""
    daten = {}
    fehler = []
    for feld in _eingabefelder(schritt):
        feld_id = feld.get("id", "")
        typ = feld.get("typ", "text")
        pflicht = feld.get("pflicht", False)

        if typ in ("bool", "einwilligung"):
            wert = feld_id in post_data
        elif typ == "checkboxen":
            wert = ", ".join(post_data.getlist(feld_id))
        elif typ == "signatur":
            b64 = post_data.get(feld_id, "").strip()
            vorhandene_ref = (vorige_daten or {}).get(feld_id, "")
            if b64 and b64.startswith("data:image/png;base64,"):
                import base64 as _b64
                from django.core.files.uploadedfile import InMemoryUploadedFile
                try:
                    png_bytes = _b64.b64decode(b64.split(",", 1)[1])
                    png_file = InMemoryUploadedFile(
                        io.BytesIO(png_bytes), None,
                        f"unterschrift_{feld_id}.png",
                        "image/png", len(png_bytes), None,
                    )
                    if sitzung:
                        ref = _speichere_datei(png_file, feld_id, sitzung)
                        wert = ref if ref else vorhandene_ref
                    else:
                        wert = vorhandene_ref
                except Exception:
                    logger.exception("Signatur-Upload fehlgeschlagen")
                    wert = vorhandene_ref
            else:
                wert = vorhandene_ref
            if pflicht and not wert:
                fehler.append(f'"{feld.get("label", feld_id)}" ist ein Pflichtfeld.')
            daten[feld_id] = wert
            continue
        elif typ == "datei":
            datei_obj = (files_data or {}).get(feld_id)
            vorhandene_ref = (vorige_daten or {}).get(feld_id, "")
            if datei_obj and sitzung:
                ref = _speichere_datei(datei_obj, feld_id, sitzung)
                if ref:
                    wert = ref
                else:
                    fehler.append(f'"{feld.get("label", feld_id)}" konnte nicht gespeichert werden.')
                    wert = ""
            else:
                wert = vorhandene_ref
            if pflicht and not wert:
                fehler.append(f'"{feld.get("label", feld_id)}" ist ein Pflichtfeld.')
            daten[feld_id] = wert
            continue
        elif typ == "gruppe":
            count_key = f"{feld_id}__count"
            try:
                count = max(0, int(post_data.get(count_key, "0") or "0"))
            except (ValueError, TypeError):
                count = 0
            eintraege = []
            for i in range(count):
                eintrag = {}
                for uf in feld.get("unterfelder", []):
                    uf_id = uf.get("id", "")
                    uf_typ = uf.get("typ", "text")
                    schluessel = f"{feld_id}__{i}__{uf_id}"
                    if uf_typ == "bool":
                        eintrag[uf_id] = schluessel in post_data
                    elif uf_typ == "checkboxen":
                        eintrag[uf_id] = ", ".join(post_data.getlist(schluessel))
                    else:
                        eintrag[uf_id] = post_data.get(schluessel, "").strip()
                    if uf.get("pflicht") and not eintrag.get(uf_id):
                        fehler.append(
                            f'"{uf.get("label", uf_id)}" ({feld.get("label", feld_id)} {i + 1}) ist Pflichtfeld.'
                        )
                eintraege.append(eintrag)
            if pflicht and count == 0:
                fehler.append(f'"{feld.get("label", feld_id)}" erfordert mindestens einen Eintrag.')
            daten[feld_id] = eintraege
            continue
        else:
            wert = post_data.get(feld_id, "").strip()

        if typ == "einwilligung" and not wert:
            fehler.append("Bitte bestaetigen Sie die Datenschutz-Einwilligung.")
        elif pflicht and not wert and wert != 0:
            fehler.append(f'"{feld.get("label", feld_id)}" ist ein Pflichtfeld.')

        if typ == "uhrzeit" and wert:
            normiert = _normalisiere_uhrzeit(wert)
            if normiert is None:
                fehler.append(f'"{feld.get("label", feld_id)}" ist keine gueltige Uhrzeit.')
            else:
                wert = normiert
        if typ == "iban" and wert:
            iban_bereinigt = wert.replace(" ", "").upper()
            if not re.match(r"^[A-Z]{2}[0-9A-Z]{13,32}$", iban_bereinigt):
                fehler.append(f'"{feld.get("label", feld_id)}" ist keine gueltige IBAN.')
            else:
                wert = iban_bereinigt
        if typ == "bic" and wert:
            bic_bereinigt = wert.replace(" ", "").upper()
            if not re.match(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$", bic_bereinigt):
                fehler.append(f'"{feld.get("label", feld_id)}" ist kein gueltiger BIC/SWIFT-Code.')
            else:
                wert = bic_bereinigt
        if typ == "telefon" and wert:
            if not re.match(r"^[+0-9][0-9\s\-/()+]{4,29}$", wert):
                fehler.append(f'"{feld.get("label", feld_id)}" ist keine gueltige Telefonnummer.')
        if typ == "plz" and wert:
            if not re.match(r"^[0-9]{5}$", wert.strip()):
                fehler.append(f'"{feld.get("label", feld_id)}" muss genau 5 Ziffern enthalten.')
            else:
                wert = wert.strip()
        if typ == "steuernummer" and wert:
            if not re.match(r"^[0-9/\s]{10,20}$", wert.strip()):
                fehler.append(f'"{feld.get("label", feld_id)}" hat ein ungueltiges Format.')
        custom_regex = feld.get("validierung_regex", "").strip()
        if custom_regex and wert:
            try:
                if not re.fullmatch(custom_regex, str(wert)):
                    fehler.append(f'"{feld.get("label", feld_id)}" entspricht nicht dem erwarteten Format.')
            except re.error:
                pass
        daten[feld_id] = wert

    # Systemfelder
    loop_durchlauf = (vorige_daten or {}).get("__loop_durchlauf", 0)
    for feld in schritt.felder():
        if feld.get("typ") != "systemfeld":
            continue
        feld_id = feld.get("id", "")
        if not feld_id:
            continue
        systemwert = feld.get("systemwert", "loop_zaehler")
        if systemwert == "loop_zaehler":
            daten[feld_id] = loop_durchlauf + 1
        elif systemwert == "loop_durchlauf":
            daten[feld_id] = loop_durchlauf
        elif systemwert == "heute":
            daten[feld_id] = datetime.date.today().isoformat()

    # Berechnungsfelder
    alle_werte = _variablen_werte(pfad) if pfad else {}
    alle_werte.update(vorige_daten or {})
    alle_werte.update(daten)
    for feld in schritt.felder():
        if feld.get("typ") != "berechnung":
            continue
        feld_id = feld.get("id", "")
        formel = feld.get("formel", "")
        if not feld_id or not formel:
            continue
        ergebnis = _berechne_formel(formel, alle_werte)
        if ergebnis is not None:
            daten[feld_id] = ergebnis
            alle_werte[feld_id] = ergebnis

    return daten, fehler


# ---------------------------------------------------------------------------
# E-Mail: PDF nach Abschluss versenden
# ---------------------------------------------------------------------------

def _versende_pdf_email(sitzung):
    """Versendet das ausgefuellte Formular als PDF per E-Mail (falls konfiguriert)."""
    from django.core.mail import EmailMessage
    try:
        from weasyprint import HTML
    except ImportError:
        return []

    schritt_map = {s.node_id: s for s in sitzung.pfad.schritte.all()}
    auto_senden = sitzung.user is not None or bool(sitzung.email_anonym)
    pdf_email_felder = []
    for node_id in sitzung.besuchte_schritte:
        schritt = schritt_map.get(node_id)
        if not schritt:
            continue
        for feld in schritt.felder():
            if feld.get("typ") == "pdf_email":
                wahl = sitzung.gesammelte_daten.get(feld.get("id", ""))
                if auto_senden or wahl == "ja":
                    pdf_email_felder.append(feld)

    if not pdf_email_felder:
        return []

    vorgangsnummer = sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}"
    html_string = render_to_string("formulare/sitzung_pdf.html", {
        "sitzung":         sitzung,
        "zusammenfassung": _baue_zusammenfassung(sitzung),
        "vorgangsnummer":  vorgangsnummer,
    })
    try:
        pdf_bytes = HTML(string=html_string).write_pdf()
    except Exception:
        logger.exception("PDF-Generierung fuer E-Mail fehlgeschlagen")
        return []
    dateiname = f"{vorgangsnummer}.pdf"

    gesendete = []
    for feld in pdf_email_felder:
        empfaenger = []
        fest = feld.get("empfaenger_fest", "")
        for adr in fest.split(","):
            adr = adr.strip()
            if adr:
                empfaenger.append(adr)
        feld_ref = feld.get("empfaenger_feld", "")
        if feld_ref:
            match = re.match(r"\{\{(\w+)\}\}", feld_ref.strip())
            if match:
                wert = sitzung.gesammelte_daten.get(match.group(1), "")
                if wert and "@" in str(wert):
                    empfaenger.append(str(wert).strip())
        if sitzung.user and sitzung.user.email:
            empfaenger.append(sitzung.user.email)
        elif sitzung.email_anonym:
            empfaenger.append(sitzung.email_anonym)
        if not empfaenger:
            continue
        betreff = feld.get("email_betreff") or f"Ihr Antrag - {sitzung.pfad.name}"
        betreff = betreff.replace("{{kuerzel}}", sitzung.pfad.kuerzel or "")
        nachricht = feld.get("email_nachricht") or (
            f"Anbei finden Sie den ausgefuellten Antrag '{sitzung.pfad.name}' als PDF.\n\n"
            f"Vorgangsnummer: {vorgangsnummer}"
        )
        try:
            mail = EmailMessage(subject=betreff, body=nachricht, to=empfaenger)
            mail.attach(dateiname, pdf_bytes, "application/pdf")
            mail.send()
            gesendete.extend(empfaenger)
        except Exception as exc:
            logger.error("PDF-E-Mail konnte nicht gesendet werden: %s", exc)

    return list(dict.fromkeys(gesendete))


# ---------------------------------------------------------------------------
# Versions-Helfer
# ---------------------------------------------------------------------------

def _pfad_version_anlegen(pfad, user, daten):
    """Legt einen Versions-Snapshot an und loescht aelteste ueber dem Limit."""
    letzte_nr = (
        AntrVersion.objects
        .filter(pfad=pfad)
        .aggregate(max_nr=models.Max("version_nr"))
        ["max_nr"] or 0
    )
    AntrVersion.objects.create(
        pfad=pfad,
        version_nr=letzte_nr + 1,
        snapshot_json={
            "name":         daten.get("name", pfad.name),
            "beschreibung": daten.get("beschreibung", pfad.beschreibung),
            "aktiv":        daten.get("aktiv", pfad.aktiv),
            "oeffentlich":  daten.get("oeffentlich", pfad.oeffentlich),
            "schritte":     daten.get("schritte", []),
            "transitionen": daten.get("transitionen", []),
            "variablen":    daten.get("variablen", {}),
        },
        erstellt_von=user,
    )
    ids = list(
        AntrVersion.objects
        .filter(pfad=pfad)
        .order_by("-version_nr")
        .values_list("pk", flat=True)
    )
    if len(ids) > AntrVersion.MAX_VERSIONEN:
        AntrVersion.objects.filter(pk__in=ids[AntrVersion.MAX_VERSIONEN:]).delete()


# ---------------------------------------------------------------------------
# Pfad-Liste
# ---------------------------------------------------------------------------

@login_required
def pfad_liste(request):
    """Uebersicht aller Antrags-Pfade, gruppiert nach Kategorie."""
    if _ist_editor(request.user):
        pfade_qs = AntrPfad.objects.all().order_by("kategorie", "name")
    else:
        pfade_qs = AntrPfad.objects.filter(aktiv=True).order_by("kategorie", "name")

    gruppen = {}
    ohne_kategorie = []
    for pfad in pfade_qs:
        if pfad.kategorie:
            gruppen.setdefault(pfad.kategorie, []).append(pfad)
        else:
            ohne_kategorie.append(pfad)

    gruppen_liste = [
        {"name": name, "pfade": pfade_list}
        for name, pfade_list in sorted(gruppen.items())
    ]
    return render(request, "formulare/pfad_liste.html", {
        "gruppen_liste":  gruppen_liste,
        "ohne_kategorie": ohne_kategorie,
        "ist_editor":     _ist_editor(request.user),
    })


# ---------------------------------------------------------------------------
# Neuer Pfad
# ---------------------------------------------------------------------------

@login_required
@require_POST
def pfad_neu(request):
    """POST: Legt einen neuen leeren Pfad an und leitet in den Editor."""
    if not _ist_editor(request.user):
        messages.error(request, "Kein Zugriff.")
        return redirect("formulare:pfad_liste")
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name ist Pflichtfeld.")
        return redirect("formulare:pfad_liste")
    pfad = AntrPfad.objects.create(
        name=name,
        beschreibung=request.POST.get("beschreibung", "").strip(),
        aktiv=request.POST.get("aktiv") == "on",
        kuerzel=request.POST.get("kuerzel", "").strip().upper()[:6],
        kategorie=request.POST.get("kategorie", "").strip(),
        erstellt_von=request.user,
    )
    return redirect("formulare:pfad_editor", pk=pfad.pk)


# ---------------------------------------------------------------------------
# Pfad loeschen
# ---------------------------------------------------------------------------

@login_required
def pfad_loeschen(request, pk):
    """Loescht einen Pfad inklusive aller Sitzungen."""
    if not _ist_editor(request.user):
        messages.error(request, "Kein Zugriff.")
        return redirect("formulare:pfad_liste")
    pfad = get_object_or_404(AntrPfad, pk=pk)
    name = pfad.name
    pfad.sitzungen.all().delete()
    pfad.delete()
    messages.success(request, f'Pfad "{name}" wurde geloescht.')
    return redirect("formulare:pfad_liste")


# ---------------------------------------------------------------------------
# Kategorie setzen
# ---------------------------------------------------------------------------

@login_required
@require_POST
def pfad_kategorie_setzen(request, pk):
    """Setzt die Kategorie eines Pfads aus der Uebersicht."""
    if not _ist_editor(request.user):
        messages.error(request, "Kein Zugriff.")
        return redirect("formulare:pfad_liste")
    pfad = get_object_or_404(AntrPfad, pk=pk)
    pfad.kategorie = request.POST.get("kategorie", "").strip()
    pfad.save(update_fields=["kategorie"])
    return redirect("formulare:pfad_liste")


# ---------------------------------------------------------------------------
# Visueller Editor
# ---------------------------------------------------------------------------

@login_required
def pfad_editor(request, pk=None):
    """Visueller Pfad-Editor (vis.js). Neuer oder bestehender Pfad."""
    if not _ist_editor(request.user):
        messages.error(request, "Kein Zugriff.")
        return redirect("formulare:pfad_liste")
    pfad = get_object_or_404(AntrPfad, pk=pk) if pk else None
    return render(request, "formulare/pfad_editor.html", {"pfad": pfad})


@login_required
def pfad_editor_laden(request, pk):
    """GET: Gibt Pfad-Daten als JSON fuer den Editor zurueck."""
    pfad = get_object_or_404(AntrPfad, pk=pk)
    schritte = [
        {
            "id":        s.pk,
            "node_id":   s.node_id,
            "titel":     s.titel,
            "felder_json": s.felder_json,
            "ist_start": s.ist_start,
            "ist_ende":  s.ist_ende,
            "pos_x":     s.pos_x,
            "pos_y":     s.pos_y,
        }
        for s in pfad.schritte.all()
    ]
    transitionen = [
        {
            "id":          t.pk,
            "von":         t.von_schritt.node_id,
            "zu":          t.zu_schritt.node_id,
            "bedingung":   t.bedingung,
            "label":       t.label,
            "reihenfolge": t.reihenfolge,
        }
        for t in pfad.transitionen.all()
    ]
    return JsonResponse({
        "pk":           pfad.pk,
        "name":         pfad.name,
        "beschreibung": pfad.beschreibung,
        "aktiv":        pfad.aktiv,
        "oeffentlich":  pfad.oeffentlich,
        "kuerzel":      pfad.kuerzel or "",
        "schritte":     schritte,
        "transitionen": transitionen,
        "variablen":    pfad.variablen_json or {},
    })


@require_POST
@login_required
def pfad_editor_speichern(request):
    """POST JSON: Speichert einen Pfad (neu oder bestehend)."""
    if not _ist_editor(request.user):
        return JsonResponse({"ok": False, "fehler": "Kein Zugriff"}, status=403)
    try:
        daten = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "fehler": "Ungueltige JSON-Daten"}, status=400)

    pk = daten.get("pk")
    name = daten.get("name", "").strip()
    if not name:
        return JsonResponse({"ok": False, "fehler": "Name ist Pflichtfeld"}, status=400)

    kuerzel = daten.get("kuerzel", "").strip().upper()[:6]
    oeffentlich = bool(daten.get("oeffentlich", False))

    if pk:
        pfad = get_object_or_404(AntrPfad, pk=pk)
        pfad.name = name
        pfad.beschreibung = daten.get("beschreibung", "")
        pfad.aktiv = daten.get("aktiv", True)
        pfad.oeffentlich = oeffentlich
        pfad.kuerzel = kuerzel
        pfad.variablen_json = daten.get("variablen", {}) or {}
        pfad.save()
        pfad.transitionen.all().delete()
        pfad.schritte.all().delete()
    else:
        pfad = AntrPfad.objects.create(
            name=name,
            beschreibung=daten.get("beschreibung", ""),
            aktiv=daten.get("aktiv", True),
            oeffentlich=oeffentlich,
            kuerzel=kuerzel,
            variablen_json=daten.get("variablen", {}) or {},
            erstellt_von=request.user,
        )

    # Schritte anlegen
    schritt_map = {}
    for s in daten.get("schritte", []):
        node_id = s.get("node_id", "")
        if not node_id:
            continue
        obj = AntrSchritt.objects.create(
            pfad=pfad,
            node_id=node_id,
            titel=s.get("titel", "Schritt"),
            felder_json=s.get("felder_json", []),
            ist_start=s.get("ist_start", False),
            ist_ende=s.get("ist_ende", False),
            pos_x=s.get("pos_x", 200),
            pos_y=s.get("pos_y", 200),
        )
        schritt_map[node_id] = obj

    # Transitionen anlegen
    for t in daten.get("transitionen", []):
        von = schritt_map.get(t.get("von"))
        zu = schritt_map.get(t.get("zu"))
        if not von or not zu:
            continue
        AntrTransition.objects.create(
            pfad=pfad,
            von_schritt=von,
            zu_schritt=zu,
            bedingung=t.get("bedingung", ""),
            label=t.get("label", ""),
            reihenfolge=t.get("reihenfolge", 0),
        )

    _pfad_version_anlegen(pfad, request.user, daten)
    return JsonResponse({"ok": True, "pk": pfad.pk, "name": pfad.name})


# ---------------------------------------------------------------------------
# Versionen-API
# ---------------------------------------------------------------------------

@login_required
def pfad_versionen(request, pk):
    """GET: Liste aller Versionen eines Pfads."""
    pfad = get_object_or_404(AntrPfad, pk=pk)
    if not _ist_editor(request.user):
        return JsonResponse({"ok": False, "fehler": "Kein Zugriff"}, status=403)
    versionen = [
        {
            "pk":           v.pk,
            "version_nr":   v.version_nr,
            "erstellt_am":  v.erstellt_am.strftime("%d.%m.%Y %H:%M"),
            "erstellt_von": str(v.erstellt_von) if v.erstellt_von else "-",
            "schritte":     len(v.snapshot_json.get("schritte", [])),
            "transitionen": len(v.snapshot_json.get("transitionen", [])),
        }
        for v in AntrVersion.objects.filter(pfad=pfad).order_by("-version_nr")
    ]
    return JsonResponse({"ok": True, "versionen": versionen})


@login_required
def pfad_version_laden(request, version_pk):
    """GET: Gibt den Snapshot einer Version als Editor-JSON zurueck."""
    version = get_object_or_404(AntrVersion, pk=version_pk)
    if not _ist_editor(request.user):
        return JsonResponse({"ok": False, "fehler": "Kein Zugriff"}, status=403)
    snap = version.snapshot_json
    return JsonResponse({
        "ok":           True,
        "pk":           version.pfad_id,
        "version_nr":   version.version_nr,
        "name":         snap.get("name", ""),
        "beschreibung": snap.get("beschreibung", ""),
        "aktiv":        snap.get("aktiv", True),
        "schritte":     snap.get("schritte", []),
        "transitionen": snap.get("transitionen", []),
        "variablen":    snap.get("variablen", {}),
    })


# ---------------------------------------------------------------------------
# FormularScanner (PDF-AcroForm -> Pfad-JSON, offline via pypdf)
# ---------------------------------------------------------------------------

@require_POST
@login_required
def pfad_scanner(request):
    """POST: Liest AcroForm-Felder aus einer hochgeladenen PDF. Nur Staff."""
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "fehler": "Kein Zugriff"}, status=403)
    pdf_datei = request.FILES.get("pdf")
    if not pdf_datei:
        return JsonResponse({"ok": False, "fehler": "Keine PDF-Datei angegeben"}, status=400)
    try:
        split_schwelle = int(request.POST.get("split_schwelle", 30))
        split_schwelle = max(0, min(split_schwelle, 500))
    except (ValueError, TypeError):
        split_schwelle = 30
    try:
        import pypdf
    except ImportError:
        return JsonResponse({"ok": False, "fehler": "pypdf nicht installiert"}, status=500)
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_datei.read()))
    except Exception as e:
        return JsonResponse({"ok": False, "fehler": f"PDF konnte nicht gelesen werden: {e}"}, status=400)

    def _feld_id(name, typ):
        s = name.lower()
        for src, dst in [("\xe4","ae"),("\xf6","oe"),("\xfc","ue"),("\xdf","ss"),("\xc4","ae"),("\xd6","oe"),("\xdc","ue")]:
            s = s.replace(src, dst)
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return f"{s}_{typ}"

    def _erkenne_typ(name, ft):
        n = name.lower()
        if ft == "/Btn":
            return "bool"
        if ft == "/Ch":
            return "auswahl"
        if any(x in n for x in ("datum", "date", "geburts", "geburt")):
            return "datum"
        if any(x in n for x in ("anzahl", "zahl", "nummer", "betrag", "preis", "euro")):
            return "zahl"
        if any(x in n for x in ("bemerkung", "hinweis", "beschreibung", "kommentar", "anmerkung")):
            return "mehrzeil"
        return "text"

    def _felder_zu_json(felder_roh):
        felder_json = []
        verwendete_ids = set()
        for f in felder_roh:
            typ = _erkenne_typ(f["name"], f["ft"])
            basis_id = _feld_id(f["name"], typ)
            fid = basis_id
            zaehler = 2
            while fid in verwendete_ids:
                fid = f"{basis_id}_{zaehler}"
                zaehler += 1
            verwendete_ids.add(fid)
            eintrag = {"id": fid, "label": f["name"], "typ": typ, "pflicht": False, "breite": 50}
            if typ == "auswahl" and f.get("opts"):
                eintrag["optionen"] = f["opts"]
            felder_json.append(eintrag)
        return felder_json

    def _gruppen_nach_y(felder_mit_pos, schwelle):
        if not felder_mit_pos:
            return []
        sortiert = sorted(felder_mit_pos, key=lambda f: f["y_top"], reverse=True)
        gruppen = [[sortiert[0]]]
        for feld in sortiert[1:]:
            luecke = gruppen[-1][-1]["y_bottom"] - feld["y_top"]
            if luecke > schwelle:
                gruppen.append([feld])
            else:
                gruppen[-1].append(feld)
        return gruppen

    alle_gruppen = []
    for page in reader.pages:
        annots_ref = page.get("/Annots", None)
        if annots_ref is None:
            continue
        annots = annots_ref.get_object()
        felder_mit_pos = []
        for annot_ref in annots:
            obj = annot_ref.get_object()
            ft = obj.get("/FT", None)
            if not ft:
                continue
            name = str(obj.get("/T", "Feld"))
            opts = []
            if str(ft) == "/Ch":
                for o in obj.get("/Opt", []):
                    if isinstance(o, (list, tuple)):
                        opts.append(str(o[1]) if len(o) > 1 else str(o[0]))
                    else:
                        opts.append(str(o))
            y_top = y_bottom = 0.0
            rect = obj.get("/Rect", None)
            if rect:
                try:
                    coords = [float(x) for x in rect]
                    y_bottom = coords[1]
                    y_top = coords[3]
                except (ValueError, TypeError, IndexError):
                    pass
            felder_mit_pos.append({"name": name, "ft": str(ft), "opts": opts, "y_top": y_top, "y_bottom": y_bottom})
        if not felder_mit_pos:
            continue
        gruppen = _gruppen_nach_y(felder_mit_pos, split_schwelle) if split_schwelle > 0 else [felder_mit_pos]
        alle_gruppen.extend(gruppen)

    if not alle_gruppen:
        return JsonResponse(
            {"ok": False, "fehler": "Keine ausfuellbaren Felder gefunden. Das PDF enthaelt moeglicherweise keine AcroForm-Felder."},
            status=400,
        )
    dateiname = pdf_datei.name.rsplit(".", 1)[0]
    schritte = []
    for i, gruppe in enumerate(alle_gruppen):
        schritte.append({
            "node_id":   f"s{i + 1}",
            "titel":     dateiname if len(alle_gruppen) == 1 else f"Abschnitt {i + 1}",
            "felder_json": _felder_zu_json(gruppe),
            "ist_start": i == 0,
            "ist_ende":  i == len(alle_gruppen) - 1,
            "pos_x":     200 + i * 320,
            "pos_y":     200,
        })
    return JsonResponse({
        "ok":           True,
        "name":         dateiname,
        "beschreibung": f"Importiert aus: {pdf_datei.name}",
        "aktiv":        True,
        "schritte":     schritte,
        "transitionen": [],
    })


# ---------------------------------------------------------------------------
# Blockansicht (schreibgeschuetzt)
# ---------------------------------------------------------------------------

@login_required
def pfad_blockansicht(request, pk):
    """Schreibgeschuetzte Blockdiagramm-Ansicht eines Pfads."""
    pfad = get_object_or_404(AntrPfad, pk=pk)
    if not pfad.aktiv and not _ist_editor(request.user):
        messages.error(request, "Kein Zugriff.")
        return redirect("formulare:pfad_liste")
    schritte = [
        {
            "id":       s.pk,
            "node_id":  s.node_id,
            "titel":    s.titel,
            "ist_start": s.ist_start,
            "ist_ende": s.ist_ende,
            "felder": [
                {
                    "id":      f.get("id", ""),
                    "label":   f.get("label") or f.get("text", "")[:60],
                    "typ":     f.get("typ", "text"),
                    "pflicht": f.get("pflicht", False),
                }
                for f in (s.felder_json if isinstance(s.felder_json, list) else [])
            ],
            "pos_x": s.pos_x,
            "pos_y": s.pos_y,
        }
        for s in pfad.schritte.all()
    ]
    transitionen = [
        {
            "von":       t.von_schritt.node_id,
            "zu":        t.zu_schritt.node_id,
            "bedingung": t.bedingung or "",
            "label":     t.label or "",
        }
        for t in pfad.transitionen.all()
    ]
    return render(request, "formulare/pfad_blockansicht.html", {
        "pfad":              pfad,
        "ist_editor":        _ist_editor(request.user),
        "schritte_json":     schritte,
        "transitionen_json": transitionen,
    })


# ---------------------------------------------------------------------------
# Player: Pfad starten
# ---------------------------------------------------------------------------

@login_required
def pfad_starten(request, pk):
    """Startet eine neue Sitzung und leitet zum ersten Schritt."""
    pfad = get_object_or_404(AntrPfad, pk=pk, aktiv=True)
    start = pfad.start_schritt()
    if not start:
        messages.error(request, "Dieser Pfad hat keinen Start-Schritt.")
        return redirect("formulare:pfad_liste")
    sitzung = AntrSitzung.objects.create(
        pfad=pfad,
        user=request.user,
        aktueller_schritt=start,
        besuchte_schritte=[start.node_id],
    )
    return redirect("formulare:pfad_schritt", sitzung_pk=sitzung.pk)


# ---------------------------------------------------------------------------
# Player: Schritt anzeigen und verarbeiten
# ---------------------------------------------------------------------------

def _schritt_kontext(sitzung, schritt):
    """Berechnet Fortschritt und Schritt-Anzeige-Liste fuer das Template."""
    fortschritt_map = _berechne_fortschritt_map(sitzung.pfad)
    aktuell_data = fortschritt_map.get(schritt.node_id, {})
    fortschritt_tiefe = aktuell_data.get("tiefe", 0)
    fortschritt_gesamt = aktuell_data.get("gesamt", 1)
    fortschritt_pct = round(fortschritt_tiefe / fortschritt_gesamt * 100) if fortschritt_gesamt else 0

    schritt_map = {s.node_id: s for s in sitzung.pfad.schritte.all()}
    schritt_anzeige = []
    for nid in sitzung.besuchte_schritte:
        s = schritt_map.get(nid)
        if s and s.node_id != schritt.node_id:
            schritt_anzeige.append({"titel": s.titel, "zustand": "erledigt", "ist_verzweigung": False})
    schritt_anzeige.append({"titel": schritt.titel, "zustand": "aktuell", "ist_verzweigung": False})
    naechste = [
        t.zu_schritt.node_id
        for t in schritt.ausgaende.select_related("zu_schritt")
        if t.zu_schritt.node_id not in sitzung.besuchte_schritte and t.zu_schritt.node_id != schritt.node_id
    ]
    hat_verzweigung = len(naechste) > 1
    if naechste:
        naechste_sortiert = sorted(naechste, key=lambda n: fortschritt_map.get(n, {}).get("tiefe", 0))
        for nid in naechste_sortiert[:1]:
            s = schritt_map.get(nid)
            if s:
                schritt_anzeige.append({"titel": s.titel, "zustand": "naechster", "ist_verzweigung": hat_verzweigung})
    return {
        "fortschritt":        fortschritt_pct,
        "fortschritt_tiefe":  fortschritt_tiefe,
        "fortschritt_gesamt": fortschritt_gesamt,
        "schritt_anzeige":    schritt_anzeige,
    }


@login_required
def pfad_schritt(request, sitzung_pk):
    """Zeigt den aktuellen Schritt und verarbeitet POST-Eingaben."""
    sitzung = get_object_or_404(
        AntrSitzung, pk=sitzung_pk, user=request.user, status=AntrSitzung.STATUS_LAUFEND
    )
    schritt = sitzung.aktueller_schritt
    if not schritt:
        messages.error(request, "Sitzung hat keinen aktuellen Schritt.")
        return redirect("formulare:pfad_liste")

    felder_render = _substituiere_system_vars(schritt.felder(), sitzung.pfad)
    ctx = _schritt_kontext(sitzung, schritt)

    def _render_schritt(fehler, vorwerte):
        return render(request, "formulare/pfad_schritt.html", {
            "sitzung":               sitzung,
            "schritt":               schritt,
            "felder_render":         felder_render,
            "fehler":                fehler,
            "vorwerte":              vorwerte,
            "gesammelte_daten_json": json.dumps(sitzung.gesammelte_daten, ensure_ascii=False),
            "zusammenfassung":       _baue_zusammenfassung(sitzung) if schritt.ist_ende else [],
            **ctx,
        })

    if request.method == "POST" and "_zurueck" in request.POST:
        besucht = sitzung.besuchte_schritte
        if len(besucht) >= 2:
            vorheriger_id = besucht[-2]
            sitzung.besuchte_schritte = besucht[:-1]
            vorheriger = get_object_or_404(AntrSchritt, pfad=sitzung.pfad, node_id=vorheriger_id)
            sitzung.aktueller_schritt = vorheriger
            sitzung.save(update_fields=["aktueller_schritt", "besuchte_schritte"])
        return redirect("formulare:pfad_schritt", sitzung_pk=sitzung.pk)

    if request.method == "POST":
        schritt_daten, fehler = _validiere_schritt(
            schritt, request.POST,
            vorige_daten=sitzung.gesammelte_daten,
            files_data=request.FILES,
            sitzung=sitzung,
            pfad=sitzung.pfad,
        )
        if fehler:
            return _render_schritt(fehler, request.POST)

        sitzung.gesammelte_daten.update(schritt_daten)
        for feld in _eingabefelder(schritt):
            if feld.get("typ") == "einwilligung" and schritt_daten.get(feld.get("id")):
                sitzung.einwilligungen_json[feld.get("id", "")] = {
                    "text":            feld.get("text", ""),
                    "zeitpunkt":       timezone.now().isoformat(),
                    "schritt_node_id": schritt.node_id,
                }

        if schritt.ist_ende:
            sitzung.abschliessen()
            return redirect("formulare:pfad_abgeschlossen", sitzung_pk=sitzung.pk)

        transition = _naechster_schritt(schritt, sitzung.gesammelte_daten)
        if transition is None:
            return _render_schritt(
                ["Es gibt keinen passenden naechsten Schritt. Bitte pruefen Sie Ihre Eingaben."],
                request.POST,
            )

        naechster = transition.zu_schritt
        # Loop-Erkennung
        if naechster.node_id in sitzung.besuchte_schritte:
            durchlauf = sitzung.gesammelte_daten.get("__loop_durchlauf", 0)
            praeffix = f"__loop_{durchlauf}__"
            for k, v in list(sitzung.gesammelte_daten.items()):
                if not k.startswith("__"):
                    sitzung.gesammelte_daten[praeffix + k] = v
            for k in [k for k in sitzung.gesammelte_daten if not k.startswith("__")]:
                del sitzung.gesammelte_daten[k]
            sitzung.gesammelte_daten["__loop_durchlauf"] = durchlauf + 1
            ziel_idx = sitzung.besuchte_schritte.index(naechster.node_id)
            besucht_liste = sitzung.besuchte_schritte[: ziel_idx + 1]
        else:
            besucht_liste = sitzung.besuchte_schritte + [naechster.node_id]

        sitzung.aktueller_schritt = naechster
        sitzung.besuchte_schritte = besucht_liste
        sitzung.save(update_fields=[
            "aktueller_schritt", "besuchte_schritte", "gesammelte_daten", "einwilligungen_json",
        ])
        if naechster.ist_ende and not naechster.felder():
            sitzung.abschliessen()
            return redirect("formulare:pfad_abgeschlossen", sitzung_pk=sitzung.pk)
        return redirect("formulare:pfad_schritt", sitzung_pk=sitzung.pk)

    return _render_schritt([], sitzung.gesammelte_daten)


# ---------------------------------------------------------------------------
# Player: Abschluss
# ---------------------------------------------------------------------------

@login_required
def pfad_abgeschlossen(request, sitzung_pk):
    """Abschluss-Seite nach erfolgreichem Durchlauf."""
    sitzung = get_object_or_404(AntrSitzung, pk=sitzung_pk, user=request.user)
    email_empfaenger = _versende_pdf_email(sitzung)
    return render(request, "formulare/pfad_abgeschlossen.html", {
        "sitzung":          sitzung,
        "zusammenfassung":  _baue_zusammenfassung(sitzung),
        "email_empfaenger": email_empfaenger,
    })


# ---------------------------------------------------------------------------
# Meine Antraege
# ---------------------------------------------------------------------------

@login_required
def meine_antraege(request):
    """Alle eigenen Sitzungen des Nutzers."""
    sitzungen = AntrSitzung.objects.filter(user=request.user).select_related("pfad")
    return render(request, "formulare/meine_antraege.html", {"sitzungen": sitzungen})


@login_required
def sitzung_loeschen(request, pk):
    """Loescht eine eigene Sitzung nach Bestaetigung (POST)."""
    sitzung = get_object_or_404(AntrSitzung, pk=pk, user=request.user)
    if request.method == "POST":
        sitzung.delete()
    return redirect("formulare:meine_antraege")


# ---------------------------------------------------------------------------
# PDF-Download
# ---------------------------------------------------------------------------

@login_required
def sitzung_pdf(request, pk):
    """Erzeugt ein PDF der abgeschlossenen Sitzung."""
    try:
        from weasyprint import HTML
    except ImportError:
        messages.error(request, "WeasyPrint nicht installiert.")
        return redirect("formulare:meine_antraege")
    sitzung = get_object_or_404(
        AntrSitzung, pk=pk, user=request.user, status=AntrSitzung.STATUS_ABGESCHLOSSEN
    )
    vorgangsnummer = sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}"
    html_string = render_to_string("formulare/sitzung_pdf.html", {
        "sitzung":         sitzung,
        "zusammenfassung": _baue_zusammenfassung(sitzung),
        "vorgangsnummer":  vorgangsnummer,
    })
    pdf = HTML(string=html_string).write_pdf()
    dateiname = f"{vorgangsnummer}.pdf".replace(" ", "_")
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


# ---------------------------------------------------------------------------
# Auswertung
# ---------------------------------------------------------------------------

_AUSWERTUNG_KEIN_WERT = {
    "textblock", "abschnitt", "trennlinie", "leerblock", "link", "einwilligung",
}


@login_required
def pfad_auswertung(request, pk):
    """Tabellarische Auswertung aller Sitzungen eines Pfads. Nur fuer Editoren."""
    pfad = get_object_or_404(AntrPfad, pk=pk)
    if not _ist_editor(request.user):
        messages.error(request, "Kein Zugriff.")
        return redirect("formulare:pfad_liste")

    spalten = []
    gesehene_ids = set()
    for schritt in pfad.schritte.order_by("pk"):
        for feld in schritt.felder():
            if not isinstance(feld, dict):
                continue
            feld_id = feld.get("id")
            typ = feld.get("typ", "")
            label = feld.get("label") or feld_id or ""
            if feld_id and typ not in _AUSWERTUNG_KEIN_WERT and feld_id not in gesehene_ids:
                spalten.append({"id": feld_id, "label": label})
                gesehene_ids.add(feld_id)

    status_filter = request.GET.get("status", "abgeschlossen")
    datum_von = request.GET.get("datum_von", "")
    datum_bis = request.GET.get("datum_bis", "")
    suche = request.GET.get("suche", "").strip()

    qs = AntrSitzung.objects.filter(pfad=pfad).select_related("user")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if datum_von:
        try:
            qs = qs.filter(gestartet_am__date__gte=datetime.date.fromisoformat(datum_von))
        except ValueError:
            pass
    if datum_bis:
        try:
            qs = qs.filter(gestartet_am__date__lte=datetime.date.fromisoformat(datum_bis))
        except ValueError:
            pass
    if suche:
        qs = qs.filter(gesammelte_daten__icontains=suche)
    qs = qs.order_by("-gestartet_am")
    gesamt = qs.count()

    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        kuerzel = (pfad.kuerzel or str(pfad.pk)).upper()
        filename = f"auswertung_{kuerzel}_{timezone.localdate()}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Vorgangsnummer", "Datum", "Status", "Einreicher"] + [s["label"] for s in spalten])
        for sitzung in qs:
            einreicher = str(sitzung.user) if sitzung.user else (sitzung.email_anonym or "anonym")
            row = [
                sitzung.vorgangsnummer or "",
                sitzung.gestartet_am.strftime("%d.%m.%Y %H:%M"),
                sitzung.get_status_display(),
                einreicher,
            ] + [
                str(sitzung.gesammelte_daten.get(sp["id"], "") or "")
                for sp in spalten
            ]
            writer.writerow(row)
        return response

    zeilen = []
    for sitzung in qs[:500]:
        einreicher = str(sitzung.user) if sitzung.user else (sitzung.email_anonym or "anonym")
        zeilen.append({
            "pk":             sitzung.pk,
            "vorgangsnummer": sitzung.vorgangsnummer or "-",
            "gestartet_am":   sitzung.gestartet_am,
            "status":         sitzung.get_status_display(),
            "einreicher":     einreicher,
            "felder":         [str(sitzung.gesammelte_daten.get(sp["id"], "") or "") for sp in spalten],
        })

    return render(request, "formulare/pfad_auswertung.html", {
        "pfad":          pfad,
        "spalten":       spalten,
        "zeilen":        zeilen,
        "gesamt":        gesamt,
        "status_filter": status_filter,
        "datum_von":     datum_von,
        "datum_bis":     datum_bis,
        "suche":         suche,
    })


# ---------------------------------------------------------------------------
# Oeffentliche Formulare (ohne Login)
# ---------------------------------------------------------------------------

def _anon_darf_sitzung(request, sitzung_pk):
    """Prueft ob die anonyme Sitzung zur Browser-Session gehoert."""
    return sitzung_pk in request.session.get("anon_sitzungen", [])


def antrag_oeffentlich(request, kuerzel):
    """Startseite eines oeffentlichen Formulars (kein Login noetig)."""
    pfad = get_object_or_404(AntrPfad, kuerzel__iexact=kuerzel, aktiv=True, oeffentlich=True)
    return render(request, "formulare/antrag_oeffentlich.html", {"pfad": pfad})


def antrag_oeffentlich_starten(request, kuerzel):
    """POST: Neue anonyme Sitzung anlegen."""
    pfad = get_object_or_404(AntrPfad, kuerzel__iexact=kuerzel, aktiv=True, oeffentlich=True)
    if request.method != "POST":
        return redirect("formulare:antrag_oeffentlich", kuerzel=kuerzel)
    start = pfad.start_schritt()
    if not start:
        return redirect("formulare:antrag_oeffentlich_fehler")
    email_anonym = request.POST.get("email_anonym", "").strip() or None
    sitzung = AntrSitzung.objects.create(
        pfad=pfad,
        user=None,
        email_anonym=email_anonym,
        aktueller_schritt=start,
        besuchte_schritte=[start.node_id],
    )
    anon_sitzungen = request.session.get("anon_sitzungen", [])
    anon_sitzungen.append(sitzung.pk)
    request.session["anon_sitzungen"] = anon_sitzungen
    return redirect("formulare:antrag_oeffentlich_schritt", sitzung_pk=sitzung.pk)


def antrag_oeffentlich_schritt(request, sitzung_pk):
    """Zeigt aktuellen Schritt einer anonymen Sitzung."""
    if not _anon_darf_sitzung(request, sitzung_pk):
        return redirect("formulare:antrag_oeffentlich_fehler")
    sitzung = get_object_or_404(
        AntrSitzung, pk=sitzung_pk, user__isnull=True, status=AntrSitzung.STATUS_LAUFEND
    )
    schritt = sitzung.aktueller_schritt
    if not schritt:
        return redirect("formulare:antrag_oeffentlich_fehler")

    felder_render = _substituiere_system_vars(schritt.felder(), sitzung.pfad)

    def _render_pub(fehler, vorwerte):
        return render(request, "formulare/antrag_oeffentlich_schritt.html", {
            "sitzung":         sitzung,
            "schritt":         schritt,
            "felder_render":   felder_render,
            "fehler":          fehler,
            "vorwerte":        vorwerte,
            "zusammenfassung": _baue_zusammenfassung(sitzung) if schritt.ist_ende else [],
        })

    if request.method == "POST" and "_zurueck" in request.POST:
        besucht = sitzung.besuchte_schritte
        if len(besucht) >= 2:
            vorheriger_id = besucht[-2]
            sitzung.besuchte_schritte = besucht[:-1]
            vorheriger = get_object_or_404(AntrSchritt, pfad=sitzung.pfad, node_id=vorheriger_id)
            sitzung.aktueller_schritt = vorheriger
            sitzung.save(update_fields=["aktueller_schritt", "besuchte_schritte"])
        return redirect("formulare:antrag_oeffentlich_schritt", sitzung_pk=sitzung.pk)

    if request.method == "POST":
        schritt_daten, fehler = _validiere_schritt(
            schritt, request.POST,
            vorige_daten=sitzung.gesammelte_daten,
            files_data=request.FILES,
            sitzung=sitzung,
            pfad=sitzung.pfad,
        )
        if fehler:
            return _render_pub(fehler, request.POST)
        sitzung.gesammelte_daten.update(schritt_daten)
        for feld in _eingabefelder(schritt):
            if feld.get("typ") == "einwilligung" and schritt_daten.get(feld.get("id")):
                sitzung.einwilligungen_json[feld.get("id", "")] = {
                    "text":            feld.get("text", ""),
                    "zeitpunkt":       timezone.now().isoformat(),
                    "schritt_node_id": schritt.node_id,
                }
        if schritt.ist_ende:
            sitzung.abschliessen()
            return redirect("formulare:antrag_oeffentlich_abgeschlossen", sitzung_pk=sitzung.pk)
        transition = _naechster_schritt(schritt, sitzung.gesammelte_daten)
        if transition is None:
            return _render_pub(["Kein passender naechster Schritt gefunden."], request.POST)
        naechster = transition.zu_schritt
        if naechster.node_id in sitzung.besuchte_schritte:
            durchlauf = sitzung.gesammelte_daten.get("__loop_durchlauf", 0)
            praeffix = f"__loop_{durchlauf}__"
            for k, v in list(sitzung.gesammelte_daten.items()):
                if not k.startswith("__"):
                    sitzung.gesammelte_daten[praeffix + k] = v
            for k in [k for k in sitzung.gesammelte_daten if not k.startswith("__")]:
                del sitzung.gesammelte_daten[k]
            sitzung.gesammelte_daten["__loop_durchlauf"] = durchlauf + 1
            ziel_idx = sitzung.besuchte_schritte.index(naechster.node_id)
            besucht_liste = sitzung.besuchte_schritte[: ziel_idx + 1]
        else:
            besucht_liste = sitzung.besuchte_schritte + [naechster.node_id]
        sitzung.aktueller_schritt = naechster
        sitzung.besuchte_schritte = besucht_liste
        sitzung.save(update_fields=[
            "aktueller_schritt", "besuchte_schritte", "gesammelte_daten", "einwilligungen_json",
        ])
        if naechster.ist_ende and not naechster.felder():
            sitzung.abschliessen()
            return redirect("formulare:antrag_oeffentlich_abgeschlossen", sitzung_pk=sitzung.pk)
        return redirect("formulare:antrag_oeffentlich_schritt", sitzung_pk=sitzung.pk)

    return _render_pub([], sitzung.gesammelte_daten)


def antrag_oeffentlich_abgeschlossen(request, sitzung_pk):
    """Abschluss-Seite anonymer Sitzungen."""
    if not _anon_darf_sitzung(request, sitzung_pk):
        return redirect("formulare:antrag_oeffentlich_fehler")
    sitzung = get_object_or_404(AntrSitzung, pk=sitzung_pk, user__isnull=True)
    email_empfaenger = _versende_pdf_email(sitzung)
    return render(request, "formulare/antrag_oeffentlich_abgeschlossen.html", {
        "sitzung":          sitzung,
        "zusammenfassung":  _baue_zusammenfassung(sitzung),
        "email_empfaenger": email_empfaenger,
    })


def antrag_oeffentlich_fehler(request):
    """Fehlerseite: Kein Zugriff auf oeffentliches Formular."""
    return render(request, "formulare/antrag_oeffentlich_fehler.html", {}, status=403)
