/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env serviceworker */
const CACHE = 'v6387cdd6';
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then(async (cache) => {
        const assets = [
          'assets/pyodide/pyodide.js',
          'assets/pyodide/pyodide.asm.wasm',
          'assets/pyodide/pyodide-lock.json',
          '../TERMS_AND_CONDITIONS/assets/preview.svg',
          '../aiga_meta_evolution/assets/bridge_overview.svg',
          '../aiga_meta_evolution/assets/logs.json',
          '../aiga_meta_evolution/assets/preview.svg',
          '../aiga_meta_evolution/assets/script.js',
          '../aiga_meta_evolution/assets/style.css',
          '../alpha_agi_business_2_v1/assets/logs.json',
          '../alpha_agi_business_2_v1/assets/preview.svg',
          '../alpha_agi_business_2_v1/assets/script.js',
          '../alpha_agi_business_2_v1/assets/style.css',
          '../alpha_agi_business_3_v1/assets/logs.json',
          '../alpha_agi_business_3_v1/assets/preview.svg',
          '../alpha_agi_business_3_v1/assets/script.js',
          '../alpha_agi_business_3_v1/assets/style.css',
          '../alpha_agi_business_v1/assets/logs.json',
          '../alpha_agi_business_v1/assets/preview.svg',
          '../alpha_agi_business_v1/assets/script.js',
          '../alpha_agi_business_v1/assets/style.css',
          '../alpha_agi_insight_v0/assets/logs.json',
          '../alpha_agi_insight_v0/assets/preview.svg',
          '../alpha_agi_insight_v0/assets/script.js',
          '../alpha_agi_insight_v0/assets/style.css',
          '../alpha_agi_insight_v1/assets/logs.json',
          '../alpha_agi_insight_v1/assets/preview.svg',
          '../alpha_agi_insight_v1/assets/script.js',
          '../alpha_agi_insight_v1/assets/style.css',
          '../alpha_agi_marketplace_v1/assets/logs.json',
          '../alpha_agi_marketplace_v1/assets/preview.svg',
          '../alpha_agi_marketplace_v1/assets/script.js',
          '../alpha_agi_marketplace_v1/assets/style.css',
          '../alpha_asi_world_model/assets/logs.json',
          '../alpha_asi_world_model/assets/preview.svg',
          '../alpha_asi_world_model/assets/script.js',
          '../alpha_asi_world_model/assets/style.css',
          '../alpha_super_planner_v1/assets/preview.svg',
          '../cross_industry_alpha_factory/assets/logs.json',
          '../cross_industry_alpha_factory/assets/preview.svg',
          '../cross_industry_alpha_factory/assets/script.js',
          '../cross_industry_alpha_factory/assets/style.css',
          '../demos/assets/readme_preview.svg',
          '../era_of_experience/assets/logs.json',
          '../era_of_experience/assets/preview.svg',
          '../era_of_experience/assets/script.js',
          '../era_of_experience/assets/style.css',
          '../finance_alpha/assets/logs.json',
          '../finance_alpha/assets/preview.svg',
          '../finance_alpha/assets/script.js',
          '../finance_alpha/assets/style.css',
          '../gpt2_small_cli/assets/preview.svg',
          '../macro_sentinel/assets/logs.json',
          '../macro_sentinel/assets/preview.svg',
          '../macro_sentinel/assets/script.js',
          '../macro_sentinel/assets/style.css',
          '../meta_agentic_agi/assets/logo.svg',
          '../meta_agentic_agi/assets/logs.json',
          '../meta_agentic_agi/assets/preview.svg',
          '../meta_agentic_agi/assets/script.js',
          '../meta_agentic_agi/assets/style.css',
          '../meta_agentic_agi/assets/theme-dark.css',
          '../meta_agentic_agi/assets/theme-light.css',
          '../meta_agentic_agi_v2/assets/logo.svg',
          '../meta_agentic_agi_v2/assets/logs.json',
          '../meta_agentic_agi_v2/assets/preview.svg',
          '../meta_agentic_agi_v2/assets/script.js',
          '../meta_agentic_agi_v2/assets/style.css',
          '../meta_agentic_agi_v2/assets/theme-dark.css',
          '../meta_agentic_agi_v2/assets/theme-light.css',
          '../meta_agentic_agi_v3/assets/logo.svg',
          '../meta_agentic_agi_v3/assets/logs.json',
          '../meta_agentic_agi_v3/assets/preview.svg',
          '../meta_agentic_agi_v3/assets/script.js',
          '../meta_agentic_agi_v3/assets/style.css',
          '../meta_agentic_agi_v3/assets/theme-dark.css',
          '../meta_agentic_agi_v3/assets/theme-light.css',
          '../meta_agentic_tree_search_v0/assets/logs.json',
          '../meta_agentic_tree_search_v0/assets/preview.svg',
          '../meta_agentic_tree_search_v0/assets/script.js',
          '../meta_agentic_tree_search_v0/assets/style.css',
          '../muzero_planning/assets/logs.json',
          '../muzero_planning/assets/preview.svg',
          '../muzero_planning/assets/script.js',
          '../muzero_planning/assets/style.css',
          '../muzeromctsllmagent_v0/assets/logs.json',
          '../muzeromctsllmagent_v0/assets/preview.svg',
          '../muzeromctsllmagent_v0/assets/script.js',
          '../muzeromctsllmagent_v0/assets/style.css',
          '../omni_factory_demo/assets/logs.json',
          '../omni_factory_demo/assets/preview.svg',
          '../omni_factory_demo/assets/script.js',
          '../omni_factory_demo/assets/style.css',
          '../self_healing_repo/assets/logs.json',
          '../self_healing_repo/assets/preview.svg',
          '../self_healing_repo/assets/script.js',
          '../self_healing_repo/assets/style.css',
          '../solving_agi_governance/assets/logs.json',
          '../solving_agi_governance/assets/preview.svg',
          '../solving_agi_governance/assets/script.js',
          '../solving_agi_governance/assets/style.css',
          '../sovereign_agentic_agialpha_agent_v0/assets/logs.json',
          '../sovereign_agentic_agialpha_agent_v0/assets/preview.svg',
          '../sovereign_agentic_agialpha_agent_v0/assets/script.js',
          '../sovereign_agentic_agialpha_agent_v0/assets/style.css',
          '../utils/assets/logs.json',
          '../utils/assets/preview.svg',
          '../utils/assets/script.js',
          '../utils/assets/style.css',
          '../aiga_meta_evolution/index.html',
          '../alpha_agi_business_2_v1/index.html',
          '../alpha_agi_business_3_v1/index.html',
          '../alpha_agi_business_v1/index.html',
          '../alpha_agi_insight_v0/index.html',
          '../alpha_agi_insight_v1/index.html',
          '../alpha_agi_marketplace_v1/index.html',
          '../alpha_asi_world_model/index.html',
          '../alpha_factory_v1/demos/aiga_meta_evolution/index.html',
          '../alpha_factory_v1/demos/alpha_agi_business_2_v1/index.html',
          '../alpha_factory_v1/demos/alpha_agi_business_3_v1/index.html',
          '../alpha_factory_v1/demos/alpha_agi_business_v1/index.html',
          '../alpha_factory_v1/demos/alpha_agi_insight_v0/index.html',
          '../alpha_factory_v1/demos/alpha_agi_insight_v1/index.html',
          '../alpha_factory_v1/demos/alpha_agi_marketplace_v1/index.html',
          '../alpha_factory_v1/demos/alpha_asi_world_model/index.html',
          '../alpha_factory_v1/demos/cross_industry_alpha_factory/index.html',
          '../alpha_factory_v1/demos/era_of_experience/index.html',
          '../alpha_factory_v1/demos/finance_alpha/index.html',
          '../alpha_factory_v1/demos/index.html',
          '../alpha_factory_v1/demos/macro_sentinel/index.html',
          '../alpha_factory_v1/demos/meta_agentic_agi/index.html',
          '../alpha_factory_v1/demos/meta_agentic_agi_v2/index.html',
          '../alpha_factory_v1/demos/meta_agentic_agi_v3/index.html',
          '../alpha_factory_v1/demos/meta_agentic_tree_search_v0/index.html',
          '../alpha_factory_v1/demos/muzero_planning/index.html',
          '../alpha_factory_v1/demos/muzeromctsllmagent_v0/index.html',
          '../alpha_factory_v1/demos/omni_factory_demo/index.html',
          '../alpha_factory_v1/demos/self_healing_repo/index.html',
          '../alpha_factory_v1/demos/solving_agi_governance/index.html',
          '../alpha_factory_v1/demos/sovereign_agentic_agialpha_agent_v0/index.html',
          '../alpha_factory_v1/index.html',
          '../cross_industry_alpha_factory/index.html',
          '../demos/index.html',
          '../era_of_experience/index.html',
          '../finance_alpha/index.html',
          '../index.html',
          '../macro_sentinel/index.html',
          '../meta_agentic_agi/index.html',
          '../meta_agentic_agi_v2/index.html',
          '../meta_agentic_agi_v3/index.html',
          '../meta_agentic_tree_search_v0/index.html',
          '../muzero_planning/index.html',
          '../muzeromctsllmagent_v0/index.html',
          '../omni_factory_demo/index.html',
          '../self_healing_repo/index.html',
          '../solving_agi_governance/index.html',
          '../sovereign_agentic_agialpha_agent_v0/index.html',
          '../utils/index.html',
        ];
        await cache.addAll(assets);
      })
      .catch(() => undefined),
  );
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.map((name) => (name !== CACHE ? caches.delete(name) : undefined)),
      ),
    ),
  );
  self.clients.claim();
});
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        try {
          const resp = await fetch(event.request);
          if (resp.ok) {
            cache.put(event.request, resp.clone());
          }
          return resp;
        } catch (err) {
          const cached =
            (await cache.match(event.request)) ||
            (await cache.match(`pyodide/${url.pathname.split('/').pop()}`));
          return cached || Promise.reject(err);
        }
      }),
    );
    return;
  }
  event.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(event.request).then(
        (cached) =>
          cached ||
          fetch(event.request)
            .then((resp) => {
              if (resp.ok) {
                cache.put(event.request, resp.clone());
              }
              return resp;
            })
            .catch(() => cached),
      ),
    ),
  );
// SPDX-License-Identifier: Apache-2.0
/* eslint-env serviceworker */
const WORKBOX_SW_HASH = 'sha384-R7RXlLLrbRAy0JWTwv62SHZwpjwwc7C0wjnLGa5bRxm6YCl5zw87IRvhlleSM5zd';
import {precacheAndRoute} from 'workbox-precaching';
import {registerRoute} from 'workbox-routing';
import {CacheFirst} from 'workbox-strategies';

// replaced during build
const CACHE_VERSION = '0.1.0';
async function init() {
  const res = await fetch('lib/workbox-sw.js');
  const buf = await res.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-384', buf);
  const b64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
  if (`sha384-${b64}` !== WORKBOX_SW_HASH) {
    throw new Error('lib/workbox-sw.js hash mismatch');
  }
  importScripts(URL.createObjectURL(new Blob([buf], {type: 'application/javascript'})));
  workbox.core.setCacheNameDetails({prefix: CACHE_VERSION});

  // include translation JSON files in the precache
  precacheAndRoute([]);

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
