# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
PDF-Ausfüll-Service: befüllt AcroForm-Felder eines Original-PDFs mit
den gesammelten Daten einer AntrSitzung.

Unterstützte acroform_name-Formate:
  "Feldname"                  → einfaches Feld, erste Iteration
  "1,2,3,4,5,6"              → Zeichen-Split: Wert zeichenweise über mehrere Felder
  "loop:Slot1,Slot2,Slot3"   → Loop-Slots: je Iteration ein Slot; Überlauf → Beiblatt
"""
import io
import logging
import re
import secrets

logger = logging.getLogger("vorgangswerk.portal")

_ISO_DATUM = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

def _format_wert(wert: str) -> str:
    """Konvertiert ISO-Datum yyyy-mm-dd → dd.mm.yyyy für PDF-Ausgabe."""
    m = _ISO_DATUM.match(wert)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return wert


# Werte die als „angehakt" gelten
_TRUTHY = {"ja", "yes", "true", "1", "x", "an", "on", "wahr", "checked"}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _checkbox_on_states(pdf_bytes: bytes) -> dict[str, str]:
    """Gibt {feldname: on-state-wert} für alle Checkbox-/Radio-Felder zurück.

    pypdf braucht den exakten AP/N-Schlüssel (z.B. '/Yes', '/Ja', '/On') um
    eine Checkbox visuell anzuhaken. Dieser Wert ist je Formular unterschiedlich.
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    result: dict[str, str] = {}

    def _scan_field(obj):
        try:
            ft = obj.get("/FT")
            if ft != "/Btn":
                parent = obj.get("/Parent")
                if parent:
                    ft = parent.get_object().get("/FT")
            if ft != "/Btn":
                return

            name = str(obj.get("/T", ""))
            if not name:
                parent = obj.get("/Parent")
                if parent:
                    name = str(parent.get_object().get("/T", ""))
            if not name or name in result:
                return

            ap = obj.get("/AP")
            if not ap:
                return
            n = ap.get("/N")
            if not n:
                return
            n_obj = n.get_object()
            for key in n_obj.keys():
                if str(key) != "/Off":
                    result[name] = str(key)   # z.B. "/Yes", "/Ja", "/1"
                    break
        except Exception:
            pass

    for page in reader.pages:
        for ref in (page.get("/Annots") or []):
            try:
                _scan_field(ref.get_object())
            except Exception:
                pass

    logger.debug("_checkbox_on_states: %d Checkbox-Felder gefunden", len(result))
    return result


def _flatten_pdf(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    """Rendert jede Seite als Bild → neues PDF ohne editierbare Felder."""
    try:
        from pdf2image import convert_from_bytes
        from pypdf import PdfWriter as _PdfWriter
        from PIL import Image as _Image

        bilder = convert_from_bytes(pdf_bytes, dpi=dpi)
        writer = _PdfWriter()
        for bild in bilder:
            img_buf = io.BytesIO()
            bild.save(img_buf, format="PDF", resolution=dpi)
            img_buf.seek(0)
            from pypdf import PdfReader as _PdfReader
            writer.append(_PdfReader(img_buf))
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception as exc:
        logger.warning("_flatten_pdf fehlgeschlagen, original zurückgegeben: %s", exc)
        return pdf_bytes


def _merge_pdfs(pdf1: bytes, pdf2: bytes) -> bytes:
    """Hängt pdf2 an pdf1 an."""
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(pdf1)))
    writer.append(PdfReader(io.BytesIO(pdf2)))
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _erstelle_beiblatt(overflow_eintraege: list, pfad_name: str, vorgangsnummer: str) -> bytes:
    """Erzeugt ein Beiblatt-PDF (WeasyPrint) für Loop-Überlaufdaten."""
    try:
        from weasyprint import HTML
        from django.template.loader import render_to_string

        # Einträge nach loop_bezeichnung + iteration gruppieren
        gruppen: dict[tuple, list] = {}
        for e in overflow_eintraege:
            key = (e["loop_bezeichnung"], e["iteration"])
            gruppen.setdefault(key, []).append(e)

        gruppen_liste = [
            {
                "loop_bezeichnung": key[0],
                "iteration": key[1],
                "felder": felder,
            }
            for key, felder in sorted(gruppen.items())
        ]

        html_str = render_to_string("portal/beiblatt.html", {
            "pfad_name": pfad_name,
            "vorgangsnummer": vorgangsnummer,
            "gruppen": gruppen_liste,
        })
        return HTML(string=html_str).write_pdf()
    except Exception as exc:
        logger.error("Beiblatt-Erstellung fehlgeschlagen: %s", exc)
        # Leeres Fallback-PDF
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

def fuelle_acroform(
    pdf_bytes: bytes,
    schritte,
    gesammelte_daten: dict,
    pfad_name: str = "",
    vorgangsnummer: str = "",
) -> bytes:
    """Füllt AcroForm-Felder im Original-PDF mit den Sitzungsdaten.

    pdf_bytes:        Original-PDF als Bytes (aus FormularAnalyse.pdf_inhalt)
    schritte:         QuerySet/Liste von AntrSchritt-Objekten des Pfades
    gesammelte_daten: dict {feld_id: wert} aus AntrSitzung.gesammelte_daten
    pfad_name:        Formularname (für Beiblatt-Header)
    vorgangsnummer:   Vorgangsnummer (für Beiblatt-Header)

    Gibt das ausgefüllte PDF als Bytes zurück.
    Bei Loop-Überlauf wird ein Beiblatt angehängt.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        raise RuntimeError("pypdf nicht installiert")

    # Checkbox-On-States vorab ermitteln (einmalig)
    on_states = _checkbox_on_states(pdf_bytes)

    field_map: dict[str, list[str]] = {}   # acroform_name → [werte]
    overflow_eintraege: list[dict] = []    # Daten ohne AcroForm-Slot

    for schritt in schritte:
        loop_bez = getattr(schritt, "loop_bezeichnung", "") or ""

        for feld in (schritt.felder_json or []):
            acroform_name = feld.get("acroform_name", "").strip()
            feld_id = feld.get("id", "").strip()
            label = feld.get("label", feld_id)

            if not feld_id or not acroform_name:
                continue

            # Alle Werte für dieses Feld (inkl. Loop-Iterationen) sammeln
            werte: list[tuple[str, str]] = []
            for schluessel, wert in gesammelte_daten.items():
                if schluessel == feld_id:
                    werte.append(("", str(wert).strip()))
                elif schluessel.startswith(f"{feld_id}__"):
                    suffix = schluessel[len(feld_id):]  # "__1", "__2", …
                    werte.append((suffix, str(wert).strip()))

            werte.sort()  # "" < "__1" < "__2" …
            if not werte:
                continue

            # ── A) Zeichen-Split: "1,2,3,4,5,6" ──────────────────────────
            if "," in acroform_name and not acroform_name.startswith("loop:"):
                ziel_felder = [n.strip() for n in acroform_name.split(",") if n.strip()]
                for _suffix, wert_str in werte:
                    if not wert_str:
                        continue
                    for i, zeichen in enumerate(wert_str):
                        if i >= len(ziel_felder):
                            break
                        field_map.setdefault(ziel_felder[i], []).append(zeichen)
                continue

            # ── B) Loop-Slots: "loop:Slot1,Slot2,Slot3" ──────────────────
            if acroform_name.startswith("loop:"):
                slots = [s.strip() for s in acroform_name[5:].split(",") if s.strip()]
                for iteration_idx, (suffix, wert_str) in enumerate(werte):
                    if not wert_str:
                        continue
                    if iteration_idx < len(slots):
                        field_map.setdefault(slots[iteration_idx], []).append(wert_str)
                    else:
                        overflow_eintraege.append({
                            "loop_bezeichnung": loop_bez or schritt.titel,
                            "iteration": iteration_idx + 1,
                            "label": label,
                            "wert": wert_str,
                        })
                continue

            # ── C) Einfaches Feld ─────────────────────────────────────────
            for suffix, wert_str in werte:
                if not wert_str:
                    continue
                if not suffix:
                    # Erste / einzige Iteration → AcroForm-Feld
                    field_map.setdefault(acroform_name, []).append(wert_str)
                elif loop_bez:
                    # Weitere Loop-Iterationen ohne dedizierten Slot → Overflow
                    try:
                        iter_nr = int(suffix.strip("_")) + 1
                    except ValueError:
                        iter_nr = 1
                    overflow_eintraege.append({
                        "loop_bezeichnung": loop_bez,
                        "iteration": iter_nr,
                        "label": label,
                        "wert": wert_str,
                    })

    # Mehrere Teilwerte pro Feld verbinden; Checkboxen auf on-state mappen
    final_map: dict[str, str] = {}
    for k, v in field_map.items():
        joined = " ".join(v).strip()
        if k in on_states:
            final_map[k] = on_states[k] if joined.lower() in _TRUTHY else "/Off"
        else:
            final_map[k] = _format_wert(joined)

    if not final_map:
        logger.warning("fuelle_acroform: keine Zuordnungen – PDF unverändert")
        return pdf_bytes

    logger.info("fuelle_acroform: %d Felder befüllen, %d Overflow-Einträge",
                len(final_map), len(overflow_eintraege))

    # PDF befüllen
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, final_map)
        except Exception as exc:
            logger.warning("fuelle_acroform: Fehler auf Seite – %s", exc)

    buf = io.BytesIO()
    writer.write(buf)
    filled_bytes = _flatten_pdf(buf.getvalue())

    # Beiblatt anhängen wenn Overflow vorhanden
    if overflow_eintraege:
        logger.info("fuelle_acroform: Beiblatt mit %d Einträgen erstellen", len(overflow_eintraege))
        beiblatt = _erstelle_beiblatt(overflow_eintraege, pfad_name, vorgangsnummer)
        return _merge_pdfs(filled_bytes, beiblatt)

    return filled_bytes


# ---------------------------------------------------------------------------
# Koordinaten-Overlay (für Non-AcroForm-PDFs)
# ---------------------------------------------------------------------------

def fuelle_pdf_overlay(
    pdf_bytes: bytes,
    schritte,
    daten: dict,
    pfad_name: str = "",
    vorgangsnummer: str = "",
    font_size: float = 9,
    font_bold: bool = False,
) -> bytes:
    """Befüllt ein Non-AcroForm-PDF per Koordinaten-Overlay (reportlab + pypdf).

    Liest x_pct / y_pct / seite_nr aus jedem Feld-Dict (aus dem KI-Scan).
    Felder ohne Koordinaten (x_pct=0 und y_pct=0) werden übersprungen.
    Gibt das befüllte PDF zurück.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:
        raise RuntimeError("reportlab nicht installiert – pip install reportlab") from exc

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    num_pages = len(reader.pages)

    # Systemwerte automatisch bereitstellen
    from datetime import date as _date
    _heute = _date.today().strftime("%d.%m.%Y")
    _system_werte = {
        "vorgangsnummer":             vorgangsnummer,
        "antragsdatum":               _heute,
        "antragsnummer_zeitstempel":  f"{vorgangsnummer} | {_heute}" if vorgangsnummer else _heute,
    }

    _SKIP = {"textblock", "abschnitt", "zusammenfassung", "quizergebnis", "signatur", "einwilligung"}

    # Felder pro Seite sammeln
    felder_pro_seite: dict[int, list[dict]] = {i: [] for i in range(num_pages)}
    for schritt in schritte:
        felder_liste = schritt.felder_json if hasattr(schritt, "felder_json") else schritt.get("felder_json", [])
        for feld in (felder_liste or []):
            if not isinstance(feld, dict):
                continue
            fid = feld.get("id", "")
            typ = feld.get("typ", "")
            x_pct = float(feld.get("x_pct") or 0.0)
            y_pct = float(feld.get("y_pct") or 0.0)
            seite = int(feld.get("seite_nr") or 0)
            if not fid or typ in _SKIP:
                continue
            if x_pct == 0.0 and y_pct == 0.0:
                continue
            if typ == "systemfeld":
                wert = _system_werte.get(feld.get("systemwert", ""), "")
            else:
                wert = str(daten.get(fid, "")).strip()
            if not wert:
                continue
            wert = _format_wert(wert)
            if seite < num_pages:
                felder_pro_seite[seite].append({"x_pct": x_pct, "y_pct": y_pct, "wert": wert})

    # Overlay pro Seite erzeugen und einmergen
    writer = PdfWriter()
    writer.append(reader)

    for page_idx, eintraege in felder_pro_seite.items():
        if not eintraege:
            continue
        page = writer.pages[page_idx]
        pw = float(page.mediabox.width)
        ph = float(page.mediabox.height)

        overlay_buf = io.BytesIO()
        c = rl_canvas.Canvas(overlay_buf, pagesize=(pw, ph))
        _font = "Helvetica-Bold" if font_bold else "Helvetica"
        c.setFont(_font, float(font_size))
        c.setFillColorRGB(0, 0, 0)

        for entry in eintraege:
            x_pt = entry["x_pct"] * pw
            # PDF Y ist von unten; y_pct ist von oben → umrechnen + 3pt Puffer nach oben
            y_pt = ph - entry["y_pct"] * ph + 3
            c.drawString(x_pt, y_pt, entry["wert"])

        c.save()
        overlay_buf.seek(0)

        overlay_reader = PdfReader(overlay_buf)
        overlay_page = overlay_reader.pages[0]
        page.merge_page(overlay_page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()
