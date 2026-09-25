# SPDX-License-Identifier: Apache-2.0
"""Build content-versioned gallery caches without touching model or operator caches."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TEMPLATE = """/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env serviceworker */
const CACHE = __CACHE__;
const ASSETS = __ASSETS__;
const URLS = new Set(ASSETS.map(path => new URL(path, self.location.href).href));
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(names => Promise.all(
    names.filter(name => name.startsWith('agialpha-gallery-') && name !== CACHE).map(name => caches.delete(name))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const normalized = new URL(event.request.url);
  if (event.request.mode === 'navigate') {
    if (normalized.pathname.endsWith('/')) normalized.pathname += 'index.html';
    normalized.search = '';
  }
  const key = normalized.href;
  if (!URLS.has(key)) return;
  event.respondWith(caches.open(CACHE).then(async cache => {
    if (event.request.mode === 'navigate') {
      try {
        const response = await fetch(event.request);
        if (response.ok) await cache.put(key, response.clone());
        return response;
      } catch {
        return (await cache.match(key)) || Response.error();
      }
    }
    return (await cache.match(key)) || fetch(event.request);
  }));
});
"""


def gather_assets(docs_dir: Path) -> list[str]:
    """Select lightweight gallery resources; Insight manages its own model cache."""
    assets: set[str] = set()
    for item in docs_dir.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(docs_dir)
        if "pyodide" in relative.parts:
            continue
        if "alpha_agi_insight_v1" in relative.parts:
            legacy = "alpha_factory_v1/demos/alpha_agi_insight_v1/"
            allowed = {
                "index.html",
                "style.css",
                "script.js",
                "plotly.min.js",
                "d3.v7.min.js",
                "forecast.json",
                "population.json",
                "tree.json",
            }
            if relative.as_posix().startswith(legacy) and relative.as_posix().removeprefix(legacy) in allowed:
                assets.add(relative.as_posix())
            continue
        if item.name == "service-worker.js":
            continue
        if item.name == "index.html" or relative.as_posix() == "gallery.html":
            assets.add(relative.as_posix())
        elif item.suffix in {".js", ".mjs", ".css", ".svg", ".json"} and (
            "assets" in relative.parts or "stylesheets" in relative.parts
        ):
            assets.add(relative.as_posix())
    return sorted(assets)


def build(docs_dir: Path) -> str:
    """Write root and compatibility workers with a digest of the actual bytes."""
    assets = gather_assets(docs_dir)
    digest = hashlib.sha256()
    for asset in assets:
        digest.update(asset.encode())
        digest.update((docs_dir / asset).read_bytes())
    version = "agialpha-gallery-" + digest.hexdigest()[:16]
    for destination, prefix in [
        (docs_dir / "service-worker.js", "./"),
        (docs_dir / "assets" / "service-worker.js", "../"),
        (docs_dir / "alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js", "../../../"),
    ]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        script = TEMPLATE.replace("__CACHE__", json.dumps(version)).replace(
            "__ASSETS__", json.dumps([prefix + asset for asset in assets], indent=2)
        )
        destination.write_text(script, encoding="utf-8")
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    args = parser.parse_args()
    print(f"Wrote gallery workers with cache {build(args.docs)}")


if __name__ == "__main__":
    main()
