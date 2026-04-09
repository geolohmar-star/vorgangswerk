# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: Datensicherung erstellen (BSI CON.3)

Nutzung:
    python manage.py sicherung_erstellen
    python manage.py sicherung_erstellen --typ datenbank
    python manage.py sicherung_erstellen --typ komplett --rhythmus monatlich
    python manage.py sicherung_erstellen --trocken   (kein Schreiben, nur Test)

Aufbewahrungsfristen (automatische Bereinigung):
    Täglich:     7 Sicherungen
    Wöchentlich: 4 Sicherungen
    Monatlich:   12 Sicherungen
    Manuell:     unbegrenzt
"""
import gzip
import hashlib
import io
import logging
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger("vorgangswerk.sicherung")

# Sicherungsverzeichnis (in Docker: gemountetes Volume)
SICHERUNGS_DIR = Path(getattr(settings, "SICHERUNGS_DIR", "/app/sicherungen"))

# Aufbewahrungsfristen
AUFBEWAHRUNG = {
    "taeglich":     7,
    "woechentlich": 4,
    "monatlich":    12,
    "manuell":      0,   # 0 = unbegrenzt
}


class Command(BaseCommand):
    help = "Erstellt eine BSI-konforme Datensicherung (CON.3)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--typ",
            choices=["datenbank", "dateien", "komplett"],
            default="komplett",
            help="Art der Sicherung (Standard: komplett)",
        )
        parser.add_argument(
            "--rhythmus",
            choices=["taeglich", "woechentlich", "monatlich", "manuell"],
            default="manuell",
            help="Rhythmus für Aufbewahrungsregel (Standard: manuell)",
        )
        parser.add_argument(
            "--trocken",
            action="store_true",
            help="Trockenlauf – keine Dateien schreiben, kein DB-Eintrag",
        )

    def handle(self, *args, **options):
        typ      = options["typ"]
        rhythmus = options["rhythmus"]
        trocken  = options["trocken"]

        if trocken:
            self.stdout.write(self.style.WARNING("TROCKENLAUF – keine Dateien werden geschrieben"))

        SICHERUNGS_DIR.mkdir(parents=True, exist_ok=True)

        zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S")
        dateiname   = f"vw_{typ}_{rhythmus}_{zeitstempel}.tar.gz"
        if _verschluesselung_aktiv():
            dateiname += ".enc"
        zieldatei = SICHERUNGS_DIR / dateiname

        self.stdout.write(f"Sicherung: {dateiname}")
        self.stdout.write(f"Typ: {typ}  |  Rhythmus: {rhythmus}  |  Ziel: {zieldatei}")

        from sicherung.models import SicherungsProtokoll

        protokoll = SicherungsProtokoll(
            typ=typ,
            rhythmus=rhythmus,
            dateiname=dateiname,
            dateipfad=str(zieldatei),
            verschluesselt=_verschluesselung_aktiv(),
            erstellt_von="system",
        )

        try:
            puffer = io.BytesIO()

            with tarfile.open(fileobj=puffer, mode="w:gz") as tar:
                if typ in ("datenbank", "komplett"):
                    self.stdout.write("  → Datenbank-Dump…")
                    dump = _datenbank_dump()
                    info = tarfile.TarInfo(name="datenbank.sql")
                    info.size = len(dump)
                    tar.addfile(info, io.BytesIO(dump))
                    self.stdout.write(f"     {len(dump):,} Bytes")

                if typ in ("dateien", "komplett"):
                    staticfiles = Path(settings.STATIC_ROOT)
                    if staticfiles.exists():
                        self.stdout.write("  → Statische Dateien…")
                        tar.add(str(staticfiles), arcname="staticfiles")

            inhalt = puffer.getvalue()

            # Verschlüsseln falls Schlüssel vorhanden
            if _verschluesselung_aktiv():
                self.stdout.write("  → AES-256-GCM Verschlüsselung…")
                inhalt = _verschluesseln(inhalt)

            # SHA-256 Prüfsumme
            pruefsumme = hashlib.sha256(inhalt).hexdigest()
            protokoll.sha256_pruefsumme = pruefsumme
            protokoll.groesse_bytes = len(inhalt)

            if not trocken:
                zieldatei.write_bytes(inhalt)
                # Prüfsummen-Datei ablegen
                (SICHERUNGS_DIR / (dateiname + ".sha256")).write_text(
                    f"{pruefsumme}  {dateiname}\n"
                )

            protokoll.status = SicherungsProtokoll.STATUS_OK

            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Sicherung erstellt: {dateiname}\n"
                f"  Größe:      {protokoll.groesse_lesbar}\n"
                f"  SHA-256:    {pruefsumme[:16]}…\n"
                f"  Verschlüsselt: {'ja' if protokoll.verschluesselt else 'NEIN – VERSCHLUESSEL_KEY nicht gesetzt!'}"
            ))

        except Exception as exc:
            protokoll.status     = SicherungsProtokoll.STATUS_FEHLER
            protokoll.fehlermeldung = str(exc)
            logger.exception("Sicherung fehlgeschlagen: %s", exc)
            self.stderr.write(self.style.ERROR(f"FEHLER: {exc}"))

        finally:
            if not trocken:
                protokoll.save()
                _aufbewahrung_bereinigen(rhythmus, typ)

        if protokoll.status == SicherungsProtokoll.STATUS_FEHLER:
            raise SystemExit(1)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _datenbank_dump() -> bytes:
    """PostgreSQL-Dump via pg_dump."""
    db = settings.DATABASES["default"]
    env = os.environ.copy()
    env["PGPASSWORD"] = db.get("PASSWORD", "")

    result = subprocess.run(
        [
            "pg_dump",
            "--no-password",
            "--format=plain",
            "--encoding=UTF8",
            f"--host={db.get('HOST', 'db')}",
            f"--port={db.get('PORT', '5432')}",
            f"--username={db.get('USER', 'vorgangswerk')}",
            db.get("NAME", "vorgangswerk"),
        ],
        capture_output=True,
        env=env,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump Fehler: {result.stderr.decode()[:500]}")

    return result.stdout


def _verschluesselung_aktiv() -> bool:
    return bool(getattr(settings, "VERSCHLUESSEL_KEY", ""))


def _verschluesseln(daten: bytes) -> bytes:
    """AES-256-GCM Verschlüsselung mit dem konfigurierten Schlüssel."""
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import secrets

    schluessel_raw = getattr(settings, "VERSCHLUESSEL_KEY", "")
    salt  = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    schluessel = kdf.derive(schluessel_raw.encode())

    aesgcm = AESGCM(schluessel)
    chiffrat = aesgcm.encrypt(nonce, daten, None)

    # Format: MAGIC(4) + salt(16) + nonce(12) + chiffrat
    return b"VWBK" + salt + nonce + chiffrat


def _aufbewahrung_bereinigen(rhythmus: str, typ: str):
    """Löscht überzählige Sicherungen gemäß Aufbewahrungsfrist."""
    limit = AUFBEWAHRUNG.get(rhythmus, 0)
    if limit == 0:
        return

    from sicherung.models import SicherungsProtokoll

    alte = list(
        SicherungsProtokoll.objects
        .filter(rhythmus=rhythmus, typ=typ, status__in=["ok", "geprueft"])
        .order_by("-erstellt_am")[limit:]
    )

    for eintrag in alte:
        pfad = Path(eintrag.dateipfad)
        try:
            if pfad.exists():
                pfad.unlink()
            pruef = Path(str(pfad) + ".sha256")
            if pruef.exists():
                pruef.unlink()
        except Exception as e:
            logger.warning("Konnte alte Sicherung nicht löschen: %s – %s", pfad, e)

        eintrag.geloescht_am = timezone.now()
        eintrag.save(update_fields=["geloescht_am"])

    if alte:
        logger.info("Bereinigung: %d alte Sicherung(en) gelöscht (%s/%s)", len(alte), rhythmus, typ)
