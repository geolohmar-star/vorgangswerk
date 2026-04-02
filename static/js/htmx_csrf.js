// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2026 Georg Klein
// HTMX CSRF-Token: wird automatisch bei jedem HTMX-Request gesetzt
document.addEventListener("DOMContentLoaded", function () {
    document.body.addEventListener("htmx:configRequest", function (event) {
        var meta = document.querySelector("meta[name='csrf-token']");
        if (meta) {
            event.detail.headers["X-CSRFToken"] = meta.content;
        }
    });
});
