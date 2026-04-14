/**
 * antraege_editor.js – Visueller Editor fuer verzweigte Antrags-Pfade. v2
 *
 * Basiert auf vis.js Network (lokal in vis-network.min.js).
 * CSP-konform: kein eval, kein inline-JS, Event-Delegation via data-action.
 *
 * Konzept:
 *  Knoten  = AntragsPfadSchritt (eine Formularseite)
 *  Kanten  = AntragsPfadTransition (Bedingung zwischen Schritten)
 */
(function () {
    "use strict";

    // -----------------------------------------------------------------------
    // Zustand
    // -----------------------------------------------------------------------

    var pfadPk = null;          // DB-PK des Pfads (null = neu)
    var modus = "normal";       // "normal" | "schritt" | "verbinden" | "loeschen"
    var network = null;
    var nodes = null;           // vis.DataSet
    var edges = null;           // vis.DataSet

    var schritte = {};          // node_id → { node_id, titel, felder_json, ist_start, ist_ende }
    var transitionen = [];      // [{ id, von, zu, bedingung, label, reihenfolge }]
    var pfadVariablen = {};     // { name: { typ, wert, beschreibung } }

    var verbindeVon = null;     // node_id des Quell-Knotens beim Verbinden-Modus

    // Aktuelle Bearbeitungs-IDs
    var editNodeId = null;      // node_id des gerade bearbeiteten Schritts
    var editEdgeId = null;      // interne Kanten-ID (vis edge id)
    var editFeldIndex = null;   // Index in schritt.felder_json beim Feld-Bearbeiten

    var schritteFelder = [];    // temporaere Feld-Liste waehrend Schritt-Bearbeitung
    var gruppeUnterfelder = []; // temporaere Unterfeld-Liste fuer Gruppe-Feld im Feld-Modal

    // Bootstrap Modals
    var schrittModal = null;
    var feldModal = null;
    var transitionModal = null;

    // -----------------------------------------------------------------------
    // Initialisierung
    // -----------------------------------------------------------------------

    document.addEventListener("DOMContentLoaded", function () {
        // PK aus json_script lesen
        var pkEl = document.getElementById("pfad-pk");
        if (pkEl) {
            pfadPk = JSON.parse(pkEl.textContent);
        }

        // vis.js Datasets
        nodes = new vis.DataSet([]);
        edges = new vis.DataSet([]);

        var container = document.getElementById("antraege-canvas");
        network = new vis.Network(container, { nodes: nodes, edges: edges }, visOptionen());

        // Modals
        schrittModal = new bootstrap.Modal(document.getElementById("schritt-modal"));
        feldModal = new bootstrap.Modal(document.getElementById("feld-modal"));
        transitionModal = new bootstrap.Modal(document.getElementById("transition-modal"));

        // Schritt-Modal: Schliessen im Test-Tab abfangen → zurueck zu Felder-Tab
        document.getElementById("schritt-modal").addEventListener("hide.bs.modal", function (e) {
            var testTabAktiv = document.getElementById("tab-btn-test").classList.contains("active");
            if (testTabAktiv) {
                e.preventDefault();
                _schrittTabWechseln("felder");
            }
        });

        // Backdrop-Cleanup
        ["schritt-modal", "feld-modal", "transition-modal", "schema-import-modal", "qrcode-modal"].forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            el.addEventListener("hidden.bs.modal", function () {
                document.querySelectorAll(".modal-backdrop").forEach(function (el2) { el2.remove(); });
                document.body.classList.remove("modal-open");
                document.body.style.removeProperty("overflow");
                document.body.style.removeProperty("padding-right");
            });
        });

        // Quiz-Import-Bridge: Target leeren wenn Schritt-Modal geschlossen wird
        var schrittModalEl = document.getElementById("schritt-modal");
        if (schrittModalEl) {
            schrittModalEl.addEventListener("hidden.bs.modal", function () {
                window._quizImportTarget = null;
                window._quizImportRenderCallback = null;
            });
        }

        // Bestehenden Pfad laden
        if (pfadPk) {
            ladePfad(pfadPk);
        }

        verdrahteEvents();

        // Auto-Entwurf alle 30 Sekunden speichern
        setInterval(entwurfSpeichern, 30000);

        // Entwurf pruefen (Verzoegerung: Pfad wird ggf. erst async geladen)
        if (pfadPk) {
            setTimeout(pruefeEntwurf, 1500);
        } else {
            pruefeEntwurf();
        }
    });

    function visOptionen() {
        return {
            autoResize: false,
            physics: { enabled: false },
            interaction: { dragNodes: true, hover: true, selectConnectedEdges: false, multiselect: true },
            nodes: {
                shape: "box",
                font: { size: 14, face: "system-ui, sans-serif" },
                borderWidth: 2,
                shadow: { enabled: true, size: 4, x: 2, y: 2 },
                margin: { top: 10, bottom: 10, left: 14, right: 14 },
            },
            edges: {
                arrows: { to: { enabled: true, scaleFactor: 0.8 } },
                font: { size: 11, align: "middle", background: "white" },
                smooth: { type: "continuous", roundness: 0 },
                color: { color: "#666", highlight: "#1a4d2e" },
                width: 2,
                selectionWidth: 3,
            },
        };
    }

    // -----------------------------------------------------------------------
    // Events verdrahten
    // -----------------------------------------------------------------------

    function verdrahteEvents() {
        // Modus-Buttons
        document.querySelectorAll("[data-modus]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                setzeModus(btn.dataset.modus);
            });
        });

        // Speichern
        document.getElementById("btn-speichern").addEventListener("click", speichern);

        // QR-Code-Modal
        var qrBtnEl = document.getElementById("btn-qrcode");
        var qrcodeModalEl = document.getElementById("qrcode-modal");
        if (qrBtnEl && qrcodeModalEl) {
            var qrcodeModal = new bootstrap.Modal(qrcodeModalEl);

            qrBtnEl.addEventListener("click", function () {
                // Aktuelle URL zusammenbauen
                var kuerzel = (document.getElementById("pfad-kuerzel").value || "").trim().toUpperCase();
                var istOeffentlich = document.getElementById("pfad-oeffentlich") &&
                                     document.getElementById("pfad-oeffentlich").checked;

                var basis = window.location.protocol + "//" + window.location.host;
                var url = kuerzel ? basis + "/antrag/" + kuerzel + "/" : "";

                var urlInput = document.getElementById("qrcode-url");
                if (urlInput) urlInput.value = url;

                var warnung = document.getElementById("qrcode-warnung-oeffentlich");
                if (warnung) warnung.style.display = istOeffentlich ? "none" : "";

                var iframeEl = document.getElementById("qrcode-iframe");
                if (iframeEl && url) {
                    var embedUrl = url + "?embed=1";
                    iframeEl.value = '<iframe src="' + embedUrl + '" width="100%" height="600" frameborder="0" style="border:none;"></iframe>';
                }

                qrcodeModal.show();
            });

            // URL kopieren
            var kopiBtn = document.getElementById("btn-url-kopieren");
            if (kopiBtn) {
                kopiBtn.addEventListener("click", function () {
                    var urlInput = document.getElementById("qrcode-url");
                    if (urlInput && urlInput.value) {
                        try {
                            navigator.clipboard.writeText(urlInput.value);
                            kopiBtn.textContent = "\u2713";
                            setTimeout(function () { kopiBtn.textContent = "\uD83D\uDCCB"; }, 1500);
                        } catch (e2) {
                            urlInput.select();
                        }
                    }
                });
            }
        }

            // iframe-Code kopieren
            var iframeKopiBtn = document.getElementById("btn-iframe-kopieren");
            if (iframeKopiBtn) {
                iframeKopiBtn.addEventListener("click", function () {
                    var iframeEl = document.getElementById("qrcode-iframe");
                    if (iframeEl && iframeEl.value) {
                        try {
                            navigator.clipboard.writeText(iframeEl.value);
                            iframeKopiBtn.textContent = "\u2713";
                            setTimeout(function () { iframeKopiBtn.textContent = "\uD83D\uDCCB"; }, 1500);
                        } catch (e2) {
                            iframeEl.select();
                        }
                    }
                });
            }
        }

        // Schema-Import
        var importModalEl = document.getElementById("schema-import-modal");
        if (importModalEl) {
            var importModal = new bootstrap.Modal(importModalEl);
            var importierteFelderJson = null;
            var importierterName = "";

            document.getElementById("btn-schema-import").addEventListener("click", function () {
                // Auswahl zuruecksetzen
                document.querySelectorAll(".import-schema-btn").forEach(function (b) {
                    b.classList.remove("btn-secondary", "active");
                    b.classList.add("btn-outline-secondary");
                });
                document.getElementById("import-vorschau").classList.add("d-none");
                document.getElementById("btn-import-bestaetigen").disabled = true;
                importierteFelderJson = null;
                importModal.show();
            });

            // Klick auf Formular-Karte
            document.getElementById("import-schema-liste").addEventListener("click", function (e) {
                var btn = e.target.closest(".import-schema-btn");
                if (!btn) return;

                // Aktive Karte markieren
                document.querySelectorAll(".import-schema-btn").forEach(function (b) {
                    b.classList.remove("btn-secondary", "active");
                    b.classList.add("btn-outline-secondary");
                });
                btn.classList.remove("btn-outline-secondary");
                btn.classList.add("btn-secondary", "active");

                var felderRaw = btn.dataset.felder;
                var name = btn.dataset.name || "";
                var felder;
                try {
                    felder = JSON.parse(felderRaw);
                } catch (e) {
                    felder = [];
                }
                importierteFelderJson = felder;
                importierterName = name;

                var TYP_LABEL_IMPORT = {
                    text: "Text", mehrzeil: "Mehrzeilig", zahl: "Zahl", datum: "Datum",
                    bool: "Ja/Nein", auswahl: "Auswahl", radio: "Radio", checkboxen: "Checkboxen",
                    email: "E-Mail", iban: "IBAN", uhrzeit: "Uhrzeit",
                    datei: "Datei-Upload", signatur: "Signatur", berechnung: "Berechnung",
                    textblock: "Fliesstext", abschnitt: "Abschnitt",
                    trennlinie: "Trennlinie", leerblock: "Leerblock", zusammenfassung: "Zusammenfassung",
                };
                var html = "";
                (felder || []).forEach(function (f) {
                    var typLabel = TYP_LABEL_IMPORT[f.typ] || f.typ;
                    var label = f.label || f.text || "(kein Label)";
                    html += '<div class="d-flex align-items-center gap-2 py-1 border-bottom">'
                        + '<span class="badge bg-secondary" style="min-width:90px;">' + typLabel + '</span>'
                        + '<span class="small">' + label + '</span>'
                        + (f.pflicht ? '<span class="text-danger ms-auto small">Pflicht</span>' : '')
                        + '</div>';
                });
                if (!html) html = '<p class="text-muted small mb-0">Keine Felder gefunden.</p>';
                document.getElementById("import-felder-liste").innerHTML = html;
                document.getElementById("import-vorschau").classList.remove("d-none");
                document.getElementById("btn-import-bestaetigen").disabled = false;
            });

            document.getElementById("btn-import-bestaetigen").addEventListener("click", function () {
                if (!importierteFelderJson || importierteFelderJson.length === 0) {
                    alert("Bitte zuerst ein Formular auswaehlen.");
                    return;
                }
                // Jedes Feld wird ein eigener Schritt – vertikal gestapelt, automatisch verbunden
                var startX = 400;
                var startY = 100;
                var abstandY = 120;
                var vorherigenId = null;
                var ts = Date.now();

                importierteFelderJson.forEach(function (feld, idx) {
                    var nodeId = "s" + (ts + idx);
                    var titel = feld.label || feld.text || feld.typ || "Schritt " + (idx + 1);
                    var posY = startY + idx * abstandY;
                    var neuerSchritt = {
                        node_id: nodeId,
                        titel: titel,
                        felder_json: [JSON.parse(JSON.stringify(feld))],
                        ist_start: false,
                        ist_ende: false,
                        pos_x: startX,
                        pos_y: posY,
                    };
                    schritte[nodeId] = neuerSchritt;
                    nodes.add({
                        id: nodeId,
                        label: knotenLabel(neuerSchritt),
                        x: startX,
                        y: posY,
                        color: knotenFarbe(neuerSchritt),
                        font: { color: "#ffffff" },
                    });
                    // Kante zum vorherigen Schritt
                    if (vorherigenId) {
                        var edgeId = "e" + vorherigenId + "_" + nodeId;
                        transitionen.push({ id: edgeId, von: vorherigenId, zu: nodeId, bedingung: "", label: "", reihenfolge: idx });
                        edges.add({ id: edgeId, from: vorherigenId, to: nodeId, label: "" });
                    }
                    vorherigenId = nodeId;
                });

                document.getElementById("canvas-hinweis").style.display = "none";
                importModal.hide();
                network.fit();
                document.getElementById("speicher-status").textContent = "Schritt \"" + importierterName + "\" importiert \u2013 bitte speichern.";
            });
        }

        // vis.js Events
        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                // Bei Mehrfach-Auswahl (Ctrl+Klick) kein Modal oeffnen
                if (network.getSelectedNodes().length > 1) return;
                knotenGeklickt(params.nodes[0]);
            } else if (params.edges.length > 0) {
                kanteGeklickt(params.edges[0]);
            } else {
                canvasGeklickt(params.pointer.canvas);
            }
        });

        network.on("dragEnd", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var pos = network.getPositions([nodeId])[nodeId];
                if (schritte[nodeId]) {
                    schritte[nodeId].pos_x = Math.round(pos.x);
                    schritte[nodeId].pos_y = Math.round(pos.y);
                }
            }
        });

        // Schritt-Modal: Speichern
        document.getElementById("btn-schritt-speichern").addEventListener("click", schrittSpeichern);

        // Schritt-Modal: Feld hinzufuegen
        document.getElementById("btn-feld-hinzufuegen-schritt").addEventListener("click", function () {
            oeffneFeldModal(null);
        });

        // Schritt-Modal: Event-Delegation auf Feld-Liste
        document.getElementById("schritt-felder-liste").addEventListener("click", function (e) {
            var btn = e.target.closest("[data-feld-action]");
            if (!btn) return;
            var action = btn.dataset.feldAction;
            var idx = parseInt(btn.dataset.idx, 10);
            if (action === "bearbeiten") {
                oeffneFeldModal(idx);
            } else if (action === "loeschen") {
                schritteFelder.splice(idx, 1);
                renderFelderListe();
            } else if (action === "hoch" && idx > 0) {
                var tmp = schritteFelder[idx - 1];
                schritteFelder[idx - 1] = schritteFelder[idx];
                schritteFelder[idx] = tmp;
                renderFelderListe();
            } else if (action === "runter" && idx < schritteFelder.length - 1) {
                var tmp2 = schritteFelder[idx + 1];
                schritteFelder[idx + 1] = schritteFelder[idx];
                schritteFelder[idx] = tmp2;
                renderFelderListe();
            }
        });

        // Schritt-Modal: Bausteine einfügen
        document.getElementById("schritt-modal").addEventListener("click", function (e) {
            var btn = e.target.closest("[data-baustein]");
            if (!btn) return;
            var name = btn.dataset.baustein;
            var felder = FELD_BAUSTEINE[name];
            if (!felder) return;
            var alleIds = [];
            Object.values(schritte).forEach(function (s) {
                (s.felder_json || []).forEach(function (f) { if (f.id) alleIds.push(f.id); });
            });
            schritteFelder.forEach(function (f) { if (f.id) alleIds.push(f.id); });
            felder.forEach(function (vorlage) {
                var neuesFeld = JSON.parse(JSON.stringify(vorlage));
                var id = labelZuId(neuesFeld.label, neuesFeld.typ);
                var basis = id; var z = 2;
                while (alleIds.indexOf(id) !== -1) { id = basis + "_" + z++; }
                neuesFeld.id = id;
                alleIds.push(id);
                schritteFelder.push(neuesFeld);
            });
            renderFelderListe();
        });

        // Schritt-Modal: Duplizieren
        document.getElementById("btn-schritt-duplizieren").addEventListener("click", function () {
            if (!editNodeId || !schritte[editNodeId]) return;
            var original = schritte[editNodeId];
            var nodeId = "s" + Date.now();
            var kopie = JSON.parse(JSON.stringify(original));
            kopie.node_id = nodeId;
            kopie.titel = original.titel + " (Kopie)";
            kopie.ist_start = false;
            kopie.pos_x = (original.pos_x || 300) + 50;
            kopie.pos_y = (original.pos_y || 300) + 120;
            schritte[nodeId] = kopie;
            nodes.add({
                id: nodeId,
                label: knotenLabel(kopie),
                x: kopie.pos_x,
                y: kopie.pos_y,
                color: knotenFarbe(kopie),
                font: { color: "#ffffff" },
            });
            document.getElementById("canvas-hinweis").style.display = "none";
            document.getElementById("speicher-status").textContent = "\"" + kopie.titel + "\" erstellt – bitte speichern.";
            schrittModal.hide();
        });

        // Feld-Modal: Option hinzufügen
        document.getElementById("btn-option-hinzu").addEventListener("click", function () {
            var container = document.getElementById("optionen-liste");
            var leer = document.getElementById("optionen-leer-hinweis");
            if (leer) leer.remove();
            var div = document.createElement("div");
            div.className = "d-flex gap-1 mb-1 optionen-item";
            div.innerHTML = '<span class="drag-handle text-muted px-1" style="cursor:grab; line-height:2;">&#8942;&#8942;</span>'
                + '<input type="text" class="form-control form-control-sm optionen-label" placeholder="Bezeichnung" style="flex:2">'
                + '<input type="text" class="form-control form-control-sm optionen-zahlwert" placeholder="Wert (optional)" style="flex:1" title="Numerischer Wert f\u00fcr Berechnungen">'
                + '<button type="button" class="btn btn-sm btn-outline-danger px-2 optionen-loeschen" title="Entfernen">&times;</button>';
            container.appendChild(div);
            div.querySelector("input").focus();
        });

        // Feld-Modal: Typ-Wechsel
        document.getElementById("feld-typ").addEventListener("change", function () {
            toggleOptionenRow(this.value);
        });

        // Feld-Modal: Label → ID-Vorschau (+ auto-fill bool Feld-ID)
        document.getElementById("feld-label").addEventListener("input", function () {
            var typ = document.getElementById("feld-typ").value;
            var genId = labelZuId(this.value, typ);
            document.getElementById("feld-id-vorschau").textContent = genId;
            // bool: Feld-ID automatisch vorausfüllen solange nicht manuell geändert
            if (typ === "bool") {
                var boolIdEl = document.getElementById("feld-bool-feld-id");
                if (boolIdEl && !boolIdEl.dataset.manuallyEdited) {
                    boolIdEl.value = genId;
                }
            }
        });
        // bool Feld-ID: manuell geändert merken
        document.getElementById("feld-bool-feld-id").addEventListener("input", function () {
            this.dataset.manuallyEdited = "1";
        });

        // Feld-Modal: OK
        document.getElementById("btn-feld-ok").addEventListener("click", feldSpeichern);

        // FIM-Suche
        document.getElementById("fim-suche").addEventListener("input", function () {
            var q = this.value.trim();
            var box = document.getElementById("fim-vorschlaege");
            if (!q || q.length < 2) { box.style.display = "none"; return; }
            var treffer = (typeof fimSuche === "function") ? fimSuche(q, 12) : [];
            if (!treffer.length) { box.innerHTML = '<div class="p-2 text-muted small">Keine Treffer</div>'; box.style.display = "block"; return; }
            // Nach Gruppe sortieren und gruppiert ausgeben
            var gruppen = {};
            treffer.forEach(function (f) {
                if (!gruppen[f.gruppe]) gruppen[f.gruppe] = [];
                gruppen[f.gruppe].push(f);
            });
            var html = "";
            Object.keys(gruppen).forEach(function (g) {
                html += '<div class="px-2 pt-1 pb-0" style="font-size:.7rem;color:#6c757d;text-transform:uppercase;letter-spacing:.04em;">' + g + '</div>';
                gruppen[g].forEach(function (f) {
                    html += '<button type="button" class="d-block w-100 text-start px-3 py-1 border-0 bg-transparent fim-vorschlag" ' +
                        'style="font-size:.875rem;cursor:pointer;" ' +
                        'data-fim-id="' + f.id + '" ' +
                        'data-fim-name="' + f.name.replace(/"/g, "&quot;") + '" ' +
                        'data-fim-typ="' + f.typ + '" ' +
                        (f.optionen ? 'data-fim-optionen="' + JSON.stringify(f.optionen).replace(/"/g, "&quot;") + '" ' : '') +
                        'onmouseover="this.style.background=\'#f0f4ff\'" onmouseout="this.style.background=\'transparent\'">' +
                        '<strong>' + f.name + '</strong> ' +
                        '<small class="text-muted">' + f.typ + '</small> ' +
                        '<small class="text-primary ms-1">' + f.id + '</small>' +
                        '</button>';
                });
            });
            box.innerHTML = html;
            box.style.display = "block";
        });

        document.getElementById("fim-vorschlaege").addEventListener("click", function (e) {
            var btn = e.target.closest(".fim-vorschlag");
            if (!btn) return;
            _fimFeldAnwenden(btn.dataset.fimId, btn.dataset.fimName, btn.dataset.fimTyp, btn.dataset.fimOptionen);
            document.getElementById("fim-vorschlaege").style.display = "none";
            document.getElementById("fim-suche").value = "";
        });

        document.addEventListener("click", function (e) {
            if (!e.target.closest("#fim-suche") && !e.target.closest("#fim-vorschlaege")) {
                document.getElementById("fim-vorschlaege").style.display = "none";
            }
        });

        // Transition-Modal: Speichern
        document.getElementById("btn-transition-speichern").addEventListener("click", transitionSpeichern);

        // Transition-Modal: verfuegbare Felder einfuegen (Event-Delegation)
        document.getElementById("verfuegbare-felder-inhalt").addEventListener("click", function (e) {
            var btn = e.target.closest("[data-feld-id]");
            if (!btn) return;
            var ta = document.getElementById("transition-bedingung");
            var insertion = "{{" + btn.dataset.feldId + "}}";
            var start = ta.selectionStart;
            var end = ta.selectionEnd;
            ta.value = ta.value.slice(0, start) + insertion + ta.value.slice(end);
            ta.selectionStart = ta.selectionEnd = start + insertion.length;
            ta.focus();
        });

        // Feld-Modal: Textblock System-Variablen einfuegen
        document.getElementById("schritt-modal").addEventListener("click", function (e) {
            var btn = e.target.closest("[data-action='insert-textblock-system']");
            if (!btn) return;
            var varName = btn.dataset.var;
            var ta = document.getElementById("feld-textblock-inhalt");
            var insertion = "{{" + varName + "}}";
            var start = ta.selectionStart;
            var end = ta.selectionEnd;
            ta.value = ta.value.slice(0, start) + insertion + ta.value.slice(end);
            ta.selectionStart = ta.selectionEnd = start + insertion.length;
            ta.focus();
        });

        // Pfeil-Stil Umschalter
        document.querySelectorAll("[data-pfeil]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                document.querySelectorAll("[data-pfeil]").forEach(function (b) {
                    b.classList.remove("active");
                });
                btn.classList.add("active");
                var SMOOTH = {
                    kurve:  { type: "curvedCW", roundness: 0.25 },
                    gerade: { type: "continuous", roundness: 0 },
                    winkel: { type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 },
                };
                network.setOptions({ edges: { smooth: SMOOTH[btn.dataset.pfeil] } });
            });
        });

        // Tab: Felder / Test
        document.getElementById("tab-btn-felder").addEventListener("click", function () {
            _schrittTabWechseln("felder");
        });
        document.getElementById("tab-btn-test").addEventListener("click", function () {
            _schrittTabWechseln("test");
        });

        // Schritt teilen
        var teilenBtn = document.getElementById("btn-schritt-teilen");
        if (teilenBtn) {
            teilenBtn.addEventListener("click", function () {
                if (!teilenBtn._teilenAktiv) {
                    // Teilen-Modus aktivieren: Checkboxen vor jede Zeile
                    teilenBtn._teilenAktiv = true;
                    teilenBtn.textContent = "\u2714 Auswahl in neuen Schritt";
                    teilenBtn.classList.remove("btn-outline-warning");
                    teilenBtn.classList.add("btn-warning");
                    document.getElementById("schritt-felder-liste")
                        .querySelectorAll("li[data-feld-idx]")
                        .forEach(function (li) {
                            var wrap = document.createElement("span");
                            wrap.className = "teilen-cb-wrap me-2";
                            var cb = document.createElement("input");
                            cb.type = "checkbox";
                            cb.className = "form-check-input teilen-cb";
                            cb.dataset.idx = li.dataset.feldIdx;
                            wrap.appendChild(cb);
                            li.insertBefore(wrap, li.firstChild);
                        });
                } else {
                    // Bestaetigen: markierte Felder in neuen Schritt
                    var ausgewaehlt = [];
                    document.getElementById("schritt-felder-liste")
                        .querySelectorAll(".teilen-cb:checked")
                        .forEach(function (cb) {
                            ausgewaehlt.push(parseInt(cb.dataset.idx, 10));
                        });

                    if (ausgewaehlt.length === 0) {
                        alert("Bitte mindestens ein Feld ankreuzen.");
                        return;
                    }
                    if (ausgewaehlt.length === schritteFelder.length) {
                        alert("Nicht alle Felder auswaehlen – mindestens eines muss im aktuellen Schritt bleiben.");
                        return;
                    }

                    // Erst aktuellen Schritt speichern (ohne die ausgew. Felder)
                    var verbleibend = schritteFelder.filter(function (_, i) {
                        return ausgewaehlt.indexOf(i) === -1;
                    });
                    var verschoben = ausgewaehlt.map(function (i) { return schritteFelder[i]; });

                    // Aktuellen Schritt aktualisieren
                    schritte[editNodeId].felder_json = JSON.parse(JSON.stringify(verbleibend));
                    nodes.update({
                        id: editNodeId,
                        label: knotenLabel(schritte[editNodeId]),
                        color: knotenFarbe(schritte[editNodeId]),
                    });

                    // Neuen Schritt anlegen (rechts neben aktuellem)
                    var altPos = network.getPositions([editNodeId])[editNodeId] || { x: 300, y: 300 };
                    var neuNodeId = "s" + Date.now();
                    var neuTitel = schritte[editNodeId].titel + " (2)";
                    var neuerSchritt = {
                        node_id: neuNodeId,
                        titel: neuTitel,
                        felder_json: JSON.parse(JSON.stringify(verschoben)),
                        ist_start: false,
                        ist_ende: schritte[editNodeId].ist_ende,
                        pos_x: Math.round(altPos.x) + 320,
                        pos_y: Math.round(altPos.y),
                    };
                    // ist_ende vom alten wegnehmen
                    schritte[editNodeId].ist_ende = false;
                    nodes.update({ id: editNodeId, color: knotenFarbe(schritte[editNodeId]) });

                    schritte[neuNodeId] = neuerSchritt;
                    nodes.add({
                        id: neuNodeId,
                        label: knotenLabel(neuerSchritt),
                        x: neuerSchritt.pos_x,
                        y: neuerSchritt.pos_y,
                        color: knotenFarbe(neuerSchritt),
                        font: { color: "#ffffff" },
                    });

                    schrittModal.hide();
                }
            });
        }

        // PDF-Scanner
        var scannerModalEl = document.getElementById("scanner-modal");
        if (scannerModalEl) {
            var scannerModal = new bootstrap.Modal(scannerModalEl);
            var scannerInput = document.getElementById("scanner-pdf-input");
            var scannerUrlInput = document.getElementById("scanner-pdf-url");
            var scannerBtn = document.getElementById("btn-scanner-starten");
            var scannerFehler = document.getElementById("scanner-fehler");
            var scannerHinweis = document.getElementById("scanner-hinweis");
            var scannerFimErgebnis = document.getElementById("scanner-fim-ergebnis");

            function _scannerReset() {
                scannerInput.value = "";
                if (scannerUrlInput) scannerUrlInput.value = "";
                scannerBtn.disabled = true;
                scannerFehler.classList.add("d-none");
                scannerHinweis.classList.add("d-none");
                scannerFimErgebnis.classList.add("d-none");
            }

            function _scannerAktivPruefen() {
                var hatDatei = scannerInput.files && scannerInput.files.length > 0;
                var hatUrl = scannerUrlInput && scannerUrlInput.value.trim().length > 8;
                scannerBtn.disabled = !(hatDatei || hatUrl);
                if (hatDatei || hatUrl) {
                    scannerHinweis.classList.remove("d-none");
                } else {
                    scannerHinweis.classList.add("d-none");
                }
            }

            document.getElementById("btn-pdf-scanner").addEventListener("click", function () {
                _scannerReset();
                scannerModal.show();
            });

            scannerInput.addEventListener("change", function () {
                scannerFehler.classList.add("d-none");
                _scannerAktivPruefen();
            });
            if (scannerUrlInput) {
                scannerUrlInput.addEventListener("input", function () {
                    scannerFehler.classList.add("d-none");
                    _scannerAktivPruefen();
                });
            }

            scannerBtn.addEventListener("click", function () {
                var hatDatei = scannerInput.files && scannerInput.files.length > 0;
                var url = scannerUrlInput ? scannerUrlInput.value.trim() : "";
                var istUrl = !hatDatei && url.length > 0;

                scannerBtn.disabled = true;
                scannerBtn.textContent = istUrl ? "Lädt PDF…" : "Scannt...";
                scannerFehler.classList.add("d-none");
                scannerFimErgebnis.classList.add("d-none");

                var splitSchwelle = document.getElementById("scanner-split-schwelle").value || "30";
                var formData = new FormData();
                formData.append("split_schwelle", splitSchwelle);
                var endpoint;
                if (istUrl) {
                    formData.append("url", url);
                    endpoint = "/formulare/editor/scanner-url/";
                } else {
                    formData.append("pdf", scannerInput.files[0]);
                    endpoint = "/formulare/editor/scanner/";
                }

                fetch(endpoint, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfToken() },
                    body: formData,
                })
                .then(function (r) { return r.json(); })
                .then(function (daten) {
                    scannerBtn.disabled = false;
                    scannerBtn.textContent = "Scannen & laden";
                    if (!daten.ok) {
                        scannerFehler.textContent = daten.fehler || "Unbekannter Fehler";
                        scannerFehler.classList.remove("d-none");
                        return;
                    }
                    // FIM-Ergebnis kurz anzeigen, dann laden
                    var fim = daten.fim_treffer || 0;
                    var ges = daten.gesamt_felder || 0;
                    if (fim > 0) {
                        scannerFimErgebnis.innerHTML =
                            "<strong>FIM-Matching:</strong> " + fim + " von " + ges +
                            " Feldern automatisch FIM-IDs zugeordnet.";
                        scannerFimErgebnis.classList.remove("d-none");
                        setTimeout(function () {
                            scannerModal.hide();
                            ladeScannerDaten(daten);
                        }, 1500);
                    } else {
                        scannerModal.hide();
                        ladeScannerDaten(daten);
                    }
                })
                .catch(function () {
                    scannerBtn.disabled = false;
                    scannerBtn.textContent = "Scannen & laden";
                    scannerFehler.textContent = "Netzwerkfehler – bitte erneut versuchen.";
                    scannerFehler.classList.remove("d-none");
                });
            });

            // Backdrop-Cleanup fuer Scanner-Modal
            scannerModalEl.addEventListener("hidden.bs.modal", function () {
                document.querySelectorAll(".modal-backdrop").forEach(function (el) { el.remove(); });
                document.body.classList.remove("modal-open");
                document.body.style.removeProperty("overflow");
                document.body.style.removeProperty("padding-right");
            });
        }

        // Versionen-Modal
        var versionenBtn = document.getElementById("btn-versionen");
        if (versionenBtn) {
            versionenBtn.addEventListener("click", oeffneVersionenModal);
        }
        var versionenModalEl = document.getElementById("versionen-modal");
        if (versionenModalEl) {
            versionenModalEl.addEventListener("click", function (e) {
                var btn = e.target.closest("[data-action='version-laden']");
                if (!btn) return;
                ladeVersion(btn.dataset.versionPk, btn.dataset.versionNr);
            });
            versionenModalEl.addEventListener("hidden.bs.modal", function () {
                document.querySelectorAll(".modal-backdrop").forEach(function (el) { el.remove(); });
                document.body.classList.remove("modal-open");
                document.body.style.removeProperty("overflow");
                document.body.style.removeProperty("padding-right");
            });
        }

        // Auto-Entwurf: Wiederherstellen / Verwerfen
        var entwurfWiederherstellenBtn = document.getElementById("btn-entwurf-wiederherstellen");
        if (entwurfWiederherstellenBtn) {
            entwurfWiederherstellenBtn.addEventListener("click", entwurfWiederherstellen);
        }
        var entwurfVerwerfenBtn = document.getElementById("btn-entwurf-verwerfen");
        if (entwurfVerwerfenBtn) {
            entwurfVerwerfenBtn.addEventListener("click", function () {
                try { localStorage.removeItem(entwurfSchluessel()); } catch (e2) {}
                document.getElementById("entwurf-banner").classList.add("d-none");
            });
        }
    }

    // -----------------------------------------------------------------------
    // Modus
    // -----------------------------------------------------------------------

    var MODUS_HINWEIS = {
        normal: "Klicke auf einen Knoten zum Bearbeiten | Klicke auf eine Kante zum Bearbeiten",
        schritt: "Klicke auf die freie Flaeche um einen neuen Schritt hinzuzufuegen",
        verbinden: "Klicke den Quell-Knoten, dann den Ziel-Knoten",
        loeschen: "Klicke auf einen Knoten oder eine Kante zum Loeschen",
    };

    function setzeModus(neuerModus) {
        modus = neuerModus;
        verbindeVon = null;
        document.querySelectorAll("[data-modus]").forEach(function (btn) {
            btn.classList.toggle("active", btn.dataset.modus === modus);
        });
        document.getElementById("modus-hinweis").textContent = MODUS_HINWEIS[modus] || "";
        network.unselectAll();
    }

    // -----------------------------------------------------------------------
    // Canvas-Klick (neuer Schritt)
    // -----------------------------------------------------------------------

    function canvasGeklickt(pos) {
        if (modus !== "schritt") return;
        document.getElementById("antraege-canvas").style.cursor = "";
        oeffneSchrittModal(null, pos);
    }

    // -----------------------------------------------------------------------
    // Knoten-Klick
    // -----------------------------------------------------------------------

    function knotenGeklickt(nodeId) {
        if (modus === "normal") {
            oeffneSchrittModal(nodeId, null);
        } else if (modus === "loeschen") {
            knotenLoeschen(nodeId);
        } else if (modus === "verbinden") {
            if (!verbindeVon) {
                verbindeVon = nodeId;
                nodes.update({ id: nodeId, borderWidth: 4, color: { border: "#198754" } });
                document.getElementById("modus-hinweis").textContent = "Jetzt Ziel-Knoten klicken";
            } else if (verbindeVon !== nodeId) {
                kanteHinzufuegen(verbindeVon, nodeId);
                nodes.update({ id: verbindeVon, borderWidth: 2, color: knotenFarbe(schritte[verbindeVon]) });
                verbindeVon = null;
                document.getElementById("modus-hinweis").textContent = MODUS_HINWEIS.verbinden;
            }
        }
    }

    // -----------------------------------------------------------------------
    // Kanten-Klick
    // -----------------------------------------------------------------------

    function kanteGeklickt(edgeId) {
        if (modus === "loeschen") {
            kanteLoeschen(edgeId);
        } else if (modus === "normal") {
            oeffneTransitionModal(edgeId);
        }
    }

    // -----------------------------------------------------------------------
    // Schritt Modal
    // -----------------------------------------------------------------------

    function oeffneSchrittModal(nodeId, canvasPos) {
        editNodeId = nodeId;
        var schritt = nodeId ? schritte[nodeId] : null;

        document.getElementById("schritt-modal-titel").textContent =
            schritt ? "Schritt bearbeiten" : "Neuer Schritt";
        document.getElementById("schritt-titel").value = schritt ? schritt.titel : "";
        document.getElementById("schritt-ist-start").checked = schritt ? !!schritt.ist_start : false;
        document.getElementById("schritt-ist-ende").checked = schritt ? !!schritt.ist_ende : false;

        // Temporaere Felder-Liste aufbauen
        schritteFelder = schritt ? JSON.parse(JSON.stringify(schritt.felder_json || [])) : [];
        // Quiz-Import-Bridge: Import-IIFE kann Felder in diese Liste schreiben
        window._quizImportTarget = schritteFelder;
        window._quizImportRenderCallback = renderFelderListe;
        renderFelderListe();

        // Canvas-Position merken (wird beim Speichern gebraucht)
        if (canvasPos) {
            document.getElementById("schritt-modal").dataset.posX = canvasPos.x;
            document.getElementById("schritt-modal").dataset.posY = canvasPos.y;
        } else {
            delete document.getElementById("schritt-modal").dataset.posX;
        }

        // Duplizieren-Button + Teilen-Button nur bei bestehendem Schritt anzeigen
        document.getElementById("btn-schritt-duplizieren").style.display = nodeId ? "" : "none";
        // Teilen erst nach Rendern der Felder aktualisieren
        _aktualisiereTeilenButton();

        // Test-Tab zuruecksetzen auf "Felder"
        _schrittTabWechseln("felder");

        schrittModal.show();
    }

    function _schrittTabWechseln(tab) {
        var istTest = tab === "test";
        document.getElementById("schritt-felder-liste").style.display = istTest ? "none" : "";
        document.getElementById("felder-toolbar").style.display = istTest ? "none" : "";
        document.getElementById("schritt-test-panel").style.display = istTest ? "" : "none";
        document.getElementById("tab-btn-felder").classList.toggle("active", !istTest);
        document.getElementById("tab-btn-test").classList.toggle("active", istTest);
        // Speichern/Teilen/Duplizieren im Footer ausblenden beim Test
        ["btn-schritt-speichern", "btn-schritt-duplizieren", "btn-schritt-teilen"].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.style.visibility = istTest ? "hidden" : "";
        });
        if (istTest) renderTestPanel();
    }

    function _aktualisiereTeilenButton() {
        var btn = document.getElementById("btn-schritt-teilen");
        if (!btn) return;
        // Nur anzeigen wenn Schritt besteht und mehr als 1 Feld hat
        btn.style.display = (editNodeId && schritteFelder.length > 1) ? "" : "none";
        // Teilen-Modus zuruecksetzen falls aktiv
        if (!btn._teilenAktiv) return;
        btn._teilenAktiv = false;
        btn.textContent = "\u2709 Schritt teilen";
        btn.classList.remove("btn-warning");
        btn.classList.add("btn-outline-warning");
        document.getElementById("schritt-felder-liste").querySelectorAll(".teilen-cb").forEach(function (cb) {
            cb.closest("li").querySelector(".teilen-cb-wrap").remove();
        });
    }

    function schrittSpeichern() {
        var titel = document.getElementById("schritt-titel").value.trim();
        if (!titel) {
            document.getElementById("schritt-titel").classList.add("is-invalid");
            return;
        }
        document.getElementById("schritt-titel").classList.remove("is-invalid");

        var istStart = document.getElementById("schritt-ist-start").checked;
        var istEnde = document.getElementById("schritt-ist-ende").checked;
        var modalEl = document.getElementById("schritt-modal");
        var posX = parseFloat(modalEl.dataset.posX || 300);
        var posY = parseFloat(modalEl.dataset.posY || 300);

        if (editNodeId) {
            // Bestehenden Schritt aktualisieren
            schritte[editNodeId].titel = titel;
            schritte[editNodeId].ist_start = istStart;
            schritte[editNodeId].ist_ende = istEnde;
            schritte[editNodeId].felder_json = JSON.parse(JSON.stringify(schritteFelder));
            nodes.update({
                id: editNodeId,
                label: knotenLabel(schritte[editNodeId]),
                color: knotenFarbe(schritte[editNodeId]),
            });
        } else {
            // Neuen Schritt erstellen
            var nodeId = "s" + Date.now();
            var neuerSchritt = {
                node_id: nodeId,
                titel: titel,
                felder_json: JSON.parse(JSON.stringify(schritteFelder)),
                ist_start: istStart,
                ist_ende: istEnde,
                pos_x: Math.round(posX),
                pos_y: Math.round(posY),
            };
            schritte[nodeId] = neuerSchritt;
            nodes.add({
                id: nodeId,
                label: knotenLabel(neuerSchritt),
                x: Math.round(posX),
                y: Math.round(posY),
                color: knotenFarbe(neuerSchritt),
                font: { color: "#ffffff" },
            });
            document.getElementById("canvas-hinweis").style.display = "none";
        }

        schrittModal.hide();
    }

    // -----------------------------------------------------------------------
    // Feld-Liste rendern (in Schritt-Modal)
    // -----------------------------------------------------------------------

    function renderFelderListe() {
        var container = document.getElementById("schritt-felder-liste");

        if (schritteFelder.length === 0) {
            container.innerHTML = '<p class="text-muted small" id="felder-leer-hinweis">Noch keine Felder. Klicke &quot;+ Feld hinzuf\u00fcgen&quot;.</p>';
            return;
        }

        var TYP_LABEL = {
            text: "Text", mehrzeil: "Mehrzeilig", zahl: "Zahl", datum: "Datum",
            datei: "Datei-Upload", signatur: "Signatur", uhrzeit: "Uhrzeit",
            email: "E-Mail", bool: "Ja/Nein", iban: "IBAN",
            auswahl: "Auswahl", radio: "Multiple Choice", checkboxen: "Checkboxen",
            bankverbindung: "Bankverbindung",
            berechnung: "Berechnung", textblock: "Fliesstext", abschnitt: "Abschnitt",
            link: "Link", trennlinie: "—", leerblock: "Leerblock",
            zusammenfassung: "Zusammenfassung", gruppe: "Wiederholungsgruppe",
            einwilligung: "Einwilligung (DSGVO)",
        };

        var gesamt = schritteFelder.length;
        var html = '<ul class="list-group list-group-flush" id="felder-sortable">';
        schritteFelder.forEach(function (feld, idx) {
            html += '<li class="list-group-item px-2 py-1 d-flex justify-content-between align-items-center" data-feld-idx="' + idx + '">';
            html += '<span class="d-flex align-items-center gap-1">';
            html += '<span class="drag-handle text-muted" style="cursor:grab; padding:0 4px; font-size:1rem;" title="Ziehen zum Sortieren">&#8942;&#8942;</span>';
            html += '<span class="badge bg-secondary small">' + (TYP_LABEL[feld.typ] || feld.typ) + '</span> ';
            html += esc(feld.label || "");
            if (feld.pflicht)    html += ' <span class="text-danger small">*</span>';
            if (feld.versteckt)  html += ' <span class="text-muted small" title="Versteckt">&#128065;&#xFE0E;</span>';
            if (feld.zeige_wenn) html += ' <span class="badge bg-info text-dark small" title="Bedingt anzeigen">&#8627; wenn ' + esc(feld.zeige_wenn) + '</span>';
            html += '</span>';
            html += '<span class="d-flex gap-1">';
            // Pfeil-Buttons hoch/runter
            html += '<button type="button" class="btn btn-xs btn-outline-secondary px-1 py-0" style="font-size:0.7rem;" '
                + 'data-feld-action="hoch" data-idx="' + idx + '" title="Nach oben"'
                + (idx === 0 ? ' disabled' : '') + '>&#9650;</button>';
            html += '<button type="button" class="btn btn-xs btn-outline-secondary px-1 py-0" style="font-size:0.7rem;" '
                + 'data-feld-action="runter" data-idx="' + idx + '" title="Nach unten"'
                + (idx === gesamt - 1 ? ' disabled' : '') + '>&#9660;</button>';
            html += '<button type="button" class="btn btn-xs btn-outline-primary px-1 py-0" style="font-size:0.7rem;" data-feld-action="bearbeiten" data-idx="' + idx + '">Bearb.</button>';
            html += '<button type="button" class="btn btn-xs btn-outline-danger px-1 py-0" style="font-size:0.7rem;" data-feld-action="loeschen" data-idx="' + idx + '">&#10005;</button>';
            html += '</span></li>';
        });
        html += '</ul>';
        container.innerHTML = html;

        // Teilen-Button aktualisieren (mehr als 1 Feld → anzeigen)
        _aktualisiereTeilenButton();

        // SortableJS: Drag & Drop Reihenfolge
        if (typeof Sortable !== "undefined") {
            var ulEl = document.getElementById("felder-sortable");
            if (ulEl) {
                Sortable.create(ulEl, {
                    handle: ".drag-handle",
                    animation: 150,
                    onEnd: function (evt) {
                        var item = schritteFelder.splice(evt.oldIndex, 1)[0];
                        schritteFelder.splice(evt.newIndex, 0, item);
                        // Indizes im DOM aktualisieren (fuer Bearbeiten/Loeschen)
                        ulEl.querySelectorAll("li[data-feld-idx]").forEach(function (li, i) {
                            li.dataset.feldIdx = i;
                            li.querySelectorAll("[data-idx]").forEach(function (btn) {
                                btn.dataset.idx = i;
                            });
                        });
                    },
                });
            }
        }
    }

    // -----------------------------------------------------------------------
    // Test-Panel (interaktive Vorschau des Schritts)
    // -----------------------------------------------------------------------

    function renderTestPanel() {
        var container = document.getElementById("schritt-test-panel");
        if (schritteFelder.length === 0) {
            container.innerHTML = '<p class="text-muted small text-center py-3">Keine Felder definiert.</p>';
            return;
        }

        function breiteZuCol(b) {
            return { 25: "col-md-3", 50: "col-md-6", 75: "col-md-9", 100: "col-12" }[b] || "col-12";
        }

        function testInputHtml(feld) {
            var cls = "form-control form-control-sm w-100";
            var ph = esc(feld.hilfetext || "");
            var t = feld.typ;
            if (t === "mehrzeil") {
                return '<textarea class="' + cls + '" rows="3" placeholder="' + ph + '"></textarea>';
            }
            if (t === "auswahl") {
                var opts = '<option value="">— wählen —</option>';
                (feld.optionen || []).forEach(function (o) { opts += '<option>' + esc(o) + '</option>'; });
                return '<select class="form-select form-select-sm w-100">' + opts + '</select>';
            }
            if (t === "radio") {
                var rHtml = '<div class="d-flex flex-column gap-1">';
                (feld.optionen || []).forEach(function (o) {
                    rHtml += '<div class="form-check"><input class="form-check-input" type="radio" name="test_' + esc(feld.id) + '">'
                           + '<label class="form-check-label">' + esc(o) + '</label></div>';
                });
                return rHtml + '</div>';
            }
            if (t === "checkboxen") {
                var cHtml = '<div class="d-flex flex-column gap-1">';
                (feld.optionen || []).forEach(function (o) {
                    cHtml += '<div class="form-check"><input class="form-check-input" type="checkbox">'
                           + '<label class="form-check-label">' + esc(o) + '</label></div>';
                });
                return cHtml + '</div>';
            }
            if (t === "bool") {
                return '<div class="form-check"><input class="form-check-input" type="checkbox" id="test_' + esc(feld.id) + '">'
                     + '<label class="form-check-label" for="test_' + esc(feld.id) + '">' + esc(feld.label) + '</label></div>';
            }
            if (t === "datum") return '<input type="date" class="' + cls + '">';
            if (t === "uhrzeit") return '<input type="text" class="' + cls + '" placeholder="HH:MM">';
            if (t === "zahl") return '<input type="number" class="' + cls + '" placeholder="' + ph + '">';
            if (t === "email") return '<input type="email" class="' + cls + '" placeholder="' + (ph || 'name@beispiel.de') + '">';
            if (t === "iban")             return '<input type="text" class="' + cls + '" placeholder="DE00 0000 0000 0000 0000 00" maxlength="34">';
            if (t === "bic")              return '<input type="text" class="' + cls + '" placeholder="BELADEBEXXX" maxlength="11">';
            if (t === "telefon")          return '<input type="tel"  class="' + cls + '" placeholder="+49 40 123456">';
            if (t === "plz")              return '<input type="text" class="' + cls + '" placeholder="20099" maxlength="5">';
            if (t === "kfz")              return '<input type="text" class="' + cls + '" placeholder="HH-AB 1234" maxlength="12">';
            if (t === "steuernummer")     return '<input type="text" class="' + cls + '" placeholder="123/456/78901" maxlength="20">';
            if (t === "mitarbeiternummer") return '<input type="text" class="' + cls + '" placeholder="12345" maxlength="20" inputmode="numeric">';
            if (t === "zahlung") {
                var zBetrag = feld.betrag_fest ? feld.betrag_fest.toFixed(2) + "\u00a0EUR" : "–";
                var zMeth = (feld.methoden || ["stripe_karte"]);
                var zBadges = zMeth.map(function(m) {
                    var labels = { stripe_karte: "&#x1F4B3;\u00a0Karte", stripe_sepa: "&#x1F3E6;\u00a0SEPA", wero: "&#x26A1;\u00a0Wero" };
                    return '<span class="badge bg-secondary me-1">' + (labels[m] || m) + '</span>';
                }).join("");
                return '<div class="border rounded p-2 bg-light text-center small">'
                     + '<div class="fw-semibold mb-1">&#x1F4B0;\u00a0Zahlungsfeld\u00a0\u2013\u00a0' + zBetrag + '</div>'
                     + '<div class="mb-1">' + zBadges + '</div>'
                     + '<button class="btn btn-sm btn-success disabled" tabindex="-1">Jetzt bezahlen</button>'
                     + '</div>';
            }
            if (t === "datei") return '<input type="file" class="form-control form-control-sm w-100">';
            if (t === "signatur") return '<div class="border rounded bg-light text-muted small text-center py-3">Signatur-Pad</div>';
            if (t === "berechnung") return '<input type="text" class="' + cls + ' bg-light font-monospace" placeholder="wird berechnet…" readonly>';
            if (t === "systemfeld") {
                var swLabel = { loop_zaehler: "Loop-Zaehler", loop_durchlauf: "Loop-Durchlaeufe", heute: "Datum" }[feld.systemwert] || feld.systemwert || "System";
                return '<div class="input-group"><span class="input-group-text bg-warning-subtle text-warning-emphasis small">\u2699</span>'
                    + '<input type="text" class="' + cls + ' bg-warning-subtle fst-italic" value="[' + esc(swLabel) + ']" readonly>'
                    + (feld.einheit ? '<span class="input-group-text">' + esc(feld.einheit) + '</span>' : '')
                    + '</div>';
            }
            return '<input type="text" class="' + cls + '" placeholder="' + ph + '">';
        }

        var html = '<div class="row g-3">';
        schritteFelder.forEach(function (feld) {
            var t = feld.typ;
            // Struktur-Elemente ohne Input
            if (t === "trennlinie") {
                html += '<div class="col-12"><hr class="my-1"></div>';
                return;
            }
            if (t === "leerblock") {
                html += '<div class="' + breiteZuCol(feld.breite || 100) + '" style="height:32px;"></div>';
                return;
            }
            if (t === "abschnitt") {
                var groesse = feld.groesse || "mittel";
                var tag = groesse === "gross" ? "h5" : (groesse === "mittel" ? "h6" : "p");
                var farbe = groesse === "klein" ? "color:#6c757d;" : "color:#1a4d2e;";
                var border = groesse !== "klein" ? "border-bottom:1px solid #dee2e6;padding-bottom:3px;" : "";
                html += '<div class="col-12"><' + tag + ' class="mb-0" style="' + farbe + border + '">'
                      + esc(feld.label || feld.text || "") + '</' + tag + '></div>';
                return;
            }
            if (t === "textblock") {
                html += '<div class="col-12"><p class="small text-muted mb-0">' + esc(feld.text || "") + '</p></div>';
                return;
            }
            if (t === "zusammenfassung") {
                html += '<div class="col-12"><div class="alert alert-info py-2 small mb-0">Zusammenfassung aller Angaben</div></div>';
                return;
            }
            if (t === "link") {
                html += '<div class="' + breiteZuCol(feld.breite || 100) + '"><a href="#" class="small">' + esc(feld.label || "Link") + ' &#8599;</a></div>';
                return;
            }
            if (t === "einwilligung") {
                html += '<div class="col-12"><div class="form-check border rounded p-2" style="background:#fffdf0;border-color:#ffc107 !important;">'
                      + '<input class="form-check-input" type="checkbox" disabled>'
                      + '<label class="form-check-label small">' + esc(feld.text || "Einwilligungstext …") + ' <span class="text-danger">*</span></label>'
                      + '</div></div>';
                return;
            }
            // Normales Eingabe-Feld
            var col = breiteZuCol(feld.breite || 100);
            html += '<div class="' + col + '">';
            if (t !== "bool") {
                html += '<label class="form-label small fw-semibold mb-1">' + esc(feld.label || "");
                if (feld.pflicht) html += ' <span class="text-danger">*</span>';
                html += '</label>';
            }
            html += testInputHtml(feld);
            html += '</div>';
        });
        html += '</div>';
        html += '<div class="mt-3 pt-2 border-top"><small class="text-muted">Dies ist eine reine Vorschau – Eingaben werden nicht gespeichert.</small></div>';

        container.innerHTML = html;
    }

    // -----------------------------------------------------------------------
    // Feld Modal
    // -----------------------------------------------------------------------

    function oeffneFeldModal(idx) {
        editFeldIndex = idx;
        var feld = (idx !== null) ? schritteFelder[idx] : null;
        document.getElementById("feld-modal-titel").textContent = feld ? "Feld bearbeiten" : "Neues Feld";
        var typ = feld ? feld.typ : "text";
        document.getElementById("feld-typ").value = typ;
        document.getElementById("feld-label").value = feld ? (feld.label || feld.text || "") : "";
        // FIM-ID
        var fimId = feld ? (feld.fim_id || "") : "";
        document.getElementById("feld-fim-id").value = fimId;
        document.getElementById("fim-suche").value = "";
        document.getElementById("fim-vorschlaege").style.display = "none";
        _fimIdAnzeigen(fimId);
        document.getElementById("feld-hilfetext").value = feld ? (feld.hilfetext || "") : "";
        document.getElementById("feld-regex").value = feld ? (feld.validierung_regex || "") : "";
        document.getElementById("feld-pflicht").checked   = feld ? !!feld.pflicht   : false;
        document.getElementById("feld-versteckt").checked = feld ? !!feld.versteckt : false;
        document.getElementById("feld-id-vorschau").textContent = feld ? (feld.id || "") : "";
        // bool: Feld-ID explizit vorbelegen; manuallyEdited-Flag zurücksetzen
        var elBoolFeldId = document.getElementById("feld-bool-feld-id");
        if (elBoolFeldId) {
            elBoolFeldId.value = (feld && typ === "bool") ? (feld.id || "") : "";
            delete elBoolFeldId.dataset.manuallyEdited;
        }
        // zeige_wenn: Dropdown mit bool-Feldern des aktuellen Schritts füllen
        _fuelleZeigeWennDropdown(feld ? (feld.zeige_wenn || "") : "");
        document.getElementById("feld-formel").value = feld ? (feld.formel || "") : "";
        document.getElementById("feld-einheit").value = feld ? (feld.einheit || "") : "";
        var elSysw = document.getElementById("feld-systemwert");
        if (elSysw) elSysw.value = feld ? (feld.systemwert || "loop_zaehler") : "loop_zaehler";
        var elSfEin = document.getElementById("feld-systemfeld-einheit");
        if (elSfEin) elSfEin.value = (feld && feld.typ === "systemfeld") ? (feld.einheit || "") : "";
        document.getElementById("feld-akzeptieren").value = feld ? (feld.akzeptieren || "") : "";
        document.getElementById("feld-textblock-inhalt").value = feld ? (feld.text || "") : "";
        document.getElementById("feld-abschnitt-groesse").value = feld ? (feld.groesse || "mittel") : "mittel";
        document.getElementById("feld-abschnitt-ausrichtung").value = feld ? (feld.ausrichtung || "links") : "links";
        document.getElementById("feld-abschnitt-stil").value = feld ? (feld.stil || "normal") : "normal";
        document.getElementById("feld-link-url").value = feld ? (feld.url || "") : "";
        document.getElementById("feld-link-ziel").value = feld ? (feld.ziel || "_blank") : "_blank";
        document.getElementById("feld-email-empfaenger-fest").value = feld ? (feld.empfaenger_fest || "") : "";
        document.getElementById("feld-email-empfaenger-feld").value = feld ? (feld.empfaenger_feld || "") : "";
        document.getElementById("feld-email-betreff").value = feld ? (feld.email_betreff || "") : "";
        document.getElementById("feld-email-nachricht").value = feld ? (feld.email_nachricht || "") : "";
        // Einwilligung – Standardtext vorausfullen wenn neues Feld
        var elEinwText = document.getElementById("feld-einwilligung-text");
        if (elEinwText) {
            if (feld && feld.text) {
                elEinwText.value = feld.text;
            } else if (typ === "einwilligung") {
                elEinwText.value =
                    "Ich bin damit einverstanden, dass [IHRE STELLE] meine oben angegebenen " +
                    "personenbezogenen Daten f\u00fcr [ZWECK] verarbeitet " +
                    "(Art.\u00a06 Abs.\u00a01 lit.\u00a0a DSGVO). " +
                    "Die Einwilligung ist freiwillig und kann jederzeit ohne Angabe von Gr\u00fcnden " +
                    "mit Wirkung f\u00fcr die Zukunft widerrufen werden. " +
                    "Widerruf an: [KONTAKTSTELLE].";
            } else {
                elEinwText.value = "";
            }
        }
        var elEinwLinkText = document.getElementById("feld-einwilligung-link-text");
        if (elEinwLinkText) elEinwLinkText.value = (feld && feld.link_text) ? feld.link_text : "";
        var elEinwLinkUrl = document.getElementById("feld-einwilligung-link-url");
        if (elEinwLinkUrl) elEinwLinkUrl.value = (feld && feld.link_url) ? feld.link_url : "";
        // Zahlung: Felder vorbelegen
        var elZahlBq = document.getElementById("zahlung-betrag-quelle");
        if (elZahlBq) {
            elZahlBq.value = (feld && feld.betrag_quelle) ? feld.betrag_quelle : "fest";
            elZahlBq.dispatchEvent(new Event("change"));
        }
        var elZahlBf = document.getElementById("zahlung-betrag-fest");
        if (elZahlBf) elZahlBf.value = (feld && feld.betrag_fest != null) ? feld.betrag_fest : "";
        var elZahlBi = document.getElementById("zahlung-betrag-feld-id");
        if (elZahlBi) elZahlBi.value = (feld && feld.betrag_feld_id) ? feld.betrag_feld_id : "";
        var elZahlVz = document.getElementById("zahlung-verwendungszweck");
        if (elZahlVz) elZahlVz.value = (feld && feld.verwendungszweck) ? feld.verwendungszweck : "";
        var zahlMethoden = (feld && feld.methoden) ? feld.methoden : ["stripe_karte"];
        ["stripe_karte", "stripe_sepa", "wero"].forEach(function(m) {
            var el = document.getElementById("zahlung-methode-" + m);
            if (el) el.checked = zahlMethoden.indexOf(m) >= 0;
        });
        // Quiz-Felder vorbelegen
        var elQhText = document.getElementById("feld-quizhinweis-text");
        if (elQhText) elQhText.value = (feld && feld.typ === "quizhinweis") ? (feld.text || "") : "";
        var elQATyp = document.getElementById("quiz-antwort-typ");
        if (elQATyp) elQATyp.value = (feld && feld.antwort_typ) ? feld.antwort_typ : "single";
        var elQP = document.getElementById("quiz-punkte");
        if (elQP) elQP.value = (feld && feld.punkte != null) ? feld.punkte : 1;
        var elQFP = document.getElementById("quiz-fehlerpunkte");
        if (elQFP) elQFP.value = (feld && feld.fehlerpunkte != null) ? feld.fehlerpunkte : "";
        var elQPK = document.getElementById("quiz-pflicht-korrekt");
        if (elQPK) elQPK.checked = !!(feld && feld.pflicht_korrekt);
        var elQTP = document.getElementById("quiz-teilpunkte");
        if (elQTP) elQTP.checked = !!(feld && feld.teilpunkte);
        var elQErkl = document.getElementById("quiz-erklaerung");
        if (elQErkl) elQErkl.value = (feld && feld.erklaerung) ? feld.erklaerung : "";
        _renderQuizAntworten((feld && feld.antworten) ? feld.antworten : []);
        // Quizergebnis
        var elQBM = document.getElementById("quiz-bewertungsmodell");
        if (elQBM) { elQBM.value = (feld && feld.bewertungsmodell) ? feld.bewertungsmodell : "prozent"; }
        var elQBA = document.getElementById("quiz-bestanden-ab");
        if (elQBA) elQBA.value = (feld && feld.bestanden_ab != null) ? feld.bestanden_ab : 50;
        var elQMF = document.getElementById("quiz-max-fehlerpunkte");
        if (elQMF) elQMF.value = (feld && feld.max_fehlerpunkte != null) ? feld.max_fehlerpunkte : 10;
        var ng = (feld && feld.noten_grenzen) ? feld.noten_grenzen : {};
        ["1","2","3","4","5"].forEach(function(n) {
            var el = document.getElementById("qe-note-" + n);
            if (el) el.value = ng[n] != null ? ng[n] : ({"1":90,"2":76,"3":63,"4":50,"5":30}[n]);
        });
        var elQETP = document.getElementById("quiz-ergebnis-teilpunkte");
        if (elQETP) elQETP.checked = !!(feld && feld.teilpunkte);
        var elQZ = document.getElementById("quiz-zertifikat");
        if (elQZ) { elQZ.checked = !!(feld && feld.zertifikat); elQZ.dispatchEvent(new Event("change")); }
        var elQZT = document.getElementById("quiz-zertifikat-titel");
        if (elQZT) elQZT.value = (feld && feld.zertifikat_titel) ? feld.zertifikat_titel : "";
        var elQZM = document.getElementById("quiz-zertifikat-monate");
        if (elQZM) elQZM.value = (feld && feld.zertifikat_gueltig_monate != null) ? feld.zertifikat_gueltig_monate : 12;
        // Quizpool
        var elQPoolQuelle = document.getElementById("quizpool-quelle");
        if (elQPoolQuelle) elQPoolQuelle.value = (feld && feld.quelle) ? feld.quelle : "bamf";
        var elQPoolAnzahl = document.getElementById("quizpool-anzahl");
        if (elQPoolAnzahl) elQPoolAnzahl.value = (feld && feld.anzahl != null) ? feld.anzahl : 33;
        var elQPoolBl = document.getElementById("quizpool-bundesland");
        if (elQPoolBl) elQPoolBl.value = (feld && feld.bundesland) ? feld.bundesland : "";
        var elQPoolId = document.getElementById("quizpool-pool-id");
        if (elQPoolId && feld && feld.pool_id) {
            elQPoolId.value = feld.pool_id;
        }
        // Pool-Dropdown befüllen wenn quelle=db
        if (feld && feld.quelle === "db") {
            ladePools(feld.pool_id || null);
        }
        if (typeof toggleQuizpoolDb === "function") {
            toggleQuizpoolDb((feld && feld.quelle) ? feld.quelle : "bamf");
        }
        // Optionen: visuelle Liste aufbauen
        renderOptionenListe((feld && feld.optionen) ? feld.optionen : []);
        // Gruppe: Unterfelder laden
        gruppeUnterfelder = (feld && feld.unterfelder) ? JSON.parse(JSON.stringify(feld.unterfelder)) : [];
        document.getElementById("feld-singular").value = feld ? (feld.singular || "") : "";
        renderGruppeUnterfelder();
        // Breite setzen (Standard: 100%)
        var breite = feld ? (feld.breite || 100) : 100;
        document.querySelectorAll("input[name='feld-breite']").forEach(function (inp) {
            inp.checked = (parseInt(inp.value, 10) === breite);
        });
        toggleOptionenRow(typ);
        feldModal.show();
    }

    // -----------------------------------------------------------------------
    // Optionen: visuelle Liste
    // -----------------------------------------------------------------------

    function renderOptionenListe(optionen) {
        var container = document.getElementById("optionen-liste");
        if (!optionen || optionen.length === 0) {
            container.innerHTML = '<p class="text-muted small mb-1" id="optionen-leer-hinweis">Noch keine Optionen. Klicke "+ Option hinzufügen".</p>';
            return;
        }
        var html = "";
        optionen.forEach(function (opt) {
            var teile  = String(opt).split("|", 2);
            var label  = teile[0].trim();
            var zwert  = teile.length > 1 ? teile[1].trim() : "";
            html += '<div class="d-flex gap-1 mb-1 optionen-item">'
                + '<span class="drag-handle text-muted px-1" style="cursor:grab; line-height:2;">&#8942;&#8942;</span>'
                + '<input type="text" class="form-control form-control-sm optionen-label" value="' + esc(label) + '" placeholder="Bezeichnung" style="flex:2">'
                + '<input type="text" class="form-control form-control-sm optionen-zahlwert" value="' + esc(zwert) + '" placeholder="Wert (optional)" style="flex:1" title="Numerischer Wert f\u00fcr Berechnungen">'
                + '<button type="button" class="btn btn-sm btn-outline-danger px-2 optionen-loeschen" title="Entfernen">&times;</button>'
                + '</div>';
        });
        container.innerHTML = html;
        // SortableJS fuer Optionen-Liste
        if (typeof Sortable !== "undefined") {
            Sortable.create(container, {
                handle: ".drag-handle",
                animation: 100,
            });
        }
        // Loeschen-Events
        container.addEventListener("click", function (e) {
            if (e.target.classList.contains("optionen-loeschen")) {
                e.target.closest(".optionen-item").remove();
                if (!container.querySelector(".optionen-item")) {
                    container.innerHTML = '<p class="text-muted small mb-1" id="optionen-leer-hinweis">Noch keine Optionen. Klicke "+ Option hinzuf\u00fcgen".</p>';
                }
            }
        });
    }

    function leseOptionen() {
        return Array.from(document.querySelectorAll("#optionen-liste .optionen-item"))
            .map(function (item) {
                var label = (item.querySelector(".optionen-label")  || {value: ""}).value.trim();
                var zwert = (item.querySelector(".optionen-zahlwert") || {value: ""}).value.trim();
                if (!label) return null;
                return zwert ? label + "|" + zwert : label;
            })
            .filter(Boolean);
    }

    var STRUKTUR_TYPEN = ["textblock", "abschnitt", "trennlinie", "leerblock", "zusammenfassung", "link", "pdf_email", "einwilligung", "systemfeld", "quizhinweis", "quizergebnis", "quizpool"];

    function toggleOptionenRow(typ) {
        var mitOptionen = ["auswahl", "radio", "checkboxen"];
        var mitFormel = ["berechnung"];
        var mitDatei = ["datei"];
        var mitTextblock = ["textblock"];
        var mitAbschnitt = ["abschnitt"];
        var mitGruppe = ["gruppe"];
        var mitLink = ["link"];
        var mitPdfEmail = ["pdf_email"];
        var mitEinwilligung = ["einwilligung"];
        var mitSystemfeld = ["systemfeld"];
        var ohneLabel = ["trennlinie", "leerblock", "zusammenfassung", "einwilligung", "quizhinweis", "quizergebnis", "quizpool"];
        var ohneHilfe = ["trennlinie", "leerblock", "bool", "abschnitt", "textblock", "berechnung",
                         "zusammenfassung", "signatur", "gruppe", "link", "pdf_email", "einwilligung", "systemfeld",
                         "quizfrage", "quizhinweis", "quizergebnis", "quizpool"];
        // Regex-Validierung nur bei freien Texteingaben sinnvoll
        var mitRegex = ["text", "mehrzeil", "telefon", "steuernummer", "kfz", "mitarbeiternummer",
                        "iban", "bic", "plz", "email", "zahl", "uhrzeit", "iban"];
        var regexRow = document.getElementById("regex-row");
        if (regexRow) regexRow.style.display = mitRegex.indexOf(typ) >= 0 ? "" : "none";
        var ohnePflicht = STRUKTUR_TYPEN.concat(["berechnung", "signatur"]);

        document.getElementById("optionen-row").style.display = mitOptionen.indexOf(typ) >= 0 ? "" : "none";
        var bvRow = document.getElementById("bankverbindung-row");
        if (bvRow) bvRow.style.display = typ === "bankverbindung" ? "" : "none";
        document.getElementById("formel-row").style.display = mitFormel.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("einheit-row").style.display = mitFormel.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("systemfeld-row").style.display = mitSystemfeld.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("systemfeld-einheit-row").style.display = mitSystemfeld.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("akzeptieren-row").style.display = mitDatei.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("textblock-row").style.display = mitTextblock.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("abschnitt-row").style.display = mitAbschnitt.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("gruppe-row").style.display = mitGruppe.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("link-row").style.display = mitLink.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("pdf-email-row").style.display = mitPdfEmail.indexOf(typ) >= 0 ? "" : "none";
        document.getElementById("einwilligung-row").style.display = mitEinwilligung.indexOf(typ) >= 0 ? "" : "none";
        var zahlungRow = document.getElementById("zahlung-row");
        if (zahlungRow) zahlungRow.style.display = typ === "zahlung" ? "" : "none";
        var quizhinweisRow = document.getElementById("quizhinweis-row");
        if (quizhinweisRow) quizhinweisRow.style.display = typ === "quizhinweis" ? "" : "none";
        var quizfrageRow = document.getElementById("quizfrage-row");
        if (quizfrageRow) quizfrageRow.style.display = typ === "quizfrage" ? "" : "none";
        var quizergebnisRow = document.getElementById("quizergebnis-row");
        if (quizergebnisRow) quizergebnisRow.style.display = typ === "quizergebnis" ? "" : "none";
        var quizpoolRow = document.getElementById("quizpool-row");
        if (quizpoolRow) quizpoolRow.style.display = typ === "quizpool" ? "" : "none";
        // Quizergebnis: Bewertungsmodell-Wechsel sofort auslösen
        if (typ === "quizergebnis") {
            var bm = document.getElementById("quiz-bewertungsmodell");
            if (bm) bm.dispatchEvent(new Event("change"));
        }
        // quizfrage: pflicht immer anzeigen, aber breite ausblenden
        var ohneBreiteQuiz = ["quizergebnis", "quizhinweis", "quizpool"];
        if (ohneBreiteQuiz.indexOf(typ) >= 0) {
            document.getElementById("breite-row").style.display = "none";
        }
        // Standardtext vorausfullen wenn das Feld leer ist (neues Feld)
        if (mitEinwilligung.indexOf(typ) >= 0) {
            var elEinwVorausfuellen = document.getElementById("feld-einwilligung-text");
            if (elEinwVorausfuellen && !elEinwVorausfuellen.value.trim()) {
                elEinwVorausfuellen.value =
                    "Ich bin damit einverstanden, dass [IHRE STELLE] meine oben angegebenen " +
                    "personenbezogenen Daten f\u00fcr [ZWECK] verarbeitet " +
                    "(Art.\u00a06 Abs.\u00a01 lit.\u00a0a DSGVO). " +
                    "Die Einwilligung ist freiwillig und kann jederzeit ohne Angabe von Gr\u00fcnden " +
                    "mit Wirkung f\u00fcr die Zukunft widerrufen werden. " +
                    "Widerruf an: [KONTAKTSTELLE].";
            }
        }
        document.getElementById("pflicht-row").style.display = ohnePflicht.indexOf(typ) >= 0 ? "none" : "";
        // Breite nur bei Trennlinie/Zusammenfassung verstecken (kein Sinn ohne Inhalt)
        var ohneBreite = ["trennlinie", "zusammenfassung", "pdf_email", "zahlung"];
        document.getElementById("breite-row").style.display = ohneBreite.indexOf(typ) >= 0 ? "none" : "";
        // Zahlung: Betrag-Quelle umschalten
        var bqSel = document.getElementById("zahlung-betrag-quelle");
        if (bqSel) {
            bqSel.onchange = function() {
                var fest = document.getElementById("zahlung-betrag-fest-wrap");
                var feld = document.getElementById("zahlung-betrag-feld-wrap");
                if (this.value === "feld") {
                    fest.classList.add("d-none"); feld.classList.remove("d-none");
                } else {
                    fest.classList.remove("d-none"); feld.classList.add("d-none");
                }
            };
        }

        var labelRow = document.getElementById("bezeichnung-row");
        if (labelRow) labelRow.style.display = ohneLabel.indexOf(typ) >= 0 ? "none" : "";
        var hilfeRow = document.getElementById("feld-hilfetext").closest(".mb-3");
        if (hilfeRow) hilfeRow.style.display = ohneHilfe.indexOf(typ) >= 0 ? "none" : "";

        // bool: Anzeigetext (label) + separate Feld-ID
        var boolIdRow = document.getElementById("bool-id-row");
        var idVorschauWrap = document.getElementById("feld-id-vorschau-wrap");
        var bezeichnungLabel = document.getElementById("bezeichnung-label");
        if (typ === "bool") {
            if (boolIdRow) boolIdRow.style.display = "";
            if (idVorschauWrap) idVorschauWrap.style.display = "none";
            if (bezeichnungLabel) bezeichnungLabel.innerHTML = 'Anzeigetext <span class="text-danger">*</span>';
        } else {
            if (boolIdRow) boolIdRow.style.display = "none";
            if (idVorschauWrap) idVorschauWrap.style.display = "";
            if (bezeichnungLabel) bezeichnungLabel.innerHTML = 'Bezeichnung <span class="text-danger">*</span>';
        }
    }

    // -----------------------------------------------------------------------
    // zeige_wenn – Dropdown befüllen
    // -----------------------------------------------------------------------

    function _fuelleZeigeWennDropdown(aktuellerWert) {
        var sel = document.getElementById("feld-zeige-wenn");
        if (!sel) return;
        // Alle bool-Felder des aktuellen Schritts sammeln
        var boolFelder = schritteFelder.filter(function (f) { return f.typ === "bool" && f.id; });
        sel.innerHTML = '<option value="">— immer anzeigen —</option>';
        boolFelder.forEach(function (f) {
            var opt = document.createElement("option");
            opt.value = f.id;
            opt.textContent = (f.label || f.id) + " (" + f.id + ")";
            if (f.id === aktuellerWert) opt.selected = true;
            sel.appendChild(opt);
        });
        // Zeige-wenn-Row verstecken wenn es keine bool-Felder gibt
        var row = document.getElementById("zeige-wenn-row");
        if (row) row.style.display = boolFelder.length ? "" : "none";
    }

    // -----------------------------------------------------------------------
    // FIM-Feld anwenden
    // -----------------------------------------------------------------------

    function _fimIdAnzeigen(fimId) {
        var anzeige = document.getElementById("fim-id-anzeige");
        var vorschau = document.getElementById("fim-id-vorschau");
        if (fimId) {
            vorschau.textContent = fimId;
            anzeige.style.display = "";
        } else {
            anzeige.style.display = "none";
        }
    }

    function _fimFeldAnwenden(fimId, fimName, fimTyp, fimOptionenJson) {
        // Typ setzen
        var typEl = document.getElementById("feld-typ");
        if (typEl.querySelector('option[value="' + fimTyp + '"]')) {
            typEl.value = fimTyp;
            typEl.dispatchEvent(new Event("change"));
        }
        // Label setzen
        var labelEl = document.getElementById("feld-label");
        labelEl.value = fimName;
        labelEl.dispatchEvent(new Event("input"));
        // FIM-ID setzen
        document.getElementById("feld-fim-id").value = fimId;
        _fimIdAnzeigen(fimId);
        // Optionen befüllen wenn vorhanden (Auswahl-Felder)
        if (fimOptionenJson) {
            try {
                var opts = JSON.parse(fimOptionenJson);
                if (Array.isArray(opts) && opts.length) {
                    // Kurz warten bis renderOptionenListe durch change-Event fertig
                    setTimeout(function () {
                        renderOptionenListe(opts.map(function (o) { return { wert: o, label: o }; }));
                    }, 50);
                }
            } catch (e) { /* ignore */ }
        }
    }

    // -----------------------------------------------------------------------

    function feldSpeichern() {
        var typ = document.getElementById("feld-typ").value;
        var label = document.getElementById("feld-label").value.trim();
        var ohneLabel = ["trennlinie", "leerblock", "zusammenfassung", "einwilligung"];
        if (!label && ohneLabel.indexOf(typ) === -1) {
            document.getElementById("feld-label").classList.add("is-invalid");
            return;
        }
        document.getElementById("feld-label").classList.remove("is-invalid");

        var feld = {
            typ: typ,
            label: label,
            pflicht:   document.getElementById("feld-pflicht").checked,
            versteckt: document.getElementById("feld-versteckt").checked,
        };
        var fimIdVal = document.getElementById("feld-fim-id").value.trim();
        if (fimIdVal) feld.fim_id = fimIdVal;
        var hilfetext = document.getElementById("feld-hilfetext").value.trim();
        if (hilfetext) feld.hilfetext = hilfetext;
        var validierungRegex = document.getElementById("feld-regex").value.trim();
        if (validierungRegex) feld.validierung_regex = validierungRegex;
        if (typ === "auswahl" || typ === "radio" || typ === "checkboxen") {
            feld.optionen = leseOptionen();
        }
        if (typ === "link") {
            feld.url = document.getElementById("feld-link-url").value.trim();
            feld.ziel = document.getElementById("feld-link-ziel").value;
        }
        if (typ === "berechnung") {
            feld.formel = document.getElementById("feld-formel").value.trim();
            var einheit = document.getElementById("feld-einheit").value.trim();
            if (einheit) feld.einheit = einheit;
        }
        if (typ === "systemfeld") {
            feld.systemwert = document.getElementById("feld-systemwert").value;
            var sfEinheit = document.getElementById("feld-systemfeld-einheit").value.trim();
            if (sfEinheit) feld.einheit = sfEinheit;
        }
        if (typ === "datei") {
            var akz = document.getElementById("feld-akzeptieren").value.trim();
            if (akz) feld.akzeptieren = akz;
        }
        if (typ === "textblock") {
            feld.text = document.getElementById("feld-textblock-inhalt").value;
        }
        if (typ === "pdf_email") {
            feld.empfaenger_fest = document.getElementById("feld-email-empfaenger-fest").value.trim();
            feld.empfaenger_feld = document.getElementById("feld-email-empfaenger-feld").value.trim();
            feld.email_betreff = document.getElementById("feld-email-betreff").value.trim();
            feld.email_nachricht = document.getElementById("feld-email-nachricht").value.trim();
            feld.label = feld.label || "Antrag per E-Mail erhalten?";
        }
        if (typ === "abschnitt") {
            feld.text = document.getElementById("feld-label").value.trim();
            feld.groesse = document.getElementById("feld-abschnitt-groesse").value;
            feld.ausrichtung = document.getElementById("feld-abschnitt-ausrichtung").value;
            feld.stil = document.getElementById("feld-abschnitt-stil").value;
        }
        if (typ === "trennlinie" || typ === "leerblock" || typ === "zusammenfassung") {
            feld.label = "";
        }
        if (typ === "zahlung") {
            var bqVal = document.getElementById("zahlung-betrag-quelle").value;
            feld.betrag_quelle = bqVal;
            if (bqVal === "fest") {
                feld.betrag_fest = parseFloat(document.getElementById("zahlung-betrag-fest").value) || 0;
            } else {
                feld.betrag_feld_id = document.getElementById("zahlung-betrag-feld-id").value.trim();
            }
            feld.verwendungszweck = document.getElementById("zahlung-verwendungszweck").value.trim();
            var methoden = [];
            ["stripe_karte", "stripe_sepa", "wero"].forEach(function(m) {
                if (document.getElementById("zahlung-methode-" + m).checked) methoden.push(m);
            });
            feld.methoden = methoden.length ? methoden : ["stripe_karte"];
        }
        if (typ === "einwilligung") {
            var elEinwTextSave = document.getElementById("feld-einwilligung-text");
            var einwText = elEinwTextSave ? elEinwTextSave.value.trim() : "";
            if (!einwText) {
                // Zeile einblenden damit Fehler sichtbar ist
                document.getElementById("einwilligung-row").style.display = "";
                if (elEinwTextSave) elEinwTextSave.classList.add("is-invalid");
                elEinwTextSave.focus();
                return;
            }
            if (elEinwTextSave) elEinwTextSave.classList.remove("is-invalid");
            feld.text = einwText;
            feld.pflicht = true;
            feld.label = "";
            var einwLinkText = document.getElementById("feld-einwilligung-link-text").value.trim();
            var einwLinkUrl = document.getElementById("feld-einwilligung-link-url").value.trim();
            if (einwLinkText) feld.link_text = einwLinkText;
            if (einwLinkUrl) feld.link_url = einwLinkUrl;
        }
        if (typ === "quizhinweis") {
            feld.text = document.getElementById("feld-quizhinweis-text").value.trim();
            feld.label = "";
        }
        if (typ === "quizfrage") {
            feld.antwort_typ = document.getElementById("quiz-antwort-typ").value;
            var qPunkte = parseFloat(document.getElementById("quiz-punkte").value) || 1;
            feld.punkte = qPunkte;
            var qFP = document.getElementById("quiz-fehlerpunkte").value.trim();
            if (qFP !== "") feld.fehlerpunkte = parseFloat(qFP) || qPunkte;
            feld.pflicht_korrekt = document.getElementById("quiz-pflicht-korrekt").checked;
            feld.teilpunkte = document.getElementById("quiz-teilpunkte").checked;
            var erkl = document.getElementById("quiz-erklaerung").value.trim();
            if (erkl) feld.erklaerung = erkl;
            feld.antworten = _leseQuizAntworten();
        }
        if (typ === "quizergebnis") {
            feld.bewertungsmodell = document.getElementById("quiz-bewertungsmodell").value;
            feld.bestanden_ab = parseFloat(document.getElementById("quiz-bestanden-ab").value) || 50;
            if (feld.bewertungsmodell === "fuehrerschein") {
                feld.max_fehlerpunkte = parseFloat(document.getElementById("quiz-max-fehlerpunkte").value) || 10;
            }
            if (feld.bewertungsmodell === "noten") {
                feld.noten_grenzen = {
                    "1": parseInt(document.getElementById("qe-note-1").value, 10) || 90,
                    "2": parseInt(document.getElementById("qe-note-2").value, 10) || 76,
                    "3": parseInt(document.getElementById("qe-note-3").value, 10) || 63,
                    "4": parseInt(document.getElementById("qe-note-4").value, 10) || 50,
                    "5": parseInt(document.getElementById("qe-note-5").value, 10) || 30,
                };
            }
            feld.teilpunkte = document.getElementById("quiz-ergebnis-teilpunkte").checked;
            feld.zertifikat = document.getElementById("quiz-zertifikat").checked;
            if (feld.zertifikat) {
                var ztitel = document.getElementById("quiz-zertifikat-titel").value.trim();
                if (ztitel) feld.zertifikat_titel = ztitel;
                feld.zertifikat_gueltig_monate = parseInt(document.getElementById("quiz-zertifikat-monate").value, 10) || 0;
            }
            feld.label = feld.label || "Testergebnis";
        }
        if (typ === "quizpool") {
            var qpQuelle = document.getElementById("quizpool-quelle");
            feld.quelle = qpQuelle ? qpQuelle.value : "bamf";
            var qpAnzahl = document.getElementById("quizpool-anzahl");
            feld.anzahl = qpAnzahl ? (parseInt(qpAnzahl.value, 10) || 33) : 33;
            var qpBl = document.getElementById("quizpool-bundesland");
            feld.bundesland = qpBl ? qpBl.value.trim() : "";
            if (feld.quelle === "db") {
                var qpPoolId = document.getElementById("quizpool-pool-id");
                feld.pool_id = qpPoolId ? (parseInt(qpPoolId.value, 10) || null) : null;
            }
            feld.label = feld.label || "Fragenkatalog";
        }
        if (typ === "gruppe") {
            feld.singular = document.getElementById("feld-singular").value.trim() || "Eintrag";
            // Unterfeld-IDs aus Label ableiten (falls noch keine vorhanden)
            var vorhandeneUfIds = [];
            feld.unterfelder = gruppeUnterfelder.map(function (uf, ufIdx) {
                var uf2 = JSON.parse(JSON.stringify(uf));
                if (!uf2.id) {
                    var basis = labelZuId(uf2.label || ("uf" + ufIdx), uf2.typ);
                    var ufId = basis; var z = 2;
                    while (vorhandeneUfIds.indexOf(ufId) !== -1) { ufId = basis + "_" + z++; }
                    uf2.id = ufId;
                }
                vorhandeneUfIds.push(uf2.id);
                return uf2;
            });
        }

        // Breite auslesen
        var breiteInput = document.querySelector("input[name='feld-breite']:checked");
        feld.breite = breiteInput ? parseInt(breiteInput.value, 10) : 100;

        // zeige_wenn auslesen
        var zeigeWennSel = document.getElementById("feld-zeige-wenn");
        var zeigeWennVal = zeigeWennSel ? zeigeWennSel.value : "";
        if (zeigeWennVal) feld.zeige_wenn = zeigeWennVal;

        // bool: explizite Feld-ID pflicht
        if (typ === "bool") {
            var elBoolFeldIdSave = document.getElementById("feld-bool-feld-id");
            var boolFeldId = elBoolFeldIdSave ? elBoolFeldIdSave.value.trim().replace(/\s+/g, "_").replace(/[^\w]/g, "_").replace(/_+/g, "_").replace(/^_|_$/, "") : "";
            if (!boolFeldId) {
                if (elBoolFeldIdSave) { elBoolFeldIdSave.classList.add("is-invalid"); elBoolFeldIdSave.focus(); }
                return;
            }
            if (elBoolFeldIdSave) elBoolFeldIdSave.classList.remove("is-invalid");
            feld.id = boolFeldId;
            if (editFeldIndex !== null) {
                schritteFelder[editFeldIndex] = feld;
            } else {
                schritteFelder.push(feld);
            }
            feldModal.hide();
            schrittModal.show();
            renderFelderListe();
            return;
        }

        if (editFeldIndex !== null) {
            feld.id = schritteFelder[editFeldIndex].id || labelZuId(label, typ);
            schritteFelder[editFeldIndex] = feld;
        } else {
            var id = labelZuId(label, typ);
            var basis = id; var z = 2;
            var alleIds = [];
            Object.values(schritte).forEach(function (s) {
                (s.felder_json || []).forEach(function (f) { alleIds.push(f.id); });
            });
            schritteFelder.forEach(function (f) { alleIds.push(f.id); });
            while (alleIds.indexOf(id) !== -1) { id = basis + "_" + z++; }
            feld.id = id;
            schritteFelder.push(feld);
        }

        feldModal.hide();
        schrittModal.show();
        renderFelderListe();
    }

    // -----------------------------------------------------------------------
    // Gruppe: Unterfelder-Editor (im Feld-Modal)
    // -----------------------------------------------------------------------

    var UNTERFELD_TYPEN = [
        ["text", "Text"],
        ["mehrzeil", "Mehrzeilig"],
        ["zahl", "Zahl"],
        ["datum", "Datum"],
        ["uhrzeit", "Uhrzeit"],
        ["bool", "Ja/Nein"],
        ["auswahl", "Auswahl (Dropdown)"],
        ["radio", "Multiple Choice"],
        ["checkboxen", "Checkboxen"],
    ];

    function renderGruppeUnterfelder() {
        var container = document.getElementById("gruppe-unterfelder-liste");
        if (!container) return;
        if (gruppeUnterfelder.length === 0) {
            container.innerHTML = '<p class="text-muted small mb-0" id="gruppe-unterfelder-leer">Noch keine Unterfelder.</p>';
            return;
        }
        var typOptionen = UNTERFELD_TYPEN.map(function (t) {
            return '<option value="' + t[0] + '">' + t[1] + '</option>';
        }).join("");
        var html = "";
        gruppeUnterfelder.forEach(function (uf, idx) {
            var mitOptionen = ["auswahl", "radio", "checkboxen"].indexOf(uf.typ) >= 0;
            html += '<div class="border rounded p-2 mb-1 bg-white">';
            html += '<div class="d-flex gap-2 align-items-start">';
            // Typ-Auswahl
            html += '<select class="form-select form-select-sm" style="width:160px; flex-shrink:0;" data-uf-action="typ" data-uf-idx="' + idx + '">';
            UNTERFELD_TYPEN.forEach(function (t) {
                html += '<option value="' + t[0] + '"' + (uf.typ === t[0] ? " selected" : "") + '>' + t[1] + '</option>';
            });
            html += '</select>';
            // Label
            html += '<input type="text" class="form-control form-control-sm" placeholder="Bezeichnung *"';
            html += ' value="' + esc(uf.label || "") + '" data-uf-action="label" data-uf-idx="' + idx + '">';
            // Pflicht
            html += '<div class="form-check mt-1 flex-shrink-0">';
            html += '<input class="form-check-input" type="checkbox" title="Pflichtfeld"';
            html += ' data-uf-action="pflicht" data-uf-idx="' + idx + '"' + (uf.pflicht ? " checked" : "") + '>';
            html += '<label class="form-check-label small">Pflicht</label></div>';
            // Loeschen
            html += '<button type="button" class="btn btn-xs btn-outline-danger px-1 py-0 flex-shrink-0"';
            html += ' style="font-size:0.75rem;" data-uf-action="loeschen" data-uf-idx="' + idx + '">&#10005;</button>';
            html += '</div>';
            // Optionen (nur bei auswahl/radio/checkboxen)
            html += '<div class="mt-1"' + (mitOptionen ? "" : ' style="display:none;"') + ' data-uf-optionen-idx="' + idx + '">';
            html += '<textarea class="form-control form-control-sm" rows="2" placeholder="Eine Option pro Zeile"';
            html += ' data-uf-action="optionen" data-uf-idx="' + idx + '">' + esc((uf.optionen || []).join("\n")) + '</textarea>';
            html += '</div>';
            html += '</div>';
        });
        container.innerHTML = html;
    }

    // Event-Delegation fuer Unterfeld-Aktionen
    document.addEventListener("DOMContentLoaded", function () {
        var gruppeContainer = document.getElementById("gruppe-unterfelder-liste");
        if (gruppeContainer) {
            gruppeContainer.addEventListener("input", function (e) {
                var el = e.target;
                var idx = parseInt(el.dataset.ufIdx);
                if (isNaN(idx)) return;
                var action = el.dataset.ufAction;
                if (action === "label") {
                    gruppeUnterfelder[idx].label = el.value;
                } else if (action === "optionen") {
                    gruppeUnterfelder[idx].optionen = el.value.split("\n").map(function (o) { return o.trim(); }).filter(Boolean);
                }
            });
            gruppeContainer.addEventListener("change", function (e) {
                var el = e.target;
                var idx = parseInt(el.dataset.ufIdx);
                if (isNaN(idx)) return;
                var action = el.dataset.ufAction;
                if (action === "typ") {
                    gruppeUnterfelder[idx].typ = el.value;
                    var mitOptionen = ["auswahl", "radio", "checkboxen"].indexOf(el.value) >= 0;
                    var optDiv = gruppeContainer.querySelector('[data-uf-optionen-idx="' + idx + '"]');
                    if (optDiv) optDiv.style.display = mitOptionen ? "" : "none";
                } else if (action === "pflicht") {
                    gruppeUnterfelder[idx].pflicht = el.checked;
                }
            });
            gruppeContainer.addEventListener("click", function (e) {
                var btn = e.target.closest("[data-uf-action='loeschen']");
                if (!btn) return;
                var idx = parseInt(btn.dataset.ufIdx);
                if (isNaN(idx)) return;
                gruppeUnterfelder.splice(idx, 1);
                renderGruppeUnterfelder();
            });
        }
        var btnUnterfeldHinzu = document.getElementById("btn-unterfeld-hinzu");
        if (btnUnterfeldHinzu) {
            btnUnterfeldHinzu.addEventListener("click", function () {
                gruppeUnterfelder.push({ typ: "text", id: "", label: "", pflicht: false });
                renderGruppeUnterfelder();
            });
        }
    });

    // -----------------------------------------------------------------------
    // Quiz-Antworten-Editor
    // -----------------------------------------------------------------------

    var quizAntworten = []; // [{text, korrekt}]

    function _renderQuizAntworten(liste) {
        quizAntworten = liste ? JSON.parse(JSON.stringify(liste)) : [];
        _renderQuizAntwortenListe();
    }

    function _renderQuizAntwortenListe() {
        var container = document.getElementById("quiz-antworten-liste");
        if (!container) return;
        if (quizAntworten.length === 0) {
            container.innerHTML = '<p class="text-muted small mb-0" id="quiz-antworten-leer">Noch keine Antworten.</p>';
            return;
        }
        var html = "";
        quizAntworten.forEach(function (a, i) {
            html += '<div class="d-flex gap-2 mb-1 align-items-center quiz-antwort-item">'
                + '<input type="checkbox" class="form-check-input flex-shrink-0" data-qa-idx="' + i + '" data-qa-action="korrekt"'
                + (a.korrekt ? " checked" : "") + ' title="Richtige Antwort">'
                + '<input type="text" class="form-control form-control-sm" placeholder="Antworttext"'
                + ' data-qa-idx="' + i + '" data-qa-action="text" value="' + esc(a.text || "") + '">'
                + '<button type="button" class="btn btn-sm btn-outline-danger px-2 flex-shrink-0"'
                + ' data-qa-idx="' + i + '" data-qa-action="loeschen" title="Entfernen">&times;</button>'
                + '</div>';
        });
        container.innerHTML = html;
    }

    function _leseQuizAntworten() {
        return quizAntworten.filter(function (a) { return a.text && a.text.trim(); });
    }

    document.addEventListener("DOMContentLoaded", function () {
        // Antwort hinzufügen
        var btnQA = document.getElementById("btn-quiz-antwort-hinzu");
        if (btnQA) {
            btnQA.addEventListener("click", function () {
                quizAntworten.push({ text: "", korrekt: false });
                _renderQuizAntwortenListe();
            });
        }

        // Antwort-Liste: Delegation
        var qaContainer = document.getElementById("quiz-antworten-liste");
        if (qaContainer) {
            qaContainer.addEventListener("input", function (e) {
                var el = e.target;
                var idx = parseInt(el.dataset.qaIdx);
                if (isNaN(idx)) return;
                if (el.dataset.qaAction === "text") quizAntworten[idx].text = el.value;
            });
            qaContainer.addEventListener("change", function (e) {
                var el = e.target;
                var idx = parseInt(el.dataset.qaIdx);
                if (isNaN(idx)) return;
                if (el.dataset.qaAction === "korrekt") quizAntworten[idx].korrekt = el.checked;
            });
            qaContainer.addEventListener("click", function (e) {
                var btn = e.target.closest("[data-qa-action='loeschen']");
                if (!btn) return;
                var idx = parseInt(btn.dataset.qaIdx);
                if (!isNaN(idx)) { quizAntworten.splice(idx, 1); _renderQuizAntwortenListe(); }
            });
        }

        // Antworttyp Wahr/Falsch → automatisch befüllen
        var elQATyp = document.getElementById("quiz-antwort-typ");
        if (elQATyp) {
            elQATyp.addEventListener("change", function () {
                if (this.value === "wahr_falsch") {
                    quizAntworten = [{ text: "Wahr", korrekt: true }, { text: "Falsch", korrekt: false }];
                    _renderQuizAntwortenListe();
                }
            });
        }

        // Bewertungsmodell-Wechsel: bedingte Felder ein-/ausblenden
        var elBM = document.getElementById("quiz-bewertungsmodell");
        if (elBM) {
            elBM.addEventListener("change", function () {
                var m = this.value;
                var elBaRow = document.getElementById("qe-bestanden-ab-row");
                var elBaLabel = document.getElementById("qe-bestanden-ab-label");
                var elMFRow = document.getElementById("qe-max-fehlerpunkte-row");
                var elNRow = document.getElementById("qe-noten-row");
                if (elBaRow) elBaRow.style.display = (m === "fuehrerschein") ? "none" : "";
                if (elBaLabel) elBaLabel.textContent = (m === "punkte") ? "Bestanden ab (Punkte)" : "Bestanden ab (%)";
                if (elMFRow) elMFRow.style.display = (m === "fuehrerschein") ? "" : "none";
                if (elNRow) elNRow.style.display = (m === "noten") ? "" : "none";
            });
        }

        // Zertifikat-Checkbox → Details ein-/ausblenden
        var elQZ = document.getElementById("quiz-zertifikat");
        if (elQZ) {
            elQZ.addEventListener("change", function () {
                var det = document.getElementById("qe-zertifikat-details");
                if (det) det.style.display = this.checked ? "" : "none";
            });
        }
    });

    // -----------------------------------------------------------------------
    // Kante hinzufuegen
    // -----------------------------------------------------------------------

    function kanteHinzufuegen(von, zu) {
        var edgeId = "e" + Date.now();
        var transition = { id: edgeId, von: von, zu: zu, bedingung: "", label: "", reihenfolge: 0 };
        transitionen.push(transition);
        edges.add({ id: edgeId, from: von, to: zu, label: "" });
        // Direkt Transition-Modal oeffnen
        oeffneTransitionModal(edgeId);
    }

    // -----------------------------------------------------------------------
    // Transition Modal – Visueller Bedingungsbuilder
    // -----------------------------------------------------------------------

    var OPERATOREN_TYPEN = {
        text:        [["==","gleich"], ["!=","ungleich"]],
        mehrzeil:    [["==","gleich"], ["!=","ungleich"]],
        email:       [["==","gleich"], ["!=","ungleich"]],
        iban:        [["==","gleich"], ["!=","ungleich"]],
        zahl:        [["==","gleich"], ["!=","ungleich"], [">","größer als"], ["<","kleiner als"], [">=","größer gleich"], ["<=","kleiner gleich"]],
        berechnung:  [["==","gleich"], ["!=","ungleich"], [">","größer als"], ["<","kleiner als"], [">=","größer gleich"], ["<=","kleiner gleich"]],
        datum:       [["==","gleich"], ["<","vor dem Datum"], [">","nach dem Datum"]],
        bool:        [["==\"True\"","ist aktiv (Ja)"], ["==\"False\"","ist nicht aktiv (Nein)"]],
        auswahl:     [["==","gleich"], ["!=","ungleich"]],
        radio:       [["==","gleich"], ["!=","ungleich"]],
        checkboxen:  [["==","enthält"], ["!=","enthält nicht"]],
        uhrzeit:     [["==","gleich"], [">","nach"], ["<","vor"]],
    };

    // -----------------------------------------------------------------------
    // Feld-Bausteine (vorgefertigte Feldgruppen)
    // -----------------------------------------------------------------------

    var FELD_BAUSTEINE = {
        personalien: [
            { typ: "text",  label: "Familienname",  pflicht: true,  fim_id: "F60000004" },
            { typ: "text",  label: "Geburtsname",   pflicht: false, fim_id: "F60000005" },
            { typ: "text",  label: "Vorname",       pflicht: true,  fim_id: "F60000003" },
            { typ: "datum", label: "Geburtsdatum",  pflicht: true,  fim_id: "F60000006" },
            { typ: "text",  label: "Geburtsort",    pflicht: false, fim_id: "F60000007" },
        ],
        adresse: [
            { typ: "text", label: "Straße und Hausnummer", pflicht: true,  fim_id: "F60000022" },
            { typ: "plz",  label: "Postleitzahl",          pflicht: true,  fim_id: "F60000024" },
            { typ: "text", label: "Wohnort",               pflicht: true,  fim_id: "F60000025" },
        ],
        kontakt: [
            { typ: "telefon", label: "Telefonnummer",  pflicht: false, fim_id: "F60000031" },
            { typ: "email",   label: "E-Mail-Adresse", pflicht: false, fim_id: "F60000030" },
        ],
        antragsteller: [
            { typ: "text",    label: "Familienname",          pflicht: true,  fim_id: "F60000004" },
            { typ: "text",    label: "Geburtsname",           pflicht: false, fim_id: "F60000005" },
            { typ: "text",    label: "Vorname",               pflicht: true,  fim_id: "F60000003" },
            { typ: "datum",   label: "Geburtsdatum",          pflicht: true,  fim_id: "F60000006" },
            { typ: "text",    label: "Geburtsort",            pflicht: false, fim_id: "F60000007" },
            { typ: "text",    label: "Straße und Hausnummer", pflicht: true,  fim_id: "F60000022" },
            { typ: "plz",     label: "Postleitzahl",          pflicht: true,  fim_id: "F60000024" },
            { typ: "text",    label: "Wohnort",               pflicht: true,  fim_id: "F60000025" },
            { typ: "telefon", label: "Telefonnummer",         pflicht: false, fim_id: "F60000031" },
            { typ: "email",   label: "E-Mail-Adresse",        pflicht: false, fim_id: "F60000030" },
        ],
    };

    // System-Variablen die in Bedingungen verwendet werden koennen (kein Formularfeld)
    var SYSTEM_FELDER = [
        { id: "__loop_durchlauf", label: "Loop-Zaehler (abgeschl. Durchlaeufe)", typ: "zahl" },
    ];

    function _alleInputFelder() {
        var felder = [];
        var KEINE = ["textblock", "abschnitt", "trennlinie", "leerblock", "zusammenfassung", "link", "signatur"];
        Object.values(schritte).forEach(function (s) {
            (s.felder_json || []).forEach(function (f) {
                if (f.id && KEINE.indexOf(f.typ) === -1) felder.push(f);
            });
        });
        return felder;
    }

    function _feldById(feld_id) {
        var sys = SYSTEM_FELDER.find(function (f) { return f.id === feld_id; });
        if (sys) return sys;
        var feld = _alleInputFelder().find(function (f) { return f.id === feld_id; }) || null;
        // Systemfeld: effektiven Typ fuer Operator-Auswahl zurueckgeben
        if (feld && feld.typ === "systemfeld") {
            var typMap = { loop_zaehler: "zahl", loop_durchlauf: "zahl", heute: "datum" };
            return Object.assign({}, feld, { typ: typMap[feld.systemwert] || "zahl" });
        }
        return feld;
    }

    function _renderRegelZeile(feld_id, op_raw, wert) {
        var felder = _alleInputFelder();
        var feldOpts = '<option value="">— Feld wählen —</option>';
        felder.forEach(function (f) {
            feldOpts += '<option value="' + esc(f.id) + '"' + (f.id === feld_id ? ' selected' : '') + '>' + esc(f.label || f.id) + '</option>';
        });
        // System-Variablen als eigene Gruppe
        var sysOpts = SYSTEM_FELDER.map(function (f) {
            return '<option value="' + esc(f.id) + '"' + (f.id === feld_id ? ' selected' : '') + '>' + esc(f.label) + '</option>';
        }).join("");
        if (sysOpts) feldOpts += '<optgroup label="System-Variablen">' + sysOpts + '</optgroup>';

        var feld = _feldById(feld_id);
        var opListe = (feld && OPERATOREN_TYPEN[feld.typ]) ? OPERATOREN_TYPEN[feld.typ] : OPERATOREN_TYPEN.text;
        var opOpts = opListe.map(function (o) {
            return '<option value="' + esc(o[0]) + '"' + (o[0] === op_raw ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
        }).join("");

        // Wert-Input: bei auswahl/radio Dropdown, bei bool versteckt
        var istBool = feld && feld.typ === "bool";
        var hatOptionen = feld && (feld.typ === "auswahl" || feld.typ === "radio" || feld.typ === "checkboxen") && feld.optionen && feld.optionen.length;
        var wertHtml = "";
        if (istBool) {
            wertHtml = '<input type="hidden" class="regel-wert" value="">';
        } else if (hatOptionen) {
            var selOpts = '<option value="">— wählen —</option>';
            feld.optionen.forEach(function (o) {
                selOpts += '<option value="' + esc(o) + '"' + (o === wert ? ' selected' : '') + '>' + esc(o) + '</option>';
            });
            wertHtml = '<select class="form-select form-select-sm regel-wert" style="min-width:140px;">' + selOpts + '</select>';
        } else {
            var inputTyp = (feld && (feld.typ === "zahl" || feld.typ === "berechnung")) ? "number" : (feld && feld.typ === "datum" ? "date" : "text");
            wertHtml = '<input type="' + inputTyp + '" class="form-control form-control-sm regel-wert" style="min-width:120px;" placeholder="Wert" value="' + esc(wert) + '">';
        }

        return '<div class="d-flex align-items-center gap-2 mb-2 regel-zeile">'
            + '<select class="form-select form-select-sm regel-feld" style="max-width:200px;">' + feldOpts + '</select>'
            + '<select class="form-select form-select-sm regel-op" style="max-width:160px;">' + opOpts + '</select>'
            + wertHtml
            + '<button type="button" class="btn btn-sm btn-outline-danger regel-loeschen" title="Entfernen">&times;</button>'
            + '</div>';
    }

    function _builderNeuzeichnen(regeln) {
        var container = document.getElementById("builder-regeln");
        container.innerHTML = "";
        if (!regeln || regeln.length === 0) {
            container.innerHTML = '<div class="text-muted small mb-2">Noch keine Bedingung. Klicke "+ Bedingung hinzufügen".</div>';
            document.getElementById("verbinder-auswahl").style.display = "none";
            return;
        }
        regeln.forEach(function (r) {
            container.insertAdjacentHTML("beforeend", _renderRegelZeile(r.feld_id || "", r.op || "==", r.wert || ""));
        });
        document.getElementById("verbinder-auswahl").style.display = regeln.length > 1 ? "" : "none";

        // Events
        container.querySelectorAll(".regel-feld").forEach(function (sel) {
            sel.addEventListener("change", function () {
                var zeile = sel.closest(".regel-zeile");
                var neu = _renderRegelZeile(sel.value, "==", "");
                zeile.outerHTML = neu;
                // re-attach events
                _reattachRegelEvents(container);
                document.getElementById("verbinder-auswahl").style.display =
                    container.querySelectorAll(".regel-zeile").length > 1 ? "" : "none";
            });
        });
        _reattachRegelEvents(container);
    }

    function _reattachRegelEvents(container) {
        container.querySelectorAll(".regel-loeschen").forEach(function (btn) {
            btn.onclick = function () {
                btn.closest(".regel-zeile").remove();
                document.getElementById("verbinder-auswahl").style.display =
                    container.querySelectorAll(".regel-zeile").length > 1 ? "" : "none";
                if (container.querySelectorAll(".regel-zeile").length === 0) {
                    container.innerHTML = '<div class="text-muted small mb-2">Noch keine Bedingung. Klicke "+ Bedingung hinzufügen".</div>';
                }
            };
        });
        container.querySelectorAll(".regel-feld").forEach(function (sel) {
            if (!sel._hasEvent) {
                sel._hasEvent = true;
                sel.addEventListener("change", function () {
                    var zeile = sel.closest(".regel-zeile");
                    zeile.outerHTML = _renderRegelZeile(sel.value, "==", "");
                    _reattachRegelEvents(container);
                    document.getElementById("verbinder-auswahl").style.display =
                        container.querySelectorAll(".regel-zeile").length > 1 ? "" : "none";
                });
            }
        });
    }

    function _leseRegeln() {
        var regeln = [];
        document.querySelectorAll("#builder-regeln .regel-zeile").forEach(function (zeile) {
            var feld_id = zeile.querySelector(".regel-feld").value;
            var op = zeile.querySelector(".regel-op").value;
            var wertEl = zeile.querySelector(".regel-wert");
            var wert = wertEl ? wertEl.value : "";
            if (feld_id) regeln.push({ feld_id: feld_id, op: op, wert: wert });
        });
        return regeln;
    }

    function _generiereFormel(regeln, verbinder) {
        if (!regeln || regeln.length === 0) return "";
        var teile = regeln.map(function (r) {
            var feld = _feldById(r.feld_id);
            var istBool = feld && feld.typ === "bool";
            var istZahl = feld && (feld.typ === "zahl" || feld.typ === "berechnung");
            if (istBool) {
                // Op ist z.B. =="True" oder =="False"
                return "{{" + r.feld_id + "}}" + r.op;
            }
            if (r.op.startsWith("==") || r.op.startsWith("!=")) {
                // == oder !=
                var op2 = r.op.length === 2 ? r.op : "==";
                if (istZahl) return "{{" + r.feld_id + "}} " + op2 + " " + (parseFloat(r.wert) || 0);
                return "{{" + r.feld_id + "}} " + op2 + " \"" + r.wert.replace(/"/g, '\\"') + "\"";
            }
            // >, <, >=, <=
            return "{{" + r.feld_id + "}} " + r.op + " " + (parseFloat(r.wert) || 0);
        });
        return teile.join(" " + (verbinder || "and") + " ");
    }

    function _parseFormelZuRegeln(formel) {
        if (!formel || !formel.trim()) return { modus: "immer", regeln: [], verbinder: "and" };
        var verbinder = "and";
        var teile;
        if (/\bor\b/.test(formel) && !/\band\b/.test(formel)) {
            verbinder = "or";
            teile = formel.split(/\bor\b/);
        } else {
            teile = formel.split(/\band\b/);
        }
        var regeln = [];
        for (var i = 0; i < teile.length; i++) {
            var teil = teile[i].trim();
            // Bool: {{feld}}=="True" oder {{feld}}=="False"
            var boolMatch = teil.match(/^\{\{(\w+)\}\}(==\"True\"|==\"False\")$/);
            if (boolMatch) {
                regeln.push({ feld_id: boolMatch[1], op: boolMatch[2], wert: "" });
                continue;
            }
            // Zahl oder Text: {{feld}} op wert
            var m = teil.match(/^\{\{(\w+)\}\}\s*(==|!=|>=|<=|>|<)\s*(.+)$/);
            if (!m) return null; // nicht parsierbar
            var wert = m[3].trim();
            if (wert.startsWith('"') && wert.endsWith('"')) wert = wert.slice(1, -1);
            regeln.push({ feld_id: m[1], op: m[2], wert: wert });
        }
        return { modus: "visuell", regeln: regeln, verbinder: verbinder };
    }

    function _setzeModus(modus) {
        document.getElementById("builder-visuell").style.display = modus === "visuell" ? "" : "none";
        document.getElementById("builder-experte").style.display = modus === "experte" ? "" : "none";
        var radio = document.querySelector('input[name="bedingung-modus"][value="' + modus + '"]');
        if (radio) radio.checked = true;
    }

    function oeffneTransitionModal(edgeId) {
        editEdgeId = edgeId;
        var t = transitionen.find(function (x) { return x.id === edgeId; });
        if (!t) return;

        document.getElementById("transition-label").value = t.label || "";
        document.getElementById("transition-reihenfolge").value = t.reihenfolge || 0;

        // Formel parsen und Modus bestimmen
        var geparst = _parseFormelZuRegeln(t.bedingung || "");
        if (!geparst) {
            // Nicht parsierbar → Experte
            _setzeModus("experte");
            document.getElementById("transition-bedingung").value = t.bedingung || "";
        } else if (geparst.modus === "immer") {
            _setzeModus("immer");
            _builderNeuzeichnen([]);
        } else {
            _setzeModus("visuell");
            document.getElementById("regel-verbinder").value = geparst.verbinder;
            _builderNeuzeichnen(geparst.regeln);
        }

        // Verfuegbare Felder fuer Experten-Modus
        var felder = _alleInputFelder();
        var html = felder.length === 0
            ? '<span class="text-muted small">Noch keine Felder definiert.</span>'
            : felder.map(function (f) {
                return '<button type="button" class="btn btn-sm btn-outline-secondary me-1 mb-1" data-feld-id="' + esc(f.id) + '">'
                    + esc(f.label || f.id) + ' <code class="small">{{' + esc(f.id) + '}}</code></button>';
            }).join("");
        // System-Variablen immer anzeigen
        var sysHtml = SYSTEM_FELDER.map(function (f) {
            return '<button type="button" class="btn btn-sm btn-outline-success me-1 mb-1" data-feld-id="' + esc(f.id) + '">'
                + esc(f.label) + ' <code class="small">{{' + esc(f.id) + '}}</code></button>';
        }).join("");
        sysHtml += '<button type="button" class="btn btn-sm btn-outline-success me-1 mb-1" data-feld-id="kuerzel">'
            + 'Kürzel <code class="small">{{kuerzel}}</code></button>';
        html += '<div class="mt-2 pt-1" style="border-top:1px dashed #ccc;">'
            + '<small class="text-muted d-block mb-1">System:</small>'
            + sysHtml
            + '</div>';
        document.getElementById("verfuegbare-felder-inhalt").innerHTML = html;

        transitionModal.show();
    }

    // Modus-Radio Listener
    document.querySelectorAll('input[name="bedingung-modus"]').forEach(function (radio) {
        radio.addEventListener("change", function () { _setzeModus(this.value); });
    });

    // + Bedingung hinzufügen
    document.getElementById("btn-regel-hinzu").addEventListener("click", function () {
        var container = document.getElementById("builder-regeln");
        var leer = container.querySelector(".text-muted");
        if (leer) leer.remove();
        container.insertAdjacentHTML("beforeend", _renderRegelZeile("", "==", ""));
        _reattachRegelEvents(container);
        document.getElementById("verbinder-auswahl").style.display =
            container.querySelectorAll(".regel-zeile").length > 1 ? "" : "none";
    });

    function transitionSpeichern() {
        var t = transitionen.find(function (x) { return x.id === editEdgeId; });
        if (!t) { transitionModal.hide(); return; }

        var modus = document.querySelector('input[name="bedingung-modus"]:checked');
        modus = modus ? modus.value : "immer";

        if (modus === "immer") {
            t.bedingung = "";
        } else if (modus === "visuell") {
            var regeln = _leseRegeln();
            var verbinder = document.getElementById("regel-verbinder").value;
            t.bedingung = _generiereFormel(regeln, verbinder);
        } else {
            t.bedingung = document.getElementById("transition-bedingung").value.trim();
        }

        t.label = document.getElementById("transition-label").value.trim();
        t.reihenfolge = parseInt(document.getElementById("transition-reihenfolge").value, 10) || 0;

        // Automatisches Label wenn leer
        if (!t.label && t.bedingung) {
            var m = t.bedingung.match(/"\s*(.*?)\s*"/);
            t.label = m ? m[1] : (t.bedingung.length <= 20 ? t.bedingung : "?");
        }

        edges.update({ id: editEdgeId, label: t.label || (t.bedingung ? "…" : "") });
        transitionModal.hide();
    }

    // -----------------------------------------------------------------------
    // Loeschen
    // -----------------------------------------------------------------------

    function knotenLoeschen(nodeId) {
        if (!confirm("Schritt \"" + (schritte[nodeId] ? schritte[nodeId].titel : nodeId) + "\" loeschen?")) return;
        // Alle verbundenen Kanten entfernen
        transitionen = transitionen.filter(function (t) {
            if (t.von === nodeId || t.zu === nodeId) {
                edges.remove(t.id);
                return false;
            }
            return true;
        });
        nodes.remove(nodeId);
        delete schritte[nodeId];
    }

    function kanteLoeschen(edgeId) {
        transitionen = transitionen.filter(function (t) { return t.id !== edgeId; });
        edges.remove(edgeId);
    }

    // -----------------------------------------------------------------------
    // Pfad laden
    // -----------------------------------------------------------------------

    function ladePfad(pk) {
        fetch("/formulare/editor/laden/" + pk + "/", {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        })
        .then(function (r) { return r.json(); })
        .then(function (daten) {
            document.getElementById("pfad-name").value = daten.name || "";
            document.getElementById("pfad-beschreibung").value = daten.beschreibung || "";
            document.getElementById("pfad-aktiv").checked = !!daten.aktiv;
            var oeffEl = document.getElementById("pfad-oeffentlich");
            if (oeffEl) oeffEl.checked = !!daten.oeffentlich;
            var wtEl = document.getElementById("pfad-workflow-template");
            if (wtEl) wtEl.value = daten.workflow_template_id || "";
            var emailEl = document.getElementById("pfad-benachrichtigung-email");
            if (emailEl) emailEl.value = daten.benachrichtigung_email || "";
            var leikaEl = document.getElementById("pfad-leika-schluessel");
            if (leikaEl) leikaEl.value = daten.leika_schluessel || "";
            pfadVariablen = daten.variablen || {};

            // Schritte aufbauen
            (daten.schritte || []).forEach(function (s) {
                schritte[s.node_id] = {
                    node_id: s.node_id,
                    titel: s.titel,
                    felder_json: s.felder_json || [],
                    ist_start: s.ist_start,
                    ist_ende: s.ist_ende,
                    pos_x: s.pos_x,
                    pos_y: s.pos_y,
                };
                nodes.add({
                    id: s.node_id,
                    label: knotenLabel(schritte[s.node_id]),
                    x: s.pos_x,
                    y: s.pos_y,
                    color: knotenFarbe(schritte[s.node_id]),
                    font: { color: "#ffffff" },
                });
            });

            // Kanten aufbauen
            (daten.transitionen || []).forEach(function (t) {
                var edgeId = "e" + t.von + "_" + t.zu + "_" + Date.now();
                transitionen.push({ id: edgeId, von: t.von, zu: t.zu, bedingung: t.bedingung, label: t.label, reihenfolge: t.reihenfolge });
                edges.add({ id: edgeId, from: t.von, to: t.zu, label: t.label || (t.bedingung ? "?" : "") });
            });

            if (nodes.length > 0) {
                document.getElementById("canvas-hinweis").style.display = "none";
                network.fit();
            }
            document.getElementById("speicher-status").textContent = "Geladen";
            // Veralteten Entwurf loeschen: nach erfolgreichem Server-Load ist
            // ein Draft aus einer frueheren Session wertlos (wuerde leeren Canvas liefern).
            // Neue Aenderungen werden ab jetzt wieder per Autosave gespeichert.
            try { localStorage.removeItem(entwurfSchluessel()); } catch (e2) {}
            var entwurfBanner = document.getElementById("entwurf-banner");
            if (entwurfBanner) entwurfBanner.classList.add("d-none");
        })
        .catch(function () {
            document.getElementById("speicher-status").textContent = "Fehler beim Laden";
        });
    }

    // -----------------------------------------------------------------------
    // Scanner-Ergebnis laden (wie ladePfad, aber mit Daten-Objekt statt PK)
    // -----------------------------------------------------------------------

    function ladeScannerDaten(daten) {
        // Canvas leeren
        nodes.clear();
        edges.clear();
        Object.keys(schritte).forEach(function (k) { delete schritte[k]; });
        transitionen.length = 0;

        // Meta-Felder befuellen
        document.getElementById("pfad-name").value = daten.name || "";
        document.getElementById("pfad-beschreibung").value = daten.beschreibung || "";
        document.getElementById("pfad-aktiv").checked = true;
        document.getElementById("pfad-workflow-template").value = "";

        // Schritte aufbauen
        (daten.schritte || []).forEach(function (s) {
            schritte[s.node_id] = {
                node_id: s.node_id,
                titel: s.titel,
                felder_json: s.felder_json || [],
                ist_start: s.ist_start,
                ist_ende: s.ist_ende,
                pos_x: s.pos_x,
                pos_y: s.pos_y,
            };
            nodes.add({
                id: s.node_id,
                label: knotenLabel(schritte[s.node_id]),
                x: s.pos_x,
                y: s.pos_y,
                color: knotenFarbe(schritte[s.node_id]),
                font: { color: "#ffffff" },
            });
        });

        if (nodes.length > 0) {
            document.getElementById("canvas-hinweis").style.display = "none";
            network.fit();
        }
        document.getElementById("speicher-status").textContent =
            (daten.schritte || []).length + " Schritt(e) geladen – bitte Transitionen ziehen und speichern";
    }

    // -----------------------------------------------------------------------
    // Speichern
    // -----------------------------------------------------------------------

    function speichern() {
        var name = document.getElementById("pfad-name").value.trim();
        if (!name) {
            document.getElementById("pfad-name").classList.add("is-invalid");
            document.getElementById("pfad-name").focus();
            return;
        }
        document.getElementById("pfad-name").classList.remove("is-invalid");

        // Aktuelle Positionen aus vis.js lesen
        var positionen = network.getPositions();
        Object.keys(schritte).forEach(function (nodeId) {
            if (positionen[nodeId]) {
                schritte[nodeId].pos_x = Math.round(positionen[nodeId].x);
                schritte[nodeId].pos_y = Math.round(positionen[nodeId].y);
            }
        });

        var oeffEl = document.getElementById("pfad-oeffentlich");
        var wtEl = document.getElementById("pfad-workflow-template");
        var emailEl = document.getElementById("pfad-benachrichtigung-email");
        var leikaEl = document.getElementById("pfad-leika-schluessel");
        var payload = {
            pk: pfadPk,
            name: name,
            beschreibung: document.getElementById("pfad-beschreibung").value.trim(),
            aktiv: document.getElementById("pfad-aktiv").checked,
            oeffentlich: oeffEl ? oeffEl.checked : false,
            kuerzel: (document.getElementById("pfad-kuerzel").value || "").trim().toUpperCase(),
            workflow_template_id: wtEl ? (wtEl.value || null) : null,
            benachrichtigung_email: emailEl ? emailEl.value.trim() : "",
            leika_schluessel: leikaEl ? leikaEl.value.trim() : "",
            schritte: Object.values(schritte),
            transitionen: transitionen,
            variablen: pfadVariablen,
        };

        document.getElementById("speicher-status").textContent = "Speichert...";
        document.getElementById("btn-speichern").disabled = true;

        fetch("/formulare/editor/speichern/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify(payload),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            document.getElementById("btn-speichern").disabled = false;
            if (data.ok) {
                pfadPk = data.pk;
                document.getElementById("speicher-status").textContent = "Gespeichert (" + data.name + ")";
                // URL aktualisieren ohne Reload
                history.replaceState(null, "", "/formulare/editor/" + pfadPk + "/");
                // Entwurf nach erfolgreichem Speichern loeschen
                try { localStorage.removeItem(entwurfSchluessel()); } catch (e2) {}
                var entwurfBanner = document.getElementById("entwurf-banner");
                if (entwurfBanner) entwurfBanner.classList.add("d-none");
            } else {
                document.getElementById("speicher-status").textContent = "Fehler: " + (data.fehler || "Unbekannt");
            }
        })
        .catch(function () {
            document.getElementById("btn-speichern").disabled = false;
            document.getElementById("speicher-status").textContent = "Netzwerkfehler";
        });
    }

    // -----------------------------------------------------------------------
    // Hilfsfunktionen
    // -----------------------------------------------------------------------

    function knotenLabel(schritt) {
        var prefix = schritt.ist_start ? "[S] " : (schritt.ist_ende ? "[E] " : "");
        var KEINE_EINGABE = ["textblock", "abschnitt", "trennlinie", "leerblock", "zusammenfassung", "link"];
        var anzahl = (schritt.felder_json || []).filter(function (f) {
            return KEINE_EINGABE.indexOf(f.typ) === -1;
        }).length;
        var suffix = anzahl > 0 ? "\n(" + anzahl + " Feld" + (anzahl !== 1 ? "er" : "") + ")" : "";
        return prefix + schritt.titel + suffix;
    }

    function knotenFarbe(schritt) {
        if (schritt.ist_start) return { background: "#198754", border: "#145c32" };
        if (schritt.ist_ende)  return { background: "#dc3545", border: "#a12030" };
        return { background: "#1a4d2e", border: "#12341f" };
    }

    function labelZuId(label, typ) {
        var basis = label.toLowerCase()
            .replace(/ae/g, "ae").replace(/oe/g, "oe").replace(/ue/g, "ue")
            .replace(/[^\w]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
        if (!basis) basis = "feld";
        var typSuffix = {
            zahl: "_zahl", datum: "_datum", uhrzeit: "_uhrzeit", bool: "_bool", email: "_email"
        };
        return basis + (typSuffix[typ] || "");
    }

    function csrfToken() {
        var meta = document.querySelector("meta[name='csrf-token']");
        return meta ? meta.content : "";
    }

    function esc(str) {
        return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // -----------------------------------------------------------------------
    // Auto-Entwurf (LocalStorage)
    // -----------------------------------------------------------------------

    function entwurfSchluessel() {
        return "pfad_entwurf_" + (pfadPk || "neu");
    }

    function entwurfSpeichern() {
        if (!network) return;
        try {
            var positionen = network.getPositions();
            Object.keys(schritte).forEach(function (nodeId) {
                if (positionen[nodeId]) {
                    schritte[nodeId].pos_x = Math.round(positionen[nodeId].x);
                    schritte[nodeId].pos_y = Math.round(positionen[nodeId].y);
                }
            });
            var oeffDraftEl = document.getElementById("pfad-oeffentlich");
            var entwurf = {
                zeitstempel: new Date().toISOString(),
                name: document.getElementById("pfad-name").value.trim(),
                beschreibung: document.getElementById("pfad-beschreibung").value.trim(),
                aktiv: document.getElementById("pfad-aktiv").checked,
                oeffentlich: oeffDraftEl ? oeffDraftEl.checked : false,
                kuerzel: (document.getElementById("pfad-kuerzel").value || "").trim().toUpperCase(),
                schritte: JSON.parse(JSON.stringify(Object.values(schritte))),
                transitionen: JSON.parse(JSON.stringify(transitionen)),
            };
            localStorage.setItem(entwurfSchluessel(), JSON.stringify(entwurf));
        } catch (e) {
            // LocalStorage nicht verfuegbar oder voll – kein Fehler
        }
    }

    function pruefeEntwurf() {
        try {
            var raw = localStorage.getItem(entwurfSchluessel());
            if (!raw) return;
            var entwurf = JSON.parse(raw);
            if (!entwurf || !entwurf.zeitstempel) return;
            var banner = document.getElementById("entwurf-banner");
            if (!banner) return;
            var ts = new Date(entwurf.zeitstempel);
            document.getElementById("entwurf-banner-text").textContent =
                "Entwurf vom " + ts.toLocaleString("de-DE") + " gefunden.";
            banner.classList.remove("d-none");
        } catch (e) {}
    }

    function entwurfWiederherstellen() {
        try {
            var raw = localStorage.getItem(entwurfSchluessel());
            if (!raw) return;
            var entwurf = JSON.parse(raw);
            ladeScannerDaten(entwurf);
            document.getElementById("pfad-aktiv").checked = !!entwurf.aktiv;
            document.getElementById("pfad-kuerzel").value = entwurf.kuerzel || "";
            if (entwurf.workflow_template_id) {
                document.getElementById("pfad-workflow-template").value = entwurf.workflow_template_id;
            }
            var emailEntwEl = document.getElementById("pfad-benachrichtigung-email");
            if (emailEntwEl && entwurf.benachrichtigung_email) {
                emailEntwEl.value = entwurf.benachrichtigung_email;
            }
            var leikaEntwEl = document.getElementById("pfad-leika-schluessel");
            if (leikaEntwEl && entwurf.leika_schluessel) {
                leikaEntwEl.value = entwurf.leika_schluessel;
            }
            document.getElementById("entwurf-banner").classList.add("d-none");
            document.getElementById("speicher-status").textContent =
                "Entwurf wiederhergestellt – bitte pruefen und speichern.";
        } catch (e) {
            alert("Entwurf konnte nicht geladen werden.");
        }
    }

    // -----------------------------------------------------------------------
    // Versionen
    // -----------------------------------------------------------------------

    var versionenModalInstanz = null;

    function oeffneVersionenModal() {
        if (!pfadPk) return;
        var modalEl = document.getElementById("versionen-modal");
        if (!modalEl) return;
        if (!versionenModalInstanz) {
            versionenModalInstanz = new bootstrap.Modal(modalEl);
        }
        var container = document.getElementById("versionen-liste-container");
        container.innerHTML = '<div class="text-center text-muted py-3">Lade Versionen…</div>';
        versionenModalInstanz.show();

        fetch("/formulare/editor/versionen/" + pfadPk + "/")
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var versionen = data.versionen || [];
            if (versionen.length === 0) {
                container.innerHTML = '<p class="text-muted small">Noch keine Versionen vorhanden. Beim naechsten Speichern wird eine angelegt.</p>';
                return;
            }
            var html = '<table class="table table-sm table-hover mb-0">'
                + '<thead class="table-light"><tr>'
                + '<th>Version</th><th>Erstellt am</th><th>Bearbeiter</th><th></th>'
                + '</tr></thead><tbody>';
            versionen.forEach(function (v) {
                var ts = v.erstellt_am;  // Backend liefert bereits "dd.mm.yyyy HH:MM"
                html += '<tr>'
                    + '<td class="fw-semibold">v' + v.version_nr + '</td>'
                    + '<td class="small">' + ts + '</td>'
                    + '<td class="small">' + esc(v.erstellt_von || "—") + '</td>'
                    + '<td><button class="btn btn-sm btn-outline-warning"'
                    + ' data-action="version-laden"'
                    + ' data-version-pk="' + v.pk + '"'
                    + ' data-version-nr="' + v.version_nr + '">'
                    + '&#8635; Laden</button></td>'
                    + '</tr>';
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        })
        .catch(function () {
            container.innerHTML = '<div class="alert alert-danger py-2 small">Fehler beim Laden der Versionen.</div>';
        });
    }

    function ladeVersion(versionPk, versionNr) {
        if (!confirm("Version v" + versionNr + " laden? Der aktuelle ungespeicherte Stand geht verloren.")) return;
        fetch("/formulare/editor/version/" + versionPk + "/")
        .then(function (r) { return r.json(); })
        .then(function (daten) {
            if (versionenModalInstanz) versionenModalInstanz.hide();
            ladeScannerDaten(daten);
            document.getElementById("speicher-status").textContent =
                "Version v" + versionNr + " geladen – bitte speichern zum Uebernehmen.";
        })
        .catch(function () {
            alert("Fehler beim Laden der Version.");
        });
    }

    // -----------------------------------------------------------------------
    // Variablen-Modal
    // -----------------------------------------------------------------------

    function renderVariablenListe() {
        var tbody = document.getElementById("variablen-liste");
        if (!tbody) return;
        tbody.innerHTML = "";
        var namen = Object.keys(pfadVariablen);
        if (namen.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted small text-center py-2">Noch keine Variablen.</td></tr>';
            return;
        }
        namen.forEach(function (name) {
            var v = pfadVariablen[name];
            var tr = document.createElement("tr");
            tr.innerHTML =
                '<td><code class="small">' + esc(name) + '</code></td>' +
                '<td><span class="badge ' + (v.typ === "zahl" ? "bg-primary" : "bg-secondary") + '">' + esc(v.typ) + '</span></td>' +
                '<td><strong>' + esc(String(v.wert)) + '</strong></td>' +
                '<td class="text-muted small">' + esc(v.beschreibung || "") + '</td>' +
                '<td><button class="btn btn-sm btn-outline-danger" data-action="var-loeschen" data-var-name="' + esc(name) + '">&#10005;</button></td>';
            tbody.appendChild(tr);
        });
    }

    function aktualisierVariablenButtons() {
        // Insert-Buttons im Textblock-Bereich
        var tbSpan = document.getElementById("textblock-variablen-buttons");
        if (tbSpan) {
            tbSpan.innerHTML = "";
            Object.keys(pfadVariablen).forEach(function (name) {
                var v = pfadVariablen[name];
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-sm btn-outline-warning me-1 mb-1";
                btn.dataset.action = "insert-textblock-var";
                btn.dataset.varName = name;
                btn.innerHTML = esc(name) + ' <code class="small">&#123;&#123;' + esc(name) + '&#125;&#125;</code>';
                btn.title = v.typ + ": " + v.wert;
                tbSpan.appendChild(btn);
            });
        }
        // Insert-Buttons im Formel-Bereich
        var fSpan = document.getElementById("formel-variablen-buttons");
        if (fSpan) {
            var namen = Object.keys(pfadVariablen).filter(function (n) { return pfadVariablen[n].typ === "zahl"; });
            if (namen.length === 0) {
                fSpan.innerHTML = '<em class="text-muted small">Noch keine Zahl-Variablen definiert.</em>';
            } else {
                fSpan.innerHTML = "";
                namen.forEach(function (name) {
                    var v = pfadVariablen[name];
                    var btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "btn btn-sm btn-outline-warning me-1 mb-1";
                    btn.dataset.action = "insert-formel-var";
                    btn.dataset.varName = name;
                    btn.innerHTML = esc(name) + ' <code class="small">=' + esc(String(v.wert)) + '</code>';
                    btn.title = "Variable " + name + " = " + v.wert;
                    fSpan.appendChild(btn);
                });
            }
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        // Variablen aus json_script laden (bei bestehendem Pfad)
        var initEl = document.getElementById("pfad-variablen-init");
        if (initEl) {
            try { pfadVariablen = JSON.parse(initEl.textContent) || {}; } catch (e) {}
        }
        aktualisierVariablenButtons();

        // Variablen-Liste rendern wenn Modal geoeffnet wird
        var varModalEl = document.getElementById("variablen-modal");
        if (varModalEl) {
            varModalEl.addEventListener("show.bs.modal", function () {
                renderVariablenListe();
            });
        }

        // Variable hinzufügen (neue Zeile im Modal)
        var btnVarHinzu = document.getElementById("btn-variable-hinzufuegen");
        if (btnVarHinzu) {
            btnVarHinzu.addEventListener("click", function () {
                var name = prompt("Variablenname (nur Buchstaben, Zahlen, Unterstrich):");
                if (!name) return;
                name = name.trim().replace(/[^\w]/g, "_").replace(/^_+|_+$/g, "");
                if (!name) { alert("Ungültiger Name."); return; }
                if (pfadVariablen[name]) { alert("Variable '" + name + "' existiert bereits."); return; }
                var typ = prompt("Typ: zahl oder text", "zahl");
                typ = (typ || "zahl").trim().toLowerCase();
                if (typ !== "zahl" && typ !== "text") typ = "zahl";
                var wertRaw = prompt("Wert:", typ === "zahl" ? "0" : "");
                if (wertRaw === null) return;
                var wert = typ === "zahl" ? (parseFloat(wertRaw.replace(",", ".")) || 0) : wertRaw.trim();
                var beschreibung = prompt("Beschreibung (optional):", "") || "";
                pfadVariablen[name] = { typ: typ, wert: wert, beschreibung: beschreibung };
                renderVariablenListe();
            });
        }

        // Variable löschen
        var tabelle = document.getElementById("variablen-liste");
        if (tabelle) {
            tabelle.addEventListener("click", function (e) {
                var btn = e.target.closest("[data-action='var-loeschen']");
                if (!btn) return;
                var name = btn.dataset.varName;
                if (!confirm("Variable '" + name + "' löschen?")) return;
                delete pfadVariablen[name];
                renderVariablenListe();
            });
        }

        // Übernehmen-Button
        var btnVarSpeichern = document.getElementById("btn-variablen-speichern");
        if (btnVarSpeichern) {
            btnVarSpeichern.addEventListener("click", function () {
                aktualisierVariablenButtons();
                bootstrap.Modal.getInstance(document.getElementById("variablen-modal")).hide();
            });
        }

        // Variable in Formel einfügen
        document.body.addEventListener("click", function (e) {
            var btn = e.target.closest("[data-action='insert-formel-var']");
            if (!btn) return;
            var varName = btn.dataset.varName;
            var ta = document.getElementById("feld-formel");
            if (!ta) return;
            var start = ta.selectionStart, end = ta.selectionEnd;
            var insertion = "{{" + varName + "}}";
            ta.value = ta.value.slice(0, start) + insertion + ta.value.slice(end);
            ta.focus();
            ta.setSelectionRange(start + insertion.length, start + insertion.length);
        });

        // Variable in Textblock einfügen
        document.body.addEventListener("click", function (e) {
            var btn = e.target.closest("[data-action='insert-textblock-var']");
            if (!btn) return;
            var varName = btn.dataset.varName;
            var ta = document.getElementById("feld-textblock-inhalt");
            if (!ta) return;
            var start = ta.selectionStart, end = ta.selectionEnd;
            var insertion = "{{" + varName + "}}";
            ta.value = ta.value.slice(0, start) + insertion + ta.value.slice(end);
            ta.focus();
            ta.setSelectionRange(start + insertion.length, start + insertion.length);
        });
    });

    // ---------------------------------------------------------------------------
    // Regex-Live-Tester + Ableiter im Feld-Modal
    // ---------------------------------------------------------------------------
    (function () {
        var regexInput    = document.getElementById("feld-regex");
        var btnTesten     = document.getElementById("btn-regex-testen");
        var testerBox     = document.getElementById("regex-tester-box");
        var testText      = document.getElementById("regex-testtext");
        var testErgebnis  = document.getElementById("regex-test-ergebnis");
        var btnAbleiten   = document.getElementById("btn-regex-ableiten");
        var beispielArea  = document.getElementById("regex-beispiele");
        var ableitErgebnis = document.getElementById("regex-ableiten-ergebnis");

        // Testen-Button oeffnet / schliesst Tester-Box
        if (btnTesten) {
            btnTesten.addEventListener("click", function () {
                if (!testerBox) return;
                testerBox.style.display = testerBox.style.display === "none" ? "" : "none";
                if (testerBox.style.display === "" && testText) testText.focus();
            });
        }

        // Live-Test ausfuehren
        function fuehreTestAus() {
            if (!testErgebnis || !regexInput || !testText) return;
            if (!testerBox || testerBox.style.display === "none") return;
            var muster = (regexInput.value || "").trim();
            var text   = testText.value;
            if (!muster) {
                testErgebnis.innerHTML = "<span class='text-muted'>Kein Muster eingegeben.</span>";
                return;
            }
            try {
                var re = new RegExp("^(?:" + muster + ")$");
                if (re.test(text)) {
                    testErgebnis.innerHTML = "<span class='text-success fw-semibold'>Treffer – Eingabe wuerde akzeptiert.</span>";
                } else {
                    testErgebnis.innerHTML = "<span class='text-danger'>Kein Treffer – Eingabe wuerde abgelehnt.</span>";
                }
            } catch (e) {
                testErgebnis.innerHTML = "<span class='text-danger'>Ungueltige Regex: " + escHtmlR(e.message) + "</span>";
            }
        }

        if (regexInput) regexInput.addEventListener("input", fuehreTestAus);
        if (testText)   testText.addEventListener("input", fuehreTestAus);

        // Ableiter: Muster aus Beispiel-Strings generieren
        if (btnAbleiten) {
            btnAbleiten.addEventListener("click", function () {
                if (!beispielArea || !ableitErgebnis) return;
                var zeilen = beispielArea.value.split("\n")
                    .map(function (z) { return z.trim(); })
                    .filter(function (z) { return z.length > 0; });
                if (zeilen.length === 0) {
                    ableitErgebnis.style.display = "";
                    ableitErgebnis.innerHTML = "<span class='text-muted'>Bitte mindestens einen Beispiel-String eingeben.</span>";
                    return;
                }
                var muster = leiteMusterAb(zeilen);
                ableitErgebnis.style.display = "";
                ableitErgebnis.innerHTML =
                    "<strong>Abgeleitetes Muster:</strong> <code id='reg-abgeleitet'>" + escHtmlR(muster) + "</code>" +
                    " <button type='button' class='btn btn-sm btn-outline-secondary ms-2' " +
                    "style='font-size:0.72rem;padding:1px 8px;' id='btn-regex-uebernehmen'>Uebernehmen</button>";
                var btnUebn = document.getElementById("btn-regex-uebernehmen");
                if (btnUebn && regexInput) {
                    btnUebn.addEventListener("click", function () {
                        regexInput.value = muster;
                        fuehreTestAus();
                    });
                }
            });
        }

        // Zeichenklassen-Segmentierung
        function leiteMusterAb(beispiele) {
            var segmente = beispiele.map(zerlege);
            var maxLen = segmente.reduce(function (mx, s) { return Math.max(mx, s.length); }, 0);
            var ergebnis = [];
            for (var i = 0; i < maxLen; i++) {
                var teile = segmente
                    .filter(function (s) { return i < s.length; })
                    .map(function (s) { return s[i]; });
                if (teile.length === 0) break;
                var typen = {};
                teile.forEach(function (t) { typen[t.typ] = true; });
                var laengen = teile.map(function (t) { return t.len; });
                var minL = Math.min.apply(null, laengen);
                var maxL = Math.max.apply(null, laengen);
                if (typen["trenner"]) {
                    var haeufig = haeufigsterWert(teile.map(function (t) { return t.val; }));
                    ergebnis.push(escapeReg(haeufig));
                } else if (typen["gross"] && !typen["ziffer"] && !typen["klein"]) {
                    ergebnis.push(laengenKlasse("[A-Z]", minL, maxL));
                } else if (typen["klein"] && !typen["ziffer"] && !typen["gross"]) {
                    ergebnis.push(laengenKlasse("[a-z]", minL, maxL));
                } else if (typen["ziffer"] && !typen["gross"] && !typen["klein"]) {
                    ergebnis.push(laengenKlasse("\\d", minL, maxL));
                } else if ((typen["gross"] || typen["klein"]) && !typen["ziffer"]) {
                    ergebnis.push(laengenKlasse("[A-Za-z]", minL, maxL));
                } else if (typen["ziffer"] && (typen["gross"] || typen["klein"])) {
                    ergebnis.push(laengenKlasse("[A-Z0-9]", minL, maxL));
                } else {
                    ergebnis.push(laengenKlasse("\\w", minL, maxL));
                }
            }
            return ergebnis.join("");
        }

        function zerlege(str) {
            var segs = [], i = 0;
            while (i < str.length) {
                var c = str[i], typ = zeichenTyp(c);
                if (typ === "trenner") { segs.push({ typ: "trenner", len: 1, val: c }); i++; }
                else {
                    var start = i;
                    while (i < str.length && zeichenTyp(str[i]) === typ) { i++; }
                    segs.push({ typ: typ, len: i - start, val: str.slice(start, i) });
                }
            }
            return segs;
        }

        function zeichenTyp(c) {
            if (c >= "A" && c <= "Z") return "gross";
            if (c >= "a" && c <= "z") return "klein";
            if (c >= "0" && c <= "9") return "ziffer";
            return "trenner";
        }

        function laengenKlasse(klasse, min, max) {
            if (min === max) return min === 1 ? klasse : klasse + "{" + min + "}";
            return klasse + "{" + min + "," + max + "}";
        }

        function escapeReg(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

        function haeufigsterWert(arr) {
            var z = {}, best = arr[0], bestN = 0;
            arr.forEach(function (v) { z[v] = (z[v] || 0) + 1; if (z[v] > bestN) { bestN = z[v]; best = v; } });
            return best;
        }

        function escHtmlR(s) {
            return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }
    }());

}());

// ============================================================================
// Quiz-Import-Modal
// ============================================================================
(function () {
    "use strict";

    var quizImportModal = null;

    function _getCsrf() {
        var el = document.querySelector("[name=csrfmiddlewaretoken]");
        if (el) return el.value;
        var cookie = document.cookie.split(";").find(function (c) { return c.trim().startsWith("csrftoken="); });
        return cookie ? cookie.trim().split("=")[1] : "";
    }

    function _zeigeFehler(msg) {
        var el = document.getElementById("qi-fehler");
        var er = document.getElementById("qi-ergebnis");
        if (el) { el.textContent = msg; el.classList.remove("d-none"); }
        if (er) er.classList.add("d-none");
    }

    function _zeigeErfolg(msg) {
        var el = document.getElementById("qi-ergebnis");
        var ef = document.getElementById("qi-fehler");
        if (el) { el.textContent = msg; el.classList.remove("d-none"); }
        if (ef) ef.classList.add("d-none");
    }

    function _setSpinner(an) {
        var s = document.getElementById("qi-spinner");
        if (s) s.classList.toggle("d-none", !an);
    }

    function _resetMeldungen() {
        var ef = document.getElementById("qi-fehler");
        var er = document.getElementById("qi-ergebnis");
        if (ef) ef.classList.add("d-none");
        if (er) er.classList.add("d-none");
    }

    function _fragenEinfuegen(fragen) {
        if (!Array.isArray(fragen) || fragen.length === 0) {
            _zeigeFehler("Keine Fragen zum Einfügen vorhanden.");
            return;
        }

        var felder = window._quizImportTarget;
        if (!felder) {
            _zeigeFehler("Kein Schritt geöffnet. Bitte öffne zuerst einen Schritt zum Bearbeiten, dann importiere erneut.");
            return;
        }

        fragen.forEach(function (f) { felder.push(f); });

        if (typeof window._quizImportRenderCallback === "function") {
            window._quizImportRenderCallback();
        }

        if (quizImportModal) quizImportModal.hide();
        // kurze Erfolgsmeldung – Modal ist weg, kein Ort mehr zum Zeigen
        alert(fragen.length + " Quizfragen wurden in den Schritt eingefügt. Speichere den Pfad danach.");
    }

    function _importKI() {
        var pdf = document.getElementById("qi-ki-pdf");
        if (!pdf || !pdf.files || !pdf.files[0]) { _zeigeFehler("Bitte wähle eine PDF-Datei aus."); return; }
        var anzahl = document.getElementById("qi-ki-anzahl").value || "10";

        _resetMeldungen();
        _setSpinner(true);

        var fd = new FormData();
        fd.append("pdf", pdf.files[0]);
        fd.append("anzahl", anzahl);
        fd.append("csrfmiddlewaretoken", _getCsrf());

        fetch("/quiz/import/ki/", { method: "POST", body: fd, credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                _setSpinner(false);
                if (data.error) { _zeigeFehler(data.error); return; }
                _fragenEinfuegen(data.fragen);
            })
            .catch(function (e) { _setSpinner(false); _zeigeFehler("Netzwerkfehler: " + e); });
    }

    function _importCSV() {
        var csv = document.getElementById("qi-csv-datei");
        if (!csv || !csv.files || !csv.files[0]) { _zeigeFehler("Bitte wähle eine CSV-Datei aus."); return; }

        _resetMeldungen();
        _setSpinner(true);

        var fd = new FormData();
        fd.append("csv", csv.files[0]);
        fd.append("csrfmiddlewaretoken", _getCsrf());

        fetch("/quiz/import/csv/", { method: "POST", body: fd, credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                _setSpinner(false);
                if (data.error) { _zeigeFehler(data.error); return; }
                _fragenEinfuegen(data.fragen);
            })
            .catch(function (e) { _setSpinner(false); _zeigeFehler("Netzwerkfehler: " + e); });
    }

    function _importDemo(deckName) {
        _resetMeldungen();
        _setSpinner(true);

        var qs = "";
        if (deckName === "einbuergerungstest") {
            var el = document.getElementById("qi-demo-einb-anzahl");
            qs = "?anzahl=" + (el ? el.value : "20");
        }

        fetch("/quiz/import/demo/" + deckName + "/" + qs, { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                _setSpinner(false);
                if (data.error) { _zeigeFehler(data.error); return; }
                _fragenEinfuegen(data.fragen);
            })
            .catch(function (e) { _setSpinner(false); _zeigeFehler("Netzwerkfehler: " + e); });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var modalEl = document.getElementById("quiz-import-modal");
        if (!modalEl) return;
        quizImportModal = new bootstrap.Modal(modalEl);

        var btnOpen = document.getElementById("btn-quiz-import");
        if (btnOpen) {
            btnOpen.addEventListener("click", function () {
                _resetMeldungen();
                quizImportModal.show();
            });
        }

        var kiPdf = document.getElementById("qi-ki-pdf");
        var btnKI = document.getElementById("btn-qi-ki-starten");
        if (kiPdf && btnKI) {
            kiPdf.addEventListener("change", function () { btnKI.disabled = !this.files || !this.files[0]; });
            btnKI.addEventListener("click", _importKI);
        }

        var csvDatei = document.getElementById("qi-csv-datei");
        var btnCSV = document.getElementById("btn-qi-csv-starten");
        if (csvDatei && btnCSV) {
            csvDatei.addEventListener("change", function () { btnCSV.disabled = !this.files || !this.files[0]; });
            btnCSV.addEventListener("click", _importCSV);
        }

        var btnDemoEinb = document.getElementById("btn-qi-demo-einbuergerung");
        if (btnDemoEinb) {
            btnDemoEinb.addEventListener("click", function () { _importDemo("einbuergerungstest"); });
        }
    });

}());

// ---------------------------------------------------------------------------
// Quizpool: DB-Pool Dropdown
// ---------------------------------------------------------------------------
function toggleQuizpoolDb(quelle) {
    var row = document.getElementById("quizpool-db-row");
    if (!row) return;
    if (quelle === "db") {
        row.style.display = "";
        ladePools(null);
    } else {
        row.style.display = "none";
    }
}

function ladePools(selectId) {
    var sel = document.getElementById("quizpool-pool-id");
    if (!sel) return;
    fetch("/quiz/pools/json/")
        .then(function(r) { return r.json(); })
        .then(function(d) {
            sel.innerHTML = '<option value="">— Pool wählen —</option>';
            (d.pools || []).forEach(function(p) {
                var opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                if (selectId && p.id == selectId) opt.selected = true;
                sel.appendChild(opt);
            });
        })
        .catch(function() {
            sel.innerHTML = '<option value="">Fehler beim Laden</option>';
        });
}
