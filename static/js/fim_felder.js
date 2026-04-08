/**
 * fim_felder.js – Lokales FIM-Datenfeld-Verzeichnis fuer den Formular-Editor.
 *
 * Quelle: XDatenfelder 2.0 (KoSIT / IT-Planungsrat), fimportal.de
 * IDs sind Referenz-IDs im FIM-Format. Bitte gegen fimportal.de verifizieren.
 *
 * Typ-Mapping auf Vorgangswerk-Feldtypen:
 *   text, mehrzeil, email, telefon, plz, iban, bic, kfz, steuernummer,
 *   zahl, datum, uhrzeit, bool, auswahl, datei
 */
var FIM_FELDER = [
    // ------------------------------------------------------------------
    // Personalien
    // ------------------------------------------------------------------
    { id: "F60000001", name: "Anrede",                         typ: "auswahl",  gruppe: "Personalien",
      optionen: ["Herr", "Frau", "Divers", "Keine Angabe"] },
    { id: "F60000002", name: "Titel / Namenszusatz",           typ: "text",     gruppe: "Personalien" },
    { id: "F60000003", name: "Vorname",                        typ: "text",     gruppe: "Personalien" },
    { id: "F60000004", name: "Familienname",                   typ: "text",     gruppe: "Personalien" },
    { id: "F60000005", name: "Geburtsname",                    typ: "text",     gruppe: "Personalien" },
    { id: "F60000006", name: "Geburtsdatum",                   typ: "datum",    gruppe: "Personalien" },
    { id: "F60000007", name: "Geburtsort",                     typ: "text",     gruppe: "Personalien" },
    { id: "F60000008", name: "Geburtsland",                    typ: "text",     gruppe: "Personalien" },
    { id: "F60000009", name: "Staatsangehörigkeit",            typ: "text",     gruppe: "Personalien" },
    { id: "F60000010", name: "Geschlecht",                     typ: "auswahl",  gruppe: "Personalien",
      optionen: ["männlich", "weiblich", "divers", "keine Angabe"] },

    // ------------------------------------------------------------------
    // Adresse
    // ------------------------------------------------------------------
    { id: "F60000020", name: "Straße",                         typ: "text",     gruppe: "Adresse" },
    { id: "F60000021", name: "Hausnummer",                     typ: "text",     gruppe: "Adresse" },
    { id: "F60000022", name: "Straße und Hausnummer",          typ: "text",     gruppe: "Adresse" },
    { id: "F60000023", name: "Adresszusatz",                   typ: "text",     gruppe: "Adresse" },
    { id: "F60000024", name: "Postleitzahl",                   typ: "plz",      gruppe: "Adresse" },
    { id: "F60000025", name: "Wohnort",                        typ: "text",     gruppe: "Adresse" },
    { id: "F60000026", name: "Ortsteil / Stadtteil",           typ: "text",     gruppe: "Adresse" },
    { id: "F60000027", name: "Land",                           typ: "text",     gruppe: "Adresse" },
    { id: "F60000028", name: "Postfach",                       typ: "text",     gruppe: "Adresse" },

    // ------------------------------------------------------------------
    // Kontakt
    // ------------------------------------------------------------------
    { id: "F60000030", name: "E-Mail-Adresse",                 typ: "email",    gruppe: "Kontakt" },
    { id: "F60000031", name: "Telefonnummer",                  typ: "telefon",  gruppe: "Kontakt" },
    { id: "F60000032", name: "Mobiltelefonnummer",             typ: "telefon",  gruppe: "Kontakt" },
    { id: "F60000033", name: "Faxnummer",                      typ: "telefon",  gruppe: "Kontakt" },
    { id: "F60000034", name: "Website / URL",                  typ: "text",     gruppe: "Kontakt" },

    // ------------------------------------------------------------------
    // Identifikation
    // ------------------------------------------------------------------
    { id: "F60000040", name: "Personalausweisnummer",          typ: "text",     gruppe: "Identifikation" },
    { id: "F60000041", name: "Reisepassnummer",                typ: "text",     gruppe: "Identifikation" },
    { id: "F60000042", name: "Steueridentifikationsnummer",    typ: "text",     gruppe: "Identifikation" },

    // ------------------------------------------------------------------
    // Bankverbindung
    // ------------------------------------------------------------------
    { id: "F60000043", name: "IBAN",                           typ: "iban",     gruppe: "Bankverbindung" },
    { id: "F60000044", name: "BIC",                            typ: "bic",      gruppe: "Bankverbindung" },
    { id: "F60000045", name: "Kontoinhaber",                   typ: "text",     gruppe: "Bankverbindung" },
    { id: "F60000046", name: "Kreditinstitut / Bankname",      typ: "text",     gruppe: "Bankverbindung" },

    // ------------------------------------------------------------------
    // Unternehmen / Organisation
    // ------------------------------------------------------------------
    { id: "F60000050", name: "Unternehmensname / Firmenname",  typ: "text",     gruppe: "Unternehmen" },
    { id: "F60000051", name: "Rechtsform",                     typ: "auswahl",  gruppe: "Unternehmen",
      optionen: ["GmbH", "UG (haftungsbeschränkt)", "AG", "OHG", "KG", "GbR", "e.K.", "e.V.", "Sonstige"] },
    { id: "F60000052", name: "Handelsregisternummer",          typ: "text",     gruppe: "Unternehmen" },
    { id: "F60000053", name: "Registergericht",                typ: "text",     gruppe: "Unternehmen" },
    { id: "F60000054", name: "Umsatzsteuer-ID",                typ: "text",     gruppe: "Unternehmen" },
    { id: "F60000055", name: "Steuernummer (Unternehmen)",     typ: "steuernummer", gruppe: "Unternehmen" },
    { id: "F60000056", name: "Gründungsdatum",                 typ: "datum",    gruppe: "Unternehmen" },
    { id: "F60000057", name: "Anzahl Mitarbeitende",           typ: "zahl",     gruppe: "Unternehmen" },

    // ------------------------------------------------------------------
    // Antrag / Vorgang
    // ------------------------------------------------------------------
    { id: "F60000060", name: "Antragsdatum",                   typ: "datum",    gruppe: "Antrag" },
    { id: "F60000061", name: "Begründung / Erläuterung",       typ: "mehrzeil", gruppe: "Antrag" },
    { id: "F60000062", name: "Gewünschter Beginn",             typ: "datum",    gruppe: "Antrag" },
    { id: "F60000063", name: "Gewünschtes Ende",               typ: "datum",    gruppe: "Antrag" },
    { id: "F60000064", name: "Anzahl (ganzzahlig)",            typ: "zahl",     gruppe: "Antrag" },
    { id: "F60000065", name: "Betrag (Euro)",                  typ: "zahl",     gruppe: "Antrag" },
    { id: "F60000066", name: "Aktenzeichen / Vorgangsnummer",  typ: "text",     gruppe: "Antrag" },
    { id: "F60000067", name: "Bemerkungen / Sonstige Angaben", typ: "mehrzeil", gruppe: "Antrag" },

    // ------------------------------------------------------------------
    // Dokumente / Nachweise
    // ------------------------------------------------------------------
    { id: "F60000070", name: "Datei-Upload (allgemein)",       typ: "datei",    gruppe: "Dokumente" },
    { id: "F60000071", name: "Personalausweis (Upload)",       typ: "datei",    gruppe: "Dokumente" },
    { id: "F60000072", name: "Nachweisdokument (Upload)",      typ: "datei",    gruppe: "Dokumente" },
    { id: "F60000073", name: "Vollmacht (Upload)",             typ: "datei",    gruppe: "Dokumente" },

    // ------------------------------------------------------------------
    // Kraftfahrzeug
    // ------------------------------------------------------------------
    { id: "F60000080", name: "Kraftfahrzeugkennzeichen",       typ: "kfz",      gruppe: "Kraftfahrzeug" },
    { id: "F60000081", name: "Fahrzeugidentifikationsnummer",  typ: "text",     gruppe: "Kraftfahrzeug" },
    { id: "F60000082", name: "Fahrzeughalter",                 typ: "text",     gruppe: "Kraftfahrzeug" },
    { id: "F60000083", name: "Erstzulassungsdatum",            typ: "datum",    gruppe: "Kraftfahrzeug" },

    // ------------------------------------------------------------------
    // Tier / Hund
    // ------------------------------------------------------------------
    { id: "F60000090", name: "Tiername",                       typ: "text",     gruppe: "Tier" },
    { id: "F60000091", name: "Tierart",                        typ: "text",     gruppe: "Tier" },
    { id: "F60000092", name: "Rasse",                          typ: "text",     gruppe: "Tier" },
    { id: "F60000093", name: "Chip-Nummer / Transponder-ID",   typ: "text",     gruppe: "Tier" },
    { id: "F60000094", name: "Geburtsdatum (Tier)",            typ: "datum",    gruppe: "Tier" },
    { id: "F60000095", name: "Haltungsbeginn",                 typ: "datum",    gruppe: "Tier" },

    // ------------------------------------------------------------------
    // Grundstück / Bau
    // ------------------------------------------------------------------
    { id: "F60000100", name: "Flurstücksnummer",               typ: "text",     gruppe: "Grundstück" },
    { id: "F60000101", name: "Gemarkung",                      typ: "text",     gruppe: "Grundstück" },
    { id: "F60000102", name: "Grundbuchblatt-Nummer",          typ: "text",     gruppe: "Grundstück" },
    { id: "F60000103", name: "Grundstücksfläche (m²)",         typ: "zahl",     gruppe: "Grundstück" },
    { id: "F60000104", name: "Flurstücksgröße (m²)",           typ: "zahl",     gruppe: "Grundstück" },
    { id: "F60000105", name: "Straße (Grundstück)",            typ: "text",     gruppe: "Grundstück" },
    { id: "F60000106", name: "Hausnummer (Grundstück)",        typ: "text",     gruppe: "Grundstück" },
    { id: "F60000107", name: "PLZ (Grundstück)",               typ: "plz",      gruppe: "Grundstück" },
    { id: "F60000108", name: "Ort (Grundstück)",               typ: "text",     gruppe: "Grundstück" },
];

/**
 * Sucht FIM-Felder nach Suchbegriff (Name oder Gruppe, case-insensitive).
 * @param {string} query
 * @param {number} maxResults
 * @returns {Array}
 */
function fimSuche(query, maxResults) {
    if (!query || query.length < 2) return [];
    var q = query.toLowerCase().trim();
    var treffer = FIM_FELDER.filter(function (f) {
        return f.name.toLowerCase().indexOf(q) !== -1 ||
               f.gruppe.toLowerCase().indexOf(q) !== -1 ||
               f.id.toLowerCase().indexOf(q) !== -1;
    });
    return treffer.slice(0, maxResults || 10);
}
