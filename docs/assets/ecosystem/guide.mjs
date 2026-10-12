// SPDX-License-Identifier: Apache-2.0
// Optional reading and clipboard controls; the complete guide is static HTML.
const french = document.documentElement.lang === "fr";
const size = document.getElementById("text-size");
const copy = document.getElementById("copy-token");
const status = document.getElementById("token-status");
let large = new URLSearchParams(location.search).get("text") === "large";

function render() {
    document.documentElement.classList.toggle("large-text", large);
    size.setAttribute("aria-pressed", String(large));
    const url = new URL(location.href);
    if (large) url.searchParams.set("text", "large");
    else url.searchParams.delete("text");
    if (url.href !== location.href) history.replaceState(history.state, "", url.href);
    for (const link of document.querySelectorAll("[data-reading-link]")) {
        const target = new URL(link.href);
        if (large) target.searchParams.set("text", "large");
        else target.searchParams.delete("text");
        link.href = target.href;
    }
}

size.addEventListener("click", () => {
    large = !large;
    render();
});
window.addEventListener("popstate", () => {
    large = new URLSearchParams(location.search).get("text") === "large";
    render();
});
render();
size.hidden = false;
if (navigator.clipboard?.writeText) {
    copy.hidden = false;
    copy.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(document.getElementById("token-address").textContent.trim());
            status.textContent = french ? "Adresse complète du jeton copiée." : "Full token address copied.";
        } catch {
            status.textContent = french
                ? "Sélectionnez et copiez l’adresse complète ci-dessus."
                : "Select and copy the full address above.";
        }
    });
}
