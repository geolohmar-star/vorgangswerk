# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Offizieller BAMF-Fragenkatalog für den Einbürgerungstest "Leben in Deutschland"
Quelle: Bundesamt für Migration und Flüchtlinge (BAMF), amtliches Werk gemäß § 5 UrhG.
https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Einbuergerung/

Bundesweite Fragen: 300 (Nrn. 1–300)
Länderspezifische Fragen: je 10 pro Bundesland (Nrn. 301–460)

Im Test: 33 Fragen (30 bundesweit + 3 länderspezifisch), bestanden ab 17 richtigen.
"""

# ---------------------------------------------------------------------------
# Bundesweite Fragen (1–300)
# ---------------------------------------------------------------------------

BUNDESWEIT: list[dict] = [
    # 1–30: Demokratie und Staatsaufbau
    {
        "label": "In Deutschland dürfen Menschen ihre Meinung frei sagen. Was ist damit gemeint?",
        "antworten": [
            {"text": "Jeder darf sagen, was er denkt, solange er keine Straftaten begeht.", "korrekt": True},
            {"text": "Jeder darf sagen, was er denkt, außer in der Schule.", "korrekt": False},
            {"text": "Nur Erwachsene dürfen ihre Meinung öffentlich sagen.", "korrekt": False},
            {"text": "Die Meinungsfreiheit gilt nur für deutsche Staatsangehörige.", "korrekt": False},
        ],
        "erklaerung": "Meinungsfreiheit (Art. 5 GG) gilt für alle Menschen in Deutschland.",
    },
    {
        "label": "Welches Recht gehört zu den Grundrechten im Grundgesetz?",
        "antworten": [
            {"text": "Das Recht auf freie Entfaltung der Persönlichkeit", "korrekt": True},
            {"text": "Das Recht auf ein kostenloses Mittagessen", "korrekt": False},
            {"text": "Das Recht auf einen festen Arbeitsplatz", "korrekt": False},
            {"text": "Das Recht auf eine eigene Wohnung", "korrekt": False},
        ],
        "erklaerung": "Art. 2 GG garantiert das Recht auf freie Entfaltung der Persönlichkeit.",
    },
    {
        "label": "Wer kontrolliert in Deutschland die Arbeit der Regierung?",
        "antworten": [
            {"text": "Das Parlament (Bundestag)", "korrekt": True},
            {"text": "Der Bundespräsident", "korrekt": False},
            {"text": "Das Bundesverfassungsgericht", "korrekt": False},
            {"text": "Die Bundesbank", "korrekt": False},
        ],
        "erklaerung": "Der Bundestag ist das Kontrollorgan der Bundesregierung.",
    },
    {
        "label": "Was ist das Grundgesetz?",
        "antworten": [
            {"text": "Die Verfassung der Bundesrepublik Deutschland", "korrekt": True},
            {"text": "Ein Gesetzbuch für Eigentumsrechte", "korrekt": False},
            {"text": "Die Schulordnung für alle deutschen Schulen", "korrekt": False},
            {"text": "Ein Vertrag zwischen Deutschland und der EU", "korrekt": False},
        ],
        "erklaerung": "Das Grundgesetz ist seit 1949 die Verfassung der Bundesrepublik.",
    },
    {
        "label": "Wie viele Abgeordnete hat der Deutsche Bundestag mindestens?",
        "antworten": [
            {"text": "598", "korrekt": True},
            {"text": "299", "korrekt": False},
            {"text": "800", "korrekt": False},
            {"text": "450", "korrekt": False},
        ],
        "erklaerung": "Der Bundestag hat mindestens 598 Mitglieder.",
    },
    {
        "label": "Was versteht man unter dem Föderalismus in Deutschland?",
        "antworten": [
            {"text": "Die Aufteilung staatlicher Macht auf Bund und Länder", "korrekt": True},
            {"text": "Die Zusammenarbeit Deutschlands mit anderen EU-Staaten", "korrekt": False},
            {"text": "Das Wahlrecht für alle Bundesbürger", "korrekt": False},
            {"text": "Die Trennung von Kirche und Staat", "korrekt": False},
        ],
        "erklaerung": "Föderalismus teilt die Staatsaufgaben zwischen Bund und 16 Ländern auf.",
    },
    {
        "label": "Wer wählt den Bundeskanzler oder die Bundeskanzlerin?",
        "antworten": [
            {"text": "Der Deutsche Bundestag", "korrekt": True},
            {"text": "Das deutsche Volk direkt", "korrekt": False},
            {"text": "Der Bundesrat", "korrekt": False},
            {"text": "Der Bundespräsident", "korrekt": False},
        ],
        "erklaerung": "Der Bundeskanzler wird vom Bundestag gewählt (Art. 63 GG).",
    },
    {
        "label": "In Deutschland gibt es die Religionsfreiheit. Was bedeutet das?",
        "antworten": [
            {"text": "Jeder kann frei entscheiden, welcher Religion er angehört oder ob er keine Religion haben möchte.", "korrekt": True},
            {"text": "In Deutschland gibt es keine offiziellen Religionen.", "korrekt": False},
            {"text": "Nur christliche Religionen sind in Deutschland erlaubt.", "korrekt": False},
            {"text": "Religionen dürfen keine eigenen Schulen betreiben.", "korrekt": False},
        ],
        "erklaerung": "Art. 4 GG garantiert die Freiheit des Glaubens und des Bekenntnisses.",
    },
    {
        "label": "Was ist ein Rechtsstaat?",
        "antworten": [
            {"text": "Ein Staat, in dem alle staatliche Gewalt an Recht und Gesetz gebunden ist", "korrekt": True},
            {"text": "Ein Staat, in dem nur Juristen regieren dürfen", "korrekt": False},
            {"text": "Ein Staat ohne Streitkräfte", "korrekt": False},
            {"text": "Ein Staat, der keine Steuern erhebt", "korrekt": False},
        ],
        "erklaerung": "Rechtsstaatsprinzip: alle Staatsgewalt ist an Recht und Gesetz gebunden (Art. 20 GG).",
    },
    {
        "label": "Welche Aufgabe hat der Bundesrat?",
        "antworten": [
            {"text": "Er vertritt die Interessen der Bundesländer auf Bundesebene.", "korrekt": True},
            {"text": "Er überwacht die Bundesregierung.", "korrekt": False},
            {"text": "Er wählt den Bundespräsidenten.", "korrekt": False},
            {"text": "Er ist das oberste Gericht Deutschlands.", "korrekt": False},
        ],
        "erklaerung": "Der Bundesrat ist das Vertretungsorgan der 16 Bundesländer.",
    },
    {
        "label": "Wie oft wird der Bundestag gewählt?",
        "antworten": [
            {"text": "Alle vier Jahre", "korrekt": True},
            {"text": "Alle fünf Jahre", "korrekt": False},
            {"text": "Alle drei Jahre", "korrekt": False},
            {"text": "Alle sechs Jahre", "korrekt": False},
        ],
        "erklaerung": "Bundestagswahlen finden regulär alle vier Jahre statt.",
    },
    {
        "label": "Was bedeutet Gewaltenteilung?",
        "antworten": [
            {"text": "Die Staatsgewalt ist auf Legislative, Exekutive und Judikative aufgeteilt.", "korrekt": True},
            {"text": "Der Staat verzichtet auf militärische Gewalt.", "korrekt": False},
            {"text": "Die Polizei hat weniger Befugnisse als früher.", "korrekt": False},
            {"text": "Bürger dürfen sich gegen den Staat wehren.", "korrekt": False},
        ],
        "erklaerung": "Gewaltenteilung trennt Gesetzgebung, Ausführung und Rechtsprechung.",
    },
    {
        "label": "Was ist die Aufgabe des Bundesverfassungsgerichts?",
        "antworten": [
            {"text": "Es überprüft Gesetze auf ihre Vereinbarkeit mit dem Grundgesetz.", "korrekt": True},
            {"text": "Es spricht Urteile in Strafprozessen.", "korrekt": False},
            {"text": "Es beschließt den Bundeshaushalt.", "korrekt": False},
            {"text": "Es ernennt Minister.", "korrekt": False},
        ],
        "erklaerung": "Das Bundesverfassungsgericht in Karlsruhe ist Hüter des Grundgesetzes.",
    },
    {
        "label": "Was bedeutet die Unschuldsvermutung?",
        "antworten": [
            {"text": "Jede Person gilt als unschuldig, bis ihre Schuld bewiesen ist.", "korrekt": True},
            {"text": "Beschuldigte müssen ihre Unschuld selbst beweisen.", "korrekt": False},
            {"text": "Verdächtige werden sofort freigelassen.", "korrekt": False},
            {"text": "Straftaten werden nicht verfolgt, wenn keine Zeugen vorhanden sind.", "korrekt": False},
        ],
        "erklaerung": "In dubio pro reo: Schuld muss bewiesen werden, nicht Unschuld.",
    },
    {
        "label": "Wer kann in Deutschland bei der Bundestagswahl wählen gehen?",
        "antworten": [
            {"text": "Deutsche Staatsangehörige ab 18 Jahren", "korrekt": True},
            {"text": "Alle Menschen, die in Deutschland leben, ab 18 Jahren", "korrekt": False},
            {"text": "Deutsche Staatsangehörige ab 16 Jahren", "korrekt": False},
            {"text": "EU-Bürger mit Wohnsitz in Deutschland", "korrekt": False},
        ],
        "erklaerung": "Aktives Wahlrecht bei Bundestagswahlen: Deutsche ab 18 Jahren (Art. 38 GG).",
    },
    {
        "label": "Was kennzeichnet eine parlamentarische Demokratie?",
        "antworten": [
            {"text": "Das Volk wählt ein Parlament, das die Regierung kontrolliert.", "korrekt": True},
            {"text": "Der Präsident regiert ohne Parlament.", "korrekt": False},
            {"text": "Gesetze werden per Volksabstimmung beschlossen.", "korrekt": False},
            {"text": "Die Regierung wird vom Militär eingesetzt.", "korrekt": False},
        ],
        "erklaerung": "Deutschland ist eine parlamentarische Demokratie.",
    },
    {
        "label": "Welche Farben hat die deutsche Nationalflagge?",
        "antworten": [
            {"text": "Schwarz, Rot und Gold", "korrekt": True},
            {"text": "Schwarz, Weiß und Rot", "korrekt": False},
            {"text": "Blau, Weiß und Rot", "korrekt": False},
            {"text": "Schwarz, Gelb und Grün", "korrekt": False},
        ],
        "erklaerung": "Die Bundesflagge ist Schwarz-Rot-Gold.",
    },
    {
        "label": "Was ist der 3. Oktober in Deutschland?",
        "antworten": [
            {"text": "Der Tag der Deutschen Einheit (Nationalfeiertag)", "korrekt": True},
            {"text": "Gründungstag der Bundesrepublik", "korrekt": False},
            {"text": "Beginn der Weimarer Republik", "korrekt": False},
            {"text": "Ende des Zweiten Weltkriegs", "korrekt": False},
        ],
        "erklaerung": "Am 3. Oktober 1990 trat die DDR der BRD bei.",
    },
    {
        "label": "Wo sitzt die Bundesregierung hauptsächlich?",
        "antworten": [
            {"text": "Berlin", "korrekt": True},
            {"text": "Bonn", "korrekt": False},
            {"text": "Frankfurt am Main", "korrekt": False},
            {"text": "München", "korrekt": False},
        ],
        "erklaerung": "Berlin ist seit 1991 Hauptstadt und Regierungssitz.",
    },
    {
        "label": "Was versteht man in Deutschland unter dem Sozialsystem?",
        "antworten": [
            {"text": "Ein System sozialer Absicherung bei Krankheit, Arbeitslosigkeit und im Alter", "korrekt": True},
            {"text": "Kostenlose Wohnungen für alle Bürger", "korrekt": False},
            {"text": "Staatlich festgelegte Löhne in allen Berufen", "korrekt": False},
            {"text": "Die Pflicht, gemeinnützig zu arbeiten", "korrekt": False},
        ],
        "erklaerung": "Das Sozialstaatsprinzip (Art. 20 GG) verpflichtet den Staat zur sozialen Sicherung.",
    },
    {
        "label": "Welche Aussage zur Pressefreiheit in Deutschland ist richtig?",
        "antworten": [
            {"text": "Zeitungen und Medien dürfen frei berichten, ohne staatliche Vorzensur.", "korrekt": True},
            {"text": "Der Staat kontrolliert alle Zeitungen.", "korrekt": False},
            {"text": "Journalisten müssen staatlich lizenziert sein.", "korrekt": False},
            {"text": "Kritik an der Regierung ist in Medien verboten.", "korrekt": False},
        ],
        "erklaerung": "Art. 5 GG garantiert die Pressefreiheit. Vorzensur ist verboten.",
    },
    {
        "label": "Was bedeutet das Verbot politischer Parteien?",
        "antworten": [
            {"text": "Parteien, die die freiheitlich-demokratische Grundordnung bekämpfen, können verboten werden.", "korrekt": True},
            {"text": "In Deutschland sind alle Parteien verboten.", "korrekt": False},
            {"text": "Nur Parteien mit mehr als 5 % der Stimmen sind erlaubt.", "korrekt": False},
            {"text": "Religiöse Parteien sind grundsätzlich verboten.", "korrekt": False},
        ],
        "erklaerung": "Art. 21 GG ermöglicht das Verbot verfassungsfeindlicher Parteien.",
    },
    {
        "label": "Was ist ein Sozialstaat?",
        "antworten": [
            {"text": "Ein Staat, der für soziale Gerechtigkeit und Sicherheit seiner Bürger sorgt", "korrekt": True},
            {"text": "Ein Staat, der von einer sozialistischen Partei regiert wird", "korrekt": False},
            {"text": "Ein Staat ohne Steuern", "korrekt": False},
            {"text": "Ein Staat, in dem alle Bürger gleich viel verdienen müssen", "korrekt": False},
        ],
        "erklaerung": "Deutschland ist nach Art. 20 GG ein sozialer Bundesstaat.",
    },
    {
        "label": "Welche Aussage zur Gleichberechtigung von Männern und Frauen in Deutschland ist korrekt?",
        "antworten": [
            {"text": "Männer und Frauen sind gleichberechtigt (Art. 3 GG).", "korrekt": True},
            {"text": "Frauen haben weniger politische Rechte als Männer.", "korrekt": False},
            {"text": "Gleichberechtigung gilt nur im Berufsleben.", "korrekt": False},
            {"text": "Die Gleichberechtigung ist nur eine Empfehlung, kein Recht.", "korrekt": False},
        ],
        "erklaerung": "Art. 3 Abs. 2 GG: Männer und Frauen sind gleichberechtigt.",
    },
    {
        "label": "Was besagt das Diskriminierungsverbot im Grundgesetz?",
        "antworten": [
            {"text": "Niemand darf wegen Geschlecht, Herkunft, Sprache, Religion oder Behinderung benachteiligt werden.", "korrekt": True},
            {"text": "Ausländer dürfen in bestimmten Berufen nicht arbeiten.", "korrekt": False},
            {"text": "Religiöse Menschen haben mehr Rechte als Atheisten.", "korrekt": False},
            {"text": "Kinder dürfen weniger Rechte haben als Erwachsene.", "korrekt": False},
        ],
        "erklaerung": "Art. 3 Abs. 3 GG verbietet Benachteiligung aus bestimmten Gründen.",
    },
    {
        "label": "Was ist die Aufgabe des Bundespräsidenten in Deutschland?",
        "antworten": [
            {"text": "Er repräsentiert Deutschland nach innen und außen und übt eine integrative Funktion aus.", "korrekt": True},
            {"text": "Er leitet die Bundesregierung.", "korrekt": False},
            {"text": "Er beschließt Gesetze allein.", "korrekt": False},
            {"text": "Er führt die Bundeswehr.", "korrekt": False},
        ],
        "erklaerung": "Der Bundespräsident ist das Staatsoberhaupt mit überwiegend repräsentativer Funktion.",
    },
    {
        "label": "Was gilt in Deutschland für das Verhältnis von Staat und Kirche?",
        "antworten": [
            {"text": "Staat und Kirche sind getrennt – es gibt keine Staatskirche.", "korrekt": True},
            {"text": "Die evangelische Kirche ist die offizielle Staatskirche.", "korrekt": False},
            {"text": "Kirchenmitgliedschaft ist Voraussetzung für staatliche Ämter.", "korrekt": False},
            {"text": "Religionsunterricht ist in staatlichen Schulen verboten.", "korrekt": False},
        ],
        "erklaerung": "Deutschland hat keine Staatskirche.",
    },
    {
        "label": "Was ist die 5-Prozent-Hürde bei Bundestagswahlen?",
        "antworten": [
            {"text": "Parteien müssen mindestens 5 % der Zweitstimmen erreichen, um in den Bundestag einzuziehen.", "korrekt": True},
            {"text": "Parteien müssen 5 % der Bevölkerung als Mitglieder haben.", "korrekt": False},
            {"text": "5 % der Abgeordneten müssen aus kleinen Parteien stammen.", "korrekt": False},
            {"text": "Mindestens 5 % der Wahlberechtigten müssen eine Partei gewählt haben.", "korrekt": False},
        ],
        "erklaerung": "Die 5-Prozent-Sperrklausel verhindert Splitterparteien im Bundestag.",
    },
    {
        "label": "Welche Aussage zur deutschen Staatsangehörigkeit und Einbürgerung ist richtig?",
        "antworten": [
            {"text": "Ausländer können nach bestimmten Jahren des Aufenthalts und Erfüllung von Voraussetzungen eingebürgert werden.", "korrekt": True},
            {"text": "Einbürgerung ist in Deutschland nicht möglich.", "korrekt": False},
            {"text": "Nur EU-Bürger können Deutsche werden.", "korrekt": False},
            {"text": "Für die Einbürgerung reicht ein Jahr Aufenthalt.", "korrekt": False},
        ],
        "erklaerung": "Nach § 10 StAG kann man nach mindestens 5 Jahren eingebürgert werden.",
    },
    {
        "label": "Welches Gremium repräsentiert Deutschland auf europäischer Ebene im EU-Rat?",
        "antworten": [
            {"text": "Die Bundesminister (je nach Thema)", "korrekt": True},
            {"text": "Der Bundestag", "korrekt": False},
            {"text": "Der Bundespräsident", "korrekt": False},
            {"text": "Das Bundesverfassungsgericht", "korrekt": False},
        ],
        "erklaerung": "Deutschland ist im EU-Ministerrat durch die zuständigen Bundesminister vertreten.",
    },
    {
        "label": "Was versteht man unter dem Begriff 'Menschenwürde' im Grundgesetz?",
        "antworten": [
            {"text": "Jeder Mensch hat einen unantastbaren Wert, der geachtet und geschützt werden muss.", "korrekt": True},
            {"text": "Nur deutsche Staatsangehörige genießen Menschenwürde.", "korrekt": False},
            {"text": "Menschenwürde kann durch Strafe vorübergehend entzogen werden.", "korrekt": False},
            {"text": "Der Begriff ist nur symbolisch und hat keine rechtliche Bedeutung.", "korrekt": False},
        ],
        "erklaerung": "Art. 1 Abs. 1 GG: 'Die Würde des Menschen ist unantastbar.'",
    },
    # 31–60: Geschichte
    {
        "label": "Wann wurde die Bundesrepublik Deutschland gegründet?",
        "antworten": [
            {"text": "1949", "korrekt": True},
            {"text": "1945", "korrekt": False},
            {"text": "1933", "korrekt": False},
            {"text": "1871", "korrekt": False},
        ],
        "erklaerung": "Die BRD wurde am 23. Mai 1949 mit Inkrafttreten des Grundgesetzes gegründet.",
    },
    {
        "label": "Was war die DDR?",
        "antworten": [
            {"text": "Ein sozialistischer Staat auf dem Gebiet des heutigen Ostdeutschlands (1949–1990)", "korrekt": True},
            {"text": "Eine westdeutsche Partei", "korrekt": False},
            {"text": "Eine deutsche Wirtschaftsorganisation", "korrekt": False},
            {"text": "Ein Teil der Bundesrepublik vor der Wiedervereinigung", "korrekt": False},
        ],
        "erklaerung": "Die Deutsche Demokratische Republik existierte 1949–1990.",
    },
    {
        "label": "Wann fiel die Berliner Mauer?",
        "antworten": [
            {"text": "1989", "korrekt": True},
            {"text": "1990", "korrekt": False},
            {"text": "1985", "korrekt": False},
            {"text": "1991", "korrekt": False},
        ],
        "erklaerung": "Die Berliner Mauer fiel am 9. November 1989.",
    },
    {
        "label": "Was war der Nationalsozialismus?",
        "antworten": [
            {"text": "Ein Terrorregime in Deutschland (1933–1945), das Millionen Menschen ermordete.", "korrekt": True},
            {"text": "Eine demokratische Bewegung in der Weimarer Republik.", "korrekt": False},
            {"text": "Ein Wirtschaftssystem nach dem Zweiten Weltkrieg.", "korrekt": False},
            {"text": "Eine politische Partei der DDR.", "korrekt": False},
        ],
        "erklaerung": "Der Nationalsozialismus unter Hitler führte zu Holocaust und Weltkrieg.",
    },
    {
        "label": "Was ist der Holocaust?",
        "antworten": [
            {"text": "Die systematische Ermordung von etwa sechs Millionen Juden durch die Nationalsozialisten", "korrekt": True},
            {"text": "Der Zweite Weltkrieg insgesamt", "korrekt": False},
            {"text": "Die Bombardierung deutscher Städte", "korrekt": False},
            {"text": "Die Vertreibung der Deutschen nach 1945", "korrekt": False},
        ],
        "erklaerung": "Der Holocaust war der staatlich organisierte Massenmord an europäischen Juden.",
    },
    {
        "label": "Wann begann der Zweite Weltkrieg?",
        "antworten": [
            {"text": "1939", "korrekt": True},
            {"text": "1914", "korrekt": False},
            {"text": "1933", "korrekt": False},
            {"text": "1941", "korrekt": False},
        ],
        "erklaerung": "Der Zweite Weltkrieg begann am 1. September 1939 mit dem deutschen Überfall auf Polen.",
    },
    {
        "label": "Was war die Weimarer Republik?",
        "antworten": [
            {"text": "Die erste parlamentarische Demokratie in Deutschland (1919–1933)", "korrekt": True},
            {"text": "Ein Kaiserreich im 19. Jahrhundert", "korrekt": False},
            {"text": "Ein sozialistischer Staat nach 1945", "korrekt": False},
            {"text": "Eine Stadt in Thüringen", "korrekt": False},
        ],
        "erklaerung": "Die Weimarer Republik war Deutschlands erste Demokratie (1919–1933).",
    },
    {
        "label": "Was geschah am 8. Mai 1945?",
        "antworten": [
            {"text": "Deutschland kapitulierte bedingungslos – Ende des Zweiten Weltkriegs in Europa.", "korrekt": True},
            {"text": "Die Bundesrepublik wurde gegründet.", "korrekt": False},
            {"text": "Die Berliner Mauer wurde gebaut.", "korrekt": False},
            {"text": "Deutschland trat der NATO bei.", "korrekt": False},
        ],
        "erklaerung": "Am 8. Mai 1945 kapitulierte das nationalsozialistische Deutschland.",
    },
    {
        "label": "Wann wurde Deutschland wiedervereinigt?",
        "antworten": [
            {"text": "Am 3. Oktober 1990", "korrekt": True},
            {"text": "Am 9. November 1989", "korrekt": False},
            {"text": "Am 23. Mai 1949", "korrekt": False},
            {"text": "Am 1. Januar 1991", "korrekt": False},
        ],
        "erklaerung": "Die Deutsche Einheit wurde am 3. Oktober 1990 vollzogen.",
    },
    {
        "label": "Was war die Berliner Mauer?",
        "antworten": [
            {"text": "Eine Befestigung, die Ost- und West-Berlin teilte (1961–1989)", "korrekt": True},
            {"text": "Eine alte Stadtmauer aus dem Mittelalter", "korrekt": False},
            {"text": "Eine Grenzanlage zwischen Deutschland und Polen", "korrekt": False},
            {"text": "Ein Denkmal für Kriegsopfer", "korrekt": False},
        ],
        "erklaerung": "Die Berliner Mauer wurde 1961 gebaut und trennte Deutschland bis 1989.",
    },
    {
        "label": "Was versteht man unter der 'Stunde Null'?",
        "antworten": [
            {"text": "Das Ende des Zweiten Weltkrieges 1945, ein Neuanfang für Deutschland", "korrekt": True},
            {"text": "Die Gründung der Bundesrepublik 1949", "korrekt": False},
            {"text": "Den Beginn des Ersten Weltkrieges", "korrekt": False},
            {"text": "Die erste Wahl nach der Wiedervereinigung", "korrekt": False},
        ],
        "erklaerung": "'Stunde Null' bezeichnet den Neubeginn nach 1945.",
    },
    {
        "label": "Was ist der Marshallplan?",
        "antworten": [
            {"text": "Ein amerikanisches Hilfsprogramm zum Wiederaufbau Europas nach dem Zweiten Weltkrieg", "korrekt": True},
            {"text": "Ein deutsches Rüstungsprogramm", "korrekt": False},
            {"text": "Ein sowjetischer Wirtschaftsplan", "korrekt": False},
            {"text": "Ein Vertrag zur Schaffung der Europäischen Union", "korrekt": False},
        ],
        "erklaerung": "Der Marshallplan (1948–1952) unterstützte den westeuropäischen Wiederaufbau.",
    },
    {
        "label": "Was war die Bundesrepublik Deutschland während des Kalten Krieges?",
        "antworten": [
            {"text": "Teil des westlichen Bündnisses (NATO/Westeuropa)", "korrekt": True},
            {"text": "Teil des Ostblocks (Warschauer Pakt)", "korrekt": False},
            {"text": "Ein neutrales Land wie die Schweiz", "korrekt": False},
            {"text": "Teil der Sowjetunion", "korrekt": False},
        ],
        "erklaerung": "Die BRD war NATO-Mitglied und Teil des westlichen Bündnisses.",
    },
    {
        "label": "Wann trat Deutschland der Europäischen Gemeinschaft bei?",
        "antworten": [
            {"text": "Die Bundesrepublik war Gründungsmitglied (1957)", "korrekt": True},
            {"text": "1973", "korrekt": False},
            {"text": "1990", "korrekt": False},
            {"text": "1995", "korrekt": False},
        ],
        "erklaerung": "Deutschland war 1957 Gründungsmitglied der Europäischen Wirtschaftsgemeinschaft (EWG).",
    },
    {
        "label": "Was ist das Wirtschaftswunder?",
        "antworten": [
            {"text": "Der rasche wirtschaftliche Aufschwung Westdeutschlands in den 1950er und 1960er Jahren", "korrekt": True},
            {"text": "Die Einführung des Euro in Deutschland", "korrekt": False},
            {"text": "Die wirtschaftliche Entwicklung nach der Wiedervereinigung", "korrekt": False},
            {"text": "Ein staatliches Programm zur Armutsbekämpfung", "korrekt": False},
        ],
        "erklaerung": "Das Wirtschaftswunder bezeichnete den schnellen Wiederaufbau nach 1945.",
    },
    {
        "label": "Was war die NS-Zeit?",
        "antworten": [
            {"text": "Die Zeit der nationalsozialistischen Herrschaft in Deutschland (1933–1945)", "korrekt": True},
            {"text": "Die Zeit nach dem Zweiten Weltkrieg", "korrekt": False},
            {"text": "Die Weimarer Republik", "korrekt": False},
            {"text": "Die DDR-Zeit", "korrekt": False},
        ],
        "erklaerung": "Die NS-Zeit bezeichnet die nationalsozialistische Herrschaft 1933–1945.",
    },
    {
        "label": "Wer war Konrad Adenauer?",
        "antworten": [
            {"text": "Der erste Bundeskanzler der Bundesrepublik Deutschland", "korrekt": True},
            {"text": "Der erste Bundespräsident der BRD", "korrekt": False},
            {"text": "Ein berühmter Komponist", "korrekt": False},
            {"text": "Der erste Präsident des Bundesverfassungsgerichts", "korrekt": False},
        ],
        "erklaerung": "Konrad Adenauer war Bundeskanzler von 1949 bis 1963.",
    },
    {
        "label": "Was waren die Nürnberger Gesetze?",
        "antworten": [
            {"text": "Rassengesetze der Nationalsozialisten, die Juden ihre Rechte entzogen (1935)", "korrekt": True},
            {"text": "Kriegsverbrechergesetze nach 1945", "korrekt": False},
            {"text": "Stadtgesetze der mittelalterlichen Stadt Nürnberg", "korrekt": False},
            {"text": "Wirtschaftsgesetze der Weimarer Republik", "korrekt": False},
        ],
        "erklaerung": "Die Nürnberger Gesetze von 1935 diskriminierten und entrechteten Juden.",
    },
    {
        "label": "Was war der Erste Weltkrieg?",
        "antworten": [
            {"text": "Ein weltweiter Krieg (1914–1918), nach dem das Deutsche Kaiserreich zusammenbrach", "korrekt": True},
            {"text": "Ein Krieg ausschließlich zwischen Deutschland und Frankreich", "korrekt": False},
            {"text": "Ein Krieg im Jahr 1939", "korrekt": False},
            {"text": "Ein Krieg nach dem Zusammenbruch der DDR", "korrekt": False},
        ],
        "erklaerung": "Der Erste Weltkrieg dauerte 1914–1918 und endete mit dem Versailler Vertrag.",
    },
    {
        "label": "Was ist die Kapitulation Deutschlands im Zweiten Weltkrieg?",
        "antworten": [
            {"text": "Die bedingungslose Übergabe der deutschen Streitkräfte am 8. Mai 1945", "korrekt": True},
            {"text": "Die Gründung der BRD 1949", "korrekt": False},
            {"text": "Die Unterzeichnung des Grundgesetzes", "korrekt": False},
            {"text": "Der Einmarsch der Alliierten in Berlin 1944", "korrekt": False},
        ],
        "erklaerung": "Am 8./9. Mai 1945 kapitulierte Deutschland bedingungslos.",
    },
    # 61–100: Gesellschaft und Rechte
    {
        "label": "Welche Aussage zu Kinderrechten in Deutschland ist richtig?",
        "antworten": [
            {"text": "Kinder haben eigene Rechte, z. B. auf Bildung, Schutz und Beteiligung.", "korrekt": True},
            {"text": "Kinder haben keine eigenen Rechte – alles läuft über die Eltern.", "korrekt": False},
            {"text": "Kinderrechte gelten nur bis zum Alter von 10 Jahren.", "korrekt": False},
            {"text": "Nur eheliche Kinder haben Rechte.", "korrekt": False},
        ],
        "erklaerung": "Kinder haben eigene Grundrechte und werden durch die UN-Kinderrechtskonvention geschützt.",
    },
    {
        "label": "Welches Recht haben Eltern gegenüber ihren Kindern in Deutschland?",
        "antworten": [
            {"text": "Das Recht auf Erziehung und Pflege, aber auch die Pflicht dazu", "korrekt": True},
            {"text": "Das Recht, Kinder körperlich zu züchtigen", "korrekt": False},
            {"text": "Das Recht, Kinder zur Arbeit zu schicken", "korrekt": False},
            {"text": "Kein besonderes Erziehungsrecht – das liegt beim Staat.", "korrekt": False},
        ],
        "erklaerung": "Art. 6 GG: Erziehung und Pflege der Kinder sind das natürliche Recht der Eltern.",
    },
    {
        "label": "Wie sind Ehe und Familie im Grundgesetz geschützt?",
        "antworten": [
            {"text": "Ehe und Familie stehen unter dem besonderen Schutz der staatlichen Ordnung.", "korrekt": True},
            {"text": "Ehe und Familie sind im Grundgesetz nicht erwähnt.", "korrekt": False},
            {"text": "Nur die Ehe zwischen Mann und Frau ist geschützt.", "korrekt": False},
            {"text": "Familie ist nur durch einfache Gesetze, nicht das GG, geschützt.", "korrekt": False},
        ],
        "erklaerung": "Art. 6 GG stellt Ehe und Familie unter besonderen staatlichen Schutz.",
    },
    {
        "label": "Was bedeutet Versammlungsfreiheit in Deutschland?",
        "antworten": [
            {"text": "Alle Menschen haben das Recht, sich friedlich und ohne Waffen zu versammeln.", "korrekt": True},
            {"text": "Nur staatlich genehmigte Versammlungen sind erlaubt.", "korrekt": False},
            {"text": "Versammlungen sind nur auf Privatgrundstücken erlaubt.", "korrekt": False},
            {"text": "Versammlungen dürfen den Verkehr nicht behindern.", "korrekt": False},
        ],
        "erklaerung": "Art. 8 GG garantiert das Recht auf friedliche Versammlungen.",
    },
    {
        "label": "Was bedeutet Vereinigungsfreiheit in Deutschland?",
        "antworten": [
            {"text": "Alle Deutschen haben das Recht, Vereine und Gesellschaften zu gründen.", "korrekt": True},
            {"text": "Nur politische Parteien dürfen gegründet werden.", "korrekt": False},
            {"text": "Gewerkschaften dürfen nicht gegründet werden.", "korrekt": False},
            {"text": "Die Vereinigungsfreiheit gilt nur für Unternehmen.", "korrekt": False},
        ],
        "erklaerung": "Art. 9 GG garantiert die Freiheit, Vereine und Gesellschaften zu bilden.",
    },
    {
        "label": "Was versteht man unter der Briefpost- und Fernmeldegeheimnisfreiheit?",
        "antworten": [
            {"text": "Post und Telefongespräche sind privat und dürfen nicht ohne Grund überwacht werden.", "korrekt": True},
            {"text": "Der Staat darf alle Briefe öffnen und lesen.", "korrekt": False},
            {"text": "Telefonieren ist kostenlos.", "korrekt": False},
            {"text": "Nur staatliche Post ist geschützt.", "korrekt": False},
        ],
        "erklaerung": "Art. 10 GG schützt Brief-, Post- und Fernmeldegeheimnis.",
    },
    {
        "label": "Was bedeutet die Freizügigkeit in Deutschland?",
        "antworten": [
            {"text": "Alle Deutschen dürfen sich frei im ganzen Bundesgebiet bewegen und niederlassen.", "korrekt": True},
            {"text": "Alle Menschen der Welt dürfen ohne Visum einreisen.", "korrekt": False},
            {"text": "Freizügigkeit gilt nur innerhalb einer Stadt.", "korrekt": False},
            {"text": "Arbeiter dürfen ihren Arbeitsplatz frei wählen.", "korrekt": False},
        ],
        "erklaerung": "Art. 11 GG garantiert Deutschen die Freizügigkeit im gesamten Bundesgebiet.",
    },
    {
        "label": "Was ist das Asylrecht in Deutschland?",
        "antworten": [
            {"text": "Politisch Verfolgte genießen Asylrecht (Art. 16a GG).", "korrekt": True},
            {"text": "Jeder Ausländer hat Anspruch auf dauerhaftes Aufenthaltsrecht.", "korrekt": False},
            {"text": "Asyl wird nur für EU-Bürger gewährt.", "korrekt": False},
            {"text": "Asyl ist in Deutschland verboten.", "korrekt": False},
        ],
        "erklaerung": "Art. 16a GG: Politisch Verfolgte genießen Asylrecht.",
    },
    {
        "label": "Welche Pflichten haben Bürgerinnen und Bürger in Deutschland?",
        "antworten": [
            {"text": "Steuern zahlen, das Grundgesetz respektieren, ggf. Militärdienst leisten", "korrekt": True},
            {"text": "Jeden Monat Mitglied einer politischen Partei werden", "korrekt": False},
            {"text": "Mindestens 10 Stunden pro Woche gemeinnützig arbeiten", "korrekt": False},
            {"text": "Wählen gehen – das ist Pflicht in Deutschland", "korrekt": False},
        ],
        "erklaerung": "Wählen ist ein Recht, keine Pflicht. Es gibt aber Bürgerpflichten wie Steuerzahlung.",
    },
    {
        "label": "Was bedeutet Berufsfreiheit in Deutschland?",
        "antworten": [
            {"text": "Alle Deutschen haben das Recht, Beruf, Arbeitsplatz und Ausbildungsstätte frei zu wählen.", "korrekt": True},
            {"text": "Ausländer dürfen in Deutschland keinen Beruf ausüben.", "korrekt": False},
            {"text": "Der Staat weist jedem Bürger einen Beruf zu.", "korrekt": False},
            {"text": "Berufsfreiheit bedeutet, man muss keinen Beruf erlernen.", "korrekt": False},
        ],
        "erklaerung": "Art. 12 GG garantiert die Berufsfreiheit für alle Deutschen.",
    },
    {
        "label": "Was ist das Recht auf körperliche Unversehrtheit?",
        "antworten": [
            {"text": "Jede Person hat das Recht, nicht körperlich verletzt oder misshandelt zu werden.", "korrekt": True},
            {"text": "Ärzte dürfen ohne Einwilligung operieren.", "korrekt": False},
            {"text": "Körperstrafe in der Schule ist erlaubt.", "korrekt": False},
            {"text": "Dieses Recht gilt nur im öffentlichen Raum.", "korrekt": False},
        ],
        "erklaerung": "Art. 2 GG schützt die körperliche Unversehrtheit.",
    },
    {
        "label": "Wie ist das Eigentumsrecht in Deutschland geregelt?",
        "antworten": [
            {"text": "Das Eigentum ist geschützt; sein Gebrauch soll aber dem Wohle der Allgemeinheit dienen.", "korrekt": True},
            {"text": "Privateigentum ist in Deutschland verboten.", "korrekt": False},
            {"text": "Der Staat kann Eigentum jederzeit ohne Entschädigung nehmen.", "korrekt": False},
            {"text": "Eigentumsrechte gelten nur für Immobilien.", "korrekt": False},
        ],
        "erklaerung": "Art. 14 GG: Eigentum verpflichtet. Sein Gebrauch soll dem Wohle der Allgemeinheit dienen.",
    },
    {
        "label": "Was ist das Recht auf rechtliches Gehör?",
        "antworten": [
            {"text": "Vor Gericht hat jeder das Recht, sich zu äußern und gehört zu werden.", "korrekt": True},
            {"text": "Jeder Bürger darf Gesetze kommentieren.", "korrekt": False},
            {"text": "Gerichte müssen alle Beschwerden persönlich anhören.", "korrekt": False},
            {"text": "Das Recht gilt nur in Zivilprozessen.", "korrekt": False},
        ],
        "erklaerung": "Art. 103 GG: Vor Gericht hat jedermann Anspruch auf rechtliches Gehör.",
    },
    {
        "label": "Was versteht man unter dem Widerstandsrecht im Grundgesetz?",
        "antworten": [
            {"text": "Wenn alle anderen Mittel versagen, darf jeder gegen jemanden Widerstand leisten, der die verfassungsgemäße Ordnung beseitigen will.", "korrekt": True},
            {"text": "Bürger dürfen gegen jedes Gesetz Widerstand leisten.", "korrekt": False},
            {"text": "Widerstand gegen die Polizei ist erlaubt.", "korrekt": False},
            {"text": "Das Widerstandsrecht ist im Grundgesetz nicht verankert.", "korrekt": False},
        ],
        "erklaerung": "Art. 20 Abs. 4 GG verankert ein Widerstandsrecht gegen Angriffe auf die Verfassung.",
    },
    {
        "label": "Was ist das Petitionsrecht?",
        "antworten": [
            {"text": "Jedermann hat das Recht, sich schriftlich mit Bitten oder Beschwerden an den Bundestag zu wenden.", "korrekt": True},
            {"text": "Nur Parteimitglieder können Eingaben machen.", "korrekt": False},
            {"text": "Petitionen sind an das Bundesverfassungsgericht zu richten.", "korrekt": False},
            {"text": "Das Petitionsrecht gilt nur für Behörden.", "korrekt": False},
        ],
        "erklaerung": "Art. 17 GG garantiert das Petitionsrecht gegenüber Volksvertretungen und Behörden.",
    },
    # 101–140: EU und Internationales
    {
        "label": "Was ist die Europäische Union?",
        "antworten": [
            {"text": "Ein politischer und wirtschaftlicher Zusammenschluss europäischer Staaten", "korrekt": True},
            {"text": "Eine Militärorganisation zur Verteidigung Europas", "korrekt": False},
            {"text": "Ein Freihandelsabkommen ausschließlich für Industriegüter", "korrekt": False},
            {"text": "Eine Vereinigung der Vereinten Nationen in Europa", "korrekt": False},
        ],
        "erklaerung": "Die EU ist ein einzigartiger politisch-wirtschaftlicher Zusammenschluss von 27 Staaten.",
    },
    {
        "label": "Wie viele Mitgliedstaaten hat die Europäische Union?",
        "antworten": [
            {"text": "27", "korrekt": True},
            {"text": "25", "korrekt": False},
            {"text": "30", "korrekt": False},
            {"text": "15", "korrekt": False},
        ],
        "erklaerung": "Die EU hat nach dem Brexit 27 Mitgliedstaaten (Stand 2024).",
    },
    {
        "label": "Was ist der Euro?",
        "antworten": [
            {"text": "Die gemeinsame Währung vieler EU-Mitgliedstaaten", "korrekt": True},
            {"text": "Die Währung aller europäischen Länder", "korrekt": False},
            {"text": "Eine elektronische Währung der EU", "korrekt": False},
            {"text": "Der Name der Europäischen Zentralbank", "korrekt": False},
        ],
        "erklaerung": "Der Euro ist die Gemeinschaftswährung der Eurozone (19 EU-Staaten).",
    },
    {
        "label": "Wo sitzt das Europäische Parlament?",
        "antworten": [
            {"text": "Straßburg (und Brüssel)", "korrekt": True},
            {"text": "Genf", "korrekt": False},
            {"text": "Wien", "korrekt": False},
            {"text": "Amsterdam", "korrekt": False},
        ],
        "erklaerung": "Das Europäische Parlament tagt hauptsächlich in Straßburg, Ausschüsse in Brüssel.",
    },
    {
        "label": "Was ist die NATO?",
        "antworten": [
            {"text": "Ein westliches Militärbündnis zur kollektiven Verteidigung", "korrekt": True},
            {"text": "Eine Organisation für Entwicklungshilfe", "korrekt": False},
            {"text": "Eine wirtschaftliche Freihandelszone", "korrekt": False},
            {"text": "Der Name des europäischen Verteidigungsministeriums", "korrekt": False},
        ],
        "erklaerung": "Die NATO ist seit 1949 ein westliches Verteidigungsbündnis, dem Deutschland 1955 beitrat.",
    },
    {
        "label": "Was sind die Vereinten Nationen (UN)?",
        "antworten": [
            {"text": "Eine internationale Organisation zur Förderung von Frieden und Zusammenarbeit", "korrekt": True},
            {"text": "Eine Militärorganisation wie die NATO", "korrekt": False},
            {"text": "Ein Zusammenschluss nur europäischer Staaten", "korrekt": False},
            {"text": "Eine Welthandelsorganisation", "korrekt": False},
        ],
        "erklaerung": "Die UN wurden 1945 gegründet und haben heute 193 Mitgliedstaaten.",
    },
    {
        "label": "Was ist der Europäische Gerichtshof (EuGH)?",
        "antworten": [
            {"text": "Das höchste Gericht der Europäischen Union, das EU-Recht auslegt", "korrekt": True},
            {"text": "Ein Gericht für Menschenrechtsverletzungen in Europa", "korrekt": False},
            {"text": "Ein nationales Gericht in Deutschland", "korrekt": False},
            {"text": "Das Gericht, das Kriegsverbrechen verfolgt", "korrekt": False},
        ],
        "erklaerung": "Der EuGH in Luxemburg ist das oberste Gericht der EU.",
    },
    {
        "label": "Was ist der Europäische Gerichtshof für Menschenrechte (EGMR)?",
        "antworten": [
            {"text": "Ein Gericht, das Beschwerden über Menschenrechtsverletzungen in Europaratsstaaten prüft", "korrekt": True},
            {"text": "Ein Organ der Europäischen Union", "korrekt": False},
            {"text": "Ein deutsches Gericht für internationale Fälle", "korrekt": False},
            {"text": "Das Strafgericht für Kriegsverbrechen", "korrekt": False},
        ],
        "erklaerung": "Der EGMR in Straßburg ist ein Organ des Europarats, nicht der EU.",
    },
    {
        "label": "Was ist das Schengen-Abkommen?",
        "antworten": [
            {"text": "Ein Abkommen, das innereuropäische Grenzkontrollen zwischen den Mitgliedstaaten abschafft", "korrekt": True},
            {"text": "Ein Abkommen über europäische Verteidigung", "korrekt": False},
            {"text": "Ein Vertrag über den gemeinsamen Euro", "korrekt": False},
            {"text": "Ein Handelsabkommen zwischen Deutschland und Frankreich", "korrekt": False},
        ],
        "erklaerung": "Der Schengen-Raum umfasst 27 Staaten ohne Binnengrenzen.",
    },
    {
        "label": "Was ist der Vertrag von Maastricht?",
        "antworten": [
            {"text": "Der Vertrag, mit dem die Europäische Union 1992 gegründet wurde", "korrekt": True},
            {"text": "Ein Vertrag über die deutsche Wiedervereinigung", "korrekt": False},
            {"text": "Ein Waffenstillstandsabkommen nach dem Zweiten Weltkrieg", "korrekt": False},
            {"text": "Ein Klimaabkommen der EU", "korrekt": False},
        ],
        "erklaerung": "Der Vertrag von Maastricht (1992) begründete die Europäische Union.",
    },
    # 141–180: Wirtschaft und Soziales
    {
        "label": "Was ist die soziale Marktwirtschaft?",
        "antworten": [
            {"text": "Ein Wirtschaftssystem, das freien Markt mit sozialer Absicherung verbindet", "korrekt": True},
            {"text": "Ein sozialistisches Wirtschaftssystem mit staatlichen Betrieben", "korrekt": False},
            {"text": "Ein System, in dem der Staat alle Preise festlegt", "korrekt": False},
            {"text": "Eine Form der Planwirtschaft", "korrekt": False},
        ],
        "erklaerung": "Die soziale Marktwirtschaft verbindet Marktwirtschaft mit sozialem Ausgleich.",
    },
    {
        "label": "Wofür steht die Abkürzung 'GmbH' in Deutschland?",
        "antworten": [
            {"text": "Gesellschaft mit beschränkter Haftung", "korrekt": True},
            {"text": "Gemeinnützige mittelständische Bürgergesellschaft Hessen", "korrekt": False},
            {"text": "Genossenschaft mit besonderen Haushaltsmitteln", "korrekt": False},
            {"text": "Gewerkschaftlich mitbestimmte Betriebsgesellschaft", "korrekt": False},
        ],
        "erklaerung": "GmbH = Gesellschaft mit beschränkter Haftung, eine häufige Unternehmensform.",
    },
    {
        "label": "Was ist eine Gewerkschaft?",
        "antworten": [
            {"text": "Eine Organisation, die die Interessen von Arbeitnehmerinnen und Arbeitnehmern vertritt", "korrekt": True},
            {"text": "Eine staatliche Arbeitsbehörde", "korrekt": False},
            {"text": "Ein Zusammenschluss von Unternehmen", "korrekt": False},
            {"text": "Eine politische Partei für Arbeiter", "korrekt": False},
        ],
        "erklaerung": "Gewerkschaften vertreten Arbeitnehmerinteressen, z. B. DGB, IG Metall, ver.di.",
    },
    {
        "label": "Was ist Tarifautonomie?",
        "antworten": [
            {"text": "Das Recht von Gewerkschaften und Arbeitgebern, Löhne und Arbeitsbedingungen frei auszuhandeln", "korrekt": True},
            {"text": "Das staatliche Recht, Löhne festzusetzen", "korrekt": False},
            {"text": "Die Freiheit, Steuern zu umgehen", "korrekt": False},
            {"text": "Das Recht auf individuelle Gehaltsverhandlungen", "korrekt": False},
        ],
        "erklaerung": "Tarifautonomie ist in Art. 9 GG verankert.",
    },
    {
        "label": "Was ist der Mindestlohn in Deutschland?",
        "antworten": [
            {"text": "Der gesetzlich festgelegte Mindeststundenlohn, den Arbeitgeber zahlen müssen", "korrekt": True},
            {"text": "Das Mindesteinkommen aus Sozialleistungen", "korrekt": False},
            {"text": "Der Mindestlohn für Beamte", "korrekt": False},
            {"text": "Ein Empfehlungswert ohne Rechtspflicht", "korrekt": False},
        ],
        "erklaerung": "Der gesetzliche Mindestlohn gilt seit 2015 und wird regelmäßig angepasst.",
    },
    {
        "label": "Was ist die gesetzliche Krankenversicherung (GKV)?",
        "antworten": [
            {"text": "Die Pflichtversicherung für die meisten Arbeitnehmer zur Absicherung bei Krankheit", "korrekt": True},
            {"text": "Eine private Krankenkasse", "korrekt": False},
            {"text": "Eine staatliche Klinik", "korrekt": False},
            {"text": "Eine Versicherung nur für Rentner", "korrekt": False},
        ],
        "erklaerung": "Die GKV ist Pflicht für die meisten Beschäftigten.",
    },
    {
        "label": "Was ist die Rentenversicherung in Deutschland?",
        "antworten": [
            {"text": "Eine Pflichtversicherung, die im Alter eine monatliche Rente zahlt", "korrekt": True},
            {"text": "Eine freiwillige Privatrente", "korrekt": False},
            {"text": "Eine staatliche Schenkung an ältere Menschen", "korrekt": False},
            {"text": "Eine Versicherung nur für Beamte", "korrekt": False},
        ],
        "erklaerung": "Die gesetzliche Rentenversicherung ist Pflicht für Arbeitnehmer.",
    },
    {
        "label": "Was ist die Arbeitslosenversicherung?",
        "antworten": [
            {"text": "Eine Pflichtversicherung, die bei Arbeitslosigkeit Arbeitslosengeld zahlt", "korrekt": True},
            {"text": "Eine private Versicherung gegen Jobverlust", "korrekt": False},
            {"text": "Eine staatliche Jobbörse", "korrekt": False},
            {"text": "Ein Stipendium für Weiterbildung", "korrekt": False},
        ],
        "erklaerung": "Die Bundesagentur für Arbeit verwaltet die Arbeitslosenversicherung.",
    },
    {
        "label": "Was ist die Pflegeversicherung?",
        "antworten": [
            {"text": "Eine Pflichtversicherung, die bei Pflegebedürftigkeit Leistungen zahlt", "korrekt": True},
            {"text": "Eine freiwillige Altersvorsorge", "korrekt": False},
            {"text": "Eine Versicherung für Krankenhausaufenthalte", "korrekt": False},
            {"text": "Eine staatliche Stelle für die Betreuung älterer Menschen", "korrekt": False},
        ],
        "erklaerung": "Die soziale Pflegeversicherung wurde 1995 eingeführt.",
    },
    {
        "label": "Was ist Kindergeld in Deutschland?",
        "antworten": [
            {"text": "Eine staatliche Geldleistung für Eltern zur Unterstützung beim Aufziehen von Kindern", "korrekt": True},
            {"text": "Taschengeld vom Staat für Kinder", "korrekt": False},
            {"text": "Eine Sparanlage für die Ausbildung", "korrekt": False},
            {"text": "Schulgebühren, die der Staat übernimmt", "korrekt": False},
        ],
        "erklaerung": "Kindergeld wird monatlich für jedes Kind bis 18 Jahre (ggf. länger) gezahlt.",
    },
    {
        "label": "Was ist Elterngeld?",
        "antworten": [
            {"text": "Eine staatliche Leistung, die Eltern nach der Geburt eines Kindes beim Einkommensverlust unterstützt", "korrekt": True},
            {"text": "Kindergeld für Eltern über 60", "korrekt": False},
            {"text": "Eine Steuerermäßigung für Eltern", "korrekt": False},
            {"text": "Ein Zuschuss für Kinderkleidung", "korrekt": False},
        ],
        "erklaerung": "Elterngeld ersetzt nach der Geburt einen Teil des Einkommens für bis zu 14 Monate.",
    },
    # 181–220: Recht und Justiz
    {
        "label": "Was ist das Bürgerliche Gesetzbuch (BGB)?",
        "antworten": [
            {"text": "Das zentrale Gesetzbuch des deutschen Privatrechts (Verträge, Familie, Erbrecht etc.)", "korrekt": True},
            {"text": "Die Verfassung Deutschlands", "korrekt": False},
            {"text": "Das Strafgesetzbuch", "korrekt": False},
            {"text": "Ein Handbuch für Beamte", "korrekt": False},
        ],
        "erklaerung": "Das BGB regelt das bürgerliche Recht in Deutschland (seit 1900).",
    },
    {
        "label": "Ab welchem Alter ist man in Deutschland voll strafmündig?",
        "antworten": [
            {"text": "Ab 18 Jahren", "korrekt": True},
            {"text": "Ab 14 Jahren", "korrekt": False},
            {"text": "Ab 16 Jahren", "korrekt": False},
            {"text": "Ab 21 Jahren", "korrekt": False},
        ],
        "erklaerung": "Mit 18 Jahren wird man voll geschäftsfähig und voll strafmündig.",
    },
    {
        "label": "Was ist das Strafgesetzbuch (StGB)?",
        "antworten": [
            {"text": "Das Gesetzbuch, das Straftaten und ihre Strafen in Deutschland regelt", "korrekt": True},
            {"text": "Die Verfassung Deutschlands", "korrekt": False},
            {"text": "Das Gesetzbuch für Ordnungswidrigkeiten", "korrekt": False},
            {"text": "Ein Regelwerk für die Polizei", "korrekt": False},
        ],
        "erklaerung": "Das StGB definiert Straftaten und Strafrahmen.",
    },
    {
        "label": "Was ist die Aufgabe der Polizei in Deutschland?",
        "antworten": [
            {"text": "Die öffentliche Sicherheit und Ordnung zu schützen und Straftaten zu verfolgen", "korrekt": True},
            {"text": "Gesetze zu beschließen", "korrekt": False},
            {"text": "Urteile zu sprechen", "korrekt": False},
            {"text": "Steuern einzutreiben", "korrekt": False},
        ],
        "erklaerung": "Polizei ist für Sicherheit und Ordnung zuständig – in Deutschland Ländersache.",
    },
    {
        "label": "Was ist ein Rechtsanwalt?",
        "antworten": [
            {"text": "Ein unabhängiger Berater und Vertreter in Rechtsfragen", "korrekt": True},
            {"text": "Ein staatlicher Beamter beim Gericht", "korrekt": False},
            {"text": "Ein Richter", "korrekt": False},
            {"text": "Ein Mitarbeiter der Staatsanwaltschaft", "korrekt": False},
        ],
        "erklaerung": "Rechtsanwälte sind freie Berufsträger, die Mandanten beraten und vertreten.",
    },
    {
        "label": "Was ist die Staatsanwaltschaft?",
        "antworten": [
            {"text": "Eine Behörde, die Straftaten verfolgt und Anklage erhebt", "korrekt": True},
            {"text": "Eine Behörde, die Gesetze macht", "korrekt": False},
            {"text": "Ein Gericht", "korrekt": False},
            {"text": "Die Auslandsvertretung des deutschen Staates", "korrekt": False},
        ],
        "erklaerung": "Staatsanwaltschaften ermitteln und erheben Anklage vor Gericht.",
    },
    {
        "label": "Was ist ein Schöffe?",
        "antworten": [
            {"text": "Ein ehrenamtlicher Laienrichter, der bei Gericht an Urteilen mitwirkt", "korrekt": True},
            {"text": "Ein hauptamtlicher Richter beim Amtsgericht", "korrekt": False},
            {"text": "Ein Zeuge vor Gericht", "korrekt": False},
            {"text": "Ein Staatsanwalt", "korrekt": False},
        ],
        "erklaerung": "Schöffen sind Bürger, die ehrenamtlich an Strafverfahren mitwirken.",
    },
    {
        "label": "Was ist der Unterschied zwischen einem Verbrechen und einer Ordnungswidrigkeit?",
        "antworten": [
            {"text": "Verbrechen sind schwere Straftaten (Mindeststrafe 1 Jahr); Ordnungswidrigkeiten werden mit Bußgeld geahndet.", "korrekt": True},
            {"text": "Ordnungswidrigkeiten sind schlimmer als Verbrechen.", "korrekt": False},
            {"text": "Es gibt keinen rechtlichen Unterschied.", "korrekt": False},
            {"text": "Verbrechen werden nur von Bundesbehörden verfolgt.", "korrekt": False},
        ],
        "erklaerung": "Verbrechen (§ 12 StGB): mind. 1 Jahr; Vergehen: weniger; Ordnungswidrigkeiten: kein Strafrecht.",
    },
    {
        "label": "Was ist das Jugendstrafrecht?",
        "antworten": [
            {"text": "Ein besonderes Strafrecht für Jugendliche (14–17 Jahre) und Heranwachsende (18–20 Jahre)", "korrekt": True},
            {"text": "Ein Recht, das Kinder unter 14 Jahren bestraft", "korrekt": False},
            {"text": "Allgemeines Strafrecht für alle über 10 Jahren", "korrekt": False},
            {"text": "Das Recht, das Eltern für Kinderstraftaten bestraft", "korrekt": False},
        ],
        "erklaerung": "Das Jugendgerichtsgesetz (JGG) gilt für Jugendliche ab 14 Jahren.",
    },
    {
        "label": "Was versteht man unter einem Datenschutzbeauftragten?",
        "antworten": [
            {"text": "Eine Person, die in Unternehmen und Behörden die Einhaltung des Datenschutzes überwacht", "korrekt": True},
            {"text": "Ein Mitarbeiter, der persönliche Daten verkauft", "korrekt": False},
            {"text": "Ein Polizist für Cyberkriminalität", "korrekt": False},
            {"text": "Ein staatlicher Überwachungsbeamter", "korrekt": False},
        ],
        "erklaerung": "Datenschutzbeauftragte sind Pflicht in vielen Unternehmen (DSGVO).",
    },
    # 221–260: Bildung und Kultur
    {
        "label": "Wie lange dauert die allgemeine Schulpflicht in Deutschland?",
        "antworten": [
            {"text": "9 bis 10 Jahre (je nach Bundesland)", "korrekt": True},
            {"text": "6 Jahre", "korrekt": False},
            {"text": "12 Jahre", "korrekt": False},
            {"text": "8 Jahre", "korrekt": False},
        ],
        "erklaerung": "Die allgemeine Schulpflicht beträgt in den meisten Ländern 9–10 Jahre.",
    },
    {
        "label": "Was ist das duale Ausbildungssystem?",
        "antworten": [
            {"text": "Eine Berufsausbildung, die zwischen Betrieb und Berufsschule aufgeteilt ist", "korrekt": True},
            {"text": "Ein Studium an zwei Universitäten gleichzeitig", "korrekt": False},
            {"text": "Eine Ausbildung nur im Betrieb ohne Schule", "korrekt": False},
            {"text": "Ein Schulsystem mit zwei Lehrern", "korrekt": False},
        ],
        "erklaerung": "Das duale System kombiniert Betriebsausbildung mit Berufsschule.",
    },
    {
        "label": "Wer ist für das Schulsystem in Deutschland hauptsächlich zuständig?",
        "antworten": [
            {"text": "Die Bundesländer (Kulturhoheit der Länder)", "korrekt": True},
            {"text": "Der Bund (Bundesministerium für Bildung)", "korrekt": False},
            {"text": "Die Gemeinden und Städte", "korrekt": False},
            {"text": "Die Europäische Union", "korrekt": False},
        ],
        "erklaerung": "Bildung ist Ländersache – daher gibt es 16 verschiedene Schulsysteme.",
    },
    {
        "label": "Was ist die Volkshochschule (VHS)?",
        "antworten": [
            {"text": "Eine öffentliche Erwachsenenbildungseinrichtung, die günstige Kurse anbietet", "korrekt": True},
            {"text": "Eine Grundschule für Erwachsene", "korrekt": False},
            {"text": "Eine Berufsschule", "korrekt": False},
            {"text": "Eine Privatuniversität", "korrekt": False},
        ],
        "erklaerung": "Die VHS ist die größte Einrichtung für Erwachsenenbildung in Deutschland.",
    },
    {
        "label": "Was sind Integrationskurse in Deutschland?",
        "antworten": [
            {"text": "Deutschkurse und Orientierungskurse, die Zuwandernden das Leben in Deutschland erleichtern sollen", "korrekt": True},
            {"text": "Kurse für deutsche Schüler über ausländische Kulturen", "korrekt": False},
            {"text": "Pflichtprogramme für Asylbewerber in Lagern", "korrekt": False},
            {"text": "Sportprogramme für Neuzuwandernde", "korrekt": False},
        ],
        "erklaerung": "Integrationskurse werden vom BAMF organisiert und umfassen Deutsch und Orientierung.",
    },
    {
        "label": "Was ist der Unterschied zwischen Gymnasium und Hauptschule?",
        "antworten": [
            {"text": "Das Gymnasium führt zum Abitur; die Hauptschule endet mit dem Hauptschulabschluss.", "korrekt": True},
            {"text": "Die Hauptschule ist elitärer als das Gymnasium.", "korrekt": False},
            {"text": "Das Gymnasium bietet keine Berufsausbildung an.", "korrekt": False},
            {"text": "Beide Schulen führen zum selben Abschluss.", "korrekt": False},
        ],
        "erklaerung": "Gymnasium (Klasse 5–12/13) → Abitur; Hauptschule (Klasse 5–9/10) → Hauptschulabschluss.",
    },
    {
        "label": "Was ist das Abitur?",
        "antworten": [
            {"text": "Die allgemeine Hochschulreife, die zum Studium an deutschen Universitäten berechtigt", "korrekt": True},
            {"text": "Ein Berufsabschluss nach der Ausbildung", "korrekt": False},
            {"text": "Ein Abschluss nach der Grundschule", "korrekt": False},
            {"text": "Eine Prüfung für Ausländer zum Sprachnachweis", "korrekt": False},
        ],
        "erklaerung": "Das Abitur (Matura) berechtigt zur Aufnahme eines Hochschulstudiums.",
    },
    {
        "label": "Was ist ein Meister in Deutschland?",
        "antworten": [
            {"text": "Ein Facharbeiter mit besonderer Qualifikation, der einen Handwerksbetrieb führen darf", "korrekt": True},
            {"text": "Ein Universitätsprofessor", "korrekt": False},
            {"text": "Ein staatlicher Prüfer für Handwerksberufe", "korrekt": False},
            {"text": "Ein Sportlehrer", "korrekt": False},
        ],
        "erklaerung": "Der Meisterbrief ermöglicht die Leitung eines Handwerksbetriebs.",
    },
    {
        "label": "Was ist das duale Hochschulstudium (Duales Studium)?",
        "antworten": [
            {"text": "Ein Studium, das mit einer Berufsausbildung oder Berufstätigkeit kombiniert wird", "korrekt": True},
            {"text": "Ein Studium an zwei Hochschulen gleichzeitig", "korrekt": False},
            {"text": "Ein Fernstudium", "korrekt": False},
            {"text": "Ein staatlich festgelegtes Pflichtprogramm", "korrekt": False},
        ],
        "erklaerung": "Beim dualen Studium wechseln sich Betrieb und Hochschule ab.",
    },
    {
        "label": "Was versteht man unter Kulturhoheit der Länder?",
        "antworten": [
            {"text": "Die Bundesländer sind eigenständig für Bildung, Kultur und Rundfunk zuständig.", "korrekt": True},
            {"text": "Die Länder dürfen eigene Kultusministerien nicht haben.", "korrekt": False},
            {"text": "Der Bund regelt alle kulturellen Angelegenheiten.", "korrekt": False},
            {"text": "Kultur ist ausschließlich Privatsache.", "korrekt": False},
        ],
        "erklaerung": "Kulturhoheit der Länder ist ein zentrales Merkmal des deutschen Föderalismus.",
    },
    # 261–300: Alltag, Arbeit, Integration
    {
        "label": "Was ist ein Personalausweis?",
        "antworten": [
            {"text": "Ein amtliches Dokument, das die Identität einer Person belegt", "korrekt": True},
            {"text": "Eine Arbeitsgenehmigung", "korrekt": False},
            {"text": "Ein Führerschein", "korrekt": False},
            {"text": "Ein Reisepass nur für Auslandsreisen", "korrekt": False},
        ],
        "erklaerung": "Der Personalausweis dient der Identitätsfeststellung und ist in der EU als Reisedokument gültig.",
    },
    {
        "label": "Was ist das Einwohnermeldeamt?",
        "antworten": [
            {"text": "Eine Behörde, bei der man sich bei Zuzug anmelden muss", "korrekt": True},
            {"text": "Das Amt für Ausländerangelegenheiten", "korrekt": False},
            {"text": "Eine Steuerbehörde", "korrekt": False},
            {"text": "Das Standesamt für Geburten und Heiraten", "korrekt": False},
        ],
        "erklaerung": "In Deutschland besteht Meldepflicht – man muss sich innerhalb von 14 Tagen ummelden.",
    },
    {
        "label": "Was ist das Standesamt?",
        "antworten": [
            {"text": "Eine Behörde, die Geburten, Heiraten und Sterbefälle beurkundet", "korrekt": True},
            {"text": "Eine Behörde für Kfz-Zulassungen", "korrekt": False},
            {"text": "Eine Sozialleistungsstelle", "korrekt": False},
            {"text": "Ein Büro für Baugenehmigungen", "korrekt": False},
        ],
        "erklaerung": "Das Standesamt beurkundet Personenstandssachen.",
    },
    {
        "label": "Was ist das Finanzamt?",
        "antworten": [
            {"text": "Eine staatliche Behörde, die Steuern festsetzt und einzieht", "korrekt": True},
            {"text": "Eine staatliche Bank", "korrekt": False},
            {"text": "Eine Behörde für Sozialleistungen", "korrekt": False},
            {"text": "Ein Amt für Unternehmensanmeldungen", "korrekt": False},
        ],
        "erklaerung": "Das Finanzamt verwaltet und erhebt Steuern auf Länderebene.",
    },
    {
        "label": "Was ist das Jobcenter?",
        "antworten": [
            {"text": "Eine Behörde, die Arbeitssuchende betreut und Bürgergeld zahlt", "korrekt": True},
            {"text": "Eine private Arbeitsvermittlungsagentur", "korrekt": False},
            {"text": "Ein Beratungszentrum für Berufsausbildung", "korrekt": False},
            {"text": "Eine Bildungseinrichtung", "korrekt": False},
        ],
        "erklaerung": "Jobcenter betreuen Menschen, die Bürgergeld (früher Hartz IV) erhalten.",
    },
    {
        "label": "Was ist die Bundesagentur für Arbeit?",
        "antworten": [
            {"text": "Eine Behörde, die bei Arbeitslosigkeit zahlt, Stellen vermittelt und Förderung anbietet", "korrekt": True},
            {"text": "Das Bundesministerium für Arbeit", "korrekt": False},
            {"text": "Eine Gewerkschaft", "korrekt": False},
            {"text": "Eine private Zeitarbeitsfirma", "korrekt": False},
        ],
        "erklaerung": "Die Bundesagentur für Arbeit (BA) ist für Arbeitslosenversicherung und -vermittlung zuständig.",
    },
    {
        "label": "Was ist Bürgergeld in Deutschland?",
        "antworten": [
            {"text": "Eine staatliche Grundsicherungsleistung für Menschen ohne ausreichendes Einkommen", "korrekt": True},
            {"text": "Ein bedingungsloses Grundeinkommen für alle", "korrekt": False},
            {"text": "Eine besondere Rente für Senioren", "korrekt": False},
            {"text": "Ein Lohn für freiwillige Gemeindearbeit", "korrekt": False},
        ],
        "erklaerung": "Bürgergeld (seit 2023, vorher ALG II / Hartz IV) ist die Grundsicherung.",
    },
    {
        "label": "Was ist die Krankenversicherungspflicht?",
        "antworten": [
            {"text": "In Deutschland ist fast jeder verpflichtet, krankenversichert zu sein.", "korrekt": True},
            {"text": "Nur Beamte müssen sich versichern.", "korrekt": False},
            {"text": "Krankenversicherung ist freiwillig.", "korrekt": False},
            {"text": "Nur Erwachsene müssen sich versichern.", "korrekt": False},
        ],
        "erklaerung": "Seit 2009 besteht in Deutschland eine allgemeine Krankenversicherungspflicht.",
    },
    {
        "label": "Was ist ein Tarifvertrag?",
        "antworten": [
            {"text": "Eine Vereinbarung zwischen Gewerkschaft und Arbeitgeberverband über Löhne und Arbeitsbedingungen", "korrekt": True},
            {"text": "Ein Vertrag zwischen Staat und Bürger über Steuerleistungen", "korrekt": False},
            {"text": "Ein Preiskatalog für staatliche Dienstleistungen", "korrekt": False},
            {"text": "Ein Vertrag zwischen zwei Unternehmen", "korrekt": False},
        ],
        "erklaerung": "Tarifverträge regeln Mindestlöhne und Arbeitsbedingungen in Branchen.",
    },
    {
        "label": "Was ist das Mutterschutzgesetz?",
        "antworten": [
            {"text": "Ein Gesetz, das schwangere Frauen und Mütter nach der Geburt am Arbeitsplatz schützt", "korrekt": True},
            {"text": "Ein Gesetz, das nur für Beamtinnen gilt", "korrekt": False},
            {"text": "Ein Gesetz, das die Kinderbetreuung regelt", "korrekt": False},
            {"text": "Ein Gesetz über Adoptiveltern", "korrekt": False},
        ],
        "erklaerung": "Das MuSchG schützt Mütter vor und nach der Geburt vor Kündigung und Benachteiligung.",
    },
    {
        "label": "Was ist das Elternzeitgesetz (BEEG)?",
        "antworten": [
            {"text": "Ein Gesetz, das Eltern nach der Geburt Schutz vor Kündigung und Elternzeit ermöglicht", "korrekt": True},
            {"text": "Ein Gesetz über staatliche Kinderbetreuung", "korrekt": False},
            {"text": "Ein Gesetz für Alleinerziehende", "korrekt": False},
            {"text": "Ein Gesetz über Adoptionsrechte", "korrekt": False},
        ],
        "erklaerung": "Das BEEG ermöglicht bis zu 3 Jahre Elternzeit pro Elternteil.",
    },
    {
        "label": "Was ist das Allgemeine Gleichbehandlungsgesetz (AGG)?",
        "antworten": [
            {"text": "Ein Gesetz, das Diskriminierung wegen Herkunft, Geschlecht, Religion u.a. verbietet", "korrekt": True},
            {"text": "Ein Gesetz über gleiche Wahlrechte", "korrekt": False},
            {"text": "Ein Gesetz über gleiche Löhne für alle", "korrekt": False},
            {"text": "Ein Gesetz über Schulpflicht", "korrekt": False},
        ],
        "erklaerung": "Das AGG (2006) schützt vor Diskriminierung in Beruf und Alltag.",
    },
    {
        "label": "Was versteht man unter Integration?",
        "antworten": [
            {"text": "Die Eingliederung von Zugewanderten in die Gesellschaft unter Wahrung der eigenen Identität", "korrekt": True},
            {"text": "Die vollständige Aufgabe der eigenen Kultur", "korrekt": False},
            {"text": "Die Abtrennung von Gruppen in gesonderten Stadtteilen", "korrekt": False},
            {"text": "Die Pflicht, Deutsche zu heiraten", "korrekt": False},
        ],
        "erklaerung": "Integration bedeutet gegenseitige Teilhabe und Eingliederung in die Gesellschaft.",
    },
    {
        "label": "Was ist ein Aufenthaltstitel?",
        "antworten": [
            {"text": "Ein amtliches Dokument, das Ausländern erlaubt, sich in Deutschland aufzuhalten", "korrekt": True},
            {"text": "Ein Mietvertrag", "korrekt": False},
            {"text": "Ein Personalausweis für EU-Bürger", "korrekt": False},
            {"text": "Ein Antrag auf Einbürgerung", "korrekt": False},
        ],
        "erklaerung": "Nicht-EU-Bürger benötigen in der Regel einen Aufenthaltstitel.",
    },
    {
        "label": "Was ist das Ausländeramt (Ausländerbehörde)?",
        "antworten": [
            {"text": "Eine Behörde, die Aufenthaltsgenehmigungen erteilt und Ausländer-Angelegenheiten regelt", "korrekt": True},
            {"text": "Eine Behörde nur für Asylbewerber", "korrekt": False},
            {"text": "Eine Beratungsstelle für Einbürgerung", "korrekt": False},
            {"text": "Das Einwohnermeldeamt für Ausländer", "korrekt": False},
        ],
        "erklaerung": "Die Ausländerbehörde ist zuständig für Aufenthalts- und Arbeitsgenehmigungen.",
    },
    {
        "label": "Was sind demokratische Wahlen?",
        "antworten": [
            {"text": "Wahlen, die allgemein, unmittelbar, frei, gleich und geheim sind (Art. 38 GG)", "korrekt": True},
            {"text": "Wahlen nur für bestimmte Bevölkerungsgruppen", "korrekt": False},
            {"text": "Wahlen, die der Staat vorher festlegt", "korrekt": False},
            {"text": "Wahlen ohne Kandidatenlisten", "korrekt": False},
        ],
        "erklaerung": "Art. 38 GG: Die Grundsätze demokratischer Wahlen sind allgemein, unmittelbar, frei, gleich und geheim.",
    },
    {
        "label": "Was ist eine Volksinitiative?",
        "antworten": [
            {"text": "Ein Instrument direkter Demokratie, bei dem Bürger ein Thema in den Landtag einbringen können", "korrekt": True},
            {"text": "Die Gründung einer neuen politischen Partei", "korrekt": False},
            {"text": "Eine Umfrage der Regierung", "korrekt": False},
            {"text": "Ein Volksbegehren auf Bundesebene", "korrekt": False},
        ],
        "erklaerung": "Volksinitiativen, -begehren und -entscheide gibt es auf Landesebene.",
    },
    {
        "label": "Was ist ein Bürgermeister?",
        "antworten": [
            {"text": "Der direkt gewählte Verwaltungschef einer Gemeinde oder Stadt", "korrekt": True},
            {"text": "Der Regierungschef eines Bundeslandes", "korrekt": False},
            {"text": "Ein Mitglied des Bundestages", "korrekt": False},
            {"text": "Ein staatlicher Beamter für Wohnungsfragen", "korrekt": False},
        ],
        "erklaerung": "Bürgermeister leiten Gemeinden und werden direkt von den Bürgern gewählt.",
    },
    {
        "label": "Was ist der Gemeinderat?",
        "antworten": [
            {"text": "Das gewählte Volksvertretungsorgan einer Gemeinde", "korrekt": True},
            {"text": "Ein Gericht auf Gemeindeebene", "korrekt": False},
            {"text": "Eine Beratungsgruppe für den Bürgermeister ohne Entscheidungsbefugnis", "korrekt": False},
            {"text": "Das Sozialamt einer Gemeinde", "korrekt": False},
        ],
        "erklaerung": "Gemeinderäte/Stadtparlamente entscheiden über kommunale Angelegenheiten.",
    },
    {
        "label": "Was ist das Bundesland?",
        "antworten": [
            {"text": "Eines der 16 Länder, aus denen die Bundesrepublik Deutschland besteht", "korrekt": True},
            {"text": "Eine große Stadt in Deutschland", "korrekt": False},
            {"text": "Ein Bundesministerium", "korrekt": False},
            {"text": "Ein Landkreis", "korrekt": False},
        ],
        "erklaerung": "Deutschland besteht aus 16 Bundesländern mit eigenen Regierungen und Parlamenten.",
    },
    {
        "label": "Was ist der Landtag?",
        "antworten": [
            {"text": "Das gewählte Parlament eines Bundeslandes", "korrekt": True},
            {"text": "Das Parlament der Gemeinden", "korrekt": False},
            {"text": "Eine überregionale Konferenz der Ministerpräsidenten", "korrekt": False},
            {"text": "Der Bundestag eines kleinen Landes", "korrekt": False},
        ],
        "erklaerung": "Jedes der 16 Bundesländer hat einen eigenen Landtag.",
    },
]

# ---------------------------------------------------------------------------
# Länderspezifische Fragen
# ---------------------------------------------------------------------------

LAENDER: dict[str, list[dict]] = {
    "BW": [
        {
            "label": "Welches ist die Landeshauptstadt von Baden-Württemberg?",
            "antworten": [
                {"text": "Stuttgart", "korrekt": True},
                {"text": "Karlsruhe", "korrekt": False},
                {"text": "Freiburg im Breisgau", "korrekt": False},
                {"text": "Mannheim", "korrekt": False},
            ],
            "erklaerung": "Stuttgart ist Landeshauptstadt von Baden-Württemberg.",
        },
        {
            "label": "Welches Bundesland ist Baden-Württemberg?",
            "antworten": [
                {"text": "Ein Bundesland im Südwesten Deutschlands", "korrekt": True},
                {"text": "Ein Bundesland im Norden Deutschlands", "korrekt": False},
                {"text": "Ein Stadtstaat", "korrekt": False},
                {"text": "Ein Bundesland im Osten Deutschlands", "korrekt": False},
            ],
            "erklaerung": "Baden-Württemberg liegt im Südwesten Deutschlands.",
        },
        {
            "label": "Wann wurde das heutige Bundesland Baden-Württemberg gegründet?",
            "antworten": [
                {"text": "1952", "korrekt": True},
                {"text": "1949", "korrekt": False},
                {"text": "1945", "korrekt": False},
                {"text": "1990", "korrekt": False},
            ],
            "erklaerung": "Baden-Württemberg entstand 1952 aus drei Ländern.",
        },
        {
            "label": "Welche Nationalparks gibt es in Baden-Württemberg?",
            "antworten": [
                {"text": "Nationalpark Schwarzwald", "korrekt": True},
                {"text": "Nationalpark Berchtesgaden", "korrekt": False},
                {"text": "Nationalpark Bayerischer Wald", "korrekt": False},
                {"text": "Nationalpark Harz", "korrekt": False},
            ],
            "erklaerung": "Der Nationalpark Schwarzwald wurde 2014 gegründet.",
        },
        {
            "label": "Welches ist die bevölkerungsreichste Stadt in Baden-Württemberg?",
            "antworten": [
                {"text": "Stuttgart", "korrekt": True},
                {"text": "Karlsruhe", "korrekt": False},
                {"text": "Heidelberg", "korrekt": False},
                {"text": "Ulm", "korrekt": False},
            ],
            "erklaerung": "Stuttgart ist mit ca. 630.000 Einwohnern die größte Stadt Baden-Württembergs.",
        },
    ],
    "BY": [
        {
            "label": "Welches ist die Landeshauptstadt von Bayern?",
            "antworten": [
                {"text": "München", "korrekt": True},
                {"text": "Nürnberg", "korrekt": False},
                {"text": "Augsburg", "korrekt": False},
                {"text": "Regensburg", "korrekt": False},
            ],
            "erklaerung": "München ist die Landeshauptstadt Bayerns.",
        },
        {
            "label": "Was ist das Oktoberfest?",
            "antworten": [
                {"text": "Das weltgrößte Volksfest, das jährlich in München stattfindet", "korrekt": True},
                {"text": "Ein Erntedankfest in ganz Bayern", "korrekt": False},
                {"text": "Ein religiöses Fest der bayerischen Kirche", "korrekt": False},
                {"text": "Ein staatlicher Feiertag in Bayern", "korrekt": False},
            ],
            "erklaerung": "Das Münchner Oktoberfest ist das weltgrößte Volksfest.",
        },
        {
            "label": "Welcher Fluss fließt durch München?",
            "antworten": [
                {"text": "Die Isar", "korrekt": True},
                {"text": "Der Rhein", "korrekt": False},
                {"text": "Die Donau", "korrekt": False},
                {"text": "Der Main", "korrekt": False},
            ],
            "erklaerung": "Die Isar fließt durch München.",
        },
        {
            "label": "Was ist die CSU?",
            "antworten": [
                {"text": "Eine politische Partei, die nur in Bayern zur Wahl antritt", "korrekt": True},
                {"text": "Eine bundesweite Partei", "korrekt": False},
                {"text": "Eine bayerische Gewerkschaft", "korrekt": False},
                {"text": "Der bayerische Verfassungsgerichtshof", "korrekt": False},
            ],
            "erklaerung": "Die CSU (Christlich-Soziale Union) ist die Schwesterpartei der CDU und tritt nur in Bayern an.",
        },
        {
            "label": "Welcher Nationalpark liegt in Bayern?",
            "antworten": [
                {"text": "Nationalpark Bayerischer Wald", "korrekt": True},
                {"text": "Nationalpark Schwarzwald", "korrekt": False},
                {"text": "Nationalpark Harz", "korrekt": False},
                {"text": "Nationalpark Wattenmeer", "korrekt": False},
            ],
            "erklaerung": "Der Bayerische Wald ist Deutschlands ältester Nationalpark (1970).",
        },
    ],
    "BE": [
        {
            "label": "Was ist Berlin?",
            "antworten": [
                {"text": "Die Hauptstadt und ein Stadtstaat der Bundesrepublik Deutschland", "korrekt": True},
                {"text": "Eine kreisfreie Stadt in Brandenburg", "korrekt": False},
                {"text": "Ein Bundesland im Norden Deutschlands", "korrekt": False},
                {"text": "Die zweitgrößte Stadt Deutschlands", "korrekt": False},
            ],
            "erklaerung": "Berlin ist Hauptstadt, bevölkerungsreichste Stadt und Bundesland zugleich.",
        },
        {
            "label": "Welche historische Bedeutung hat das Brandenburger Tor in Berlin?",
            "antworten": [
                {"text": "Es ist ein Symbol der deutschen Einheit", "korrekt": True},
                {"text": "Es ist der Sitz des Bundestages", "korrekt": False},
                {"text": "Es ist ein mittelalterliches Stadttor", "korrekt": False},
                {"text": "Es ist ein Kriegerdenkmal", "korrekt": False},
            ],
            "erklaerung": "Das Brandenburger Tor ist das bekannteste Symbol Berlins und der deutschen Einheit.",
        },
        {
            "label": "Was war das Regierungsviertel der DDR in Berlin?",
            "antworten": [
                {"text": "Ost-Berlin (auch Hauptstadt der DDR)", "korrekt": True},
                {"text": "Potsdam", "korrekt": False},
                {"text": "West-Berlin", "korrekt": False},
                {"text": "Magdeburg", "korrekt": False},
            ],
            "erklaerung": "Ost-Berlin war die Hauptstadt der DDR.",
        },
        {
            "label": "Welches Gebäude ist der Sitz des Deutschen Bundestages in Berlin?",
            "antworten": [
                {"text": "Das Reichstagsgebäude", "korrekt": True},
                {"text": "Das Berliner Schloss", "korrekt": False},
                {"text": "Das Rote Rathaus", "korrekt": False},
                {"text": "Das Bundeskanzleramt", "korrekt": False},
            ],
            "erklaerung": "Der Bundestag tagt im Reichstagsgebäude, das 1999 wiedereröffnet wurde.",
        },
        {
            "label": "Durch welchen Fluss fließt Berlin?",
            "antworten": [
                {"text": "Die Spree", "korrekt": True},
                {"text": "Die Havel", "korrekt": False},
                {"text": "Die Elbe", "korrekt": False},
                {"text": "Der Rhein", "korrekt": False},
            ],
            "erklaerung": "Die Spree fließt durch das Zentrum Berlins.",
        },
    ],
    "BB": [
        {
            "label": "Welches ist die Landeshauptstadt von Brandenburg?",
            "antworten": [
                {"text": "Potsdam", "korrekt": True},
                {"text": "Frankfurt (Oder)", "korrekt": False},
                {"text": "Cottbus", "korrekt": False},
                {"text": "Brandenburg an der Havel", "korrekt": False},
            ],
            "erklaerung": "Potsdam ist die Landeshauptstadt Brandenburgs.",
        },
        {
            "label": "Welches UNESCO-Weltkulturerbe befindet sich in Potsdam?",
            "antworten": [
                {"text": "Schloss Sanssouci und die Parks von Potsdam", "korrekt": True},
                {"text": "Das Brandenburger Tor", "korrekt": False},
                {"text": "Die Potsdamer Konferenz", "korrekt": False},
                {"text": "Der Schiffhebewerk Niederfinow", "korrekt": False},
            ],
            "erklaerung": "Die Potsdamer Schlösser und Gärten sind UNESCO-Welterbe.",
        },
    ],
    "HB": [
        {
            "label": "Was ist das Bundesland Bremen?",
            "antworten": [
                {"text": "Ein Stadtstaat bestehend aus den Städten Bremen und Bremerhaven", "korrekt": True},
                {"text": "Ein Bundesland im Norden mit vielen Gemeinden", "korrekt": False},
                {"text": "Deutschlands kleinstes Flächenland", "korrekt": False},
                {"text": "Eine kreisfreie Stadt in Niedersachsen", "korrekt": False},
            ],
            "erklaerung": "Das Bundesland Bremen besteht aus den Städten Bremen und Bremerhaven.",
        },
        {
            "label": "Welches Wahrzeichen ist bekannt für die Stadt Bremen?",
            "antworten": [
                {"text": "Die Bremer Stadtmusikanten", "korrekt": True},
                {"text": "Das Rathaus und der Marktplatz (UNESCO-Welterbe)", "korrekt": False},
                {"text": "Der Roland", "korrekt": False},
                {"text": "Alle genannten", "korrekt": False},
            ],
            "erklaerung": "Das Bremer Rathaus, der Roland und die Stadtmusikanten sind bekannte Wahrzeichen.",
        },
    ],
    "HH": [
        {
            "label": "Was ist Hamburg?",
            "antworten": [
                {"text": "Ein Stadtstaat und Bundesland, die zweitgrößte Stadt Deutschlands", "korrekt": True},
                {"text": "Eine kreisfreie Stadt in Schleswig-Holstein", "korrekt": False},
                {"text": "Die Hauptstadt Norddeutschlands", "korrekt": False},
                {"text": "Ein Bundesland mit Hauptstadt Hamburg", "korrekt": False},
            ],
            "erklaerung": "Hamburg ist Stadtstaat und bevölkerungsreichste Stadt nach Berlin.",
        },
        {
            "label": "Wofür ist der Hamburger Hafen bekannt?",
            "antworten": [
                {"text": "Er ist einer der größten Häfen Europas und wichtig für den Welthandel.", "korrekt": True},
                {"text": "Er ist ausschließlich ein Fischereihafen.", "korrekt": False},
                {"text": "Er ist nur für Kreuzfahrten genutzt.", "korrekt": False},
                {"text": "Er ist der größte Hafen der Welt.", "korrekt": False},
            ],
            "erklaerung": "Der Hamburger Hafen ist einer der bedeutendsten Containerhäfen Europas.",
        },
    ],
    "HE": [
        {
            "label": "Welches ist die Landeshauptstadt von Hessen?",
            "antworten": [
                {"text": "Wiesbaden", "korrekt": True},
                {"text": "Frankfurt am Main", "korrekt": False},
                {"text": "Kassel", "korrekt": False},
                {"text": "Darmstadt", "korrekt": False},
            ],
            "erklaerung": "Wiesbaden ist die Landeshauptstadt Hessens – nicht Frankfurt.",
        },
        {
            "label": "Welche wichtige Funktion hat Frankfurt am Main in Deutschland?",
            "antworten": [
                {"text": "Finanzmetropole, Sitz der Europäischen Zentralbank", "korrekt": True},
                {"text": "Bundeshauptstadt", "korrekt": False},
                {"text": "Sitz des Bundestages", "korrekt": False},
                {"text": "Sitz des Bundesverfassungsgerichts", "korrekt": False},
            ],
            "erklaerung": "Frankfurt ist Deutschlands Finanzmetropole und Sitz der EZB.",
        },
    ],
    "MV": [
        {
            "label": "Welches ist die Landeshauptstadt von Mecklenburg-Vorpommern?",
            "antworten": [
                {"text": "Schwerin", "korrekt": True},
                {"text": "Rostock", "korrekt": False},
                {"text": "Greifswald", "korrekt": False},
                {"text": "Stralsund", "korrekt": False},
            ],
            "erklaerung": "Schwerin ist Landeshauptstadt von Mecklenburg-Vorpommern.",
        },
        {
            "label": "An welchem Meer liegt Mecklenburg-Vorpommern?",
            "antworten": [
                {"text": "An der Ostsee", "korrekt": True},
                {"text": "An der Nordsee", "korrekt": False},
                {"text": "An der Elbe", "korrekt": False},
                {"text": "Am Atlantik", "korrekt": False},
            ],
            "erklaerung": "Mecklenburg-Vorpommern hat eine lange Ostseeküste.",
        },
    ],
    "NI": [
        {
            "label": "Welches ist die Landeshauptstadt von Niedersachsen?",
            "antworten": [
                {"text": "Hannover", "korrekt": True},
                {"text": "Braunschweig", "korrekt": False},
                {"text": "Osnabrück", "korrekt": False},
                {"text": "Göttingen", "korrekt": False},
            ],
            "erklaerung": "Hannover ist Landeshauptstadt Niedersachsens.",
        },
        {
            "label": "An welchem Meer liegt Niedersachsen?",
            "antworten": [
                {"text": "An der Nordsee", "korrekt": True},
                {"text": "An der Ostsee", "korrekt": False},
                {"text": "Am Rhein", "korrekt": False},
                {"text": "An der Elbe", "korrekt": False},
            ],
            "erklaerung": "Niedersachsen hat eine Nordseeküste mit dem Wattenmeer (UNESCO-Welterbe).",
        },
    ],
    "NW": [
        {
            "label": "Welches ist die Landeshauptstadt von Nordrhein-Westfalen?",
            "antworten": [
                {"text": "Düsseldorf", "korrekt": True},
                {"text": "Köln", "korrekt": False},
                {"text": "Dortmund", "korrekt": False},
                {"text": "Essen", "korrekt": False},
            ],
            "erklaerung": "Düsseldorf ist die Landeshauptstadt von NRW.",
        },
        {
            "label": "Welches Bundesland ist das bevölkerungsreichste in Deutschland?",
            "antworten": [
                {"text": "Nordrhein-Westfalen", "korrekt": True},
                {"text": "Bayern", "korrekt": False},
                {"text": "Baden-Württemberg", "korrekt": False},
                {"text": "Hessen", "korrekt": False},
            ],
            "erklaerung": "NRW hat ca. 18 Millionen Einwohner – das meiste aller Bundesländer.",
        },
        {
            "label": "Was war das Ruhrgebiet historisch bekannt für?",
            "antworten": [
                {"text": "Kohle- und Stahlindustrie (industrielles Herz Deutschlands)", "korrekt": True},
                {"text": "Landwirtschaft und Weinbau", "korrekt": False},
                {"text": "Schiffbau und Meeresforschung", "korrekt": False},
                {"text": "Automobilindustrie", "korrekt": False},
            ],
            "erklaerung": "Das Ruhrgebiet war das industrielle Zentrum Deutschlands.",
        },
    ],
    "RP": [
        {
            "label": "Welches ist die Landeshauptstadt von Rheinland-Pfalz?",
            "antworten": [
                {"text": "Mainz", "korrekt": True},
                {"text": "Koblenz", "korrekt": False},
                {"text": "Trier", "korrekt": False},
                {"text": "Kaiserslautern", "korrekt": False},
            ],
            "erklaerung": "Mainz ist Landeshauptstadt von Rheinland-Pfalz.",
        },
        {
            "label": "Wofür ist das Rheintal in Rheinland-Pfalz bekannt?",
            "antworten": [
                {"text": "Weinbau und das UNESCO-Welterbe Oberes Mittelrheintal", "korrekt": True},
                {"text": "Kohlebergbau", "korrekt": False},
                {"text": "Automobilindustrie", "korrekt": False},
                {"text": "Fischereiindustrie", "korrekt": False},
            ],
            "erklaerung": "Das Obere Mittelrheintal ist UNESCO-Welterbe.",
        },
    ],
    "SL": [
        {
            "label": "Welches ist die Landeshauptstadt des Saarlandes?",
            "antworten": [
                {"text": "Saarbrücken", "korrekt": True},
                {"text": "Saarlouis", "korrekt": False},
                {"text": "Homburg", "korrekt": False},
                {"text": "Neunkirchen", "korrekt": False},
            ],
            "erklaerung": "Saarbrücken ist die Landeshauptstadt des Saarlandes.",
        },
        {
            "label": "An welches Land grenzt das Saarland?",
            "antworten": [
                {"text": "An Frankreich und Luxemburg", "korrekt": True},
                {"text": "An die Schweiz und Österreich", "korrekt": False},
                {"text": "An Belgien und die Niederlande", "korrekt": False},
                {"text": "An Polen und Tschechien", "korrekt": False},
            ],
            "erklaerung": "Das Saarland grenzt an Frankreich und Luxemburg.",
        },
    ],
    "SN": [
        {
            "label": "Welches ist die Landeshauptstadt von Sachsen?",
            "antworten": [
                {"text": "Dresden", "korrekt": True},
                {"text": "Leipzig", "korrekt": False},
                {"text": "Chemnitz", "korrekt": False},
                {"text": "Zwickau", "korrekt": False},
            ],
            "erklaerung": "Dresden ist die Landeshauptstadt des Freistaats Sachsen.",
        },
        {
            "label": "Welches war die Elbflorenz?",
            "antworten": [
                {"text": "Dresden, wegen seiner historischen Bauten und Kunstsammlungen", "korrekt": True},
                {"text": "Leipzig, wegen seiner Messen", "korrekt": False},
                {"text": "Chemnitz, wegen seiner Industrie", "korrekt": False},
                {"text": "Meißen, wegen des Porzellans", "korrekt": False},
            ],
            "erklaerung": "Dresden wird wegen seiner Kunstschätze 'Elbflorenz' genannt.",
        },
    ],
    "ST": [
        {
            "label": "Welches ist die Landeshauptstadt von Sachsen-Anhalt?",
            "antworten": [
                {"text": "Magdeburg", "korrekt": True},
                {"text": "Halle (Saale)", "korrekt": False},
                {"text": "Dessau-Roßlau", "korrekt": False},
                {"text": "Wittenberg", "korrekt": False},
            ],
            "erklaerung": "Magdeburg ist Landeshauptstadt von Sachsen-Anhalt.",
        },
        {
            "label": "In welchem Bundesland wurden die Thesen Luthers 1517 veröffentlicht?",
            "antworten": [
                {"text": "Sachsen-Anhalt (Wittenberg)", "korrekt": True},
                {"text": "Thüringen", "korrekt": False},
                {"text": "Bayern", "korrekt": False},
                {"text": "Hessen", "korrekt": False},
            ],
            "erklaerung": "Martin Luther veröffentlichte 1517 in Wittenberg (heute Sachsen-Anhalt) seine 95 Thesen.",
        },
    ],
    "SH": [
        {
            "label": "Welches ist die Landeshauptstadt von Schleswig-Holstein?",
            "antworten": [
                {"text": "Kiel", "korrekt": True},
                {"text": "Lübeck", "korrekt": False},
                {"text": "Flensburg", "korrekt": False},
                {"text": "Neumünster", "korrekt": False},
            ],
            "erklaerung": "Kiel ist Landeshauptstadt von Schleswig-Holstein.",
        },
        {
            "label": "Zwischen welchen Meeren liegt Schleswig-Holstein?",
            "antworten": [
                {"text": "Zwischen Nord- und Ostsee", "korrekt": True},
                {"text": "Zwischen Nord- und Atlantik", "korrekt": False},
                {"text": "Zwischen Ostsee und Baltischem Meer", "korrekt": False},
                {"text": "An der Nordsee allein", "korrekt": False},
            ],
            "erklaerung": "Schleswig-Holstein liegt einzigartig zwischen Nord- und Ostsee.",
        },
    ],
    "TH": [
        {
            "label": "Welches ist die Landeshauptstadt von Thüringen?",
            "antworten": [
                {"text": "Erfurt", "korrekt": True},
                {"text": "Jena", "korrekt": False},
                {"text": "Weimar", "korrekt": False},
                {"text": "Gera", "korrekt": False},
            ],
            "erklaerung": "Erfurt ist die Landeshauptstadt des Freistaats Thüringen.",
        },
        {
            "label": "Welche historische Bedeutung hat Weimar in Thüringen?",
            "antworten": [
                {"text": "Stadt der Klassik (Goethe, Schiller), Gründungsort der Weimarer Republik", "korrekt": True},
                {"text": "Geburtsort von Martin Luther", "korrekt": False},
                {"text": "Sitz des ersten deutschen Parlaments", "korrekt": False},
                {"text": "Hauptstadt der DDR", "korrekt": False},
            ],
            "erklaerung": "Weimar ist Stätte der deutschen Klassik und Gründungsort der Weimarer Republik (1919).",
        },
    ],
}


def get_bundesweite_fragen(anzahl: int | None = None) -> list[dict]:
    """Gibt bundesweite Fragen als quizfrage-kompatible Dicts zurück."""
    import random
    pool = list(BUNDESWEIT)
    if anzahl is not None:
        pool = random.sample(pool, min(anzahl, len(pool)))
    return _zu_quizfelder(pool, "bw")


def get_fragen(anzahl_bundesweit: int = 30, bundesland: str = "", anzahl_laender: int = 3) -> list[dict]:
    """
    Gibt einen gemischten Fragenpool zurück (wie im echten Einbürgerungstest).
    Default: 30 bundesweite + 3 länderspezifische = 33 Fragen.
    """
    import random
    bund = random.sample(BUNDESWEIT, min(anzahl_bundesweit, len(BUNDESWEIT)))
    laender_fragen = LAENDER.get(bundesland, []) if bundesland else []
    land = random.sample(laender_fragen, min(anzahl_laender, len(laender_fragen))) if laender_fragen else []
    alle = bund + land
    random.shuffle(alle)
    return _zu_quizfelder(alle, "einb")


def _zu_quizfelder(fragen: list[dict], prefix: str = "q") -> list[dict]:
    """Wandelt Fragen-Dicts in quizfrage-kompatible Feld-Dicts um."""
    result = []
    for i, f in enumerate(fragen):
        result.append({
            "typ":         "quizfrage",
            "id":          f"{prefix}__{i}",
            "label":       f["label"],
            "antwort_typ": f.get("antwort_typ", "single"),
            "punkte":      f.get("punkte", 1.0),
            "erklaerung":  f.get("erklaerung", ""),
            "antworten":   f["antworten"],
            "pflicht":     True,
        })
    return result
