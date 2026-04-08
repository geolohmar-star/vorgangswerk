# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
LeiKa-Datensatz für häufige kommunale Verwaltungsleistungen.

Jeder Eintrag enthält:
- schluessel: 14-stellige LeiKa-Leistungsnummer
- name:       Leistungsbezeichnung laut LeiKa-Katalog
- fim_ids:    FIM-Felder die typischerweise in diesem Formular vorkommen
- gruppen:    FIM-Gruppen die signifikant für diese Leistung sind
- xoev:       Relevante XÖV-Domäne(n)

Quellen: https://www.leika.de / Onlinezugangsgesetz Anlage
"""

LEIKA_LEISTUNGEN = [
    # -----------------------------------------------------------------------
    # Steuern & Abgaben
    # -----------------------------------------------------------------------
    {
        "schluessel": "99108018026000",
        "name": "Hundesteuer – Anmeldung",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000021",
                    "F60000024", "F60000025", "F60000030", "F60000031", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XMeld"],
    },
    {
        "schluessel": "99108018027000",
        "name": "Hundesteuer – Abmeldung",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000060", "F60000063"],
        "gruppen": ["Personalien", "Adresse", "Antrag"],
        "xoev": ["XMeld"],
    },
    {
        "schluessel": "99108018028000",
        "name": "Hundesteuer – Ummeldung",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000021", "F60000024",
                    "F60000025", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Antrag"],
        "xoev": ["XMeld"],
    },
    {
        "schluessel": "99041001000000",
        "name": "Grundsteuer – Erklärung / Antrag auf Erlass",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000042", "F60000060", "F60000065", "F60000043"],
        "gruppen": ["Personalien", "Adresse", "Identifikation", "Bankverbindung", "Antrag"],
        "xoev": ["XMeld"],
    },
    # -----------------------------------------------------------------------
    # Melde- & Personenstandswesen
    # -----------------------------------------------------------------------
    {
        "schluessel": "99010016000000",
        "name": "An-/Ummeldung Wohnsitz",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000005", "F60000006",
                    "F60000009", "F60000010", "F60000020", "F60000021", "F60000024",
                    "F60000025", "F60000027", "F60000040"],
        "gruppen": ["Personalien", "Adresse", "Identifikation"],
        "xoev": ["XMeld"],
    },
    {
        "schluessel": "99010017000000",
        "name": "Abmeldung Wohnsitz",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000024",
                    "F60000025", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Antrag"],
        "xoev": ["XMeld"],
    },
    {
        "schluessel": "99020001000000",
        "name": "Personalausweis beantragen",
        "fim_ids": ["F60000001", "F60000002", "F60000003", "F60000004", "F60000005",
                    "F60000006", "F60000007", "F60000008", "F60000009", "F60000010",
                    "F60000020", "F60000021", "F60000024", "F60000025", "F60000040"],
        "gruppen": ["Personalien", "Adresse", "Identifikation"],
        "xoev": ["XMeld", "XPersonenstand"],
    },
    {
        "schluessel": "99020002000000",
        "name": "Reisepass beantragen",
        "fim_ids": ["F60000001", "F60000002", "F60000003", "F60000004", "F60000005",
                    "F60000006", "F60000007", "F60000009", "F60000010", "F60000020",
                    "F60000024", "F60000025", "F60000040", "F60000041"],
        "gruppen": ["Personalien", "Adresse", "Identifikation"],
        "xoev": ["XMeld", "XPersonenstand"],
    },
    {
        "schluessel": "99030001000000",
        "name": "Geburtsurkunde beantragen",
        "fim_ids": ["F60000003", "F60000004", "F60000005", "F60000006", "F60000007",
                    "F60000020", "F60000024", "F60000025", "F60000030"],
        "gruppen": ["Personalien", "Adresse", "Kontakt"],
        "xoev": ["XPersonenstand"],
    },
    {
        "schluessel": "99030002000000",
        "name": "Sterbeurkunde beantragen",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000024",
                    "F60000025", "F60000030", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XPersonenstand"],
    },
    {
        "schluessel": "99030003000000",
        "name": "Heiratsurkunde / Eheschließung anmelden",
        "fim_ids": ["F60000003", "F60000004", "F60000005", "F60000006", "F60000007",
                    "F60000009", "F60000020", "F60000024", "F60000025", "F60000030"],
        "gruppen": ["Personalien", "Adresse", "Kontakt"],
        "xoev": ["XPersonenstand"],
    },
    # -----------------------------------------------------------------------
    # KFZ & Führerschein
    # -----------------------------------------------------------------------
    {
        "schluessel": "99050001000000",
        "name": "Kfz-Zulassung",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000030", "F60000043", "F60000044", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Bankverbindung", "Antrag"],
        "xoev": ["XKfz"],
    },
    {
        "schluessel": "99050002000000",
        "name": "Kfz-Abmeldung",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Antrag"],
        "xoev": ["XKfz"],
    },
    {
        "schluessel": "99050011000000",
        "name": "Führerschein beantragen (Ersterteilung)",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000007",
                    "F60000020", "F60000024", "F60000025", "F60000030", "F60000031"],
        "gruppen": ["Personalien", "Adresse", "Kontakt"],
        "xoev": ["XKfz"],
    },
    # -----------------------------------------------------------------------
    # Bauen & Wohnen
    # -----------------------------------------------------------------------
    {
        "schluessel": "99070001000000",
        "name": "Baugenehmigung beantragen",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000030", "F60000031", "F60000050", "F60000060", "F60000061"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Unternehmen", "Antrag"],
        "xoev": ["XBau"],
    },
    {
        "schluessel": "99070002000000",
        "name": "Abrissgenehmigung beantragen",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000030", "F60000060", "F60000061"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XBau"],
    },
    {
        "schluessel": "99073001000000",
        "name": "Wohngeld beantragen",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000043", "F60000044",
                    "F60000060", "F60000065"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Bankverbindung", "Antrag"],
        "xoev": ["XSoziales"],
    },
    # -----------------------------------------------------------------------
    # Gewerbe & Wirtschaft
    # -----------------------------------------------------------------------
    {
        "schluessel": "99080001000000",
        "name": "Gewerbeanmeldung",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000031", "F60000050",
                    "F60000051", "F60000052", "F60000054", "F60000055", "F60000056",
                    "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Unternehmen", "Antrag"],
        "xoev": ["XGewerbe"],
    },
    {
        "schluessel": "99080002000000",
        "name": "Gewerbeabmeldung",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000050", "F60000055", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Unternehmen", "Antrag"],
        "xoev": ["XGewerbe"],
    },
    {
        "schluessel": "99080003000000",
        "name": "Gewerbeummeldung",
        "fim_ids": ["F60000003", "F60000004", "F60000020", "F60000024", "F60000025",
                    "F60000050", "F60000055", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Unternehmen", "Antrag"],
        "xoev": ["XGewerbe"],
    },
    {
        "schluessel": "99080010000000",
        "name": "Erlaubnis nach Gaststättenrecht",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000050", "F60000060",
                    "F60000061", "F60000062"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Unternehmen", "Antrag"],
        "xoev": ["XGewerbe"],
    },
    # -----------------------------------------------------------------------
    # Soziales & Jugend
    # -----------------------------------------------------------------------
    {
        "schluessel": "99090001000000",
        "name": "Kindergartenzulassung / Kita-Antrag",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000031", "F60000060",
                    "F60000062"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XSoziales"],
    },
    {
        "schluessel": "99090011000000",
        "name": "Elterngeld beantragen",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000042", "F60000043",
                    "F60000044", "F60000060", "F60000062", "F60000063", "F60000065"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Identifikation", "Bankverbindung", "Antrag"],
        "xoev": ["XSoziales"],
    },
    {
        "schluessel": "99090021000000",
        "name": "Grundsicherung / ALG II beantragen",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000009",
                    "F60000020", "F60000024", "F60000025", "F60000030", "F60000042",
                    "F60000043", "F60000044", "F60000060", "F60000065"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Identifikation", "Bankverbindung", "Antrag"],
        "xoev": ["XSoziales"],
    },
    {
        "schluessel": "99090031000000",
        "name": "Schwerbehindertenausweis beantragen",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000006", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000060", "F60000061"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XSoziales"],
    },
    # -----------------------------------------------------------------------
    # Ausländerwesen
    # -----------------------------------------------------------------------
    {
        "schluessel": "99110001000000",
        "name": "Aufenthaltstitel beantragen",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000005", "F60000006",
                    "F60000007", "F60000008", "F60000009", "F60000010", "F60000020",
                    "F60000024", "F60000025", "F60000030", "F60000040", "F60000041",
                    "F60000060", "F60000061"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Identifikation", "Antrag"],
        "xoev": ["XMeld"],
    },
    # -----------------------------------------------------------------------
    # Bescheinigungen & Auskünfte
    # -----------------------------------------------------------------------
    {
        "schluessel": "99121001000000",
        "name": "Führungszeugnis beantragen",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000024",
                    "F60000025", "F60000030", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XJustiz"],
    },
    {
        "schluessel": "99010021000000",
        "name": "Melderegisterauskunft",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000024",
                    "F60000025", "F60000030", "F60000060"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": ["XMeld"],
    },
    {
        "schluessel": "99010031000000",
        "name": "Meldebescheinigung beantragen",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000024",
                    "F60000025", "F60000030"],
        "gruppen": ["Personalien", "Adresse", "Kontakt"],
        "xoev": ["XMeld"],
    },
    # -----------------------------------------------------------------------
    # Umwelt & Ordnung
    # -----------------------------------------------------------------------
    {
        "schluessel": "99130001000000",
        "name": "Sondernutzungserlaubnis (Straße/Platz)",
        "fim_ids": ["F60000001", "F60000003", "F60000004", "F60000020", "F60000024",
                    "F60000025", "F60000030", "F60000031", "F60000060", "F60000061",
                    "F60000062", "F60000063"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": [],
    },
    {
        "schluessel": "99132001000000",
        "name": "Fischereierlaubnis",
        "fim_ids": ["F60000003", "F60000004", "F60000006", "F60000020", "F60000024",
                    "F60000025", "F60000030", "F60000060", "F60000062", "F60000063"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Antrag"],
        "xoev": [],
    },
    # -----------------------------------------------------------------------
    # Fundsachen
    # -----------------------------------------------------------------------
    {
        "schluessel": "99008001014000",
        "name": "Anzeige Wiederauffinden einer Sache",
        "fim_ids": ["F60000003", "F60000004", "F60000022", "F60000024", "F60000025",
                    "F60000030", "F60000031", "F60000060", "F60000061"],
        "gruppen": ["Personalien", "Adresse", "Kontakt", "Fundsache"],
        "xoev": [],
    },
]

# ---------------------------------------------------------------------------
# Schnellsuche: LeiKa-Schlüssel → Eintrag
# ---------------------------------------------------------------------------
LEIKA_INDEX = {l["schluessel"]: l for l in LEIKA_LEISTUNGEN}
