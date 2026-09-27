/* SPDX-License-Identifier: Apache-2.0 */
// Activate newly deployed assets without discarding work begun during installation.
(() => {
    if (!("serviceWorker" in navigator) || !navigator.serviceWorker.controller)
        return;
    navigator.serviceWorker
        .getRegistration()
        .then((registration) => registration?.update())
        .catch(() => {}); // An offline visit continues using the verified cache.
    let edited = false;
    let handled = false;
    document.addEventListener(
        "input",
        () => {
            edited = true;
        },
        { once: true, capture: true },
    );
    document.addEventListener(
        "click",
        () => {
            edited = true;
        },
        { once: true, capture: true },
    );
    navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (handled) return;
        handled = true;
        if (!edited) {
            location.reload();
            return;
        }
        const notice = document.createElement("aside");
        notice.setAttribute("aria-label", "Workspace update");
        notice.setAttribute("role", "status");
        notice.className = "cache-update-notice";
        const message = document.createElement("p");
        message.textContent =
            "A new workspace version is ready. Save or export your work before reloading.";
        const reload = document.createElement("button");
        reload.textContent = "Reload updated workspace";
        reload.addEventListener("click", () => location.reload());
        notice.append(message, reload);
        document.body.append(notice);
    });
})();
