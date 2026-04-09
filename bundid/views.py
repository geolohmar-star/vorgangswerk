# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
BundID-Views: SAML-SP Login, ACS-Callback, Metadata.
"""
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .saml import build_authn_request, parse_saml_response

logger = logging.getLogger("vorgangswerk.bundid")


def bundid_login(request):
    """Startet den BundID-Login via HTTP-POST-Binding:
    Rendert eine Auto-Submit-Form, die den SAMLRequest an den IDP schickt."""
    try:
        idp_url, saml_request_b64 = build_authn_request(request)
    except Exception as e:
        logger.error("BundID AuthnRequest fehlgeschlagen: %s", e)
        messages.error(request, "BundID-Login konnte nicht gestartet werden.")
        return redirect("login")

    from django.conf import settings
    return render(request, "bundid/post_binding.html", {
        "idp_url": idp_url,
        "saml_request": saml_request_b64,
        "relay_state": request.GET.get("next", ""),
        "domain_context": getattr(settings, "BUNDID_SP_ENTITY_ID", "vorgangswerk"),
    })


@csrf_exempt
def bundid_acs(request):
    """Assertion Consumer Service: Empfängt die SAML-Response vom IDP,
    validiert sie und loggt den Benutzer ein."""
    if request.method != "POST":
        return HttpResponse("Nur POST erlaubt.", status=405)

    saml_response = request.POST.get("SAMLResponse", "")
    if not saml_response:
        messages.error(request, "Keine SAML-Response empfangen.")
        return redirect("login")

    try:
        attrs = parse_saml_response(saml_response)
    except ValueError as e:
        logger.warning("SAML-Response ungültig: %s", e)
        messages.error(request, f"BundID-Authentifizierung fehlgeschlagen: {e}")
        return redirect("login")

    bpk2 = attrs.get("bpk2")
    if not bpk2:
        messages.error(request, "Kein Personenkennzeichen (bPK2) in der SAML-Response.")
        return redirect("login")

    # Benutzer anlegen oder abrufen (Schlüssel: bPK2)
    user = _get_or_create_user(attrs)
    if user is None:
        messages.error(request, "Benutzeranmeldung konnte nicht abgeschlossen werden.")
        return redirect("login")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    logger.info("BundID-Login erfolgreich: bPK2=%s user=%s", bpk2, user.username)

    next_url = request.GET.get("next") or request.POST.get("RelayState") or "/"
    return redirect(next_url)


def bundid_metadata(request):
    """Liefert die SAML SP-Metadaten als XML."""
    from django.conf import settings
    sp_entity = getattr(settings, "BUNDID_SP_ENTITY_ID", "vorgangswerk")
    acs_url = request.build_absolute_uri("/bundid/acs/")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{sp_entity}">
  <md:SPSSODescriptor
      AuthnRequestsSigned="false"
      WantAssertionsSigned="false"
      protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{acs_url}"
        index="1"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""

    return HttpResponse(xml, content_type="application/xml")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_or_create_user(attrs: dict) -> User | None:
    """Legt einen Django-User anhand der BundID-Attribute an oder aktualisiert ihn."""
    bpk2 = attrs.get("bpk2", "")
    vorname = attrs.get("vorname", "")
    nachname = attrs.get("nachname", "")
    email = attrs.get("email", "")

    # Username = bPK2 (eindeutig, persistent)
    username = f"bundid_{bpk2}"[:150]

    try:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": vorname[:150],
                "last_name":  nachname[:150],
                "email":      email[:254],
                "is_active":  True,
                "is_staff":   False,
            },
        )
        if not created:
            # Daten bei jedem Login aktualisieren
            updated = False
            if vorname and user.first_name != vorname:
                user.first_name = vorname[:150]
                updated = True
            if nachname and user.last_name != nachname:
                user.last_name = nachname[:150]
                updated = True
            if email and user.email != email:
                user.email = email[:254]
                updated = True
            if updated:
                user.save(update_fields=["first_name", "last_name", "email"])

        logger.info(
            "BundID-Benutzer %s (%s %s)",
            "angelegt" if created else "aktualisiert",
            vorname, nachname,
        )
        return user

    except Exception as e:
        logger.error("Fehler beim Anlegen des BundID-Benutzers: %s", e)
        return None
