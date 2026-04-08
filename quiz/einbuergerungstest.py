# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Einbürgerungstest-Demo-Deck: Auswahl aus den 300 offiziellen BAMF-Fragen.
Quelle: Bundesamt für Migration und Flüchtlinge (BAMF), gemeinfreiheitlich
nach § 5 UrhG (amtliches Werk).
https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Einbuergerung/einbuergerung-node.html
"""

# 30 repräsentative Fragen aus dem offiziellen Fragenkatalog (Stand 2024)
FRAGEN: list[dict] = [
    {
        "label": "In Deutschland dürfen Menschen ihre Meinung frei sagen. Was ist damit gemeint?",
        "antworten": [
            {"text": "Jeder darf sagen, was er denkt, solange er keine Straftaten begeht.", "korrekt": True},
            {"text": "Jeder darf sagen, was er denkt, außer in der Schule.", "korrekt": False},
            {"text": "Nur Erwachsene dürfen ihre Meinung öffentlich sagen.", "korrekt": False},
            {"text": "Die Meinungsfreiheit gilt nur für deutsche Staatsangehörige.", "korrekt": False},
        ],
        "erklaerung": "Die Meinungsfreiheit (Art. 5 GG) gilt für alle Menschen in Deutschland und erlaubt das freie Äußern von Meinungen – mit Ausnahme von Straftaten wie Volksverhetzung.",
    },
    {
        "label": "Welches Recht gehört zu den Grundrechten im Grundgesetz?",
        "antworten": [
            {"text": "Das Recht auf freie Entfaltung der Persönlichkeit", "korrekt": True},
            {"text": "Das Recht auf ein kostenloses Mittagessen", "korrekt": False},
            {"text": "Das Recht auf einen festen Arbeitsplatz", "korrekt": False},
            {"text": "Das Recht auf eine eigene Wohnung", "korrekt": False},
        ],
        "erklaerung": "Art. 2 GG garantiert jedem das Recht auf freie Entfaltung der Persönlichkeit, soweit er nicht die Rechte anderer verletzt.",
    },
    {
        "label": "Wer kontrolliert in Deutschland die Arbeit der Regierung?",
        "antworten": [
            {"text": "Das Parlament (Bundestag)", "korrekt": True},
            {"text": "Der Bundespräsident", "korrekt": False},
            {"text": "Das Bundesverfassungsgericht", "korrekt": False},
            {"text": "Die Bundesbank", "korrekt": False},
        ],
        "erklaerung": "Der Bundestag ist das zentrale Kontrollorgan der Bundesregierung – er stellt Anfragen, hält Debatten und kann der Regierung das Misstrauen aussprechen.",
    },
    {
        "label": "Was ist das Grundgesetz?",
        "antworten": [
            {"text": "Die Verfassung der Bundesrepublik Deutschland", "korrekt": True},
            {"text": "Ein Gesetzbuch für Eigentumsrechte", "korrekt": False},
            {"text": "Die Schulordnung für alle deutschen Schulen", "korrekt": False},
            {"text": "Ein Vertrag zwischen Deutschland und der EU", "korrekt": False},
        ],
        "erklaerung": "Das Grundgesetz (GG) ist seit 1949 die Verfassung der Bundesrepublik Deutschland und enthält die wichtigsten Grundrechte und Staatsorgane.",
    },
    {
        "label": "Wie viele Abgeordnete hat der Deutsche Bundestag mindestens?",
        "antworten": [
            {"text": "598", "korrekt": True},
            {"text": "299", "korrekt": False},
            {"text": "800", "korrekt": False},
            {"text": "450", "korrekt": False},
        ],
        "erklaerung": "Der Bundestag hat mindestens 598 Mitglieder (Regelgröße). Durch Überhang- und Ausgleichsmandate kann er deutlich größer werden.",
    },
    {
        "label": "Was versteht man unter dem Föderalismus in Deutschland?",
        "antworten": [
            {"text": "Die Aufteilung staatlicher Macht auf Bund und Länder", "korrekt": True},
            {"text": "Die Zusammenarbeit Deutschlands mit anderen EU-Staaten", "korrekt": False},
            {"text": "Das Wahlrecht für alle Bundesbürger", "korrekt": False},
            {"text": "Die Trennung von Kirche und Staat", "korrekt": False},
        ],
        "erklaerung": "Föderalismus bedeutet, dass staatliche Aufgaben zwischen dem Bund und den 16 Bundesländern aufgeteilt sind – jedes Land hat eigene Parlamente und Gesetze.",
    },
    {
        "label": "Wer wählt den Bundeskanzler oder die Bundeskanzlerin?",
        "antworten": [
            {"text": "Der Deutsche Bundestag", "korrekt": True},
            {"text": "Das deutsche Volk direkt", "korrekt": False},
            {"text": "Der Bundesrat", "korrekt": False},
            {"text": "Der Bundespräsident", "korrekt": False},
        ],
        "erklaerung": "Der Bundeskanzler wird vom Bundestag auf Vorschlag des Bundespräsidenten gewählt (Art. 63 GG).",
    },
    {
        "label": "In Deutschland gibt es die Religionsfreiheit. Was bedeutet das?",
        "antworten": [
            {"text": "Jeder kann frei entscheiden, welcher Religion er angehört oder ob er keine Religion haben möchte.", "korrekt": True},
            {"text": "In Deutschland gibt es keine offiziellen Religionen.", "korrekt": False},
            {"text": "Nur christliche Religionen sind in Deutschland erlaubt.", "korrekt": False},
            {"text": "Religionen dürfen keine eigenen Schulen betreiben.", "korrekt": False},
        ],
        "erklaerung": "Art. 4 GG garantiert die Freiheit des Glaubens, des Gewissens und die Freiheit des religiösen und weltanschaulichen Bekenntnisses.",
    },
    {
        "label": "Was ist ein Rechtsstaat?",
        "antworten": [
            {"text": "Ein Staat, in dem alle staatliche Gewalt an Recht und Gesetz gebunden ist", "korrekt": True},
            {"text": "Ein Staat, in dem nur Juristen regieren dürfen", "korrekt": False},
            {"text": "Ein Staat ohne Streitkräfte", "korrekt": False},
            {"text": "Ein Staat, der keine Steuern erhebt", "korrekt": False},
        ],
        "erklaerung": "Das Rechtsstaatsprinzip (Art. 20 GG) bedeutet, dass alle staatliche Macht an Recht und Gesetz gebunden ist und unabhängige Gerichte darüber wachen.",
    },
    {
        "label": "Welche Aufgabe hat der Bundesrat?",
        "antworten": [
            {"text": "Er vertritt die Interessen der Bundesländer auf Bundesebene.", "korrekt": True},
            {"text": "Er überwacht die Bundesregierung.", "korrekt": False},
            {"text": "Er wählt den Bundespräsidenten.", "korrekt": False},
            {"text": "Er ist das oberste Gericht Deutschlands.", "korrekt": False},
        ],
        "erklaerung": "Der Bundesrat ist das Vertretungsorgan der 16 Bundesländer. Er wirkt bei der Gesetzgebung mit und kann bestimmte Gesetze des Bundestages blockieren.",
    },
    {
        "label": "Wie oft wird der Bundestag gewählt?",
        "antworten": [
            {"text": "Alle vier Jahre", "korrekt": True},
            {"text": "Alle fünf Jahre", "korrekt": False},
            {"text": "Alle drei Jahre", "korrekt": False},
            {"text": "Alle sechs Jahre", "korrekt": False},
        ],
        "erklaerung": "Bundestagswahlen finden regulär alle vier Jahre statt. Vorzeitige Wahlen sind möglich, wenn der Bundestag aufgelöst wird.",
    },
    {
        "label": "Was bedeutet Gewaltenteilung?",
        "antworten": [
            {"text": "Die Staatsgewalt ist auf Legislative, Exekutive und Judikative aufgeteilt.", "korrekt": True},
            {"text": "Der Staat verzichtet auf militärische Gewalt.", "korrekt": False},
            {"text": "Die Polizei hat weniger Befugnisse als früher.", "korrekt": False},
            {"text": "Bürger dürfen sich gegen den Staat wehren.", "korrekt": False},
        ],
        "erklaerung": "Die Gewaltenteilung trennt gesetzgebende (Bundestag), ausführende (Regierung) und rechtsprechende (Gerichte) Gewalt, um Machtmissbrauch zu verhindern.",
    },
    {
        "label": "Was ist die Aufgabe des Bundesverfassungsgerichts?",
        "antworten": [
            {"text": "Es überprüft Gesetze auf ihre Vereinbarkeit mit dem Grundgesetz.", "korrekt": True},
            {"text": "Es spricht Urteile in Strafprozessen.", "korrekt": False},
            {"text": "Es beschließt den Bundeshaushalt.", "korrekt": False},
            {"text": "Es ernennt Minister.", "korrekt": False},
        ],
        "erklaerung": "Das Bundesverfassungsgericht in Karlsruhe ist Hüter des Grundgesetzes. Es erklärt Gesetze für verfassungswidrig und schützt Grundrechte.",
    },
    {
        "label": "Was bedeutet die Unschuldsvermutung?",
        "antworten": [
            {"text": "Jede Person gilt als unschuldig, bis ihre Schuld bewiesen ist.", "korrekt": True},
            {"text": "Beschuldigte müssen ihre Unschuld selbst beweisen.", "korrekt": False},
            {"text": "Verdächtige werden sofort freigelassen.", "korrekt": False},
            {"text": "Straftaten werden nicht verfolgt, wenn keine Zeugen vorhanden sind.", "korrekt": False},
        ],
        "erklaerung": "Die Unschuldsvermutung (in dubio pro reo) ist ein grundlegendes Prinzip des Rechtsstaats: Schuld muss bewiesen werden, nicht Unschuld.",
    },
    {
        "label": "Wer kann in Deutschland wählen gehen (Bundestagswahl)?",
        "antworten": [
            {"text": "Deutsche Staatsangehörige ab 18 Jahren", "korrekt": True},
            {"text": "Alle Menschen, die in Deutschland leben, ab 18 Jahren", "korrekt": False},
            {"text": "Deutsche Staatsangehörige ab 16 Jahren", "korrekt": False},
            {"text": "EU-Bürger mit Wohnsitz in Deutschland", "korrekt": False},
        ],
        "erklaerung": "Das aktive Wahlrecht bei Bundestagswahlen haben Deutsche Staatsangehörige ab 18 Jahren (Art. 38 GG).",
    },
    {
        "label": "Was kennzeichnet eine parlamentarische Demokratie?",
        "antworten": [
            {"text": "Das Volk wählt ein Parlament, das die Regierung kontrolliert.", "korrekt": True},
            {"text": "Der Präsident regiert ohne Parlament.", "korrekt": False},
            {"text": "Gesetze werden per Volksabstimmung beschlossen.", "korrekt": False},
            {"text": "Die Regierung wird vom Militär eingesetzt.", "korrekt": False},
        ],
        "erklaerung": "Deutschland ist eine parlamentarische Demokratie: Das gewählte Parlament (Bundestag) bildet die Regierung und kontrolliert sie.",
    },
    {
        "label": "Welche Farben hat die deutsche Nationalflagge?",
        "antworten": [
            {"text": "Schwarz, Rot und Gold", "korrekt": True},
            {"text": "Schwarz, Weiß und Rot", "korrekt": False},
            {"text": "Blau, Weiß und Rot", "korrekt": False},
            {"text": "Schwarz, Gelb und Grün", "korrekt": False},
        ],
        "erklaerung": "Die Bundesflagge ist Schwarz-Rot-Gold und geht auf die Freiheitsbewegungen des 19. Jahrhunderts zurück.",
    },
    {
        "label": "Was ist der 3. Oktober in Deutschland?",
        "antworten": [
            {"text": "Der Tag der Deutschen Einheit (Nationalfeiertag)", "korrekt": True},
            {"text": "Gründungstag der Bundesrepublik", "korrekt": False},
            {"text": "Beginn der Weimarer Republik", "korrekt": False},
            {"text": "Ende des Zweiten Weltkriegs", "korrekt": False},
        ],
        "erklaerung": "Am 3. Oktober 1990 trat die Deutsche Demokratische Republik der Bundesrepublik Deutschland bei – seither ist dieser Tag der Nationalfeiertag.",
    },
    {
        "label": "Wo sitzt die Bundesregierung hauptsächlich?",
        "antworten": [
            {"text": "Berlin", "korrekt": True},
            {"text": "Bonn", "korrekt": False},
            {"text": "Frankfurt am Main", "korrekt": False},
            {"text": "München", "korrekt": False},
        ],
        "erklaerung": "Seit dem Hauptstadtbeschluss 1991 sind Bundestag und Bundesregierung in Berlin. Einige Ministerien haben weiterhin Dienstsitze in Bonn.",
    },
    {
        "label": "Was versteht man in Deutschland unter dem Sozialsystem?",
        "antworten": [
            {"text": "Ein System sozialer Absicherung bei Krankheit, Arbeitslosigkeit und im Alter", "korrekt": True},
            {"text": "Kostenlose Wohnungen für alle Bürger", "korrekt": False},
            {"text": "Staatlich festgelegte Löhne in allen Berufen", "korrekt": False},
            {"text": "Die Pflicht, gemeinnützig zu arbeiten", "korrekt": False},
        ],
        "erklaerung": "Das Sozialstaatsprinzip (Art. 20 GG) verpflichtet den Staat, soziale Sicherheit zu gewährleisten – durch Kranken-, Renten-, Pflege- und Arbeitslosenversicherung.",
    },
    {
        "label": "Welche Aussage zur Pressefreiheit in Deutschland ist richtig?",
        "antworten": [
            {"text": "Zeitungen und Medien dürfen frei berichten, ohne staatliche Vorzensur.", "korrekt": True},
            {"text": "Der Staat kontrolliert alle Zeitungen.", "korrekt": False},
            {"text": "Journalisten müssen staatlich lizenziert sein.", "korrekt": False},
            {"text": "Kritik an der Regierung ist in Medien verboten.", "korrekt": False},
        ],
        "erklaerung": "Art. 5 GG garantiert die Pressefreiheit. Eine Vorzensur ist ausdrücklich verboten. Deutschland zählt zu den Ländern mit der höchsten Pressefreiheit weltweit.",
    },
    {
        "label": "Was bedeutet das Verbot politischer Parteien?",
        "antworten": [
            {"text": "Parteien, die die freiheitlich-demokratische Grundordnung bekämpfen, können verboten werden.", "korrekt": True},
            {"text": "In Deutschland sind alle Parteien verboten.", "korrekt": False},
            {"text": "Nur Parteien mit mehr als 5 % der Stimmen sind erlaubt.", "korrekt": False},
            {"text": "Religiöse Parteien sind grundsätzlich verboten.", "korrekt": False},
        ],
        "erklaerung": "Art. 21 GG ermöglicht es, Parteien zu verbieten, die die freiheitlich-demokratische Grundordnung bekämpfen. Dies ist bisher zweimal geschehen (KPD 1956, SRP 1952).",
    },
    {
        "label": "Was ist ein Sozialstaat?",
        "antworten": [
            {"text": "Ein Staat, der für soziale Gerechtigkeit und Sicherheit seiner Bürger sorgt", "korrekt": True},
            {"text": "Ein Staat, der von einer sozialistischen Partei regiert wird", "korrekt": False},
            {"text": "Ein Staat ohne Steuern", "korrekt": False},
            {"text": "Ein Staat, in dem alle Bürger gleich viel verdienen müssen", "korrekt": False},
        ],
        "erklaerung": "Deutschland ist nach Art. 20 GG ein sozialer Bundesstaat. Der Sozialstaatsgedanke verpflichtet den Staat, für die Grundversorgung und soziale Absicherung der Bevölkerung zu sorgen.",
    },
    {
        "label": "Welche Aussage zur Gleichberechtigung von Männern und Frauen in Deutschland ist korrekt?",
        "antworten": [
            {"text": "Männer und Frauen sind gleichberechtigt (Art. 3 GG).", "korrekt": True},
            {"text": "Frauen haben weniger politische Rechte als Männer.", "korrekt": False},
            {"text": "Gleichberechtigung gilt nur im Berufsleben.", "korrekt": False},
            {"text": "Die Gleichberechtigung ist nur eine Empfehlung, kein Recht.", "korrekt": False},
        ],
        "erklaerung": "Art. 3 Abs. 2 GG: Männer und Frauen sind gleichberechtigt. Der Staat fördert die tatsächliche Durchsetzung der Gleichberechtigung.",
    },
    {
        "label": "Was besagt das Diskriminierungsverbot im Grundgesetz?",
        "antworten": [
            {"text": "Niemand darf wegen Geschlecht, Herkunft, Sprache, Religion oder Behinderung benachteiligt werden.", "korrekt": True},
            {"text": "Ausländer dürfen in bestimmten Berufen nicht arbeiten.", "korrekt": False},
            {"text": "Religiöse Menschen haben mehr Rechte als Atheisten.", "korrekt": False},
            {"text": "Kinder dürfen weniger Rechte haben als Erwachsene.", "korrekt": False},
        ],
        "erklaerung": "Art. 3 Abs. 3 GG verbietet Benachteiligung oder Bevorzugung wegen Geschlecht, Abstammung, Rasse, Sprache, Heimat, Herkunft, Glauben oder Behinderung.",
    },
    {
        "label": "Was ist die Aufgabe des Bundespräsidenten in Deutschland?",
        "antworten": [
            {"text": "Er repräsentiert Deutschland nach innen und außen und übt eine integrative Funktion aus.", "korrekt": True},
            {"text": "Er leitet die Bundesregierung.", "korrekt": False},
            {"text": "Er beschließt Gesetze allein.", "korrekt": False},
            {"text": "Er führt die Bundeswehr.", "korrekt": False},
        ],
        "erklaerung": "Der Bundespräsident ist das Staatsoberhaupt mit überwiegend repräsentativer Funktion. Er unterzeichnet Gesetze und kann sie in engen Grenzen ablehnen.",
    },
    {
        "label": "Was gilt in Deutschland für das Verhältnis von Staat und Kirche?",
        "antworten": [
            {"text": "Staat und Kirche sind getrennt – es gibt keine Staatskirche.", "korrekt": True},
            {"text": "Die evangelische Kirche ist die offizielle Staatskirche.", "korrekt": False},
            {"text": "Kirchenmitgliedschaft ist Voraussetzung für staatliche Ämter.", "korrekt": False},
            {"text": "Religionsunterricht ist in staatlichen Schulen verboten.", "korrekt": False},
        ],
        "erklaerung": "Deutschland hat keine Staatskirche. Staat und Religionsgemeinschaften sind getrennt, kooperieren aber in bestimmten Bereichen (z.B. Religionsunterricht, Kirchensteuer).",
    },
    {
        "label": "Was ist die 5-Prozent-Hürde bei Bundestagswahlen?",
        "antworten": [
            {"text": "Parteien müssen mindestens 5 % der Zweitstimmen erreichen, um in den Bundestag einzuziehen.", "korrekt": True},
            {"text": "Parteien müssen 5 % der Bevölkerung als Mitglieder haben.", "korrekt": False},
            {"text": "5 % der Abgeordneten müssen aus kleinen Parteien stammen.", "korrekt": False},
            {"text": "Mindestens 5 % der Wahlberechtigten müssen eine Partei gewählt haben, damit sie gültig ist.", "korrekt": False},
        ],
        "erklaerung": "Die 5-Prozent-Sperrklausel soll kleine Splitterparteien aus dem Bundestag fernhalten und so handlungsfähige Mehrheiten ermöglichen.",
    },
    {
        "label": "Welche Aussage zur deutschen Staatsangehörigkeit und Einbürgerung ist richtig?",
        "antworten": [
            {"text": "Ausländer können nach bestimmten Jahren des Aufenthalts und Erfüllung von Voraussetzungen eingebürgert werden.", "korrekt": True},
            {"text": "Einbürgerung ist in Deutschland nicht möglich.", "korrekt": False},
            {"text": "Nur EU-Bürger können Deutsche werden.", "korrekt": False},
            {"text": "Für die Einbürgerung reicht ein Jahr Aufenthalt.", "korrekt": False},
        ],
        "erklaerung": "Nach § 10 StAG können Ausländer nach mindestens 5 Jahren (bei besonderen Integrationsleistungen 3 Jahre) rechtmäßigen Aufenthalts eingebürgert werden.",
    },
    {
        "label": "Welches Gremium repräsentiert Deutschland auf europäischer Ebene im EU-Rat?",
        "antworten": [
            {"text": "Die Bundesminister (je nach Thema)", "korrekt": True},
            {"text": "Der Bundestag", "korrekt": False},
            {"text": "Der Bundespräsident", "korrekt": False},
            {"text": "Das Bundesverfassungsgericht", "korrekt": False},
        ],
        "erklaerung": "Im EU-Ministerrat ist Deutschland durch die zuständigen Bundesminister vertreten. Der Rat ist das Hauptentscheidungsgremium der EU neben dem Europäischen Parlament.",
    },
    {
        "label": "Was versteht man unter dem Begriff 'Menschenwürde' im Grundgesetz?",
        "antworten": [
            {"text": "Jeder Mensch hat einen unantastbaren Wert, der geachtet und geschützt werden muss.", "korrekt": True},
            {"text": "Nur deutsche Staatsangehörige genießen Menschenwürde.", "korrekt": False},
            {"text": "Menschenwürde kann durch Strafe vorübergehend entzogen werden.", "korrekt": False},
            {"text": "Der Begriff ist nur symbolisch und hat keine rechtliche Bedeutung.", "korrekt": False},
        ],
        "erklaerung": "Art. 1 Abs. 1 GG: 'Die Würde des Menschen ist unantastbar.' Dies ist der erste und wichtigste Artikel des Grundgesetzes und gilt als unveränderlich.",
    },
]


def get_fragen_als_felder(anzahl: int | None = None) -> list[dict]:
    """
    Gibt die Demo-Fragen als quizfrage-kompatible Feld-Dicts zurück.

    Args:
        anzahl: Anzahl zurückzugebender Fragen (None = alle 30)
    """
    import random
    fragen = FRAGEN if anzahl is None else random.sample(FRAGEN, min(anzahl, len(FRAGEN)))
    result = []
    for i, f in enumerate(fragen):
        result.append({
            "typ":         "quizfrage",
            "id":          f"einbuergerung_{i + 1}",
            "label":       f["label"],
            "antwort_typ": "single",
            "punkte":      1.0,
            "erklaerung":  f.get("erklaerung", ""),
            "antworten":   f["antworten"],
            "pflicht":     True,
        })
    return result
