// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2026 Georg Klein
// E-Mail-Detail: HTML-Body in iframe laden (CSP-sicher, kein srcdoc)

document.addEventListener("DOMContentLoaded", function () {
    var htmlEl = document.getElementById("email-html-content");
    var iframe = document.getElementById("email-iframe");
    if (!htmlEl || !iframe) return;

    var htmlContent = JSON.parse(htmlEl.textContent);
    var doc = iframe.contentDocument || iframe.contentWindow.document;
    doc.open();
    doc.write(htmlContent);
    doc.close();

    // Iframe-Hoehe an Inhalt anpassen
    setTimeout(function () {
        try {
            var hoehe = doc.body.scrollHeight;
            if (hoehe > 100) {
                iframe.style.height = hoehe + 40 + "px";
            }
        } catch (e) {
            // Cross-Origin – ignorieren
        }
    }, 300);
});
