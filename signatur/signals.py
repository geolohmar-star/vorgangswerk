# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .crypto import get_session_schluessel, privaten_schluessel_aus_session

logger = logging.getLogger(__name__)

_passwort_hash_cache: dict[int, str] = {}


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def schluessel_bei_passwortaenderung_neu_verschluesseln(sender, instance, created, **kwargs):
    if created:
        _passwort_hash_cache[instance.pk] = instance.password
        return

    letzter_hash = _passwort_hash_cache.get(instance.pk)
    aktueller_hash = instance.password
    _passwort_hash_cache[instance.pk] = aktueller_hash

    if letzter_hash is None or letzter_hash == aktueller_hash:
        return

    user = instance
    from .models import MitarbeiterZertifikat

    try:
        zert = MitarbeiterZertifikat.objects.filter(user=user, status="aktiv").first()
        if not zert or not zert.key_ist_verschluesselt:
            return

        privater_schluessel_pem = privaten_schluessel_aus_session(zert)
        if not privater_schluessel_pem:
            logger.warning(
                "Passwortaenderung fuer %s ohne aktive Session – "
                "Schluessel wird beim naechsten Login neu verschluesselt.",
                user.username,
            )
            zert.privater_schluessel_verschluesselt = None
            zert.schluessel_salt = ""
            zert.schluessel_nonce = ""
            zert.save(update_fields=[
                "privater_schluessel_verschluesselt",
                "schluessel_salt",
                "schluessel_nonce",
            ])
            return

        dk_hex = get_session_schluessel()
        if dk_hex:
            import os
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            salt = bytes.fromhex(zert.schluessel_salt)
            nonce = os.urandom(12)
            aes_schluessel = bytes.fromhex(dk_hex)
            aesgcm = AESGCM(aes_schluessel)
            verschluesselt = aesgcm.encrypt(nonce, privater_schluessel_pem.encode("utf-8"), None)
            zert.schluessel_nonce = nonce.hex()
            zert.privater_schluessel_verschluesselt = verschluesselt
            zert.save(update_fields=["privater_schluessel_verschluesselt", "schluessel_nonce"])
            logger.info("Privater Schluessel von %s nach Passwortaenderung neu verschluesselt.", user.username)

    except Exception as exc:
        logger.error("Fehler bei Schluessel-Re-Verschluesselung fuer %s: %s", getattr(user, "username", "?"), exc)
