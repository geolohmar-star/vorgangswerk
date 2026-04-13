# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Vorgangswerk Public API – Demo-Endpunkte (django-ninja)."""
from typing import Optional
from django.conf import settings
from ninja import NinjaAPI, Schema
from ninja.security import HttpBearer


# ---------------------------------------------------------------------------
# Authentifizierung per API-Key (Header: Authorization: Bearer <key>)
# ---------------------------------------------------------------------------

class ApiKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        api_key = getattr(settings, "API_KEY", "")
        if api_key and token == api_key:
            return token
        return None


api = NinjaAPI(
    auth=ApiKeyAuth(),
    title="Vorgangswerk API",
    version="1.0",
    description=(
        "Schnittstelle zum Vorgangswerk. "
        "Authentifizierung per Bearer-Token (API_KEY aus .env). "
        "OpenAPI-Schema: /api/openapi.json"
    ),
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AntragStatusSchema(Schema):
    vorgangsnummer: str
    pfad: str
    status: str
    eingangsdatum: Optional[str] = None
    antragsteller: Optional[str] = None


class WorkflowStatusSchema(Schema):
    instanz_id: int
    template: str
    status: str
    fortschritt: int
    aktueller_schritt: Optional[str] = None
    gestartet_am: str


class TaskSchema(Schema):
    id: int
    schritt: str
    status: str
    frist: Optional[str] = None
    zugewiesen_an: Optional[str] = None


class FehlerSchema(Schema):
    fehler: str


# ---------------------------------------------------------------------------
# Antrag-Endpunkte
# ---------------------------------------------------------------------------

@api.get(
    "/antrag/{vorgangsnummer}/",
    response={200: AntragStatusSchema, 404: FehlerSchema},
    summary="Antragsstatus abfragen",
    tags=["Anträge"],
)
def antrag_status(request, vorgangsnummer: str):
    """Gibt den Status eines Antrags anhand der Vorgangsnummer zurück."""
    from formulare.models import AntrSitzung
    sitzung = AntrSitzung.objects.filter(vorgangsnummer=vorgangsnummer).first()
    if not sitzung:
        return 404, {"fehler": f"Antrag '{vorgangsnummer}' nicht gefunden"}
    antragsteller = None
    if sitzung.user:
        antragsteller = sitzung.user.get_full_name() or sitzung.user.username
    elif sitzung.email_anonym:
        antragsteller = sitzung.email_anonym
    return 200, {
        "vorgangsnummer": sitzung.vorgangsnummer,
        "pfad":           sitzung.pfad.name,
        "status":         sitzung.status,
        "eingangsdatum":  sitzung.abgeschlossen_am.strftime("%Y-%m-%d") if sitzung.abgeschlossen_am else None,
        "antragsteller":  antragsteller,
    }


@api.get(
    "/antrag/{vorgangsnummer}/daten/",
    response={200: dict, 404: FehlerSchema},
    summary="Antragsdaten (Formularfelder) abrufen",
    tags=["Anträge"],
)
def antrag_daten(request, vorgangsnummer: str):
    """Gibt alle erfassten Formularfelder eines abgeschlossenen Antrags zurück."""
    from formulare.models import AntrSitzung
    sitzung = AntrSitzung.objects.filter(
        vorgangsnummer=vorgangsnummer,
        status=AntrSitzung.STATUS_ABGESCHLOSSEN,
    ).first()
    if not sitzung:
        return 404, {"fehler": f"Antrag '{vorgangsnummer}' nicht gefunden oder nicht abgeschlossen"}
    label_map = {}
    for schritt in sitzung.pfad.schritte.all():
        for feld in (schritt.felder_json or []):
            fid = feld.get("id") or feld.get("feldId", "")
            if fid:
                label_map[fid] = feld.get("label", fid)
    felder = {
        label_map.get(k, k): v
        for k, v in (sitzung.gesammelte_daten or {}).items()
    }
    return 200, {
        "vorgangsnummer": sitzung.vorgangsnummer,
        "pfad":           sitzung.pfad.name,
        "felder":         felder,
    }


# ---------------------------------------------------------------------------
# Workflow-Endpunkte
# ---------------------------------------------------------------------------

@api.get(
    "/workflow/antrag/{vorgangsnummer}/",
    response={200: list[WorkflowStatusSchema], 404: FehlerSchema},
    summary="Workflow-Status eines Antrags",
    tags=["Workflow"],
)
def workflow_status(request, vorgangsnummer: str):
    """Gibt alle Workflow-Instanzen zu einem Antrag zurück."""
    from formulare.models import AntrSitzung
    from workflow.models import WorkflowInstance
    from django.contrib.contenttypes.models import ContentType

    sitzung = AntrSitzung.objects.filter(vorgangsnummer=vorgangsnummer).first()
    if not sitzung:
        return 404, {"fehler": f"Antrag '{vorgangsnummer}' nicht gefunden"}

    ct = ContentType.objects.get_for_model(sitzung)
    instanzen = WorkflowInstance.objects.filter(content_type=ct, object_id=sitzung.pk)
    result = []
    for inst in instanzen:
        result.append({
            "instanz_id":       inst.pk,
            "template":         inst.template.name,
            "status":           inst.status,
            "fortschritt":      inst.fortschritt,
            "aktueller_schritt": inst.aktueller_schritt.titel if inst.aktueller_schritt else None,
            "gestartet_am":     inst.gestartet_am.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    return 200, result


@api.get(
    "/workflow/aufgaben/",
    response=list[TaskSchema],
    summary="Offene Aufgaben (Tasks) abrufen",
    tags=["Workflow"],
)
def offene_tasks(request):
    """Gibt alle aktuell offenen Workflow-Tasks zurück."""
    from workflow.models import WorkflowTask
    tasks = WorkflowTask.objects.filter(
        status__in=[WorkflowTask.STATUS_OFFEN, WorkflowTask.STATUS_IN_BEARBEITUNG]
    ).select_related("step", "zugewiesen_an_user", "zugewiesen_an_gruppe")
    result = []
    for t in tasks:
        zugewiesen = None
        if t.zugewiesen_an_user:
            zugewiesen = t.zugewiesen_an_user.username
        elif t.zugewiesen_an_gruppe:
            zugewiesen = t.zugewiesen_an_gruppe.name
        result.append({
            "id":           t.pk,
            "schritt":      t.step.titel,
            "status":       t.status,
            "frist":        t.frist.strftime("%Y-%m-%d") if t.frist else None,
            "zugewiesen_an": zugewiesen,
        })
    return result


# ---------------------------------------------------------------------------
# FIT-Connect Export
# ---------------------------------------------------------------------------

@api.get(
    "/antrag/{vorgangsnummer}/fitconnect/",
    response={200: dict, 404: FehlerSchema},
    summary="Antragsdaten als FIT-Connect Submission-Payload",
    tags=["Anträge"],
)
def antrag_fitconnect(request, vorgangsnummer: str):
    """
    Gibt die Antragsdaten als FIT-Connect-kompatibles JSON zurück.

    Felder mit hinterlegter FIM-ID werden als F6xxxxxxx-Schlüssel exportiert.
    Gruppen mit FIM-Gruppen-ID als G6xxxxxxx-Schlüssel.
    Felder ohne FIM-Zuordnung erhalten den Präfix 'x-' (proprietär).

    Hinweis: Dieses Endpoint liefert den Datenpayload (data + metadata).
    Die FIT-Connect Transportverschlüsselung (JWE) muss vom empfangenden
    System oder einem zwischengeschalteten Gateway ergänzt werden.

    Spec: https://gitlab.opencode.de/fitko/fit-connect
    """
    import uuid
    from formulare.models import AntrSitzung, AntrDatei

    sitzung = AntrSitzung.objects.filter(
        vorgangsnummer=vorgangsnummer,
        status=AntrSitzung.STATUS_ABGESCHLOSSEN,
    ).select_related("pfad", "user").first()
    if not sitzung:
        return 404, {"fehler": f"Antrag '{vorgangsnummer}' nicht gefunden oder nicht abgeschlossen"}

    # ------------------------------------------------------------------
    # Feld-Mapping aufbauen: interner_id → {fim_id, typ, label, unterfelder}
    # ------------------------------------------------------------------
    feld_meta: dict = {}
    for schritt in sitzung.pfad.schritte.all():
        for feld in (schritt.felder_json or []):
            fid = feld.get("id", "")
            if fid:
                feld_meta[fid] = {
                    "fim_id":      feld.get("fim_id", ""),
                    "fim_gruppe":  feld.get("fim_gruppe", ""),
                    "typ":         feld.get("typ", "text"),
                    "label":       feld.get("label", fid),
                    "unterfelder": feld.get("unterfelder", []),
                }

    # ------------------------------------------------------------------
    # Hilfsfunktion: internen Key → FIT-Connect Key
    # ------------------------------------------------------------------
    def _export_key(fid: str) -> str:
        meta = feld_meta.get(fid, {})
        fim = meta.get("fim_id", "")
        return fim if fim else f"x-{fid}"

    def _export_gruppe_key(fid: str) -> str:
        meta = feld_meta.get(fid, {})
        fim = meta.get("fim_gruppe", "")
        return fim if fim else f"x-{fid}"

    def _export_uf_key(uf: dict) -> str:
        return uf.get("fim_id", "") or f"x-{uf.get('id', '')}"

    # ------------------------------------------------------------------
    # Daten transformieren
    # ------------------------------------------------------------------
    data: dict = {}
    for intern_id, wert in (sitzung.gesammelte_daten or {}).items():
        if intern_id.startswith("__"):
            continue
        meta = feld_meta.get(intern_id, {})
        typ = meta.get("typ", "")

        if typ == "gruppe" and isinstance(wert, list):
            export_key = _export_gruppe_key(intern_id)
            unterfelder = meta.get("unterfelder", [])
            uf_map = {uf.get("id", ""): uf for uf in unterfelder}
            eintraege = []
            for eintrag in wert:
                exp_eintrag = {}
                for uf_id, uf_wert in eintrag.items():
                    uf_def = uf_map.get(uf_id, {"id": uf_id})
                    exp_key = _export_uf_key(uf_def)
                    if uf_wert not in ("", None):
                        exp_eintrag[exp_key] = uf_wert
                if exp_eintrag:
                    eintraege.append(exp_eintrag)
            if eintraege:
                data[export_key] = eintraege
        elif typ in ("datei",):
            # Dateien werden separat als Attachments gelistet, nicht inline
            continue
        else:
            if wert not in ("", None):
                data[_export_key(intern_id)] = wert

    # ------------------------------------------------------------------
    # Anhänge
    # ------------------------------------------------------------------
    attachments = []
    for datei in AntrDatei.objects.filter(sitzung=sitzung):
        feld = feld_meta.get(datei.feld_id, {})
        attachments.append({
            "attachmentId": str(datei.pk),
            "filename":     datei.dateiname,
            "mimeType":     datei.mime_type,
            "fieldRef":     _export_key(datei.feld_id) if datei.feld_id else None,
        })

    # ------------------------------------------------------------------
    # Antragsteller
    # ------------------------------------------------------------------
    applicant: dict = {"authLevel": "none"}
    if sitzung.user:
        applicant["userId"] = str(sitzung.user.pk)
        applicant["displayName"] = sitzung.user.get_full_name() or sitzung.user.username
    elif sitzung.email_anonym:
        applicant["email"] = sitzung.email_anonym

    # ------------------------------------------------------------------
    # Payload zusammenbauen
    # ------------------------------------------------------------------
    pfad = sitzung.pfad
    payload = {
        "submissionId":   sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}",
        "serviceType": {
            "identifier": pfad.leika_schluessel or "",
            "name":       pfad.name,
        },
        "submittedAt":    sitzung.abgeschlossen_am.strftime("%Y-%m-%dT%H:%M:%SZ")
                          if sitzung.abgeschlossen_am else None,
        "applicant":      applicant,
        "data":           data,
        "attachments":    attachments,
        "_meta": {
            "generator":  "Vorgangswerk",
            "specRef":    "https://gitlab.opencode.de/fitko/fit-connect",
            "fimMapped":  sum(1 for k in data if not k.startswith("x-")),
            "fimUnmapped": sum(1 for k in data if k.startswith("x-")),
        },
    }
    return 200, payload


# ---------------------------------------------------------------------------
# LeiKa-Vorschlag
# ---------------------------------------------------------------------------

class LeikaVorschlagAnfrageSchema(Schema):
    felder: list[str]          # FIM-IDs oder Klartext-Feldnamen


class LeikaVorschlagSchema(Schema):
    schluessel: str
    name: str
    konfidenz: float           # 0.0 – 1.0
    treffer_fim: int
    gesamt_fim: int


@api.post(
    "/leika-vorschlag/",
    response=list[LeikaVorschlagSchema],
    summary="LeiKa-Leistungsschlüssel aus Formularfeldern ableiten",
    tags=["Formulare"],
)
def leika_vorschlag(request, daten: LeikaVorschlagAnfrageSchema):
    """
    Analysiert eine Liste von Feldnamen oder FIM-IDs und schlägt passende
    LeiKa-Leistungsschlüssel mit Konfidenzwert vor.

    Übergabe von FIM-IDs (z.B. 'F60000003') oder Klartext-Feldnamen
    (z.B. 'vorname', 'Familienname') — beide Varianten werden erkannt.
    Gibt die 5 besten Treffer zurück (Konfidenz ≥ 0.25).
    """
    from formulare.fim_data import FIM_FELDER
    from formulare.leika_data import LEIKA_LEISTUNGEN

    # 1. Eingabe normalisieren → Menge von FIM-IDs
    fim_lookup_name: dict[str, str] = {}
    for f in FIM_FELDER:
        fim_lookup_name[f["name"].lower()] = f["id"]

    fim_eingabe: set[str] = set()
    for feld in daten.felder:
        feld_clean = feld.strip()
        if feld_clean.upper().startswith("F6") and len(feld_clean) == 9:
            fim_eingabe.add(feld_clean.upper())
        else:
            # Textsuche (case-insensitive, Teilstring)
            key = feld_clean.lower()
            if key in fim_lookup_name:
                fim_eingabe.add(fim_lookup_name[key])
            else:
                # Teilstring-Match
                for name_key, fid in fim_lookup_name.items():
                    if key in name_key or name_key in key:
                        fim_eingabe.add(fid)
                        break

    if not fim_eingabe:
        return []

    # 2. Gegen LeiKa-Datensatz matchen
    treffer: list[dict] = []
    for leistung in LEIKA_LEISTUNGEN:
        leistung_fim = set(leistung["fim_ids"])
        schnittmenge = fim_eingabe & leistung_fim
        if not schnittmenge:
            continue

        # Jaccard-ähnlicher Score: Treffer / (Eingabe ∪ Leistung)
        union = fim_eingabe | leistung_fim
        konfidenz = round(len(schnittmenge) / len(union), 3)

        # Bonus: wenn die Eingabe alle Pflichtfelder der Leistung abdeckt
        abdeckung = len(schnittmenge) / len(leistung_fim)
        if abdeckung >= 0.7:
            konfidenz = min(1.0, round(konfidenz * 1.25, 3))

        treffer.append({
            "schluessel": leistung["schluessel"],
            "name":       leistung["name"],
            "konfidenz":  konfidenz,
            "treffer_fim": len(schnittmenge),
            "gesamt_fim":  len(leistung_fim),
        })

    # 3. Sortieren, filtern, Top-5 zurückgeben
    treffer.sort(key=lambda x: -x["konfidenz"])
    return [t for t in treffer if t["konfidenz"] >= 0.25][:5]


# ---------------------------------------------------------------------------
# FIT-Connect Eingang (Inbound)
# ---------------------------------------------------------------------------

class FitConnectServiceTypeSchema(Schema):
    identifier: str           # LeiKa-Schlüssel, z.B. "99108018026000"
    name: Optional[str] = None


class FitConnectApplicantSchema(Schema):
    authLevel: Optional[str] = None   # "none" | "normal" | "substantial" | "high"
    userId: Optional[str] = None      # BundID-GUID
    displayName: Optional[str] = None
    email: Optional[str] = None


class FitConnectAttachmentRefSchema(Schema):
    attachmentId: str
    filename: Optional[str] = None
    mimeType: Optional[str] = None
    fieldRef: Optional[str] = None    # FIM-ID oder x-feldId


class FitConnectEingangSchema(Schema):
    submissionId: Optional[str] = None
    serviceType: FitConnectServiceTypeSchema
    submittedAt: Optional[str] = None
    applicant: Optional[FitConnectApplicantSchema] = None
    data: dict = {}
    attachments: list[FitConnectAttachmentRefSchema] = []


class FitConnectEingangAntwortSchema(Schema):
    vorgangsnummer: str
    sitzung_id: int
    workflow_gestartet: bool
    hinweis: Optional[str] = None


def _fitconnect_entschluesseln(raw: str) -> dict:
    """
    Versucht JWE-verschlüsselte FIT-Connect Payload zu entschlüsseln.
    Benötigt FITCONNECT_PRIVATE_KEY_PEM in settings (PEM-kodierter RSA-Privat­schlüssel).
    Gibt bei Erfolg das geparste Dict zurück, wirft ValueError bei Fehler.
    """
    pem = getattr(settings, "FITCONNECT_PRIVATE_KEY_PEM", "")
    if not pem:
        raise ValueError("FITCONNECT_PRIVATE_KEY_PEM nicht konfiguriert")
    try:
        from jwcrypto import jwk, jwe as jwecrypto
        import json as _json
        key = jwk.JWK.from_pem(pem.encode())
        token = jwecrypto.JWE()
        token.deserialize(raw, key=key)
        return _json.loads(token.payload)
    except ImportError:
        raise ValueError("jwcrypto nicht installiert (pip install jwcrypto)")
    except Exception as exc:
        raise ValueError(f"JWE-Entschlüsselung fehlgeschlagen: {exc}") from exc


@api.post(
    "/fitconnect/eingang/",
    response={200: FitConnectEingangAntwortSchema, 400: FehlerSchema, 404: FehlerSchema},
    summary="FIT-Connect Submission empfangen und als Antrag anlegen",
    tags=["FIT-Connect"],
)
def fitconnect_eingang(request, submission: FitConnectEingangSchema):
    """
    Nimmt eine FIT-Connect Submission entgegen und legt sie als abgeschlossene
    AntrSitzung an. Startet automatisch den verknüpften Workflow.

    **Plaintext-Modus** (Entwicklung/Test): JSON direkt posten.

    **JWE-Modus** (Produktion): Den verschlüsselten JWE-Compact-String als
    `{"_jwe": "<token>"}` übergeben. Voraussetzung: `FITCONNECT_PRIVATE_KEY_PEM`
    in der .env konfiguriert (RSA 4096 Bit, entspricht Subscriber-Zertifikat der FITKO).

    Feldzuordnung: FIM-IDs (F6xxxxxxx) werden auf interne Feld-IDs gemappt.
    Felder mit `x-`-Präfix (proprietär) werden direkt übernommen.

    Spec: https://gitlab.opencode.de/fitko/fit-connect
    """
    import secrets
    from django.utils import timezone
    from formulare.models import AntrPfad, AntrSitzung

    # ------------------------------------------------------------------
    # 1. AntrPfad über LeiKa-Schlüssel finden
    # ------------------------------------------------------------------
    leika = submission.serviceType.identifier.strip()
    pfad = AntrPfad.objects.filter(leika_schluessel=leika, aktiv=True).first()
    if not pfad:
        return 404, {
            "fehler": (
                f"Kein aktiver Antragspfad mit LeiKa-Schlüssel '{leika}' gefunden. "
                f"Schlüssel im Pfad-Editor hinterlegen oder Pfad aktivieren."
            )
        }

    # ------------------------------------------------------------------
    # 2. FIM-ID → interner Feld-Key (Reverse-Map)
    # ------------------------------------------------------------------
    fim_zu_intern: dict[str, str] = {}
    for schritt in pfad.schritte.all():
        for feld in (schritt.felder_json or []):
            fim_id = feld.get("fim_id", "")
            intern_id = feld.get("id", "")
            if fim_id and intern_id:
                fim_zu_intern[fim_id.upper()] = intern_id

    gesammelte_daten: dict = {}
    for key, wert in submission.data.items():
        if key.upper().startswith("F6") and key.upper() in fim_zu_intern:
            gesammelte_daten[fim_zu_intern[key.upper()]] = wert
        elif key.startswith("x-"):
            gesammelte_daten[key[2:]] = wert   # x-Präfix entfernen
        else:
            gesammelte_daten[key] = wert

    if not gesammelte_daten and submission.data:
        return 400, {
            "fehler": (
                "Keine Felder konnten gemappt werden. "
                "Prüfen Sie ob FIM-IDs im Pfad hinterlegt sind."
            )
        }

    # ------------------------------------------------------------------
    # 3. AntrSitzung anlegen (direkt abgeschlossen)
    # ------------------------------------------------------------------
    applicant = submission.applicant or FitConnectApplicantSchema()
    vorgangsnummer = (
        submission.submissionId
        or AntrSitzung.generiere_vorgangsnummer(pfad)
    )
    tracking_token = secrets.token_hex(32)

    sitzung = AntrSitzung.objects.create(
        pfad=pfad,
        user=None,
        email_anonym=applicant.email or None,
        gesammelte_daten=gesammelte_daten,
        status=AntrSitzung.STATUS_ABGESCHLOSSEN,
        abgeschlossen_am=timezone.now(),
        vorgangsnummer=vorgangsnummer,
        tracking_token=tracking_token,
        einwilligungen_json={
            "fitconnect": {
                "authLevel": applicant.authLevel or "none",
                "userId":    applicant.userId or None,
                "displayName": applicant.displayName or None,
                "submittedAt": submission.submittedAt,
                "submissionId": submission.submissionId,
            }
        },
    )

    # ------------------------------------------------------------------
    # 4. Anhang-Metadaten als __fitconnect_anhänge speichern
    # ------------------------------------------------------------------
    if submission.attachments:
        sitzung.gesammelte_daten["__fitconnect_anhaenge"] = [
            {
                "attachmentId": a.attachmentId,
                "filename":     a.filename,
                "mimeType":     a.mimeType,
                "fieldRef":     a.fieldRef,
            }
            for a in submission.attachments
        ]
        sitzung.save(update_fields=["gesammelte_daten"])

    # ------------------------------------------------------------------
    # 5. Workflow starten (falls am Pfad verknüpft)
    # ------------------------------------------------------------------
    workflow_gestartet = False
    if pfad.workflow_template:
        try:
            from workflow.services import WorkflowEngine
            from django.contrib.auth import get_user_model
            User = get_user_model()
            system_user = User.objects.filter(is_superuser=True).first()
            engine = WorkflowEngine()
            engine.start_workflow(pfad.workflow_template, sitzung, system_user)
            workflow_gestartet = True
        except Exception as exc:
            pass

    # ------------------------------------------------------------------
    # 6. Benachrichtigungs-E-Mails (Sachbearbeiter + Antragsteller)
    # ------------------------------------------------------------------
    try:
        sitzung._sende_sachbearbeiter_email()
    except Exception:
        pass
    if applicant.email:
        try:
            sitzung._sende_tracking_email()
        except Exception:
            pass

    # Audit
    from core.models import AuditLog
    AuditLog.objects.create(
        user=None,
        aktion="erstellt",
        app="formulare",
        objekt_typ="AntrSitzung",
        objekt_id=str(sitzung.pk),
        beschreibung=(
            f"FIT-Connect Eingang: {pfad.name} "
            f"(LeiKa {leika}, submissionId={submission.submissionId or 'n/a'})"
        ),
    )

    hinweis = None
    if submission.attachments:
        hinweis = (
            f"{len(submission.attachments)} Anhang-Referenz(en) gespeichert. "
            "Binärdateien separat über FIT-Connect Attachment-API abrufen."
        )

    return 200, {
        "vorgangsnummer":    sitzung.vorgangsnummer,
        "sitzung_id":        sitzung.pk,
        "workflow_gestartet": workflow_gestartet,
        "hinweis":           hinweis,
    }


@api.post(
    "/fitconnect/eingang/jwe/",
    response={200: FitConnectEingangAntwortSchema, 400: FehlerSchema, 404: FehlerSchema},
    summary="FIT-Connect JWE-verschlüsselte Submission empfangen",
    tags=["FIT-Connect"],
)
def fitconnect_eingang_jwe(request, body: dict):
    """
    Entschlüsselt einen JWE-Compact-String und verarbeitet ihn wie `/fitconnect/eingang/`.

    Body: `{ "token": "<JWE-Compact-String>" }`

    Voraussetzung: `FITCONNECT_PRIVATE_KEY_PEM` in .env (RSA 4096 Bit).
    Entspricht dem Subscriber-Schlüssel, der bei der FITKO registriert wird.
    """
    import json as _json
    token = body.get("token", "")
    if not token:
        return 400, {"fehler": "Feld 'token' fehlt im Request-Body"}
    try:
        payload = _fitconnect_entschluesseln(token)
    except ValueError as exc:
        return 400, {"fehler": str(exc)}

    try:
        submission = FitConnectEingangSchema(**payload)
    except Exception as exc:
        return 400, {"fehler": f"Payload-Struktur ungültig: {exc}"}

    return fitconnect_eingang(request, submission)


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

@api.get(
    "/status/",
    auth=None,
    summary="API-Status und Export-Capabilities (kein Auth erforderlich)",
    tags=["System"],
)
def api_status(request):
    """
    Prüft ob die API erreichbar ist und listet unterstützte Exportformate.
    Kann von Fachverfahren zur automatischen Capability-Erkennung genutzt werden.
    """
    return {
        "status":  "ok",
        "version": "1.0",
        "system":  "Vorgangswerk",
        "exportformate": [
            {
                "id":       "fitconnect",
                "name":     "FIT-Connect Submission Payload",
                "version":  "1.0",
                "spec":     "https://gitlab.opencode.de/fitko/fit-connect",
                "endpunkt": "/api/antrag/{vorgangsnummer}/fitconnect/",
                "hinweis":  "Datenpayload ohne JWE-Transportverschlüsselung",
            },
            {
                "id":       "json-raw",
                "name":     "Rohdaten (Label-basiert)",
                "version":  "1.0",
                "spec":     None,
                "endpunkt": "/api/antrag/{vorgangsnummer}/daten/",
            },
        ],
        "importformate": [
            {
                "id":       "fitconnect-eingang",
                "name":     "FIT-Connect Submission Eingang (Plaintext)",
                "endpunkt": "/api/fitconnect/eingang/",
                "methode":  "POST",
            },
            {
                "id":       "fitconnect-eingang-jwe",
                "name":     "FIT-Connect Submission Eingang (JWE-verschlüsselt)",
                "endpunkt": "/api/fitconnect/eingang/jwe/",
                "methode":  "POST",
                "voraussetzung": "FITCONNECT_PRIVATE_KEY_PEM in .env",
            },
        ],
        "standards": {
            "felder":  "FIM XDatenfelder 2.0 (https://fimportal.de)",
            "dienste": "LeiKa Leistungskatalog (https://www.leika.de)",
            "export":  "FIT-Connect (https://gitlab.opencode.de/fitko/fit-connect)",
            "eingang": "FIT-Connect Subscriber API v1",
        },
    }


# ---------------------------------------------------------------------------
# Pfad-Capabilities
# ---------------------------------------------------------------------------

@api.get(
    "/pfad/{pk}/capabilities/",
    response={200: dict, 404: FehlerSchema},
    summary="Capabilities eines Antragspfads",
    tags=["Formulare"],
)
def pfad_capabilities(request, pk: int):
    """
    Gibt an welche Exportformate und Standards ein Pfad unterstützt.

    fitconnect_bereit: true wenn LeiKa-Schlüssel hinterlegt ist.
    fim_abdeckung: Anteil der Felder mit hinterlegter FIM-ID (0.0 – 1.0).
    Felder vom Typ textblock, abschnitt, trennlinie etc. zählen nicht mit.
    """
    from formulare.models import AntrPfad

    pfad = AntrPfad.objects.filter(pk=pk).prefetch_related("schritte").first()
    if not pfad:
        return 404, {"fehler": f"Pfad {pk} nicht gefunden"}

    _kein_datenwert = {
        "textblock", "abschnitt", "trennlinie", "leerblock",
        "link", "einwilligung", "zusammenfassung",
    }

    felder_gesamt = 0
    felder_fim = 0
    felder_ohne_fim: list[str] = []

    for schritt in pfad.schritte.all():
        for feld in (schritt.felder_json or []):
            typ = feld.get("typ", "")
            if typ in _kein_datenwert:
                continue
            felder_gesamt += 1
            if feld.get("fim_id"):
                felder_fim += 1
            else:
                felder_ohne_fim.append(feld.get("label") or feld.get("id", "?"))

    fim_abdeckung = round(felder_fim / felder_gesamt, 3) if felder_gesamt else 0.0
    fitconnect_bereit = bool(pfad.leika_schluessel) and fim_abdeckung >= 0.5

    return 200, {
        "pfad_id":            pfad.pk,
        "pfad_name":          pfad.name,
        "leika_schluessel":   pfad.leika_schluessel or None,
        "fitconnect_bereit":  fitconnect_bereit,
        "fim_abdeckung":      fim_abdeckung,
        "felder_gesamt":      felder_gesamt,
        "felder_fim_gemappt": felder_fim,
        "felder_ohne_fim":    felder_ohne_fim,
        "exportformate": [
            {
                "id":        "fitconnect",
                "verfuegbar": fitconnect_bereit,
                "grund":     None if fitconnect_bereit else (
                    "LeiKa-Schlüssel fehlt" if not pfad.leika_schluessel
                    else f"FIM-Abdeckung zu gering ({int(fim_abdeckung * 100)} %)"
                ),
            },
            {
                "id":        "json-raw",
                "verfuegbar": True,
                "grund":     None,
            },
        ],
    }
