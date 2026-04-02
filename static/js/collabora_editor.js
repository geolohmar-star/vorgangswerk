// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2026 Georg Klein
// Collabora Online Editor – WOPI-Integration

(function () {
    "use strict";

    var wopiSrc = JSON.parse(document.getElementById("wopi-src").textContent);
    var wopiToken = JSON.parse(document.getElementById("wopi-token").textContent);
    var collaboraUrl = JSON.parse(document.getElementById("collabora-url").textContent);
    var detailUrl = document.getElementById("detail-url").dataset.url;

    // ---------------------------------------------------------------------------
    // Collabora-Frame initialisieren
    // Collabora erwartet: POST an editor-URL mit wopiSrc + access_token als
    // Form-Parameter (hidden form submit in iframe)
    // ---------------------------------------------------------------------------
    function starteEditor() {
        var frame = document.getElementById("collabora-frame");

        // Hilfsdokument erzeugen das ein Form-POST in den iframe ausfuehrt
        // (Collabora Online WOPI erfordert POST mit access_token als Form-Feld)
        var formContainer = document.createElement("div");
        formContainer.style.display = "none";
        document.body.appendChild(formContainer);

        var form = document.createElement("form");
        form.method = "POST";
        // Collabora-Editor-URL mit wopiSrc als Query-Parameter
        form.action = collaboraUrl + "/browser/dist/cool.html?WOPISrc=" + encodeURIComponent(wopiSrc);
        form.target = "collabora-frame";
        form.enctype = "multipart/form-data";

        var tokenInput = document.createElement("input");
        tokenInput.type = "hidden";
        tokenInput.name = "access_token";
        tokenInput.value = wopiToken;
        form.appendChild(tokenInput);

        formContainer.appendChild(form);
        form.submit();

        // Aufraeum
        setTimeout(function () {
            document.body.removeChild(formContainer);
        }, 1000);
    }

    // ---------------------------------------------------------------------------
    // PostMessage von Collabora empfangen (u.a. "App_LoadingStatus")
    // ---------------------------------------------------------------------------
    window.addEventListener("message", function (event) {
        if (!collaboraUrl || !event.origin) return;
        // Nur Nachrichten vom Collabora-Server akzeptieren
        var collaboraOrigin = new URL(collaboraUrl).origin;
        if (event.origin !== collaboraOrigin) return;

        try {
            var msg = JSON.parse(event.data);
            if (msg.MessageId === "App_LoadingStatus" && msg.Values && msg.Values.Status === "Document_Loaded") {
                document.getElementById("speicher-status").textContent = "Bereit";
            }
        } catch (e) {
            // kein JSON – ignorieren
        }
    });

    // ---------------------------------------------------------------------------
    // Speichern & zurueck
    // Sendet "save" an Collabora via PostMessage, wartet kurz, leitet weiter
    // ---------------------------------------------------------------------------
    document.getElementById("btn-speichern").addEventListener("click", function () {
        var frame = document.getElementById("collabora-frame");
        var btn = this;
        btn.disabled = true;
        document.getElementById("speicher-status").textContent = "Speichern...";

        // PostMessage an Collabora: Dokument speichern
        try {
            var collaboraOrigin = new URL(collaboraUrl).origin;
            frame.contentWindow.postMessage(
                JSON.stringify({ MessageId: "Action_Save", SendNotifications: true, Values: { DontTerminateEdit: false, DontSaveIfUnmodified: false, Notify: false } }),
                collaboraOrigin
            );
        } catch (e) {
            // Falls Collabora nicht antwortet einfach weiterleiten
        }

        // Nach 2 Sekunden weiterleiten (WOPI PutFile wird async von Collabora gesendet)
        setTimeout(function () {
            window.location.href = detailUrl;
        }, 2000);
    });

    // ---------------------------------------------------------------------------
    // Editor starten
    // ---------------------------------------------------------------------------
    starteEditor();

}());
