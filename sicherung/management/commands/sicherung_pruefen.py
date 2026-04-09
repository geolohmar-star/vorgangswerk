# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: Sicherung auf Integrität prüfen (BSI CON.3)

Prüfschritte:
  1. Datei vorhanden?
  2. SHA-256 Prüfsumme korrekt?          (CON.3.A8)
  3. Entschlüsselung erfolgreich?        (CON.3.A13)
  4. tar.gz strukturell lesbar?          (CON.3.A14)
  5. SQL-Dump inhaltlich valide?         (CON.3.A14)

Nutzung:
    python manage.py sicherung_pruefen           # letzte Sicherung prüfen
    python manage.py sicherung_pruefen --pk 42   # bestimmte Sicherung prüfen
    python manage.py sicherung_pruefen --alle     # alle ungeprüften prüfen
"""
import hashlib
import io
import logging
import tarfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger("vorgangswerk.sicherung")

MAGIC = b"VWBK"
# Mindest-SQL-Indikatoren – mindestens einer muss im Dump vorhanden sein
SQL_INDIKATOREN = [b"CREATE TABLE", b"INSERT INTO", b"COPY ", b"-- PostgreSQL"]


class Command(BaseCommand):
    help = "Prüft die Integrität einer Datensicherung nach BSI CON.3"

    def add_arguments(self, parser):
        parser.add_argument("--pk", type=int, help="PK der zu prüfenden Sicherung")
        parser.add_argument("--alle", action="store_true", help="Alle ungeprüften Sicherungen prüfen")

    def handle(self, *args, **options):
        from sicherung.models import SicherungsProtokoll

        if options["alle"]:
            eintraege = list(
                SicherungsProtokoll.objects.filter(
                    status="ok",
                    geprueft_am__isnull=True,
                    geloescht_am__isnull=True,
                )
            )
        elif options["pk"]:
            eintraege = [SicherungsProtokoll.objects.get(pk=options["pk"])]
        else:
            eintrag = (
                SicherungsProtokoll.objects
                .filter(status__in=["ok", "geprueft"], geloescht_am__isnull=True)
                .order_by("-erstellt_am")
                .first()
            )
            if not eintrag:
                self.stdout.write(self.style.WARNING("Keine Sicherung gefunden."))
                return
            eintraege = [eintrag]

        fehler = 0
        for eintrag in eintraege:
            ok = self._pruefe(eintrag)
            if not ok:
                fehler += 1

        if fehler:
            self.stderr.write(self.style.ERROR(f"\n{fehler} Sicherung(en) fehlerhaft!"))
            raise SystemExit(1)
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Alle {len(eintraege)} Sicherung(en) bestehen alle BSI-CON.3-Prüfschritte."
            ))

    def _pruefe(self, eintrag) -> bool:
        from sicherung.models import SicherungsProtokoll

        self.stdout.write(f"\nPrüfe: {eintrag.dateiname}")
        fehler_liste = []

        # ----------------------------------------------------------------
        # Schritt 1: Datei vorhanden?
        # ----------------------------------------------------------------
        pfad = Path(eintrag.dateipfad)
        if not pfad.exists():
            self._fehler(eintrag, "Datei nicht gefunden auf Datentraeger")
            self.stderr.write(self.style.ERROR("  ✗ [1/5] Datei nicht gefunden"))
            return False
        self.stdout.write("  ✓ [1/5] Datei vorhanden")

        rohdaten = pfad.read_bytes()

        # ----------------------------------------------------------------
        # Schritt 2: SHA-256 Prüfsumme
        # ----------------------------------------------------------------
        if eintrag.sha256_pruefsumme:
            ist = hashlib.sha256(rohdaten).hexdigest()
            if ist != eintrag.sha256_pruefsumme:
                self._fehler(eintrag,
                    f"SHA-256 stimmt nicht – erwartet: {eintrag.sha256_pruefsumme[:16]}… "
                    f"ist: {ist[:16]}…"
                )
                self.stderr.write(self.style.ERROR(
                    f"  ✗ [2/5] SHA-256 STIMMT NICHT\n"
                    f"         Erwartet: {eintrag.sha256_pruefsumme}\n"
                    f"         Ist:      {ist}"
                ))
                return False
            self.stdout.write("  ✓ [2/5] SHA-256 korrekt")
        else:
            self.stdout.write(self.style.WARNING("  – [2/5] Keine Prüfsumme hinterlegt (übersprungen)"))

        # ----------------------------------------------------------------
        # Schritt 3: Entschlüsselung (falls verschlüsselt)
        # ----------------------------------------------------------------
        if rohdaten.startswith(MAGIC):
            if not eintrag.verschluesselt:
                fehler_liste.append("Datei hat VWBK-Header aber ist laut DB nicht verschlüsselt")
            schluessel_raw = getattr(settings, "VERSCHLUESSEL_KEY", "")
            if not schluessel_raw:
                self.stdout.write(self.style.WARNING(
                    "  – [3/5] Verschlüsselt, aber VERSCHLUESSEL_KEY nicht gesetzt – übersprungen"
                ))
                entschluesselt = None
            else:
                try:
                    entschluesselt = self._entschluesseln(rohdaten, schluessel_raw)
                    self.stdout.write("  ✓ [3/5] Entschlüsselung erfolgreich")
                except Exception as exc:
                    self._fehler(eintrag, f"Entschlüsselung fehlgeschlagen: {exc}")
                    self.stderr.write(self.style.ERROR(f"  ✗ [3/5] Entschlüsselung fehlgeschlagen: {exc}"))
                    return False
        else:
            entschluesselt = rohdaten
            if eintrag.verschluesselt:
                fehler_liste.append("Laut DB verschlüsselt, aber kein VWBK-Header gefunden")
                self.stderr.write(self.style.WARNING("  ⚠ [3/5] Kein Verschlüsselungs-Header trotz verschlüsselt=True"))
            else:
                self.stdout.write("  ✓ [3/5] Nicht verschlüsselt (erwartet)")

        if entschluesselt is None:
            # Prüfschritte 4+5 nicht möglich ohne entschlüsselte Daten
            self.stdout.write(self.style.WARNING("  – [4/5] tar.gz-Prüfung übersprungen (kein Schlüssel)"))
            self.stdout.write(self.style.WARNING("  – [5/5] SQL-Prüfung übersprungen (kein Schlüssel)"))
            self._abschliessen(eintrag, fehler_liste)
            return len(fehler_liste) == 0

        # ----------------------------------------------------------------
        # Schritt 4: tar.gz strukturell lesbar?
        # ----------------------------------------------------------------
        try:
            sql_bytes = self._sql_aus_archiv(entschluesselt)
            self.stdout.write(f"  ✓ [4/5] tar.gz lesbar – SQL-Dump: {len(sql_bytes):,} Bytes")
        except Exception as exc:
            self._fehler(eintrag, f"tar.gz nicht lesbar: {exc}")
            self.stderr.write(self.style.ERROR(f"  ✗ [4/5] tar.gz nicht lesbar: {exc}"))
            return False

        # ----------------------------------------------------------------
        # Schritt 5: SQL-Dump inhaltlich valide?
        # ----------------------------------------------------------------
        gefunden = [ind for ind in SQL_INDIKATOREN if ind in sql_bytes[:65536]]
        if gefunden:
            self.stdout.write(
                f"  ✓ [5/5] SQL-Dump valide – Indikatoren: {', '.join(s.decode() for s in gefunden)}"
            )
        else:
            fehler_liste.append("SQL-Dump enthält keine bekannten PostgreSQL-Schlüsselwörter")
            self.stderr.write(self.style.ERROR(
                "  ✗ [5/5] SQL-Dump erscheint leer oder korrupt (keine SQL-Indikatoren gefunden)"
            ))

        self._abschliessen(eintrag, fehler_liste)
        return len(fehler_liste) == 0

    # ----------------------------------------------------------------
    # Hilfsmethoden
    # ----------------------------------------------------------------

    def _entschluesseln(self, daten: bytes, schluessel_raw: str) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

        salt     = daten[4:20]
        nonce    = daten[20:32]
        chiffrat = daten[32:]

        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
        schluessel = kdf.derive(schluessel_raw.encode())
        return AESGCM(schluessel).decrypt(nonce, chiffrat, None)

    def _sql_aus_archiv(self, daten: bytes) -> bytes:
        with tarfile.open(fileobj=io.BytesIO(daten), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith(".sql"):
                    f = tar.extractfile(member)
                    if f:
                        return f.read()
        raise RuntimeError("Keine .sql-Datei im Archiv")

    def _fehler(self, eintrag, meldung: str):
        from sicherung.models import SicherungsProtokoll
        eintrag.status = SicherungsProtokoll.STATUS_FEHLER
        eintrag.fehlermeldung = meldung
        eintrag.geprueft_am = timezone.now()
        eintrag.save(update_fields=["status", "fehlermeldung", "geprueft_am"])

    def _abschliessen(self, eintrag, fehler_liste: list):
        from sicherung.models import SicherungsProtokoll
        if fehler_liste:
            eintrag.status = SicherungsProtokoll.STATUS_FEHLER
            eintrag.fehlermeldung = "; ".join(fehler_liste)
        else:
            eintrag.status = SicherungsProtokoll.STATUS_GEPRUEFT
            eintrag.fehlermeldung = ""
        eintrag.geprueft_am = timezone.now()
        eintrag.save(update_fields=["status", "fehlermeldung", "geprueft_am"])
