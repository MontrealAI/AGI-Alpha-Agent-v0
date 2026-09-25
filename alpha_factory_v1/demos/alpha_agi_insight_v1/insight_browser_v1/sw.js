// SPDX-License-Identifier: Apache-2.0
/* eslint-env serviceworker */
import {clientsClaim, setCacheNameDetails} from 'workbox-core';
import {precacheAndRoute} from 'workbox-precaching';
import {registerRoute} from 'workbox-routing';
import {CacheFirst} from 'workbox-strategies';

const WORKBOX_SW_HASH = '__WORKBOX_SW_HASH__';
const CACHE_VERSION = '__CACHE_VERSION__';
const CACHE_PREFIX = `alpha-insight-${CACHE_VERSION}`;
setCacheNameDetails({prefix: CACHE_PREFIX});
precacheAndRoute(self.__WB_MANIFEST);
clientsClaim();

// Keep the distributed Workbox asset pinned, without executing a remote loader.
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const res = await fetch('assets/lib/workbox-sw.js');
    if (!res.ok) throw new Error('Workbox asset unavailable');
    const digest = await crypto.subtle.digest('SHA-384', await res.arrayBuffer());
    const b64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
    if (`sha384-${b64}` !== WORKBOX_SW_HASH) throw new Error('Workbox asset hash mismatch');
    await self.skipWaiting();
  })());
});

registerRoute(
  ({request, url}) =>
    request.destination === 'script' ||
    request.destination === 'worker' ||
    request.destination === 'font' ||
    url.pathname.endsWith('.wasm') ||
    (url.pathname.includes('/ipfs/') && url.pathname.endsWith('.json')),
  new CacheFirst({cacheName: `${CACHE_PREFIX}-assets`})
);

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((names) => Promise.all(
    names.filter((name) => name.startsWith('alpha-insight-') && !name.startsWith(CACHE_PREFIX))
      .map((name) => caches.delete(name))
  )));
});
