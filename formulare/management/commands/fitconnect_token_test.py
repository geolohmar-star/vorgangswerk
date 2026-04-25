# SPDX-License-Identifier: EUPL-1.2
"""Management-Command: FIT-Connect OAuth2 Token testen.

Verwendung:
    docker compose exec web python manage.py fitconnect_token_test
    docker compose exec web python manage.py fitconnect_token_test --refresh
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "FIT-Connect OAuth2 Token gegen FITKO-Server testen"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Cache ignorieren und Token neu anfordern",
        )

    def handle(self, *args, **options):
        from formulare.fitconnect_client import (
            FitConnectConfigError,
            FitConnectTokenError,
            get_token,
            token_info,
        )

        self.stdout.write("\n─── FIT-Connect Token-Test ───\n")

        try:
            info = token_info()
        except FitConnectConfigError as exc:
            self.stderr.write(self.style.ERROR(f"Konfigurationsfehler: {exc}"))
            self.stderr.write(
                "Bitte in .env setzen:\n"
                "  FITCONNECT_CLIENT_ID=<ihre-client-id>\n"
                "  FITCONNECT_CLIENT_SECRET=<ihr-secret>\n"
            )
            return

        self.stdout.write(f"  Client-ID:      {info['client_id']}")
        self.stdout.write(f"  Token-URL:      {info['token_url']}")
        self.stdout.write(f"  Submission-URL: {info['submission_url']}")
        self.stdout.write(f"  Scope:          {info['scope']}")
        self.stdout.write(f"  Token gecacht:  {info['token_cached']}")
        if info["token_preview"]:
            self.stdout.write(f"  Token-Vorschau: {info['token_preview']}")
        self.stdout.write("")

        try:
            token = get_token(force_refresh=options["refresh"])
            self.stdout.write(self.style.SUCCESS(
                f"✓ Token erfolgreich erhalten ({len(token)} Zeichen)"
            ))
            self.stdout.write(f"  Vorschau: {token[:20]}…\n")
        except FitConnectConfigError as exc:
            self.stderr.write(self.style.ERROR(f"Konfigurationsfehler: {exc}"))
        except FitConnectTokenError as exc:
            self.stderr.write(self.style.ERROR(f"Token-Fehler: {exc}"))
            self.stderr.write(
                "\nMögliche Ursachen:\n"
                "  - Client-ID oder Secret falsch\n"
                "  - Testumgebung nicht erreichbar (Netzwerk/Firewall)\n"
                "  - FITCONNECT_TOKEN_URL falsch gesetzt\n"
            )
