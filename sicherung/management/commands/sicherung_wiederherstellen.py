# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Management-Command: Datenbank aus einer Sicherungsdatei wiederherstellen.

Verwendung:
    python manage.py sicherung_wiederherstellen --pk 42
    python manage.py sicherung_wiederherstellen --datei /app/sicherungen/2026-04-06_datenbank.tar.gz

WARNUNG: Ueberschreibt die laufende Datenbank vollstaendig.
"""
import gzip
import io
import logging
import os
import subprocess
import tarfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

MAGIC = b"VWBK"


def _entschluesseln(daten: bytes) -> bytes:
    """Entschluesselt AES-256-GCM gesicherte Daten (Format: MAGIC+salt+nonce+chiffrat)."""
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    if not daten.startswith(MAGIC):
        raise ValueError("Datei ist nicht verschluesselt (kein VWBK-Header).")

    schluessel_raw = getattr(settings, "VERSCHLUESSEL_KEY", "")
    if not schluessel_raw:
        raise ValueError("VERSCHLUESSEL_KEY nicht gesetzt – Entschluesselung nicht moeglich.")

    salt   = daten[4:20]
    nonce  = daten[20:32]
    chiffrat = daten[32:]

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    schluessel = kdf.derive(schluessel_raw.encode())

    aesgcm = AESGCM(schluessel)
    return aesgcm.decrypt(nonce, chiffrat, None)


def _sql_aus_archiv(pfad: str) -> bytes:
    """Liest den SQL-Dump aus einer .tar.gz-Sicherungsdatei."""
    with open(pfad, "rb") as f:
        rohdaten = f.read()

    # Verschluesselt?
    if rohdaten.startswith(MAGIC):
        rohdaten = _entschluesseln(rohdaten)

    # tar.gz entpacken
    with tarfile.open(fileobj=io.BytesIO(rohdaten), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".sql"):
                f = tar.extractfile(member)
                if f:
                    return f.read()

    raise RuntimeError("Keine .sql-Datei im Archiv gefunden.")


def wiederherstellen_aus_datei(pfad: str, stdout=None) -> None:
    """Stellt die Datenbank aus einer Sicherungsdatei wieder her."""
    def log(msg):
        logger.info(msg)
        if stdout:
            stdout.write(msg + "\n")

    log(f"Lese Archiv: {pfad}")
    sql_bytes = _sql_aus_archiv(pfad)
    log(f"SQL-Dump extrahiert: {len(sql_bytes):,} Bytes")

    db = settings.DATABASES["default"]
    env = os.environ.copy()
    env["PGPASSWORD"] = db.get("PASSWORD", "")

    psql_basis = [
        "psql",
        "--no-password",
        f"--host={db.get('HOST', 'db')}",
        f"--port={db.get('PORT', '5432')}",
        f"--username={db.get('USER', 'vorgangswerk')}",
    ]
    db_name = db.get("NAME", "vorgangswerk")

    # Bestehende Verbindungen trennen + DB neu erstellen
    log("Trenne bestehende Verbindungen...")
    subprocess.run(
        psql_basis + ["postgres", "-c",
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname='{db_name}' AND pid <> pg_backend_pid();"
        ],
        env=env, capture_output=True,
    )

    log("Lösche und erstelle Datenbank neu...")
    subprocess.run(psql_basis + ["postgres", "-c", f"DROP DATABASE IF EXISTS {db_name};"],
                   env=env, capture_output=True, check=True)
    subprocess.run(psql_basis + ["postgres", "-c", f"CREATE DATABASE {db_name} OWNER {db.get('USER', 'vorgangswerk')};"],
                   env=env, capture_output=True, check=True)

    # SQL einspielen
    log("Spiele SQL-Dump ein...")
    result = subprocess.run(
        psql_basis + [db_name],
        input=sql_bytes,
        env=env,
        capture_output=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql Fehler: {result.stderr.decode()[:500]}")

    log("Wiederherstellung abgeschlossen.")


class Command(BaseCommand):
    help = "Datenbank aus Sicherungsdatei wiederherstellen (WARNUNG: ueberschreibt aktuelle DB)"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--pk", type=int, help="Primaerschluessel des SicherungsProtokoll-Eintrags")
        group.add_argument("--datei", type=str, help="Absoluter Pfad zur Sicherungsdatei")

    def handle(self, *args, **options):
        from sicherung.management.commands.sicherung_erstellen import SICHERUNGS_DIR

        if options.get("pk"):
            from sicherung.models import SicherungsProtokoll
            try:
                protokoll = SicherungsProtokoll.objects.get(pk=options["pk"])
            except SicherungsProtokoll.DoesNotExist:
                raise CommandError(f"Sicherung mit PK {options['pk']} nicht gefunden.")
            pfad = str(SICHERUNGS_DIR / protokoll.dateiname)
        else:
            pfad = options["datei"]

        if not os.path.exists(pfad):
            raise CommandError(f"Datei nicht gefunden: {pfad}")

        self.stdout.write(self.style.WARNING(
            f"\nWARNUNG: Die Datenbank wird vollstaendig ueberschrieben!\nDatei: {pfad}\n"
        ))

        try:
            wiederherstellen_aus_datei(pfad, stdout=self.stdout)
            self.stdout.write(self.style.SUCCESS("Wiederherstellung erfolgreich."))
        except Exception as exc:
            raise CommandError(f"Wiederherstellung fehlgeschlagen: {exc}")
