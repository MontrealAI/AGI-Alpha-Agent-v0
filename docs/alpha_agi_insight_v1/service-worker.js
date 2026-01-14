// SPDX-License-Identifier: Apache-2.0
// Minimal service worker for the Insight demo.
self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
