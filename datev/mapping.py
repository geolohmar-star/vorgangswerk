# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Mapping: Vorgangswerk Personalfragebogen → DATEV HR:Exchange Employee-Schema."""

_GESCHLECHT = {
    "männlich": "Male",
    "weiblich": "Female",
    "divers":   "Diverse",
}

_FAMILIENSTAND = {
    "ledig":             "Single",
    "verheiratet":       "Married",
    "geschieden":        "Divorced",
    "verwitwet":         "Widowed",
    "eingetragene Lebenspartnerschaft": "CivilUnion",
}

_STEUERKLASSE = {
    "I": "I", "1": "I",
    "II": "II", "2": "II",
    "III": "III", "3": "III",
    "IV": "IV", "4": "IV",
    "V": "V", "5": "V",
    "VI": "VI", "6": "VI",
}

_BESCHAEFTIGUNGSART = {
    "Hauptbeschäftigung": "MainEmployment",
    "Nebenbeschäftigung": "SecondaryEmployment",
}

_BEFRISTUNG = {
    "unbefristet":    "Permanent",
    "befristet":      "FixedTerm",
    "zweckbefristet": "PurposeLimited",
}


def _datum(wert: str) -> str | None:
    """Konvertiert dd.mm.yyyy → yyyy-mm-dd für DATEV-API."""
    if not wert:
        return None
    teile = wert.replace("/", ".").split(".")
    if len(teile) == 3:
        try:
            return f"{teile[2]}-{teile[1].zfill(2)}-{teile[0].zfill(2)}"
        except Exception:
            pass
    return wert or None


def _bool(wert: str) -> bool:
    return str(wert).lower() in ("ja", "true", "1", "yes")


def personalfragebogen_zu_datev(daten: dict, token) -> dict:
    """
    Wandelt gesammelte_daten einer Personalfragebogen-Sitzung in das
    DATEV HR:Exchange v1 Employee-Objekt um.
    token: DatevToken-Instanz (liefert consultant_number + client_number).
    """
    payload: dict = {}

    if token.consultant_number:
        payload["consultantNumber"] = token.consultant_number
    if token.client_number:
        payload["clientNumber"] = token.client_number

    # Person
    person: dict = {}
    if daten.get("familienname"):
        person["lastName"] = daten["familienname"]
    if daten.get("vorname"):
        person["firstName"] = daten["vorname"]
    if daten.get("geburtsdatum"):
        person["birthDate"] = _datum(daten["geburtsdatum"])
    if daten.get("geschlecht"):
        person["gender"] = _GESCHLECHT.get(daten["geschlecht"], daten["geschlecht"])
    if daten.get("familienstand"):
        person["maritalStatus"] = _FAMILIENSTAND.get(
            daten["familienstand"], daten["familienstand"]
        )
    if daten.get("schwerbehindert"):
        person["disability"] = _bool(daten["schwerbehindert"])
    if daten.get("staatsangehoerigkeit"):
        person["nationality"] = daten["staatsangehoerigkeit"]
    if daten.get("geburtsort_land"):
        person["placeOfBirth"] = daten["geburtsort_land"]
    if person:
        payload["person"] = person

    # Adresse
    adresse: dict = {}
    if daten.get("strasse"):
        adresse["street"] = daten["strasse"]
    if daten.get("plz"):
        adresse["postalCode"] = daten["plz"]
    if daten.get("ort"):
        adresse["city"] = daten["ort"]
    adresse["countryCode"] = "DE"
    if adresse:
        payload["address"] = adresse

    # Bankverbindung
    if daten.get("iban"):
        bank: dict = {"iban": daten["iban"]}
        if daten.get("bic"):
            bank["bic"] = daten["bic"]
        payload["bankAccounts"] = [bank]

    # Beschäftigung
    beschaeftigung: dict = {}
    if daten.get("eintrittsdatum"):
        beschaeftigung["entryDate"] = _datum(daten["eintrittsdatum"])
    if daten.get("ersteintritt_datum"):
        beschaeftigung["firstEntryDate"] = _datum(daten["ersteintritt_datum"])
    if daten.get("berufsbezeichnung"):
        beschaeftigung["jobTitle"] = daten["berufsbezeichnung"]
    if daten.get("ausgeuebte_taetigkeit"):
        beschaeftigung["occupation"] = daten["ausgeuebte_taetigkeit"]
    if daten.get("beschaeftigungsart"):
        beschaeftigung["employmentType"] = _BESCHAEFTIGUNGSART.get(
            daten["beschaeftigungsart"], daten["beschaeftigungsart"]
        )
    if daten.get("befristung_art"):
        beschaeftigung["contractType"] = _BEFRISTUNG.get(
            daten["befristung_art"], daten["befristung_art"]
        )
    if daten.get("befristung_bis"):
        beschaeftigung["contractEndDate"] = _datum(daten["befristung_bis"])
    if daten.get("probezeit"):
        beschaeftigung["probationaryPeriod"] = _bool(daten["probezeit"])
    if daten.get("probezeit_dauer"):
        beschaeftigung["probationaryPeriodDuration"] = daten["probezeit_dauer"]
    if beschaeftigung:
        payload["employment"] = beschaeftigung

    # Steuerdaten
    steuer: dict = {}
    if daten.get("steuer_identifikationsnr"):
        steuer["taxIdentificationNumber"] = daten["steuer_identifikationsnr"]
    if daten.get("finanzamt_nr"):
        steuer["taxOfficeNumber"] = daten["finanzamt_nr"]
    if daten.get("steuerklasse"):
        steuer["taxClass"] = _STEUERKLASSE.get(
            str(daten["steuerklasse"]).strip(), str(daten["steuerklasse"])
        )
    if daten.get("kinderfreibetraege") is not None:
        try:
            steuer["childAllowances"] = float(daten["kinderfreibetraege"])
        except (ValueError, TypeError):
            pass
    if daten.get("konfession"):
        steuer["denomination"] = daten["konfession"]
    if steuer:
        payload["taxData"] = steuer

    # Sozialversicherung
    sv: dict = {}
    if daten.get("versicherungsnummer"):
        sv["socialInsuranceNumber"] = daten["versicherungsnummer"]
    if daten.get("krankenkasse"):
        sv["healthInsuranceName"] = daten["krankenkasse"]
    if daten.get("elterneigenschaft"):
        sv["parenthood"] = _bool(daten["elterneigenschaft"])
    if sv:
        payload["socialInsurance"] = sv

    return payload
