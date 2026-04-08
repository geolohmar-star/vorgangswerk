# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Management-Command: IMAP-Worker – pollt eingehende E-Mails in einer Endlosschleife.

Verwendung:
    python manage.py email_worker                    # Endlosschleife (fuer Docker-Worker)
    python manage.py email_worker --einmalig         # Einmalig abrufen und beenden
    python manage.py email_worker --intervall 120    # Alle 2 Minuten (Standard: 60s)
"""
import email
import email.policy
import imaplib
import logging
import time
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


def _dekodiere_header(wert):
    """Dekodiert einen E-Mail-Header-Wert (MIME-Encoded-Words)."""
    if not wert:
        return ""
    teile = decode_header(wert)
    ergebnis = []
    for teil, charset in teile:
        if isinstance(teil, bytes):
            try:
                ergebnis.append(teil.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                ergebnis.append(teil.decode("latin-1", errors="replace"))
        else:
            ergebnis.append(teil)
    return "".join(ergebnis)


def _hole_text_und_html(msg):
    """Extrahiert Text- und HTML-Body aus einer E-Mail."""
    text = ""
    html = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = part.get_content_disposition() or ""
            if "attachment" in cd:
                continue
            if ct == "text/plain" and not text:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
            elif ct == "text/html" and not html:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="replace")
    else:
        ct = msg.get_content_type()
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        dekodiert = payload.decode(charset, errors="replace")
        if ct == "text/plain":
            text = dekodiert
        elif ct == "text/html":
            html = dekodiert
    return text, html


def _hole_anhaenge(msg):
    """Gibt Liste von (dateiname, dateityp, inhalt_bytes) fuer alle Anhaenge zurueck."""
    anhaenge = []
    if not msg.is_multipart():
        return anhaenge
    for part in msg.walk():
        cd = part.get_content_disposition() or ""
        if "attachment" not in cd:
            continue
        dateiname = _dekodiere_header(part.get_filename() or "anhang")
        dateityp = part.get_content_type() or "application/octet-stream"
        inhalt = part.get_payload(decode=True) or b""
        anhaenge.append((dateiname, dateityp, inhalt))
    return anhaenge


def importiere_emails():
    """Stellt eine IMAP-Verbindung her und importiert neue E-Mails.

    Gibt die Anzahl der neu importierten E-Mails zurueck.
    """
    # Lazy import – erst hier importieren damit Django vollstaendig geladen ist
    from kommunikation.models import Benachrichtigung, EingehendeEmail, EmailAnhang

    host = getattr(settings, "IMAP_HOST", "")
    port = int(getattr(settings, "IMAP_PORT", 993))
    user = getattr(settings, "IMAP_USER", "")
    password = getattr(settings, "IMAP_PASSWORD", "")
    ordner = getattr(settings, "IMAP_ORDNER", "INBOX")
    benachrichtige_staff = getattr(settings, "IMAP_BENACHRICHTIGE_STAFF", True)

    if not host or not user or not password:
        logger.debug("IMAP nicht konfiguriert – ueberspringe.")
        return 0

    neu_importiert = 0

    try:
        # Verbindung aufbauen (SSL)
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        conn.select(ordner, readonly=False)

        # Alle ungelesenen Nachrichten
        _, nachrichtenliste = conn.search(None, "UNSEEN")
        ids = nachrichtenliste[0].split() if nachrichtenliste[0] else []

        for msg_id_bytes in ids:
            try:
                _, data = conn.fetch(msg_id_bytes, "(RFC822)")
                if not data or not data[0]:
                    continue
                raw = data[0][1]
                msg = email.message_from_bytes(raw, policy=email.policy.compat32)

                # Message-ID
                message_id = (msg.get("Message-ID") or "").strip()
                if not message_id:
                    # Fallback: Hash aus Absender+Datum+Betreff
                    import hashlib
                    message_id = "local-" + hashlib.md5(
                        (msg.get("From", "") + msg.get("Date", "") + msg.get("Subject", "")).encode()
                    ).hexdigest()

                # Deduplizierung
                if EingehendeEmail.objects.filter(message_id=message_id).exists():
                    continue

                # Header dekodieren
                betreff = _dekodiere_header(msg.get("Subject", ""))
                von_raw = msg.get("From", "")
                absender_name, absender_email = parseaddr(von_raw)
                absender_name = _dekodiere_header(absender_name)
                empfaenger_email = parseaddr(msg.get("To", ""))[1]

                # Datum parsen
                datum_str = msg.get("Date", "")
                try:
                    empfangen_am = parsedate_to_datetime(datum_str)
                    if timezone.is_naive(empfangen_am):
                        empfangen_am = timezone.make_aware(empfangen_am)
                except Exception:
                    empfangen_am = timezone.now()

                # Body
                inhalt_text, inhalt_html = _hole_text_und_html(msg)

                # Speichern
                neue_email = EingehendeEmail.objects.create(
                    message_id=message_id,
                    betreff=betreff[:500],
                    absender_name=absender_name[:255],
                    absender_email=absender_email[:254],
                    empfaenger_email=empfaenger_email[:254],
                    empfangen_am=empfangen_am,
                    inhalt_text=inhalt_text,
                    inhalt_html=inhalt_html,
                    status=EingehendeEmail.STATUS_NEU,
                )

                # Anhaenge speichern
                for dateiname, dateityp, inhalt in _hole_anhaenge(msg):
                    EmailAnhang.objects.create(
                        email=neue_email,
                        dateiname=dateiname[:255],
                        dateityp=dateityp[:100],
                        inhalt=inhalt,
                        groesse_bytes=len(inhalt),
                    )

                neu_importiert += 1
                logger.info("E-Mail importiert: %s von %s", betreff[:80], absender_email)

                # Postbuch-Eintrag (Eingang)
                try:
                    from post.models import Posteintrag
                    Posteintrag.objects.create(
                        datum=empfangen_am.date(),
                        richtung=Posteintrag.RICHTUNG_EINGANG,
                        typ=Posteintrag.TYP_EMAIL,
                        absender_empfaenger=(absender_name or absender_email)[:300],
                        betreff=betreff[:500],
                        eingehende_email=neue_email,
                    )
                except Exception as exc:
                    logger.warning("Postbuch-Eintrag fehlgeschlagen: %s", exc)

                # Staff-Benutzer benachrichtigen
                if benachrichtige_staff:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    for staff_user in User.objects.filter(is_staff=True, is_active=True):
                        Benachrichtigung.erstelle(
                            user=staff_user,
                            titel=f"Neue E-Mail: {betreff[:100] or '(kein Betreff)'}",
                            nachricht=f"Von: {absender_name or absender_email}\n{inhalt_text[:300]}",
                            typ=Benachrichtigung.TYP_EMAIL,
                            link=f"/kommunikation/email/{neue_email.pk}/",
                        )

            except Exception as exc:
                logger.error("Fehler beim Importieren einer E-Mail: %s", exc)
                continue

        conn.logout()

    except imaplib.IMAP4.error as exc:
        logger.error("IMAP-Fehler: %s", exc)
    except OSError as exc:
        logger.error("Netzwerkfehler beim IMAP-Abruf: %s", exc)

    return neu_importiert


class Command(BaseCommand):
    help = "IMAP-Worker: Pollt eingehende E-Mails (Endlosschleife fuer Docker-Worker)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--einmalig",
            action="store_true",
            help="Einmalig abrufen und beenden (kein Loop)",
        )
        parser.add_argument(
            "--intervall",
            type=int,
            default=60,
            help="Wartezeit zwischen Abrufen in Sekunden (Standard: 60)",
        )

    def handle(self, *args, **options):
        einmalig = options["einmalig"]
        intervall = options["intervall"]

        self.stdout.write("IMAP-Worker gestartet.")

        if einmalig:
            anzahl = importiere_emails()
            self.stdout.write(f"{anzahl} E-Mail(s) importiert.")
            return

        # Endlosschleife fuer Docker-Worker
        while True:
            try:
                anzahl = importiere_emails()
                if anzahl:
                    self.stdout.write(f"{anzahl} neue E-Mail(s) importiert.")
            except Exception as exc:
                logger.error("Unerwarteter Fehler im IMAP-Worker: %s", exc)

            time.sleep(intervall)
