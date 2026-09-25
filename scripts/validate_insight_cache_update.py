#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prove that host-only and worker-only changes invalidate the cached Insight page."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def index_revision(dist: Path) -> str:
    """Read the actual Workbox manifest and verify its non-circular assets."""
    worker = (dist / "service-worker.js").read_text()
    match = re.search(r"precacheAndRoute\((\[.*?\])[,)]", worker, re.DOTALL)
    if match is None:
        raise ValueError("Workbox precache manifest is missing")
    entries = {item["url"]: item["revision"] for item in json.loads(match[1])}
    for name, revision in entries.items():
        if name != "index.html":
            assert hashlib.md5((dist / name).read_bytes(), usedforsecurity=False).hexdigest() == revision, name
    # The page embeds the worker's integrity hash, so its revision deliberately
    # covers the policy-complete template and all worker inputs before that
    # circular reference is filled.
    html = (dist / "index.html").read_text()
    integrity = "sha384-" + base64.b64encode(hashlib.sha384(worker.encode()).digest()).decode()
    assert integrity in html
    return entries["index.html"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    browser = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
    dist = browser / "dist"
    host = browser / "sandbox_worker_host.js"
    original = host.read_bytes()
    worker_source = browser / "sw.js"
    original_source = worker_source.read_bytes()
    before = index_revision(dist)
    initial_worker = (dist / "service-worker.js").read_bytes()
    initial_index = (dist / "index.html").read_bytes()
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT"}}
    env["FETCH_ASSETS_SKIP_LLM"] = "1"
    try:
        host.write_bytes(original + b"\n// Cache revision acceptance probe.\n")
        subprocess.run(["npm", "run", "build"], cwd=browser, env=env, check=True, timeout=180)
        after = index_revision(dist)
        policy = "sha384-" + base64.b64encode(hashlib.sha384(host.read_bytes()).digest()).decode()
        assert policy in (dist / "index.html").read_text()
        assert before != after, "host-only policy change reused the old cached page revision"
        host.write_bytes(original)
        worker_source.write_bytes(original_source + b"\nself.__alphaCacheRevisionProbe = true;\n")
        subprocess.run(["npm", "run", "build"], cwd=browser, env=env, check=True, timeout=180)
        assert index_revision(dist) != before, "worker-only change reused a page with outdated worker integrity"
    finally:
        host.write_bytes(original)
        worker_source.write_bytes(original_source)
        subprocess.run(["npm", "run", "build"], cwd=browser, env=env, check=True, timeout=180)
    assert index_revision(dist) == before
    assert (dist / "service-worker.js").read_bytes() == initial_worker
    assert (dist / "index.html").read_bytes() == initial_index
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "passed": True,
                "host_only_change_invalidates_page": True,
                "worker_only_change_invalidates_page": True,
                "worker_integrity_valid": True,
                "original_build_restored": True,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
