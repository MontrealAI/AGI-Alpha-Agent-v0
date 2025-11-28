// SPDX-License-Identifier: Apache-2.0
/* eslint-env serviceworker */

const CACHE_VERSION = '0.1.0';

const CORE_ASSETS = [
  './',
  './index.html',
  './insight.bundle.js',
  './d3.v7.min.js',
  './d3.exports.js',
  './plotly.min.js',
  './plotly.min.js.LICENSE.txt',
  './script.js',
  './style.css',
  './manifest.json',
  './tree.json',
  './population.json',
  './forecast.json',
  './assets/logs.json',
  './assets/preview.svg',
  '../assets/pyodide_demo.js',
  './assets/script.js',
  './assets/style.css',
  './favicon.svg',
  './data/critics/innovations.txt',
  './docs/API.md',
  './docs/bus_tls.md',
  './src/i18n/en.json',
  './src/i18n/es.json',
  './src/i18n/fr.json',
  './src/i18n/zh.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(`${CACHE_VERSION}-precache`).then((cache) => cache.addAll(CORE_ASSETS)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names.map((name) => {
            if (!name.startsWith(CACHE_VERSION)) {
              return caches.delete(name);
            }
            return undefined;
          }),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;

      return fetch(request)
        .then((resp) => {
          const clone = resp.clone();
          caches.open(`${CACHE_VERSION}-dynamic`).then((cache) => cache.put(request, clone));
          return resp;
        })
        .catch(() => cached || Response.error());
    }),
  );
});
