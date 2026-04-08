# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""HTTP-Reverse-Proxy fuer den lokalen OnlyOffice Document Server.

Der Browser laedt api.js und weitere Ressourcen ueber diesen Proxy,
sodass OnlyOffice ueber den bestehenden Cloudflare-Tunnel erreichbar ist.
Kein separater oeffentlicher Port fuer OnlyOffice noetig.
"""
import logging
import urllib.request
import urllib.error

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse

logger = logging.getLogger(__name__)

# Header, die nicht weitergeleitet werden (Hop-by-Hop)
_SKIP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
})


def onlyoffice_proxy(request, pfad):
    """Leitet alle Anfragen unter /onlyoffice-proxy/* an den lokalen OO-Server weiter."""
    oo_internal = getattr(settings, "ONLYOFFICE_INTERNAL_URL", "http://localhost:8012").rstrip("/")
    ziel_url = f"{oo_internal}/{pfad}"
    if request.META.get("QUERY_STRING"):
        ziel_url += "?" + request.META["QUERY_STRING"]

    # Request-Header weiterleiten (ohne Hop-by-Hop)
    headers = {}
    for key, value in request.META.items():
        if key.startswith("HTTP_"):
            header_name = key[5:].replace("_", "-").lower()
            if header_name not in _SKIP_HEADERS:
                headers[header_name] = value
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH") and value:
            headers[key.replace("_", "-").lower()] = value

    body = request.body if request.method in ("POST", "PUT", "PATCH") else None

    req = urllib.request.Request(
        ziel_url,
        data=body,
        headers=headers,
        method=request.method,
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            status = resp.getcode()

            response = HttpResponse(resp.read(), content_type=content_type, status=status)
            # Alle relevanten Antwortheader weiterleiten (inkl. Content-Encoding fuer gzip)
            for header in (
                "Cache-Control", "ETag", "Last-Modified", "X-Content-Type-Options",
                "Content-Encoding", "Vary", "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods", "Access-Control-Allow-Headers",
            ):
                wert = resp.headers.get(header)
                if wert:
                    response[header] = wert
            return response

    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.read(), content_type=exc.headers.get("Content-Type", "text/plain"),
                            status=exc.code)
    except Exception as exc:
        logger.error("OnlyOffice-Proxy-Fehler fuer %s: %s", ziel_url, exc)
        return HttpResponse(f"Proxy-Fehler: {exc}", status=502)
