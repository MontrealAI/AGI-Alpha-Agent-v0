// SPDX-License-Identifier: Apache-2.0
/* eslint-env serviceworker */
const WORKBOX_SW_HASH = '__WORKBOX_SW_HASH__';
import {precacheAndRoute} from 'workbox-precaching';
import {registerRoute} from 'workbox-routing';
import {CacheFirst} from 'workbox-strategies';

// replaced during build
const CACHE_VERSION = '__CACHE_VERSION__';
async function init() {
  const res = await fetch('assets/lib/workbox-sw.js');
  const buf = await res.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-384', buf);
  const b64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
  if (`sha384-${b64}` !== WORKBOX_SW_HASH) {
    throw new Error('assets/lib/workbox-sw.js hash mismatch');
  }
  importScripts(URL.createObjectURL(new Blob([buf], {type: 'application/javascript'})));
  workbox.core.setCacheNameDetails({prefix: CACHE_VERSION});

  // include translation JSON files in the precache
  precacheAndRoute(self.__WB_MANIFEST);

  registerRoute(
    ({request, url}) =>
      request.destination === 'script' ||
      request.destination === 'worker' ||
      request.destination === 'font' ||
      url.pathname.endsWith('.wasm') ||
      (url.pathname.includes('/ipfs/') && url.pathname.endsWith('.json')),
    new CacheFirst({cacheName: `${CACHE_VERSION}-assets`})
  );

  self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
      self.skipWaiting();
    }
  });

  self.addEventListener('activate', (event) => {
    event.waitUntil(
      caches.keys().then((names) =>
        Promise.all(
          names.map((name) => {
            if (!name.startsWith(CACHE_VERSION)) {
              return caches.delete(name);
            }
            return undefined;
          }),
        ),
      ),
    );
  });
}

init().catch((err) => {
  console.error('Service worker failed to initialize', err);
  self.registration.unregister();
});
