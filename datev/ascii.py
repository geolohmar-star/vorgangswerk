# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Erzeugt DATEV-LODAS ASCII-Importdatei aus Personalfragebogen-Daten.
Format: DATEV Lohn ASCII (Stammdaten-Import).
Dokumentation: DATEV-Dok-Nr. 9211748 (LODAS ASCII-Schnittstelle).
"""
import io
from datetime import datetime


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _datum_datev(wert: str) -> str:
    """dd.mm.yyyy oder yyyy-mm-dd → TTMMJJJJ (DATEV-Datumsformat)."""
    if not wert:
        return ""
    wert = wert.strip()
    # ISO-Format yyyy-mm-dd
    if len(wert) == 10 and wert[4] == "-":
        j, m, t = wert[:4], wert[5:7], wert[8:10]
        return f"{t}{m}{j}"
    # Deutsches Format dd.mm.yyyy
    teile = wert.replace("/", ".").split(".")
    if len(teile) == 3:
        return f"{teile[0].zfill(2)}{teile[1].zfill(2)}{teile[2]}"
    return wert


def _bool_jn(wert) -> str:
    return "1" if str(wert).lower() in ("ja", "true", "1") else "0"


def _geschlecht_lodas(wert: str) -> str:
    """männlich=1, weiblich=2, divers=3."""
    mapping = {"männlich": "1", "weiblich": "2", "divers": "3"}
    return mapping.get(wert, "")


def _steuerklasse(wert: str) -> str:
    mapping = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6"}
    return mapping.get(str(wert).strip().upper(), str(wert).strip())


def _familienstand_lodas(wert: str) -> str:
    mapping = {
        "ledig": "1",
        "verheiratet": "2",
        "geschieden": "3",
        "verwitwet": "4",
        "eingetragene Lebenspartnerschaft": "5",
    }
    return mapping.get(wert, "")


# ---------------------------------------------------------------------------
# ASCII-Datei erzeugen
# ---------------------------------------------------------------------------

def erzeuge_lodas_ascii(
    daten: dict,
    beraternummer: str,
    mandantennummer: str,
    personalnummer: str = "1",
) -> bytes:
    """
    Gibt eine DATEV LODAS ASCII-Importdatei als Bytes zurück.
    daten: gesammelte_daten der AntrSitzung.
    """
    buf = io.StringIO()
    jetzt = datetime.now()

    # --- Vorlaufsatz ---
    buf.write("DATEV-Format-KZ;DATEV LODAS;ASCII;ST;\n")
    buf.write(
        f"Beraternummer;{beraternummer};Mandantennummer;{mandantennummer};"
        f"Datum;{jetzt.strftime('%d%m%Y')};Version;2;\n"
    )
    buf.write("\n")

    # --- Stammdatensatz Mitarbeiter ---
    def zeile(feldnr: str, wert: str):
        if wert:
            buf.write(f"{personalnummer};{feldnr};{wert}\n")

    # Persönliche Daten
    zeile("u1", daten.get("familienname", ""))
    zeile("u2", daten.get("vorname", ""))
    zeile("u3", _datum_datev(daten.get("geburtsdatum", "")))
    zeile("u4", _geschlecht_lodas(daten.get("geschlecht", "")))
    zeile("u5", daten.get("geburtsort_land", ""))
    zeile("u6", daten.get("staatsangehoerigkeit", ""))
    zeile("u7", _familienstand_lodas(daten.get("familienstand", "")))
    zeile("u8", _bool_jn(daten.get("schwerbehindert", "")))
    zeile("u9", daten.get("versicherungsnummer", ""))

    # Anschrift
    zeile("u20", daten.get("strasse", ""))
    zeile("u21", daten.get("plz", ""))
    zeile("u22", daten.get("ort", ""))

    # Bankverbindung
    zeile("u30", daten.get("iban", ""))
    zeile("u31", daten.get("bic", ""))

    # Beschäftigung
    zeile("b1", _datum_datev(daten.get("eintrittsdatum", "")))
    zeile("b2", _datum_datev(daten.get("ersteintritt_datum", "")))
    zeile("b3", daten.get("berufsbezeichnung", ""))
    zeile("b4", daten.get("ausgeuebte_taetigkeit", ""))
    zeile("b5", _datum_datev(daten.get("befristung_bis", "")))

    # Steuerdaten
    zeile("s1", daten.get("steuer_identifikationsnr", ""))
    zeile("s2", daten.get("finanzamt_nr", ""))
    zeile("s3", _steuerklasse(daten.get("steuerklasse", "")))
    if daten.get("kinderfreibetraege") is not None:
        zeile("s4", str(daten["kinderfreibetraege"]).replace(",", "."))
    zeile("s5", daten.get("konfession", ""))

    # Sozialversicherung
    zeile("sv1", daten.get("krankenkasse", ""))
    zeile("sv2", _bool_jn(daten.get("elterneigenschaft", "")))

    # Entlohnung
    for i in range(1, 4):
        bez = daten.get(f"entlohnung_bezeichnung_{i}", "")
        betrag = daten.get(f"entlohnung_betrag_{i}", "")
        if bez or betrag:
            zeile(f"e{i}a", bez)
            zeile(f"e{i}b", str(betrag).replace(",", ".") if betrag else "")

    buf.write("\n")
    return buf.getvalue().encode("cp1252", errors="replace")
