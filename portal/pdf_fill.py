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

def _extract_text_field_rects(pdf_bytes: bytes) -> dict[str, dict]:
    """Gibt {feldname: {page, x_pct, y_pct, w_pct, h_pct}} für alle Tx-Felder zurück.

    Liest die /Rect-Annotation aus dem AcroForm – damit können Textwerte
    via reportlab präzise positioniert werden (umgeht Font-Subset-Probleme).
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    result: dict[str, dict] = {}

    for page_idx, page in enumerate(reader.pages):
        pw = float(page.mediabox.width)
        ph = float(page.mediabox.height)
        for ref in (page.get("/Annots") or []):
            try:
                obj = ref.get_object()
                ft = obj.get("/FT")
                if not ft:
                    parent = obj.get("/Parent")
                    if parent:
                        ft = parent.get_object().get("/FT")
                if str(ft) != "/Tx":
                    continue
                name = str(obj.get("/T", ""))
                if not name or name in result:
                    continue
                rect = obj.get("/Rect")
                if not rect:
                    continue
                x1, y1, x2, y2 = [float(v) for v in rect]
                result[name] = {
                    "page": page_idx,
                    "x_pct": x1 / pw,
                    "y_pct": 1.0 - y2 / ph,   # PDF-Koordinaten: y2 = Oberkante
                    "h_pct": (y2 - y1) / ph,
                }
            except Exception:
                pass

    logger.debug("_extract_text_field_rects: %d Tx-Felder gefunden", len(result))
    return result


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

    # Normalisierter Lookup: bereinigter Name → echter AcroForm-Feldname
    # (AcroForm-Namen sind Optionstexte ohne Sonderzeichen)
    def _norm(text: str) -> str:
        return re.sub(r'[^a-zA-Z0-9À-ž]', '', text).lower()

    acro_norm_lookup: dict[str, str] = {_norm(k): k for k in on_states}

    field_map: dict[str, list[str]] = {}   # acroform_name → [werte]
    btn_map: dict[str, str] = {}           # AcroForm-Btn-Feld → on-state oder "/Off"
    overflow_eintraege: list[dict] = []    # Daten ohne AcroForm-Slot

    for schritt in schritte:
        loop_bez = getattr(schritt, "loop_bezeichnung", "") or ""

        for feld in (schritt.felder_json or []):
            acroform_name = feld.get("acroform_name", "").strip()
            feld_id = feld.get("id", "").strip()
            typ = feld.get("typ", "")
            label = feld.get("label", feld_id)
            optionen = feld.get("optionen") or []

            if not feld_id:
                continue

            wert_roh = str(gesammelte_daten.get(feld_id, "")).strip()

            # ── Checkbox / Radio / Bool: per Optionstexten matchen ─────────
            if typ in ("checkboxen", "radio", "bool"):
                if typ == "bool":
                    selected_set = {_norm(acroform_name)} if wert_roh.lower() in _TRUTHY else set()
                    search_list = [acroform_name]
                else:
                    # Wert ist kommagetrennte Liste gewählter Optionen
                    selected_set = {_norm(v.strip()) for v in wert_roh.split(",") if v.strip()}
                    search_list = optionen or [acroform_name]

                for option in search_list:
                    acro_real = acro_norm_lookup.get(_norm(option))
                    if not acro_real:
                        continue
                    is_selected = _norm(option) in selected_set
                    btn_map[acro_real] = on_states[acro_real] if is_selected else "/Off"
                continue

            if not acroform_name:
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

            # ── C) Einfaches Textfeld ─────────────────────────────────────
            for suffix, wert_str in werte:
                if not wert_str:
                    continue
                if not suffix:
                    field_map.setdefault(acroform_name, []).append(wert_str)
                elif loop_bez:
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

    # Textwerte zusammenführen
    final_map: dict[str, str] = {}
    for k, v in field_map.items():
        final_map[k] = _format_wert(" ".join(v).strip())

    if not final_map:
        logger.warning("fuelle_acroform: keine Zuordnungen – PDF unverändert")
        return pdf_bytes

    logger.info("fuelle_acroform: %d Felder befüllen, %d Overflow-Einträge",
                len(final_map), len(overflow_eintraege))

    # Tx-Feld-Positionen vorab aus AcroForm lesen (für reportlab-Overlay)
    tx_rects = _extract_text_field_rects(pdf_bytes)

    # Nur Checkbox-/Radio-Felder per AcroForm setzen (Text via reportlab, s.u.)
    checkbox_map = {k: v for k, v in final_map.items() if k in on_states}
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append(reader)
    if btn_map:
        for page in writer.pages:
            try:
                writer.update_page_form_field_values(page, btn_map, auto_regenerate=False)
            except Exception as exc:
                logger.warning("fuelle_acroform: Checkbox-Fehler – %s", exc)
        from pypdf.generic import BooleanObject, NameObject
        if "/AcroForm" in writer._root_object:
            writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
        logger.info("fuelle_acroform: %d Btn-Felder gesetzt", len(btn_map))

    buf = io.BytesIO()
    writer.write(buf)
    # Flatten baked checkboxes (poppler regeneriert Appearance via NeedAppearances)
    filled_bytes = _flatten_pdf(buf.getvalue())

    # Textwerte per reportlab-Overlay einzeichnen (volle Latin-1 Unterstützung inkl. Umlaute)
    text_eintraege: dict[int, list[dict]] = {}  # page → [{x_pct, y_pct, h_pct, wert}]
    for acroform_name, wert in final_map.items():
        if acroform_name in on_states or acroform_name in btn_map:
            continue  # Btn-Felder bereits erledigt
        rect = tx_rects.get(acroform_name)
        if not rect:
            continue
        page_idx = rect["page"]
        text_eintraege.setdefault(page_idx, []).append({
            "x_pct": rect["x_pct"],
            "y_pct": rect["y_pct"],
            "h_pct": rect["h_pct"],
            "wert": wert,
        })

    if text_eintraege:
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from pypdf import PdfReader as _PR2, PdfWriter as _PW2
            reader2 = _PR2(io.BytesIO(filled_bytes))
            writer2 = _PW2()
            writer2.append(reader2)
            num_pages = len(reader2.pages)
            for page_idx, eintraege in text_eintraege.items():
                if page_idx >= num_pages:
                    continue
                page = writer2.pages[page_idx]
                pw = float(page.mediabox.width)
                ph = float(page.mediabox.height)
                overlay_buf = io.BytesIO()
                c = rl_canvas.Canvas(overlay_buf, pagesize=(pw, ph))
                c.setFont("Helvetica", 10)
                c.setFillColorRGB(0, 0, 0)
                for e in eintraege:
                    x_pt = e["x_pct"] * pw + 2
                    # Vertikal mittig im Feld ausrichten
                    field_top = ph - e["y_pct"] * ph
                    field_h   = e["h_pct"] * ph
                    y_pt = field_top - field_h * 0.72
                    c.drawString(x_pt, y_pt, e["wert"])
                c.save()
                overlay_buf.seek(0)
                from pypdf import PdfReader as _PR3
                overlay_page = _PR3(overlay_buf).pages[0]
                page.merge_page(overlay_page)
            out_buf = io.BytesIO()
            writer2.write(out_buf)
            filled_bytes = out_buf.getvalue()
            logger.info("fuelle_acroform: Tx-Overlay für %d Seiten angewendet", len(text_eintraege))
        except Exception as exc:
            logger.error("fuelle_acroform: Tx-Overlay fehlgeschlagen – %s", exc)

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
    import re as _re

    # Felder pro Seite sammeln
    felder_pro_seite: dict[int, list[dict]] = {i: [] for i in range(num_pages)}
    for schritt in schritte:
        felder_liste = schritt.felder_json if hasattr(schritt, "felder_json") else schritt.get("felder_json", [])
        for feld in (felder_liste or []):
            if not isinstance(feld, dict):
                continue
            fid = feld.get("id", "")
            typ = feld.get("typ", "")
            if not fid or typ in _SKIP:
                continue

            # ── Ankreuz-Modus: radio/checkboxen/bool mit optionen_koord ────
            optionen_koord = feld.get("optionen_koord") or {}
            if optionen_koord and typ == "bool":
                raw = str(daten.get(fid, "")).strip().lower()
                is_true = raw in _TRUTHY
                opt_key = "ja" if is_true else "nein"
                koord = optionen_koord.get(opt_key, {})
                ox = float(koord.get("x_pct") or 0)
                oy = float(koord.get("y_pct") or 0)
                os = int(koord.get("seite_nr") or 0)
                if (ox != 0 or oy != 0) and os < num_pages:
                    felder_pro_seite[os].append({"x_pct": ox, "y_pct": oy, "wert": "X", "zentriert": True})
                continue
            if optionen_koord and typ in ("radio", "checkboxen"):
                raw_wert = str(daten.get(fid, "")).strip().lower()
                for opt_wert, opt_koord in optionen_koord.items():
                    if not isinstance(opt_koord, dict):
                        continue
                    ox = float(opt_koord.get("x_pct") or 0)
                    oy = float(opt_koord.get("y_pct") or 0)
                    os = int(opt_koord.get("seite_nr") or 0)
                    if ox == 0.0 and oy == 0.0:
                        continue
                    if opt_wert.lower() in raw_wert:
                        if os < num_pages:
                            felder_pro_seite[os].append({"x_pct": ox, "y_pct": oy, "wert": "X", "zentriert": True})
                continue

            x_pct = float(feld.get("x_pct") or 0.0)
            y_pct = float(feld.get("y_pct") or 0.0)
            seite = int(feld.get("seite_nr") or 0)
            if x_pct == 0.0 and y_pct == 0.0:
                continue

            vorlage = feld.get("vorlage", "").strip()
            if typ == "systemfeld":
                wert = _system_werte.get(feld.get("systemwert", ""), "")
            elif typ == "bool":
                # Boolean-Felder: "True"/"False" → "X"/leer
                raw = str(daten.get(fid, "")).strip()
                wert = "X" if raw.lower() in _TRUTHY else ""
            elif vorlage:
                wert = _re.sub(
                    r"\{(\w+)\}",
                    lambda m: str(daten.get(m.group(1), "")).strip(),
                    vorlage,
                ).strip()
            else:
                wert = str(daten.get(fid, "")).strip()
            if not wert:
                continue
            wert = _format_wert(wert)
            if seite < num_pages:
                eintrag = {"x_pct": x_pct, "y_pct": y_pct, "wert": wert}
                if typ == "bool":
                    eintrag["zentriert"] = True
                felder_pro_seite[seite].append(eintrag)

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
            if entry.get("zentriert"):
                # Ankreuz-Felder: Kreuz zentriert auf Klickposition (vertikal + horizontal)
                y_pt = ph - entry["y_pct"] * ph - float(font_size) * 0.25
                c.drawCentredString(x_pt, y_pt, entry["wert"])
            else:
                # Textfelder: linksbündig, kleiner Puffer nach oben
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
