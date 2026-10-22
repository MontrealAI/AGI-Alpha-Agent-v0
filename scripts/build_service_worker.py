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
const RELEASE = __RELEASE__;
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
  } else if (normalized.search) {
    // A newer HTML release must bypass an older worker's cached application assets.
    if (normalized.search !== '?v=' + RELEASE) return;
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


def is_cache_asset(relative: Path) -> bool:
    """Select the same lightweight paths for disk and exact-Git validation."""
    if relative.parts[:2] == ("reports", "computer-use-study"):
        return False
    if {"ascension-wallet", "nova-studio"}.intersection(relative.parts) or (
        "mainnet" in relative.parts and {"ascension-protocol", "ascension"}.intersection(relative.parts)
    ):
        return False
    if "pyodide" in relative.parts:
        return False
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
        return relative.as_posix().startswith(legacy) and relative.as_posix().removeprefix(legacy) in allowed
    if relative.name == "service-worker.js":
        return False
    if relative.name == "index.html" or relative.as_posix() == "gallery.html":
        return True
    if relative.parts[:1] == ("deployments",) and relative.name in {"directory.css", "manifest.json"}:
        return True
    return relative.suffix in {".js", ".mjs", ".css", ".svg", ".json"} and (
        "assets" in relative.parts or "stylesheets" in relative.parts
    )


def gather_assets(docs_dir: Path) -> list[str]:
    """Select lightweight gallery resources; Insight manages its own model cache."""
    result = []
    if docs_dir.is_symlink():
        raise ValueError("Gallery source cannot be a symlink")
    for path in docs_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError("Gallery assets cannot contain symlinks")
        relative = path.relative_to(docs_dir)
        if path.is_file() and is_cache_asset(relative):
            result.append(relative.as_posix())
    return sorted(result)


def render_scripts(asset_bytes: dict[str, bytes], release: str) -> dict[str, str]:
    """Pure rendering: no input data can change the worker program or cache policy."""
    digest = hashlib.sha256()
    assets = sorted(asset_bytes)
    for asset in assets:
        if not is_cache_asset(Path(asset)):
            raise ValueError("Unexpected gallery cache input")
        digest.update(asset.encode())
        digest.update(asset_bytes[asset])
    version = "agialpha-gallery-" + digest.hexdigest()[:16]
    result = {}
    for destination, prefix in [
        ("service-worker.js", "./"),
        ("assets/service-worker.js", "../"),
        ("alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js", "../../../"),
    ]:
        result[destination] = (
            TEMPLATE.replace("__RELEASE__", json.dumps(release))
            .replace("__CACHE__", json.dumps(version))
            .replace("__ASSETS__", json.dumps([prefix + asset for asset in assets], indent=2))
        )
    return result


def build(docs_dir: Path) -> str:
    """Write root and compatibility workers with a digest of the actual bytes."""
    release = json.loads((docs_dir.resolve().parent / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    scripts = render_scripts({name: (docs_dir / name).read_bytes() for name in gather_assets(docs_dir)}, release)
    for name, script in scripts.items():
        destination = docs_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(script, encoding="utf-8")
    cache = json.loads(scripts["service-worker.js"].split("const CACHE = ", 1)[1].split(";", 1)[0])
    if not isinstance(cache, str):
        raise ValueError("Invalid generated cache name")
    return cache


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    args = parser.parse_args()
    print(f"Wrote gallery workers with cache {build(args.docs)}")


if __name__ == "__main__":
    main()
