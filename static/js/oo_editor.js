// SPDX-License-Identifier: EUPL-1.2
// OnlyOffice Editor – Speichern via Forcesave + Version-Polling

var _config   = JSON.parse(document.getElementById("onlyoffice-config").textContent);
var _tokenEl  = document.getElementById("onlyoffice-token");
var _urls     = JSON.parse(document.getElementById("oo-urls").textContent);
var _version  = JSON.parse(document.getElementById("oo-version").textContent);

if (_tokenEl) { _config.token = JSON.parse(_tokenEl.textContent); }
_config.width  = "100%";
_config.height = "100%";

new DocsAPI.DocEditor("oo-editor", _config);

// ---- Speichern & Zurueck ----
document.getElementById("btn-speichern").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    btn.textContent = "Wird gespeichert...";

    fetch(_urls.forcesave, {
        method: "POST",
        headers: { "X-CSRFToken": _urls.csrf },
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.ok) {
            btn.textContent = "Warte auf Speicherung...";
            _warteAufVersion(0);
        } else {
            btn.disabled = false;
            btn.textContent = "Speichern & zurueck";
            alert("Speichern fehlgeschlagen: " + (data.fehler || "unbekannt"));
        }
    })
    .catch(function () {
        btn.disabled = false;
        btn.textContent = "Speichern & zurueck";
        alert("Verbindungsfehler beim Speichern.");
    });
});

function _warteAufVersion(versuch) {
    if (versuch > 20) { window.location.href = _urls.zurueck; return; }
    fetch(_urls.version)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.version > _version) {
                window.location.href = _urls.zurueck;
            } else {
                setTimeout(function () { _warteAufVersion(versuch + 1); }, 200);
            }
        })
        .catch(function () {
            setTimeout(function () { _warteAufVersion(versuch + 1); }, 200);
        });
}

// ---- Platzhalter-Sidebar ----
var btnToggle    = document.getElementById("btn-sidebar-toggle");
var sidebar      = document.getElementById("sidebar");
var hinweis      = document.getElementById("kopiert-hinweis");
var hinweisTimer = null;

if (btnToggle && sidebar) {
    btnToggle.addEventListener("click", function () { sidebar.classList.toggle("versteckt"); });
}

document.querySelectorAll(".platzhalter-item").forEach(function (item) {
    item.addEventListener("click", function () {
        var text = "{{" + item.dataset.platzhalter + "}}";
        navigator.clipboard.writeText(text).then(function () {
            _zeigHinweis();
        }).catch(function () {
            var ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.opacity  = "0";
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
            _zeigHinweis();
        });
    });
});

function _zeigHinweis() {
    if (!hinweis) { return; }
    hinweis.style.display = "block";
    clearTimeout(hinweisTimer);
    hinweisTimer = setTimeout(function () { hinweis.style.display = "none"; }, 1500);
}
