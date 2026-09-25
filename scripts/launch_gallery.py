#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Launch the Alpha-Factory demo gallery.

This helper prints the project disclaimer and opens the GitHub Pages
mirror under ``alpha_factory_v1/demos/``. If the remote site is
unreachable it builds a local copy and serves it from an ephemeral HTTP
server so users can explore the demos offline.
"""
from __future__ import annotations

import subprocess
import re
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
import webbrowser

from alpha_factory_v1.utils.disclaimer import DISCLAIMER


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_local_site(repo_root: Path) -> bool:
    script = repo_root / "scripts" / "build_gallery_site.sh"
    if not script.is_file():
        return False
    try:
        subprocess.run([str(script)], check=True, cwd=repo_root)
    except Exception:
        return False
    return True


def _gallery_url() -> str:
    try:
        remote = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        remote = ""
    match = re.search(r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?$", remote)
    org, repo = match.groups() if match else ("MontrealAI", "AGI-Alpha-Agent-v0")
    return f"https://{org}.github.io/{repo}/alpha_factory_v1/demos/"


def _remote_available(url: str) -> bool:
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=3) as resp:
            status = getattr(resp, "status", None)
        return bool(status and 200 <= int(status) < 300)
    except Exception:
        return False


def main() -> None:
    print(DISCLAIMER, file=sys.stderr)
    base_url = _gallery_url()
    index_url = base_url + "index.html"
    if _remote_available(index_url):
        webbrowser.open(index_url)
        return
    site_dir = REPO_ROOT / "site"
    local_page = site_dir / "alpha_factory_v1" / "demos" / "index.html"
    if not local_page.is_file():
        print("Remote gallery unavailable. Building local copy...", file=sys.stderr)
        if not _build_local_site(REPO_ROOT) or not local_page.is_file():
            print("Gallery not found. Run scripts/build_gallery_site.sh", file=sys.stderr)
            sys.exit(1)
    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        local_url = f"http://127.0.0.1:{port}/alpha_factory_v1/demos/index.html"
        print(f"Serving local gallery at {local_url}", file=sys.stderr)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            webbrowser.open(local_url)
            thread.join()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
