# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Kryptografische Hilfsfunktionen fuer die Signatur-App.

Schuetzt private Schluessel mit PBKDF2-HMAC-SHA256 + AES-256-GCM.
Der abgeleitete Schluessel wird NIE persistent gespeichert –
er lebt nur im Thread-Local dieser Anfrage.

Sicherheitsmodell:
  - DB-Dump allein: nutzlos (verschluesselte Blobs ohne Schluessel)
  - Session-Hijack allein: nutzlos (kein verschluesseltes Material)
  - Nur Kombination aus aktivem Login + DB ermoeglicht Entschluesselung
  - PBKDF2: 600.000 Iterationen (OWASP 2023-Empfehlung)
"""
import hashlib
import os
import threading

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SESSION_KEY = "_signatur_dk"

PBKDF2_ITERATIONEN = 600_000
PBKDF2_HASH = "sha256"
SCHLUESSELBYTES = 32
SALT_BYTES = 32
NONCE_BYTES = 12

_thread_local = threading.local()


def set_session_schluessel(dk_hex: str) -> None:
    _thread_local.dk_hex = dk_hex


def get_session_schluessel() -> str | None:
    return getattr(_thread_local, "dk_hex", None)


def clear_session_schluessel() -> None:
    if hasattr(_thread_local, "dk_hex"):
        del _thread_local.dk_hex


def leite_schluessel_ab(passwort: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        PBKDF2_HASH,
        passwort.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONEN,
        dklen=SCHLUESSELBYTES,
    )


def verschluessele_privaten_schluessel(pem: str, passwort: str) -> tuple[bytes, bytes, bytes]:
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    aes_schluessel = leite_schluessel_ab(passwort, salt)
    aesgcm = AESGCM(aes_schluessel)
    verschluesselt = aesgcm.encrypt(nonce, pem.encode("utf-8"), None)
    return verschluesselt, salt, nonce


def entschluessele_privaten_schluessel(
    verschluesselt: bytes,
    passwort_oder_dk: str | bytes,
    salt: bytes,
    nonce: bytes,
) -> str:
    if isinstance(passwort_oder_dk, str) and len(passwort_oder_dk) == SCHLUESSELBYTES * 2:
        try:
            aes_schluessel = bytes.fromhex(passwort_oder_dk)
            if len(aes_schluessel) == SCHLUESSELBYTES:
                aesgcm = AESGCM(aes_schluessel)
                pem_bytes = aesgcm.decrypt(nonce, bytes(verschluesselt), None)
                return pem_bytes.decode("utf-8")
        except Exception:
            pass
    aes_schluessel = leite_schluessel_ab(passwort_oder_dk, salt)
    aesgcm = AESGCM(aes_schluessel)
    pem_bytes = aesgcm.decrypt(nonce, bytes(verschluesselt), None)
    return pem_bytes.decode("utf-8")


def privaten_schluessel_aus_session(zert) -> str | None:
    if not zert.schluessel_salt or not zert.schluessel_nonce or not zert.privater_schluessel_verschluesselt:
        return None
    dk_hex = get_session_schluessel()
    if not dk_hex:
        return None
    try:
        salt = bytes.fromhex(zert.schluessel_salt)
        nonce = bytes.fromhex(zert.schluessel_nonce)
        return entschluessele_privaten_schluessel(
            bytes(zert.privater_schluessel_verschluesselt),
            dk_hex,
            salt,
            nonce,
        )
    except Exception:
        return None
