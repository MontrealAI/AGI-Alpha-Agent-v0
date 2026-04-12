// SPDX-License-Identifier: Apache-2.0
// Bootstrap globals and service worker wiring for the Insight demo.

window.PINNER_TOKEN = "";
window.OTEL_ENDPOINT = "";
window.IPFS_GATEWAY = "";

if (typeof window.toast !== "function") {
  window.toast = (msg) => {
    const toastNode = document.getElementById("toast");
    if (!toastNode) {
      console.warn(msg);
      return;
    }

    toastNode.textContent = String(msg);
    toastNode.classList.add("show");
    const toastFn = window.toast;
    if (typeof toastFn.id === "number") {
      window.clearTimeout(toastFn.id);
    }
    toastFn.id = window.setTimeout(() => toastNode.classList.remove("show"), 2000);
  };
}

const SW_URL = "service-worker.js";

const supportsServiceWorker = (() => {
  try {
    return Boolean(navigator.serviceWorker);
  } catch {
    return false;
  }
})();

if (supportsServiceWorker && !navigator.webdriver) {
  window.addEventListener("load", async () => {
    try {
      const response = await fetch(SW_URL);
      const buffer = await response.arrayBuffer();
      const digest = await crypto.subtle.digest("SHA-384", buffer);
      const digestB64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
      const swHash = typeof window.SW_HASH === "string" ? window.SW_HASH : "";
      if (!swHash || `sha384-${digestB64}` !== swHash) {
        throw new Error("Service worker hash mismatch");
      }

      const registration = await navigator.serviceWorker.register(SW_URL);
      await navigator.serviceWorker.ready;
      registration.addEventListener("updatefound", () => {
        const installingWorker = registration.installing;
        if (!installingWorker) {
          return;
        }

        installingWorker.addEventListener("statechange", () => {
          if (installingWorker.state === "installed") {
            window.toast("Update available — reload to use the latest version.");
          }
        });
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(err);
      window.toast(`Service worker failed: ${message}`);
    }
  });
}
