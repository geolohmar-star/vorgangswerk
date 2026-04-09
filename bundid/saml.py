# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
SAML-Hilfsfunktionen für die BundID-Integration.

Der BundID-Simulator signiert SAML-Responses NICHT – daher ist im
Test-Modus keine Zertifikatsvalidierung nötig.
In Produktion gegen test.id.bund.de / id.bund.de wird eine signierte
Response mit echtem Zertifikat verwendet.
"""
import base64
import uuid
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from django.conf import settings


SAML_NAMESPACES = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml":  "urn:oasis:names:tc:SAML:2.0:assertion",
}

# SAML-Attribut-OIDs des BundID-Simulators
ATTR_BPK2      = "urn:oid:1.3.6.1.4.1.25484.494450.3"
ATTR_VORNAME   = "urn:oid:2.5.4.42"
ATTR_NACHNAME  = "urn:oid:2.5.4.4"
ATTR_MAIL      = "urn:oid:0.9.2342.19200300.100.1.3"
ATTR_GEBURTSTAG = "urn:oid:1.2.40.0.10.2.1.1.55"
ATTR_QAA_LEVEL = "urn:oid:1.2.40.0.10.2.1.1.261.94"


def _sp_entity_id():
    return getattr(settings, "BUNDID_SP_ENTITY_ID", "vorgangswerk")


def _idp_sso_url():
    return getattr(settings, "BUNDID_IDP_SSO_URL", "http://localhost:8089/saml")


def _acs_url(request):
    return request.build_absolute_uri("/bundid/acs/")


def build_authn_request(request) -> tuple[str, str]:
    """Erstellt einen SAML AuthnRequest für HTTP-POST-Binding.

    Gibt ein Tupel (idp_url, saml_request_b64) zurück – der Aufrufer
    rendert eine Auto-Submit-Form, die den SAMLRequest per POST an den IDP sendet.
    """
    request_id = "_" + uuid.uuid4().hex
    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    acs = _acs_url(request)
    sp_entity = _sp_entity_id()

    xml = (
        f'<samlp:AuthnRequest'
        f' xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
        f' xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"'
        f' ID="{request_id}"'
        f' Version="2.0"'
        f' IssueInstant="{issue_instant}"'
        f' AssertionConsumerServiceURL="{acs}"'
        f' ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        f'<saml:Issuer>{sp_entity}</saml:Issuer>'
        f'</samlp:AuthnRequest>'
    )

    # Für POST-Binding: einfaches Base64 (kein DEFLATE)
    encoded = base64.b64encode(xml.encode("utf-8")).decode("utf-8")
    return _idp_sso_url(), encoded


def parse_saml_response(saml_response_b64: str) -> dict:
    """Parst eine Base64-kodierte SAML-Response und gibt ein Dict
    mit den BundID-Attributen zurück.

    Im Simulator-Modus wird die Signatur nicht geprüft.
    """
    try:
        xml_bytes = base64.b64decode(saml_response_b64)
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        raise ValueError(f"SAML-Response konnte nicht geparst werden: {e}")

    # Status prüfen
    status_el = root.find(
        ".//samlp:Status/samlp:StatusCode",
        {"samlp": "urn:oasis:names:tc:SAML:2.0:protocol"},
    )
    if status_el is not None:
        status_value = status_el.get("Value", "")
        if "Success" not in status_value:
            raise ValueError(f"SAML-Authentifizierung fehlgeschlagen: {status_value}")

    # Attribute extrahieren
    attrs = {}
    for attr_el in root.iter("{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"):
        name = attr_el.get("Name", "")
        values = [
            v.text or ""
            for v in attr_el.iter("{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue")
        ]
        if values:
            attrs[name] = values[0] if len(values) == 1 else values

    # NameID (Fallback-Identifier)
    name_id_el = root.find(
        ".//{urn:oasis:names:tc:SAML:2.0:assertion}NameID"
    )
    name_id = name_id_el.text if name_id_el is not None else None

    return {
        "bpk2":       attrs.get(ATTR_BPK2) or name_id,
        "vorname":    attrs.get(ATTR_VORNAME, ""),
        "nachname":   attrs.get(ATTR_NACHNAME, ""),
        "email":      attrs.get(ATTR_MAIL, ""),
        "geburtstag": attrs.get(ATTR_GEBURTSTAG, ""),
        "qaa_level":  attrs.get(ATTR_QAA_LEVEL, ""),
        "raw":        attrs,
    }
