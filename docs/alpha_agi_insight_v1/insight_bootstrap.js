// SPDX-License-Identifier: Apache-2.0
const markReady = () => {
  document.documentElement.dataset.insightReady = '1';
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', markReady, {once: true});
} else {
  markReady();
}

if (typeof window.toast !== 'function') {
  window.toast = (msg) => {
    const t = document.getElementById('toast');
    if (t) {
      t.textContent = msg;
      t.classList.add('show');
      clearTimeout(window.toast.id);
      window.toast.id = window.setTimeout(() => t.classList.remove('show'), 2000);
      return;
    }
    console.warn(msg);
  };
}

window.PINNER_TOKEN = atob('');
window.OTEL_ENDPOINT = atob('');
window.IPFS_GATEWAY = atob('');

const SW_URL = 'sw.js';
const SW_HASH = 'sha384-jDVWK0Oeu8IVp27/4rYIkLaIUPdbOpFA8fEe5aPcVTMQ/mABGrVYWBhM7GXRBC/H';

if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const res = await fetch(SW_URL);
      const buf = await res.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-384', buf);
      const b64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
      if (`sha384-${b64}` !== SW_HASH) {
        throw new Error('Service worker hash mismatch');
      }

      navigator.serviceWorker.register(SW_URL).then((registration) => {
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
        });
      });
    } catch (err) {
      console.error(err);
      window.toast(`Service worker failed: ${err.message}`);
    }
  });
}
