// SPDX-License-Identifier: Apache-2.0
// This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
/* eslint-disable no-restricted-globals */
importScripts('workbox-sw.js');
import {precacheAndRoute} from 'workbox-precaching';
import {registerRoute} from 'workbox-routing';
import {CacheFirst} from 'workbox-strategies';
import {ExpirationPlugin} from 'workbox-expiration';

// replaced during build
const CACHE_VERSION = '__CACHE_VERSION__';
workbox.core.setCacheNameDetails({prefix: CACHE_VERSION});

precacheAndRoute([{"revision":"62b69abec756bb975cf16c3d6dfa6054","url":"workbox-sw.js"},{"revision":"18c85b433c3d03e289f9db0552164f22","url":"manifest.webmanifest"},{"revision":"6f33aa8489dcc310f61d043e9e7893b3","url":"index.html"},{"revision":"e86bb9d7eba6e25530d170e1c6c224e6","url":"icon.svg"},{"revision":"31a28332a5739c7d798936e40cc89fc0","url":"assets/index.DAwkOG1H.css"},{"revision":"392d85689bffa6cdec5454dc68f16422","url":"assets/index-D-bH7Z_k.js"},{"revision":"3e9cb3ea205765685609ede9235de830","url":"assets/index-BUoPmXBX.js"}]);

registerRoute(
  ({request, url}) =>
    request.destination === 'script' ||
    request.destination === 'worker' ||
    request.destination === 'font' ||
    url.pathname.endsWith('.wasm'),
  new CacheFirst({
    cacheName: `${CACHE_VERSION}-assets`,
    plugins: [
      new ExpirationPlugin({maxEntries: 50, maxAgeSeconds: 30 * 24 * 60 * 60})
    ],
  })
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
