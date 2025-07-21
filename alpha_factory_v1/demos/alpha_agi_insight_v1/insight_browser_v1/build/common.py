# SPDX-License-Identifier: Apache-2.0
"""Shared build helpers for the Insight browser."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import subprocess
import sys
import re
from pathlib import Path


def sha384(path: Path) -> str:
    """Return the SHA-384 digest of ``path`` in SRI format."""
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def check_gzip_size(path: Path, max_bytes: int = 5 * 1024 * 1024) -> None:
    """Exit if gzip-compressed ``path`` exceeds ``max_bytes``."""
    compressed = gzip.compress(path.read_bytes())
    if len(compressed) > max_bytes:
        sys.exit(f"gzip size {len(compressed)} bytes exceeds limit")


from typing import Any


def generate_service_worker(root: Path, dist_dir: Path, manifest: dict[str, Any]) -> None:
    """Create ``sw.js`` using workbox and inject it into ``index.html``."""
    sw_src = root / "sw.js"
    sw_dest = dist_dir / "sw.js"
    version = json.loads((root / "package.json").read_text())["version"]
    temp_sw = dist_dir / "sw.build.js"
    temp_sw.write_text(sw_src.read_text().replace("__CACHE_VERSION__", version))
    node_script = f"""
const {{injectManifest}} = require('workbox-build');
injectManifest({{
  swSrc: {json.dumps(str(temp_sw))},
  swDest: {json.dumps(str(sw_dest))},
  globDirectory: {json.dumps(str(dist_dir))},
  globPatterns: {json.dumps(manifest['precache'])},
}}).catch(err => {{console.error(err); process.exit(1);}});
"""
    try:
        subprocess.run(["node", "-e", node_script], check=True)
    except FileNotFoundError:
        print(
            "[manual_build] node not found; service worker not generated – offline features disabled",
            file=sys.stderr,
        )
        return
    except subprocess.CalledProcessError as exc:
        print(
            f"[manual_build] workbox build failed: {exc}; offline features disabled",
            file=sys.stderr,
        )
        return
    finally:
        temp_sw.unlink(missing_ok=True)
    sw_hash = sha384(sw_dest)
    wb_path = dist_dir / "workbox-sw.js"
    if not wb_path.exists():
        wb_path = dist_dir / "lib" / "workbox-sw.js"
    wb_hash = sha384(wb_path) if wb_path.exists() else ""
    index_path = dist_dir / "index.html"
    text = index_path.read_text()
    text = text.replace(".register('sw.js')", ".register('service-worker.js')")
    text = text.replace("__SW_HASH__", sw_hash)
    inline_sri = None
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", text, flags=re.DOTALL):
        if "navigator.serviceWorker" in match.group(1):
            snippet = match.group(1).strip()
            reg_hash = hashlib.sha384(snippet.encode()).digest()
            inline_sri = "sha384-" + base64.b64encode(reg_hash).decode()
            break
    if inline_sri:
        text = re.sub(
            r"(script-src 'self' 'wasm-unsafe-eval')(?:\s+'(?:unsafe-inline|sha384-[^']+)')?",
            rf"\1 'unsafe-inline' '{inline_sri}'",
            text,
        )
    else:
        print("WARNING: service worker registration script not found", file=sys.stderr)
    index_path.write_text(text)
    sw_text = sw_dest.read_text()
    sw_text = sw_text.replace("__WORKBOX_SW_HASH__", wb_hash)
    sw_dest.write_text(sw_text)
