/* SPDX-License-Identifier: Apache-2.0 */
(() => {
  window.PINNER_TOKEN = atob('');
  window.OTEL_ENDPOINT = atob('');
  window.IPFS_GATEWAY = atob('');

  if (typeof window.toast !== 'function') {
    window.toast = msg => {
      const toast = document.getElementById('toast');
      if (toast) {
        toast.textContent = msg;
        toast.classList.add('show');
        clearTimeout(window.toast.id);
        window.toast.id = window.setTimeout(() => toast.classList.remove('show'), 2000);
        return;
      }
      // Avoid noisy console warnings in offline smoke tests.
    };
  }

  const markReady = () => {
    document.documentElement.dataset.insightReady = '1';
  };

  const shouldSkipServiceWorker = () => {
    const hostname = window.location.hostname;
    if (navigator.webdriver) {
      return true;
    }
    return hostname === 'localhost' || hostname === '127.0.0.1';
  };

  window.addEventListener('load', () => {
    window.requestAnimationFrame(markReady);

    if (!('serviceWorker' in navigator) || shouldSkipServiceWorker()) {
      return;
    }

    const SW_URL = 'service-worker.js';
    const SW_HASH = 'sha384-kQo+PZJcRiSq81DoHg7dyh+D8v/XRPNke0/dvpo2pT968hYeKRy2hfcZk4KYSIh5';

    window
      .fetch(SW_URL)
      .then(res => res.arrayBuffer())
      .then(buf => window.crypto.subtle.digest('SHA-384', buf))
      .then(digest => {
        const b64 = window.btoa(String.fromCharCode(...new Uint8Array(digest)));
        if (`sha384-${b64}` !== SW_HASH) {
          throw new Error('Service worker hash mismatch');
        }
        return navigator.serviceWorker.register(SW_URL);
      })
      .then(registration =>
        navigator.serviceWorker.ready.then(() => {
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (!newWorker) return;
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed') {
                window.toast('Update available — reload to use the latest version.');
              }
            });
          });
        }),
      )
      .catch(() => {
        // Keep failures silent in production to avoid breaking offline demos.
      });
  });
})();
