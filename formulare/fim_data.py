# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
FIM-Datenfeld-Katalog (Server-Seite) fuer automatisches Matching beim PDF-Import.
Spiegelt static/js/fim_felder.js – beide Dateien synchron halten.
IDs: XDatenfelder 2.0 Referenz-Format. Verifikation: https://fimportal.de/
"""

FIM_FELDER = [
    # Personalien
    {"id": "F60000001", "name": "Anrede",                        "typ": "auswahl",  "gruppe": "Personalien"},
    {"id": "F60000002", "name": "Titel / Namenszusatz",          "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000003", "name": "Vorname",                       "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000004", "name": "Familienname",                  "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000005", "name": "Geburtsname",                   "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000006", "name": "Geburtsdatum",                  "typ": "datum",    "gruppe": "Personalien"},
    {"id": "F60000007", "name": "Geburtsort",                    "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000008", "name": "Geburtsland",                   "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000009", "name": "Staatsangehörigkeit",           "typ": "text",     "gruppe": "Personalien"},
    {"id": "F60000010", "name": "Geschlecht",                    "typ": "auswahl",  "gruppe": "Personalien"},
    # Adresse
    {"id": "F60000020", "name": "Straße",                        "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000021", "name": "Hausnummer",                    "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000022", "name": "Straße und Hausnummer",         "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000023", "name": "Adresszusatz",                  "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000024", "name": "Postleitzahl",                  "typ": "plz",      "gruppe": "Adresse"},
    {"id": "F60000025", "name": "Wohnort",                       "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000026", "name": "Ortsteil",                      "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000027", "name": "Land",                          "typ": "text",     "gruppe": "Adresse"},
    {"id": "F60000028", "name": "Postfach",                      "typ": "text",     "gruppe": "Adresse"},
    # Kontakt
    {"id": "F60000030", "name": "E-Mail-Adresse",                "typ": "email",    "gruppe": "Kontakt"},
    {"id": "F60000031", "name": "Telefonnummer",                 "typ": "telefon",  "gruppe": "Kontakt"},
    {"id": "F60000032", "name": "Mobiltelefonnummer",            "typ": "telefon",  "gruppe": "Kontakt"},
    {"id": "F60000033", "name": "Faxnummer",                     "typ": "telefon",  "gruppe": "Kontakt"},
    {"id": "F60000034", "name": "Website",                       "typ": "text",     "gruppe": "Kontakt"},
    # Identifikation
    {"id": "F60000040", "name": "Personalausweisnummer",         "typ": "text",     "gruppe": "Identifikation"},
    {"id": "F60000041", "name": "Reisepassnummer",               "typ": "text",     "gruppe": "Identifikation"},
    {"id": "F60000042", "name": "Steueridentifikationsnummer",   "typ": "text",     "gruppe": "Identifikation"},
    # Bankverbindung
    {"id": "F60000043", "name": "IBAN",                          "typ": "iban",     "gruppe": "Bankverbindung"},
    {"id": "F60000044", "name": "BIC",                           "typ": "bic",      "gruppe": "Bankverbindung"},
    {"id": "F60000045", "name": "Kontoinhaber",                  "typ": "text",     "gruppe": "Bankverbindung"},
    {"id": "F60000046", "name": "Kreditinstitut",                "typ": "text",     "gruppe": "Bankverbindung"},
    # Unternehmen
    {"id": "F60000050", "name": "Unternehmensname",              "typ": "text",     "gruppe": "Unternehmen"},
    {"id": "F60000051", "name": "Rechtsform",                    "typ": "auswahl",  "gruppe": "Unternehmen"},
    {"id": "F60000052", "name": "Handelsregisternummer",         "typ": "text",     "gruppe": "Unternehmen"},
    {"id": "F60000053", "name": "Registergericht",               "typ": "text",     "gruppe": "Unternehmen"},
    {"id": "F60000054", "name": "Umsatzsteuer-ID",               "typ": "text",     "gruppe": "Unternehmen"},
    {"id": "F60000055", "name": "Steuernummer",                  "typ": "steuernummer", "gruppe": "Unternehmen"},
    {"id": "F60000056", "name": "Gründungsdatum",                "typ": "datum",    "gruppe": "Unternehmen"},
    # Antrag
    {"id": "F60000060", "name": "Antragsdatum",                  "typ": "datum",    "gruppe": "Antrag"},
    {"id": "F60000061", "name": "Begründung",                    "typ": "mehrzeil", "gruppe": "Antrag"},
    {"id": "F60000062", "name": "Beginn",                        "typ": "datum",    "gruppe": "Antrag"},
    {"id": "F60000063", "name": "Ende",                          "typ": "datum",    "gruppe": "Antrag"},
    {"id": "F60000064", "name": "Anzahl",                        "typ": "zahl",     "gruppe": "Antrag"},
    {"id": "F60000065", "name": "Betrag",                        "typ": "zahl",     "gruppe": "Antrag"},
    {"id": "F60000066", "name": "Aktenzeichen",                  "typ": "text",     "gruppe": "Antrag"},
    {"id": "F60000067", "name": "Bemerkungen",                   "typ": "mehrzeil", "gruppe": "Antrag"},
    # Dokumente
    {"id": "F60000070", "name": "Datei-Upload",                  "typ": "datei",    "gruppe": "Dokumente"},
    {"id": "F60000071", "name": "Personalausweis Upload",        "typ": "datei",    "gruppe": "Dokumente"},
    {"id": "F60000072", "name": "Nachweisdokument",              "typ": "datei",    "gruppe": "Dokumente"},
    # Kraftfahrzeug
    {"id": "F60000080", "name": "Kraftfahrzeugkennzeichen",      "typ": "kfz",      "gruppe": "Kraftfahrzeug"},
    {"id": "F60000081", "name": "Fahrzeugidentifikationsnummer", "typ": "text",     "gruppe": "Kraftfahrzeug"},
    {"id": "F60000082", "name": "Fahrzeughalter",                "typ": "text",     "gruppe": "Kraftfahrzeug"},
    # Tier
    {"id": "F60000090", "name": "Tiername",                      "typ": "text",     "gruppe": "Tier"},
    {"id": "F60000091", "name": "Tierart",                       "typ": "text",     "gruppe": "Tier"},
    {"id": "F60000092", "name": "Rasse",                         "typ": "text",     "gruppe": "Tier"},
    {"id": "F60000093", "name": "Chip-Nummer",                   "typ": "text",     "gruppe": "Tier"},
    {"id": "F60000094", "name": "Geburtsdatum Tier",             "typ": "datum",    "gruppe": "Tier"},
    {"id": "F60000095", "name": "Haltungsbeginn",                "typ": "datum",    "gruppe": "Tier"},
    # Grundstück
    {"id": "F60000100", "name": "Flurstücksnummer",              "typ": "text",     "gruppe": "Grundstück"},
    {"id": "F60000101", "name": "Gemarkung",                     "typ": "text",     "gruppe": "Grundstück"},
    {"id": "F60000102", "name": "Grundbuchblatt",                "typ": "text",     "gruppe": "Grundstück"},
    {"id": "F60000103", "name": "Grundstücksfläche",             "typ": "zahl",     "gruppe": "Grundstück"},
]

# Umlaut-Normalisierung
_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                          "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def _norm(s: str) -> str:
    return s.lower().translate(_UMLAUT)


# Abkuerzungs-Aliase: Normalisierte Schreibweise → FIM-ID
_ALIASE: dict[str, str] = {
    "plz": "F60000024",
    "postleitzahl": "F60000024",
    "strasse": "F60000022",
    "str": "F60000022",
    "hnr": "F60000021",
    "hausnr": "F60000021",
    "email": "F60000030",
    "mail": "F60000030",
    "tel": "F60000031",
    "telefon": "F60000031",
    "fax": "F60000033",
    "mobil": "F60000032",
    "handy": "F60000032",
    "iban": "F60000043",
    "bic": "F60000044",
    "swift": "F60000044",
    "vorname": "F60000003",
    "nachname": "F60000004",
    "familienname": "F60000004",
    "name": "F60000004",
    "geburtsdatum": "F60000006",
    "geburtstag": "F60000006",
    "geburtsort": "F60000007",
    "geburtsname": "F60000005",
    "kfz": "F60000080",
    "kfz-kennzeichen": "F60000080",
    "kennzeichen": "F60000080",
    "aktenzeichen": "F60000066",
    "az": "F60000066",
    "steuernummer": "F60000055",
    "steuer-id": "F60000042",
    "steuerid": "F60000042",
    "ustid": "F60000054",
    "umsatzsteuer": "F60000054",
    "handelsregister": "F60000052",
    "hr-nummer": "F60000052",
    "flurstuck": "F60000100",
    "flurstueck": "F60000100",
}
_FIM_BY_ID = {f["id"]: f for f in FIM_FELDER}


def fim_match(label: str) -> dict | None:
    """
    Versucht ein FIM-Feld fuer das gegebene Label zu finden.
    Gibt das passendste FIM-Feld oder None zurueck.
    Prueft: exakter Treffer → Teilstring → Einzelwoerter.
    """
    if not label:
        return None
    n = _norm(label.strip())

    # 0. Alias-Treffer (haeufige Abkuerzungen)
    for alias, fid in _ALIASE.items():
        if alias == n or alias in n.split():
            return _FIM_BY_ID.get(fid)

    # 1. Exakter Treffer
    for f in FIM_FELDER:
        if _norm(f["name"]) == n:
            return f

    # 2. Normalisierter Label enthaelt FIM-Name vollstaendig (oder umgekehrt)
    for f in FIM_FELDER:
        fn = _norm(f["name"])
        if fn in n or n in fn:
            return f

    # 3. Einzelnes Schluesselwort stimmt ueberein (mind. 4 Zeichen)
    woerter = {w for w in n.split() if len(w) >= 4}
    for f in FIM_FELDER:
        fim_woerter = set(_norm(f["name"]).split())
        if woerter & fim_woerter:
            return f

    return None
