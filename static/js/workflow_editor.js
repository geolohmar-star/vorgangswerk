// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2026 Georg Klein
// Workflow-Editor: vis.js basierter Graph-Editor fuer Workflow-Templates

(function () {
    "use strict";

    // ---------------------------------------------------------------------------
    // Daten aus Template laden
    // ---------------------------------------------------------------------------
    var gruppen = JSON.parse(document.getElementById("gruppen-data").textContent);
    var users = JSON.parse(document.getElementById("users-data").textContent);
    var templateIdEl = document.getElementById("template-id");
    var templateId = templateIdEl ? parseInt(templateIdEl.dataset.id, 10) : null;

    // Gruppen-Dropdown befuellen
    var nodeGruppeSelect = document.getElementById("node-gruppe");
    gruppen.forEach(function (g) {
        var opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = g.name;
        nodeGruppeSelect.appendChild(opt);
    });

    // User-Dropdown befuellen
    var nodeUserSelect = document.getElementById("node-user");
    users.forEach(function (u) {
        var opt = document.createElement("option");
        opt.value = u.id;
        var label = (u.first_name || u.last_name)
            ? u.first_name + " " + u.last_name
            : u.username;
        opt.textContent = label;
        nodeUserSelect.appendChild(opt);
    });

    // ---------------------------------------------------------------------------
    // vis.js Netzwerk initialisieren
    // ---------------------------------------------------------------------------
    var nodes = new vis.DataSet();
    var edges = new vis.DataSet();

    // Interne Konfiguration pro Node speichern
    var nodeConfig = {};
    var edgeConfig = {};
    var nodeCounter = 0;
    var edgeCounter = 0;

    var container = document.getElementById("editor-canvas");
    var networkData = { nodes: nodes, edges: edges };
    var options = {
        manipulation: {
            enabled: false
        },
        nodes: {
            shape: "box",
            font: { size: 13 },
            widthConstraint: { maximum: 180 },
            color: {
                background: "#e8f4e8",
                border: "#1a4d2e",
                highlight: { background: "#c8e6c9", border: "#1a4d2e" }
            }
        },
        edges: {
            arrows: { to: { enabled: true, scaleFactor: 0.8 } },
            smooth: { type: "curvedCW", roundness: 0.2 },
            font: { size: 11, align: "middle" },
            color: { color: "#666" }
        },
        physics: { enabled: false },
        interaction: {
            dragNodes: true,
            dragView: true,
            zoomView: true,
            selectConnectedEdges: false
        }
    };

    var network = new vis.Network(container, networkData, options);

    // ---------------------------------------------------------------------------
    // Bestehenden Workflow laden (wenn Template vorhanden)
    // ---------------------------------------------------------------------------
    if (templateId) {
        fetch("/workflow/editor/load/" + templateId + "/")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                data.nodes.forEach(function (n) {
                    var id = "n_" + (++nodeCounter);
                    nodeConfig[id] = n;
                    nodes.add(_nodeVisObj(id, n));
                    n._vis_id = id;
                });
                data.edges.forEach(function (e) {
                    var fromNode = data.nodes.find(function (n) { return n.id === e.from; });
                    var toNode = e.to ? data.nodes.find(function (n) { return n.id === e.to; }) : null;
                    if (!fromNode) return;
                    var eid = "e_" + (++edgeCounter);
                    edgeConfig[eid] = e;
                    edges.add({
                        id: eid,
                        from: fromNode._vis_id,
                        to: toNode ? toNode._vis_id : null,
                        label: e.label || ""
                    });
                });
            });
    }

    // ---------------------------------------------------------------------------
    // Hilfsfunktionen
    // ---------------------------------------------------------------------------
    function _nodeVisObj(id, cfg) {
        var farbe = {
            background: cfg.schritt_typ === "auto" ? "#fff3cd"
                : cfg.schritt_typ === "decision" ? "#d1ecf1" : "#e8f4e8",
            border: "#1a4d2e"
        };
        return {
            id: id,
            label: cfg.label || cfg.titel || "Schritt",
            x: cfg.x || 200,
            y: cfg.y || 200,
            color: farbe
        };
    }

    function _nodeDefaultConfig() {
        return {
            label: "Neuer Schritt",
            beschreibung: "",
            schritt_typ: "task",
            aktion_typ: "pruefen",
            zustaendig_rolle: "gruppe",
            gruppeId: null,
            userId: null,
            frist_tage: 3
        };
    }

    // ---------------------------------------------------------------------------
    // Schritt hinzufuegen
    // ---------------------------------------------------------------------------
    document.getElementById("btn-add-node").addEventListener("click", function () {
        var id = "n_" + (++nodeCounter);
        var cfg = _nodeDefaultConfig();
        nodeConfig[id] = cfg;
        var canvasCenter = network.getViewPosition();
        cfg.x = canvasCenter.x;
        cfg.y = canvasCenter.y;
        nodes.add(_nodeVisObj(id, cfg));
        network.selectNodes([id]);
        _showNodePanel(id);
    });

    // ---------------------------------------------------------------------------
    // Verbindung hinzufuegen (Modus aktivieren)
    // ---------------------------------------------------------------------------
    var edgeModeActive = false;
    var edgeFromNode = null;

    document.getElementById("btn-add-edge").addEventListener("click", function () {
        edgeModeActive = !edgeModeActive;
        edgeFromNode = null;
        var btn = document.getElementById("btn-add-edge");
        btn.textContent = edgeModeActive ? "Verbindung: Quell-Node klicken" : "+ Verbindung";
        btn.classList.toggle("btn-warning", edgeModeActive);
        btn.classList.toggle("btn-outline-secondary", !edgeModeActive);
    });

    network.on("click", function (params) {
        if (!edgeModeActive) return;
        if (params.nodes.length === 0) return;

        var clickedId = params.nodes[0];
        if (!edgeFromNode) {
            edgeFromNode = clickedId;
            var btn = document.getElementById("btn-add-edge");
            btn.textContent = "Verbindung: Ziel-Node klicken (oder 'Ende' fuer Ende-Node)";
        } else {
            var eid = "e_" + (++edgeCounter);
            edgeConfig[eid] = { bedingung_typ: "immer", label: "" };
            edges.add({ id: eid, from: edgeFromNode, to: clickedId, label: "" });
            edgeFromNode = null;
            edgeModeActive = false;
            var btn2 = document.getElementById("btn-add-edge");
            btn2.textContent = "+ Verbindung";
            btn2.classList.remove("btn-warning");
            btn2.classList.add("btn-outline-secondary");
        }
    });

    // ---------------------------------------------------------------------------
    // Loeschen
    // ---------------------------------------------------------------------------
    document.getElementById("btn-delete").addEventListener("click", function () {
        var sel = network.getSelection();
        sel.nodes.forEach(function (id) {
            nodes.remove(id);
            delete nodeConfig[id];
        });
        sel.edges.forEach(function (id) {
            edges.remove(id);
            delete edgeConfig[id];
        });
    });

    // Entf-Taste
    document.addEventListener("keydown", function (e) {
        if (e.key === "Delete" || e.key === "Backspace") {
            if (document.activeElement.tagName === "INPUT" ||
                document.activeElement.tagName === "TEXTAREA") return;
            var sel = network.getSelection();
            sel.nodes.forEach(function (id) {
                nodes.remove(id);
                delete nodeConfig[id];
            });
            sel.edges.forEach(function (id) {
                edges.remove(id);
                delete edgeConfig[id];
            });
        }
    });

    // ---------------------------------------------------------------------------
    // Selektion
    // ---------------------------------------------------------------------------
    var selectedNodeId = null;
    var selectedEdgeId = null;

    network.on("selectNode", function (params) {
        selectedNodeId = params.nodes[0];
        selectedEdgeId = null;
        _showNodePanel(selectedNodeId);
        document.getElementById("selected-edge-panel").classList.add("d-none");
    });

    network.on("selectEdge", function (params) {
        if (edgeModeActive) return;
        selectedEdgeId = params.edges[0];
        selectedNodeId = null;
        _showEdgePanel(selectedEdgeId);
        document.getElementById("selected-node-panel").classList.add("d-none");
    });

    network.on("deselectNode", function () {
        document.getElementById("selected-node-panel").classList.add("d-none");
    });

    network.on("deselectEdge", function () {
        document.getElementById("selected-edge-panel").classList.add("d-none");
    });

    // ---------------------------------------------------------------------------
    // Node-Panel
    // ---------------------------------------------------------------------------
    function _showNodePanel(id) {
        var cfg = nodeConfig[id] || _nodeDefaultConfig();
        document.getElementById("node-titel").value = cfg.label || cfg.titel || "";
        document.getElementById("node-beschreibung").value = cfg.beschreibung || "";
        document.getElementById("node-schritt-typ").value = cfg.schritt_typ || "task";
        document.getElementById("node-aktion-typ").value = cfg.aktion_typ || "pruefen";
        document.getElementById("node-rolle").value = cfg.zustaendig_rolle || "gruppe";
        document.getElementById("node-gruppe").value = cfg.gruppeId || "";
        document.getElementById("node-user").value = cfg.userId || "";
        document.getElementById("node-frist").value = cfg.frist_tage || 3;
        // Verteiler-Config laden
        var vc = cfg.auto_config || {};
        document.getElementById("vc-empfaenger").value = vc.empfaenger || "";
        document.getElementById("vc-empfaenger-namen").value = vc.empfaenger_namen || "";
        document.getElementById("vc-dokumente").value = vc.dokumente || "antrag_pdf";
        document.getElementById("vc-betreff").value = vc.betreff || "";
        document.getElementById("vc-begleittext").value = vc.begleittext || "";
        _updateVerteilerUI(cfg.aktion_typ || "pruefen");
        document.getElementById("selected-node-panel").classList.remove("d-none");
        _updateNodeRolleUI(cfg.zustaendig_rolle || "gruppe");
    }

    document.getElementById("node-rolle").addEventListener("change", function () {
        _updateNodeRolleUI(this.value);
    });

    document.getElementById("node-aktion-typ").addEventListener("change", function () {
        _updateVerteilerUI(this.value);
    });

    function _updateVerteilerUI(aktionTyp) {
        var panel = document.getElementById("verteiler-config");
        if (panel) panel.classList.toggle("d-none", aktionTyp !== "verteilen");
    }

    function _updateNodeRolleUI(rolle) {
        var gruppeWrap = document.getElementById("gruppe-select-wrap");
        var userWrap = document.getElementById("user-select-wrap");
        gruppeWrap.classList.toggle("d-none", rolle !== "gruppe");
        userWrap.classList.toggle("d-none", rolle !== "spezifischer_user");
    }

    document.getElementById("btn-node-apply").addEventListener("click", function () {
        if (!selectedNodeId) return;
        var cfg = nodeConfig[selectedNodeId] || {};
        cfg.label = document.getElementById("node-titel").value;
        cfg.beschreibung = document.getElementById("node-beschreibung").value;
        cfg.schritt_typ = document.getElementById("node-schritt-typ").value;
        cfg.aktion_typ = document.getElementById("node-aktion-typ").value;
        cfg.zustaendig_rolle = document.getElementById("node-rolle").value;
        cfg.gruppeId = parseInt(document.getElementById("node-gruppe").value) || null;
        cfg.userId = parseInt(document.getElementById("node-user").value) || null;
        cfg.frist_tage = parseInt(document.getElementById("node-frist").value) || 3;
        // Verteiler-Config speichern
        if (cfg.aktion_typ === "verteilen") {
            cfg.auto_config = {
                empfaenger:         document.getElementById("vc-empfaenger").value.trim(),
                empfaenger_namen:   document.getElementById("vc-empfaenger-namen").value.trim(),
                dokumente:          document.getElementById("vc-dokumente").value,
                betreff:            document.getElementById("vc-betreff").value.trim(),
                begleittext:        document.getElementById("vc-begleittext").value.trim(),
            };
            cfg.schritt_typ = "auto";
        }
        nodeConfig[selectedNodeId] = cfg;

        // Position aus dem Netzwerk holen
        var pos = network.getPosition(selectedNodeId);
        cfg.x = pos.x;
        cfg.y = pos.y;

        nodes.update(_nodeVisObj(selectedNodeId, cfg));
    });

    document.getElementById("btn-node-close").addEventListener("click", function () {
        document.getElementById("selected-node-panel").classList.add("d-none");
    });

    // ---------------------------------------------------------------------------
    // Edge-Panel
    // ---------------------------------------------------------------------------
    function _showEdgePanel(id) {
        var cfg = edgeConfig[id] || { bedingung_typ: "immer", label: "" };
        document.getElementById("edge-bedingung-typ").value = cfg.bedingung_typ || "immer";
        document.getElementById("edge-entscheidung").value = cfg.bedingung_entscheidung || "";
        document.getElementById("edge-label").value = cfg.label || "";
        document.getElementById("selected-edge-panel").classList.remove("d-none");
        _updateEdgeBedingungUI(cfg.bedingung_typ || "immer");
    }

    document.getElementById("edge-bedingung-typ").addEventListener("change", function () {
        _updateEdgeBedingungUI(this.value);
    });

    function _updateEdgeBedingungUI(typ) {
        var wrap = document.getElementById("edge-entscheidung-wrap");
        wrap.classList.toggle("d-none", typ !== "entscheidung");
    }

    document.getElementById("btn-edge-apply").addEventListener("click", function () {
        if (!selectedEdgeId) return;
        var cfg = edgeConfig[selectedEdgeId] || {};
        cfg.bedingung_typ = document.getElementById("edge-bedingung-typ").value;
        cfg.bedingung_entscheidung = document.getElementById("edge-entscheidung").value || null;
        cfg.label = document.getElementById("edge-label").value;
        edgeConfig[selectedEdgeId] = cfg;
        edges.update({ id: selectedEdgeId, label: cfg.label });
    });

    document.getElementById("btn-edge-close").addEventListener("click", function () {
        document.getElementById("selected-edge-panel").classList.add("d-none");
    });

    // ---------------------------------------------------------------------------
    // Speichern
    // ---------------------------------------------------------------------------
    document.getElementById("btn-save").addEventListener("click", function () {
        // Positionen aller Nodes aktualisieren
        nodes.getIds().forEach(function (id) {
            var pos = network.getPosition(id);
            if (nodeConfig[id]) {
                nodeConfig[id].x = pos.x;
                nodeConfig[id].y = pos.y;
            }
        });

        var nodesPayload = nodes.getIds().map(function (id) {
            var cfg = nodeConfig[id] || _nodeDefaultConfig();
            return Object.assign({}, cfg, { id: id });
        });

        var edgesPayload = edges.getIds().map(function (eid) {
            var e = edges.get(eid);
            var cfg = edgeConfig[eid] || {};
            return Object.assign({}, cfg, {
                from: e.from,
                to: e.to || null
            });
        });

        var payload = {
            template_id: templateId,
            meta: {
                name: document.getElementById("meta-name").value,
                beschreibung: document.getElementById("meta-beschreibung").value,
                kategorie: document.getElementById("meta-kategorie").value,
                ist_aktiv: true
            },
            nodes: nodesPayload,
            edges: edgesPayload
        };

        var csrf = document.querySelector("meta[name='csrf-token']").content;
        fetch("/workflow/editor/save/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf
            },
            body: JSON.stringify(payload)
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.status === "ok") {
                templateId = data.template_id;
                var hint = document.getElementById("editor-hint");
                hint.textContent = "Gespeichert.";
                hint.classList.add("text-success");
                setTimeout(function () {
                    hint.textContent = "Klick auf Leinwand: Schritt hinzufuegen. Ziehen: Verbindung erstellen. Entf: loeschen.";
                    hint.classList.remove("text-success");
                }, 2000);
                // URL aktualisieren ohne Reload
                if (window.history.replaceState) {
                    window.history.replaceState({}, "", "/workflow/editor/" + templateId + "/");
                }
            } else {
                alert("Fehler: " + JSON.stringify(data));
            }
        })
        .catch(function (err) {
            alert("Netzwerkfehler: " + err);
        });
    });

    // ---------------------------------------------------------------------------
    // Organisations-Autocomplete im Verteiler
    // ---------------------------------------------------------------------------
    var orgSuche = document.getElementById("vc-org-suche");
    var orgDropdown = document.getElementById("vc-org-dropdown");
    var orgTimer = null;

    if (orgSuche) {
        orgSuche.addEventListener("input", function () {
            clearTimeout(orgTimer);
            var q = orgSuche.value.trim();
            if (q.length < 2) { orgDropdown.style.display = "none"; return; }
            orgTimer = setTimeout(function () {
                fetch("/postbuch/organisationen/autocomplete/?q=" + encodeURIComponent(q))
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        orgDropdown.innerHTML = "";
                        if (!data.length) { orgDropdown.style.display = "none"; return; }
                        data.forEach(function (o) {
                            var item = document.createElement("a");
                            item.className = "dropdown-item py-1";
                            item.href = "#";
                            item.innerHTML = "<strong>" + o.name + "</strong>"
                                + (o.email ? " <small class='text-muted'>" + o.email + "</small>" : "")
                                + " <span class='badge bg-light text-secondary border ms-1'>" + o.typ + "</span>";
                            item.addEventListener("click", function (e) {
                                e.preventDefault();
                                // E-Mail anhängen
                                var empf = document.getElementById("vc-empfaenger");
                                var namen = document.getElementById("vc-empfaenger-namen");
                                if (o.email) {
                                    empf.value = empf.value
                                        ? empf.value.replace(/,\s*$/, "") + ", " + o.email
                                        : o.email;
                                }
                                namen.value = namen.value
                                    ? namen.value.replace(/,\s*$/, "") + ", " + o.name
                                    : o.name;
                                orgSuche.value = "";
                                orgDropdown.style.display = "none";
                            });
                            orgDropdown.appendChild(item);
                        });
                        orgDropdown.style.removeProperty("display");
                    });
            }, 250);
        });

        document.addEventListener("click", function (e) {
            if (!orgSuche.contains(e.target)) orgDropdown.style.display = "none";
        });
    }

}());
