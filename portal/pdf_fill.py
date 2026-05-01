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
                    "w_pct": (x2 - x1) / pw,
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


def _radio_group_states(pdf_bytes: bytes) -> dict[str, list[str]]:
    """Gibt {feldname: [state0, state1, ...]} für Radio-Gruppen zurück.

    Für Radio-Buttons teilen sich alle Optionen einen Feldnamen; jede Annotation
    hat einen eigenen Appearance-State (/0, /1, /2 oder /Auswahl1, /Auswahl2 …).
    Die Reihenfolge entspricht der Seitenreihenfolge der Annotationen.
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    result: dict[str, list[str]] = {}
    for page in reader.pages:
        for ref in (page.get("/Annots") or []):
            try:
                obj = ref.get_object()
                ft = obj.get("/FT")
                if ft != "/Btn":
                    parent = obj.get("/Parent")
                    if parent:
                        ft = parent.get_object().get("/FT")
                if ft != "/Btn":
                    continue
                name = str(obj.get("/T", ""))
                if not name:
                    parent = obj.get("/Parent")
                    if parent:
                        name = str(parent.get_object().get("/T", ""))
                if not name:
                    continue
                ap = obj.get("/AP", {})
                n = ap.get("/N")
                if not n:
                    continue
                n_obj = n.get_object()
                for key in n_obj.keys():
                    if str(key) != "/Off":
                        result.setdefault(name, []).append(str(key))
                        break
            except Exception:
                pass
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
    baseline_offset: float = 0.0,
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
    radio_states = _radio_group_states(pdf_bytes)  # alle States je Radio-Gruppe

    # Normalisierter Lookup: bereinigter Name → echter AcroForm-Feldname
    # (AcroForm-Namen sind Optionstexte ohne Sonderzeichen)
    def _norm(text: str) -> str:
        return re.sub(r'[^a-zA-Z0-9À-ž]', '', text).lower()

    acro_norm_lookup: dict[str, str] = {_norm(k): k for k in on_states}

    field_map: dict[str, list[str]] = {}   # acroform_name → [werte]
    btn_map: dict[str, str] = {}           # AcroForm-Btn-Feld → on-state oder "/Off"
    overflow_eintraege: list[dict] = []    # Daten ohne AcroForm-Slot
    sig_eintraege: dict[int, list[dict]] = {}  # page → [{x_pct, y_pct, bild_b64}]
    badge_eintraege: dict[int, list[dict]] = {}  # page → [{x_pct, y_pct, custom:True, wert}]

    # Felder die in einer Vorlage referenziert werden nicht separat als Badge zeichnen
    felder_in_vorlage: set = set()
    for _s in schritte:
        for _f in (_s.felder_json or []):
            for _m in re.finditer(r'\{(\w+)\}', _f.get("vorlage", "")):
                felder_in_vorlage.add(_m.group(1))

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

            if typ == "systemfeld":
                import datetime as _dt
                _heute_str = _dt.date.today().strftime("%d.%m.%Y")
                _sys_map = {
                    "antragsdatum":              _heute_str,
                    "heute":                     _dt.date.today().isoformat(),
                    "vorgangsnummer":            vorgangsnummer,
                    "antragsnummer_zeitstempel": f"{vorgangsnummer} | {_heute_str}" if vorgangsnummer else _heute_str,
                }
                wert_roh = _sys_map.get(feld.get("systemwert", ""), str(gesammelte_daten.get(feld_id, ""))).strip()
            else:
                vorlage = feld.get("vorlage", "").strip()
                if vorlage:
                    wert_roh = re.sub(
                        r"\{(\w+)\}",
                        lambda m: str(gesammelte_daten.get(m.group(1), "")).strip(),
                        vorlage,
                    ).strip()
                    # Vorlage-Wert direkt in field_map eintragen – werte-Schleife überspringen
                    if wert_roh and acroform_name and "," not in acroform_name and not acroform_name.startswith("loop:"):
                        field_map.setdefault(acroform_name, []).append(wert_roh)
                        continue
                else:
                    wert_roh = str(gesammelte_daten.get(feld_id, "")).strip()

            # ── Badge-Overlay für Felder mit Koordinaten aber ohne AcroForm ──
            if not acroform_name and wert_roh and feld_id not in felder_in_vorlage and typ not in ("signatur", "checkboxen", "radio", "bool", "einwilligung"):
                _xb = float(feld.get("x_pct") or 0)
                _yb = float(feld.get("y_pct") or 0)
                if _xb != 0 or _yb != 0:
                    _sb = int(feld.get("seite_nr") or 0)
                    badge_eintraege.setdefault(_sb, []).append({
                        "x_pct": _xb, "y_pct": _yb,
                        "w_pct": 0, "h_pct": 0.03,
                        "custom": True,
                        "wert": _format_wert(wert_roh),
                    })

            # ── Signatur: Koordinaten für Bild-Overlay merken ───────────────
            if typ == "signatur":
                x_sig = float(feld.get("x_pct") or 0)
                y_sig = float(feld.get("y_pct") or 0)
                seite_sig = int(feld.get("seite_nr") or 0)
                if x_sig != 0 or y_sig != 0:
                    wert_sig = str(gesammelte_daten.get(feld_id, "")).strip()
                    if wert_sig.startswith("data:image"):
                        b64 = wert_sig.split(",", 1)[-1]
                        eintrag = {"x_pct": x_sig, "y_pct": y_sig, "bild_b64": b64}
                        audit = str(gesammelte_daten.get(f"__sig_audit__{feld_id}", "")).strip()
                        if audit:
                            eintrag["audit_text"] = audit
                        sig_eintraege.setdefault(seite_sig, []).append(eintrag)
                continue

            # ── Checkbox / Radio / Bool: per Optionstexten matchen ─────────
            if typ in ("checkboxen", "radio", "bool", "einwilligung"):
                optionen_koord = feld.get("optionen_koord") or {}

                # Koordinaten-Overlay wenn optionen_koord gesetzt (kein AcroForm nötig)
                if optionen_koord and not acroform_name:
                    if typ in ("bool", "einwilligung"):
                        is_true = wert_roh.lower() in _TRUTHY
                        koord = optionen_koord.get("ja" if is_true else "nein") or {}
                        ox, oy = float(koord.get("x_pct") or 0), float(koord.get("y_pct") or 0)
                        os_ = int(koord.get("seite_nr") or 0)
                        if ox != 0 or oy != 0:
                            badge_eintraege.setdefault(os_, []).append({"x_pct": ox, "y_pct": oy, "wert": "X", "zentriert": True})
                    else:
                        norm_wert = _norm(wert_roh)
                        gewaehlte = {_norm(v.strip()) for v in wert_roh.split(",")} if typ == "checkboxen" else {norm_wert}
                        for opt_label, koord in optionen_koord.items():
                            if _norm(opt_label) in gewaehlte:
                                ox, oy = float(koord.get("x_pct") or 0), float(koord.get("y_pct") or 0)
                                os_ = int(koord.get("seite_nr") or 0)
                                if ox != 0 or oy != 0:
                                    badge_eintraege.setdefault(os_, []).append({"x_pct": ox, "y_pct": oy, "wert": "X", "zentriert": True})
                    continue

                if typ in ("bool", "einwilligung"):
                    selected_set = {_norm(acroform_name)} if wert_roh.lower() in _TRUTHY else set()
                    search_list = [acroform_name]
                elif typ == "radio":
                    # Radio-Gruppe: gewählten Index → Appearance-State des PDF
                    if acroform_name and optionen:
                        norm_wert = _norm(wert_roh.strip())
                        for idx, opt in enumerate(optionen):
                            if _norm(opt) == norm_wert:
                                states = radio_states.get(acroform_name, [])
                                if idx < len(states):
                                    btn_map[acroform_name] = states[idx]
                                break
                    continue
                else:
                    # checkboxen: mehrere PDF-Felder, je ein Feldname pro Option
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

    logger.info("fuelle_acroform: %d Felder befüllen, %d Overflow-Einträge, baseline_offset=%.1f",
                len(final_map), len(overflow_eintraege), baseline_offset)

    # Tx-Feld-Positionen vorab aus AcroForm lesen (für reportlab-Overlay)
    tx_rects = _extract_text_field_rects(pdf_bytes)

    # Checkbox-/Radio-Felder per AcroForm setzen
    from pypdf.generic import NameObject as _NO, BooleanObject as _BO
    radio_btn_names = set()

    # Radio-Gruppen: /AS auf Widget-Annotationen + /V auf Parent-Feld setzen
    radio_entries = {k: v for k, v in btn_map.items() if k in radio_states and len(radio_states[k]) > 1}
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if radio_entries:
        # /V am AcroForm-Root-Feld setzen
        try:
            acroform = reader.trailer["/Root"].get_object().get("/AcroForm", {}).get_object()
            for ref in (acroform.get("/Fields") or []):
                f = ref.get_object()
                fname = str(f.get("/T", ""))
                if fname in radio_entries:
                    f[_NO("/V")] = _NO(radio_entries[fname])
        except Exception as exc:
            logger.warning("fuelle_acroform: Radio /V Root-Fehler – %s", exc)

        # /AS auf jeder Widget-Annotation setzen
        for page in reader.pages:
            for ref in (page.get("/Annots") or []):
                try:
                    obj = ref.get_object()
                    t = obj.get("/T")
                    if not t and obj.get("/Parent"):
                        t = obj.get("/Parent").get_object().get("/T")
                    field_name = str(t) if t else ""
                    if field_name not in radio_entries:
                        continue
                    selected_state = radio_entries[field_name]
                    ap = obj.get("/AP", {})
                    n_obj_ref = ap.get("/N")
                    if not n_obj_ref:
                        continue
                    n_obj = n_obj_ref.get_object()
                    annotation_on_state = next(
                        (str(k) for k in n_obj.keys() if str(k) != "/Off"), None
                    )
                    if annotation_on_state is None:
                        continue
                    new_as = annotation_on_state if annotation_on_state == selected_state else "/Off"
                    obj[_NO("/AS")] = _NO(new_as)
                    radio_btn_names.add(field_name)
                except Exception as exc:
                    logger.warning("fuelle_acroform: Radio-Annotation-Fehler – %s", exc)

    writer = PdfWriter()
    writer.append(reader)
    if btn_map:
        # Checkboxen (non-radio) per pypdf update
        checkbox_only = {k: v for k, v in btn_map.items() if k not in radio_entries}
        if checkbox_only:
            for page in writer.pages:
                try:
                    writer.update_page_form_field_values(page, checkbox_only, auto_regenerate=False)
                except Exception as exc:
                    logger.warning("fuelle_acroform: Checkbox-Fehler – %s", exc)

        if "/AcroForm" in writer._root_object:
            writer._root_object["/AcroForm"][_NO("/NeedAppearances")] = _BO(True)
        logger.info("fuelle_acroform: %d Btn-Felder gesetzt (%d Radio-Gruppen direkt)",
                    len(btn_map), len(radio_btn_names))

    buf = io.BytesIO()
    writer.write(buf)
    # Flatten baked checkboxes (poppler regeneriert Appearance via NeedAppearances)
    filled_bytes = _flatten_pdf(buf.getvalue())

    # Vom Nutzer manuell gesetzte Koordinaten sammeln (überschreiben tx_rects)
    custom_koord: dict[str, dict] = {}
    for schritt in schritte:
        for feld in (schritt.felder_json or []):
            acroform_name = (feld.get("acroform_name") or "").strip()
            if not acroform_name or "," in acroform_name or acroform_name.startswith("loop:"):
                continue
            x = float(feld.get("x_pct") or 0)
            y = float(feld.get("y_pct") or 0)
            if x != 0 or y != 0:
                custom_koord[acroform_name] = {
                    "x_pct": x, "y_pct": y,
                    "seite_nr": int(feld.get("seite_nr") or 0),
                }

    # Textwerte per reportlab-Overlay einzeichnen (volle Latin-1 Unterstützung inkl. Umlaute)
    # Priorität: AcroForm-Rect (tx_rects) > manuell gesetzte Badge-Koordinaten (custom_koord)
    text_eintraege: dict[int, list[dict]] = {}  # page → [{x_pct, y_pct, w_pct, h_pct, custom, wert}]
    for acroform_name, wert in final_map.items():
        if acroform_name in on_states or acroform_name in btn_map:
            continue  # Btn-Felder bereits erledigt
        rect = tx_rects.get(acroform_name)
        if rect:
            # AcroForm-Feldgeometrie hat Vorrang – präzise Positionierung ohne manuelle Badges
            text_eintraege.setdefault(rect["page"], []).append({
                "x_pct": rect["x_pct"],
                "y_pct": rect["y_pct"],
                "w_pct": rect["w_pct"],
                "h_pct": rect["h_pct"],
                "custom": False,
                "wert": wert,
            })
        elif acroform_name in custom_koord:
            # Fallback: manuell gesetzte Badge-Koordinaten (kein AcroForm-Rect vorhanden)
            c = custom_koord[acroform_name]
            text_eintraege.setdefault(c["seite_nr"], []).append({
                "x_pct": c["x_pct"],
                "y_pct": c["y_pct"],
                "w_pct": 0,
                "h_pct": 0.03,
                "custom": True,
                "wert": wert,
            })

    for p, entries in sig_eintraege.items():
        text_eintraege.setdefault(p, []).extend(entries)
    for p, entries in badge_eintraege.items():
        text_eintraege.setdefault(p, []).extend(entries)

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
                from reportlab.pdfbase.pdfmetrics import stringWidth
                FONT_NAME = "Helvetica"
                FONT_SIZE = 10
                LINE_GAP  = FONT_SIZE * 1.2

                c = rl_canvas.Canvas(overlay_buf, pagesize=(pw, ph))
                c.setFont(FONT_NAME, FONT_SIZE)
                c.setFillColorRGB(0, 0, 0)
                for e in eintraege:
                    x_pt = e["x_pct"] * pw + 2
                    if e.get("zentriert"):
                        # X-Kreuz: exakt auf Pin-Spitze zentrieren (kein Offset)
                        cx = e["x_pct"] * pw
                        cy = ph - e["y_pct"] * ph - FONT_SIZE * 0.3
                        c.drawCentredString(cx, cy, e["wert"])
                        continue
                    if "bild_b64" in e:
                        import base64 as _b64
                        from reportlab.lib.utils import ImageReader as _IR
                        sig_bytes = _b64.b64decode(e["bild_b64"])
                        sig_img = _IR(io.BytesIO(sig_bytes))
                        sig_w = pw * 0.25
                        sig_h = sig_w * 0.25
                        y_pt = ph - e["y_pct"] * ph  # Bildboden auf Badge-Position
                        c.drawImage(sig_img, x_pt, y_pt, width=sig_w, height=sig_h, mask="auto")
                        if e.get("audit_text"):
                            c.setFont("Helvetica", 6)
                            c.setFillColorRGB(0.4, 0.4, 0.4)
                            c.drawString(x_pt, y_pt - 8, e["audit_text"])
                            c.setFont("Helvetica", FONT_SIZE)
                            c.setFillColorRGB(0, 0, 0)
                        continue
                    w_pt = e["w_pct"] * pw - 4 if e.get("w_pct") else 0
                    if e.get("custom"):
                        y_pt = ph - e["y_pct"] * ph + 3
                    else:
                        field_top = ph - e["y_pct"] * ph
                        field_h   = e["h_pct"] * ph
                        # Baseline knapp über der Feldunterkante (wie Schreiben auf eine Linie)
                        y_pt = field_top - field_h + max(2.0, FONT_SIZE * 0.25) + baseline_offset

                    text = e["wert"]
                    # Zeilenumbruch nur wenn Feldbreite bekannt und Text zu lang
                    if w_pt > 20 and stringWidth(text, FONT_NAME, FONT_SIZE) > w_pt:
                        # Wörter umbrechen bis sie in die Breite passen
                        worte = text.split()
                        zeilen, zeile = [], []
                        for wort in worte:
                            probe = " ".join(zeile + [wort])
                            if zeile and stringWidth(probe, FONT_NAME, FONT_SIZE) > w_pt:
                                zeilen.append(" ".join(zeile))
                                zeile = [wort]
                            else:
                                zeile.append(wort)
                        if zeile:
                            zeilen.append(" ".join(zeile))
                        for i, z in enumerate(zeilen):
                            c.drawString(x_pt, y_pt - i * LINE_GAP, z)
                    else:
                        c.drawString(x_pt, y_pt, text)
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
        "heute":                      _date.today().isoformat(),
        "antragsnummer_zeitstempel":  f"{vorgangsnummer} | {_heute}" if vorgangsnummer else _heute,
    }

    _SKIP = {"textblock", "abschnitt", "zusammenfassung", "quizergebnis", "einwilligung"}
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

            # ── Signatur: base64-PNG als Bild einbetten ──────────────────────
            if typ == "signatur":
                wert_sig = str(daten.get(fid, "")).strip()
                if wert_sig.startswith("data:image"):
                    b64 = wert_sig.split(",", 1)[-1]
                    if seite < num_pages:
                        eintrag = {"x_pct": x_pct, "y_pct": y_pct, "bild_b64": b64}
                        audit = str(daten.get(f"__sig_audit__{fid}", "")).strip()
                        if audit:
                            eintrag["audit_text"] = audit
                        felder_pro_seite[seite].append(eintrag)
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
            loop_zeile_pct = float(feld.get("loop_zeile_pct") or 0) / 100.0
            if not wert and not loop_zeile_pct:
                continue
            if wert:
                wert = _format_wert(wert)
                if seite < num_pages:
                    eintrag = {"x_pct": x_pct, "y_pct": y_pct, "wert": wert}
                    if typ == "bool":
                        eintrag["zentriert"] = True
                    felder_pro_seite[seite].append(eintrag)

            # Loop-Zeilen: __loop_0__fid, __loop_1__fid ...
            loop_y_offsets = feld.get("loop_y_offsets") or []
            if loop_zeile_pct or loop_y_offsets:
                loop_n = 0
                while True:
                    loop_key = f"__loop_{loop_n}__{fid}"
                    if loop_key not in daten:
                        break
                    if vorlage:
                        n_cap = loop_n
                        wert_loop = _re.sub(
                            r"\{(\w+)\}",
                            lambda m: str(daten.get(f"__loop_{n_cap}__{m.group(1)}", "")).strip(),
                            vorlage,
                        ).strip()
                    else:
                        wert_loop = str(daten[loop_key]).strip()
                    if wert_loop:
                        if loop_n < len(loop_y_offsets):
                            y_loop = float(loop_y_offsets[loop_n])
                        else:
                            y_loop = y_pct + (loop_n + 1) * loop_zeile_pct
                        if seite < num_pages:
                            felder_pro_seite[seite].append({"x_pct": x_pct, "y_pct": y_loop, "wert": _format_wert(wert_loop)})
                    loop_n += 1

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
            if "bild_b64" in entry:
                import base64 as _b64
                from reportlab.lib.utils import ImageReader as _IR
                sig_bytes = _b64.b64decode(entry["bild_b64"])
                sig_img = _IR(io.BytesIO(sig_bytes))
                sig_w = pw * 0.35
                sig_h = sig_w * 0.3
                y_pt = ph - entry["y_pct"] * ph  # Bildboden auf Badge-Position
                c.drawImage(sig_img, x_pt, y_pt, width=sig_w, height=sig_h, mask="auto")
                if entry.get("audit_text"):
                    c.setFont("Helvetica", 6)
                    c.setFillColorRGB(0.4, 0.4, 0.4)
                    c.drawString(x_pt, y_pt - 8, entry["audit_text"])
                    c.setFont(_font, float(font_size))
                    c.setFillColorRGB(0, 0, 0)
            elif entry.get("zentriert"):
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
