# SPDX-License-Identifier: Apache-2.0
"""Generate docs/assets/service-worker.js with updated precache list."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

HEADER_TEMPLATE = """/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env serviceworker */
const CACHE = '{cache}';
self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches
      .open(CACHE)
      .then(async (cache) => {{
        const assets = ["""

FOOTER = """        ];
        await cache.addAll(assets);
      })
      .catch(() => undefined),
  );
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.map((name) => (name !== CACHE ? caches.delete(name) : undefined)),
      ),
    ),
  );
  self.clients.claim();
});
self.addEventListener('fetch', (event) => {{
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {{
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {{
        try {{
          const resp = await fetch(event.request);
          if (resp.ok) {{
            cache.put(event.request, resp.clone());
          }
          return resp;
        }} catch (err) {{
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
            .then((resp) => {{
              if (resp.ok) {{
                cache.put(event.request, resp.clone());
              }}
              return resp;
            }})
            .catch(() => cached),
      ),
    ),
  );
});
"""


def gather_assets(docs_dir: Path) -> list[str]:
    base_assets = docs_dir / "assets"
    assets: list[str] = []
    allowed = {".js", ".css", ".svg", ".json", ".wasm", ".tar", ".cast"}
    pyodide_dir = base_assets / "pyodide"
    if pyodide_dir.is_dir():
        order = ["pyodide.js", "pyodide.asm.wasm", "pyodide-lock.json"]
        for name in order:
            file = pyodide_dir / name
            if file.is_file() and file.suffix in allowed:
                rel = Path("assets") / "pyodide" / file.name
                assets.append(rel.as_posix())
    for item in sorted(docs_dir.iterdir()):
        if not item.is_dir() or item.name == "assets":
            continue
        a_dir = item / "assets"
        if a_dir.is_dir():
            for file in sorted(a_dir.rglob("*")):
                if file.is_file() and file.suffix in allowed:
                    rel = Path("..") / item.name / "assets" / file.relative_to(a_dir)
                    assets.append(rel.as_posix())

    # Add index.html pages so navigation works offline without prior visits
    for file in sorted(docs_dir.rglob("index.html")):
        if file.is_file():
            rel = Path("..") / file.relative_to(docs_dir)
            assets.append(rel.as_posix())
    return assets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", default="docs", help="Documentation directory")
    args = parser.parse_args()
    docs_dir = Path(args.docs)
    assets = gather_assets(docs_dir)
    version = "v" + hashlib.sha1("\n".join(assets).encode()).hexdigest()[:8]
    sw_path = docs_dir / "assets" / "service-worker.js"
    header = HEADER_TEMPLATE.format(cache=version)
    lines = [header]
    for asset in assets:
        lines.append(f"          '{asset}',")
    lines.append(FOOTER.replace("{{", "{").replace("}}", "}"))
    sw_path.write_text("\n".join(lines))
    print(f"Wrote {sw_path} with cache {version}")


if __name__ == "__main__":
    main()
