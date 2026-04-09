# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Backup-Worker: Läuft als Daemon-Prozess im Docker-Container.

Zeitplan (BSI CON.3):
  - Täglich    02:00 Uhr  → komplett (Aufbewahrung: 7)
  - Wöchentlich So 03:00  → komplett (Aufbewahrung: 4)
  - Monatlich  1. 04:00   → komplett (Aufbewahrung: 12)
  - Nach jeder Sicherung: SHA-256 Integritätsprüfung
"""
import logging
import time
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger("vorgangswerk.sicherung")


class Command(BaseCommand):
    help = "Backup-Daemon: führt automatische Sicherungen nach Zeitplan aus"

    def handle(self, *args, **options):
        self.stdout.write("Backup-Worker gestartet (BSI CON.3)")
        self.stdout.write("Zeitplan: täglich 02:00 | wöchentlich So 03:00 | monatlich 1. 04:00")

        letzter_tag       = None
        letzte_woche      = None
        letzter_monat     = None

        while True:
            jetzt = datetime.now()
            tag       = jetzt.date()
            wochentag = jetzt.weekday()   # 6 = Sonntag
            monatstag = jetzt.day
            stunde    = jetzt.hour
            minute    = jetzt.minute

            # Täglich um 02:00
            if stunde == 2 and minute < 5 and tag != letzter_tag:
                self.stdout.write(f"[{jetzt:%Y-%m-%d %H:%M}] Starte tägliche Sicherung…")
                try:
                    call_command("sicherung_erstellen", typ="komplett", rhythmus="taeglich")
                    call_command("sicherung_pruefen")
                    letzter_tag = tag
                    logger.info("Tägliche Sicherung erfolgreich")
                except Exception as e:
                    logger.error("Tägliche Sicherung fehlgeschlagen: %s", e)

            # Wöchentlich Sonntag 03:00
            elif wochentag == 6 and stunde == 3 and minute < 5 and tag != letzte_woche:
                self.stdout.write(f"[{jetzt:%Y-%m-%d %H:%M}] Starte wöchentliche Sicherung…")
                try:
                    call_command("sicherung_erstellen", typ="komplett", rhythmus="woechentlich")
                    call_command("sicherung_pruefen")
                    letzte_woche = tag
                    logger.info("Wöchentliche Sicherung erfolgreich")
                except Exception as e:
                    logger.error("Wöchentliche Sicherung fehlgeschlagen: %s", e)

            # Monatlich am 1. um 04:00
            elif monatstag == 1 and stunde == 4 and minute < 5 and tag != letzter_monat:
                self.stdout.write(f"[{jetzt:%Y-%m-%d %H:%M}] Starte monatliche Sicherung…")
                try:
                    call_command("sicherung_erstellen", typ="komplett", rhythmus="monatlich")
                    call_command("sicherung_pruefen")
                    letzter_monat = tag
                    logger.info("Monatliche Sicherung erfolgreich")
                except Exception as e:
                    logger.error("Monatliche Sicherung fehlgeschlagen: %s", e)

            time.sleep(60)  # jede Minute prüfen
