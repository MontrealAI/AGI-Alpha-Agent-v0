# SPDX-License-Identifier: Apache-2.0
"""Exercise the complete TI browser journey against exact packaged or HTTPS bytes."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from scripts.transformational_evidence import CHECKS, ROOT, asset_identity, read_regular, verify_report
from scripts.validate_successor_alpha import checkout_identity


def public_url(value: str) -> str:
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or parts.netloc != "montrealai.github.io"
        or parts.path
        not in {
            "/AGI-Alpha-Agent-v0/",
            "/AGI-Alpha-Agent-v0/transformational-intelligence/",
            "/AGI-Alpha-Agent-v0/transformational-intelligence/index.html",
        }
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError("TI readback requires a credential-free HTTPS gallery URL")
    if parts.path.endswith("/transformational-intelligence/index.html"):
        return value.removesuffix("index.html")
    if parts.path.endswith("/transformational-intelligence/"):
        return value
    return urljoin(value.rstrip("/") + "/", "transformational-intelligence/")


def verify_received(page: bytes, manifest: bytes, site: Path) -> None:
    directory = site / "transformational-intelligence"
    if page != read_regular(directory / "index.html") or manifest != read_regular(directory / "sources.json"):
        raise ValueError("Public TI workspace differs from the exact packaged bytes")


def verify_public(url: str, site: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        request = playwright.request.new_context(ignore_https_errors=False)
        try:
            raw = []
            for destination in (url, urljoin(url, "sources.json")):
                response = request.get(destination, headers={"Cache-Control": "no-cache"}, timeout=60_000)
                if response.status != 200 or response.url != destination:
                    raise ValueError("TI public readback requires exact successful HTTPS responses")
                raw.append(response.body())
            verify_received(raw[0], raw[1], site)
        finally:
            request.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "docs")
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path, default=Path("evidence/transformational-intelligence"))
    args = parser.parse_args()
    commit, version = checkout_identity()
    identity = asset_identity(ROOT, site=args.site.resolve())
    if identity != asset_identity(ROOT):
        raise ValueError("Packaged TI identity differs from current source")
    entry = (
        public_url(args.url)
        if args.url
        else (args.site.resolve() / "transformational-intelligence/index.html").as_uri()
    )
    if args.url:
        verify_public(entry, args.site)
    path = ROOT / "tests/browser/test_transformational_intelligence_browser.py"
    spec = importlib.util.spec_from_file_location("ti_browser_acceptance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Complete TI browser acceptance is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run_acceptance(entry, expected_page_sha256=identity["pageSha256"] if args.url else None)
    if args.url:
        verify_public(entry, args.site)
    report: dict[str, Any] = {
        "schema": "agialpha.transformational.acceptance.v1",
        "commit": commit,
        "version": version,
        "mode": "public" if args.url else "local",
        "origin": entry,
        "passed": True,
        "sourceIdentity": identity,
        "checks": sorted(CHECKS),
        "public": (
            {"httpsVerified": True, "exactPackagedBytes": True, "savedOfflineJourney": True} if args.url else None
        ),
    }
    verify_report(report, commit, version, mode=report["mode"])
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "mode": report["mode"], "identity": identity}, sort_keys=True))


if __name__ == "__main__":
    main()
