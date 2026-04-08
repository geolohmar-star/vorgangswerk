/**
 * pfad_liste.js – Bestaetigungsdialog fuer Pfad-Loeschen
 */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-loeschen-form]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            var name    = form.dataset.name    || "diesen Pfad";
            var anzahl  = parseInt(form.dataset.anzahl || "0", 10);
            var hinweis = anzahl > 0
                ? "\n\nACHTUNG: " + anzahl + " Einreichung" + (anzahl !== 1 ? "en" : "") + " werden ebenfalls geloescht!"
                : "";
            if (!confirm('Pfad "' + name + '" wirklich loeschen?' + hinweis)) {
                e.preventDefault();
            }
        });
    });
});
