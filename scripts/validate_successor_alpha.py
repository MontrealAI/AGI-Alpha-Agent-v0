# SPDX-License-Identifier: Apache-2.0
"""Qualify exact packaged/public SUCCESSOR Alpha bytes and the complete browser journey."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_PAGE_BYTES = 8_000_000
MAX_MANIFEST_BYTES = 200_000
HASH = re.compile(r"[0-9a-f]{64}\Z")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def flagship_url(value: str) -> str:
    """Require public HTTPS and accept either the gallery base or exact flagship URL."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Public qualification requires an HTTPS URL without credentials, query or fragment")
    if parsed.path.endswith("/successor/alpha/index.html"):
        return value.removesuffix("index.html")
    if parsed.path.endswith("/successor/alpha/"):
        return value
    if parsed.path.endswith("/successor/alpha"):
        return value + "/"
    return urljoin(value.rstrip("/") + "/", "successor/alpha/")


def manifest_data(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Flagship source manifest exceeds its byte budget")
    value = json.loads(raw.decode("utf-8"))
    expected = {"schema", "sources", "engineSourceHash", "pageSha256"}
    if not isinstance(value, dict) or set(value) != expected or value["schema"] != "successor-alpha-source/v1":
        raise ValueError("Unsupported flagship source manifest")
    if not HASH.fullmatch(str(value["engineSourceHash"])) or not HASH.fullmatch(str(value["pageSha256"])):
        raise ValueError("Flagship manifest lacks exact page and implementation identities")
    sources = value["sources"]
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Flagship source inventory is empty")
    for name, digest in sources.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("Invalid source inventory entry")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name:
            raise ValueError("Source inventory paths must stay inside the repository")
    return value


def verify_packaged(site: Path, source_root: Path = ROOT) -> dict[str, Any]:
    """Bind the packaged page to every exact reviewed implementation source."""
    page_path = site.resolve() / "successor/alpha/index.html"
    manifest_path = page_path.with_name("sources.json")
    page = page_path.read_bytes()
    manifest_raw = manifest_path.read_bytes()
    manifest = manifest_data(manifest_raw)
    if len(page) > MAX_PAGE_BYTES or sha256(page) != manifest["pageSha256"]:
        raise ValueError("Packaged flagship page differs from its source manifest")
    for name, expected in manifest["sources"].items():
        path = (source_root / name).resolve()
        if not path.is_relative_to(source_root.resolve()) or sha256(path.read_bytes()) != expected:
            raise ValueError(f"Packaged flagship source identity differs from checkout: {name}")
    return {
        "page": page,
        "manifest": manifest_raw,
        "pagePath": str(page_path),
        "pageSha256": sha256(page),
        "manifestSha256": sha256(manifest_raw),
        "engineSourceHash": manifest["engineSourceHash"],
        "sourcesChecked": len(manifest["sources"]),
    }


def verify_received(page: bytes, manifest: bytes, expected: dict[str, Any]) -> None:
    """Reject stale or different public bytes even if that page has a self-consistent manifest."""
    observed = manifest_data(manifest)
    if len(page) > MAX_PAGE_BYTES or sha256(page) != observed["pageSha256"]:
        raise ValueError("Public flagship page does not match its advertised source identity")
    if page != expected["page"] or manifest != expected["manifest"]:
        raise ValueError("Public flagship differs from the exact packaged release bytes")


def verify_public(url: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Read actual HTTPS responses with certificate verification and compare their exact bodies."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        request = playwright.request.new_context(ignore_https_errors=False)
        try:
            received: list[bytes] = []
            for destination in (url, urljoin(url, "sources.json")):
                response = request.get(destination, headers={"Cache-Control": "no-cache"}, timeout=60_000)
                if response.status != 200 or response.url != destination:
                    raise ValueError(
                        f"Expected exact public response: {destination}; got {response.status} {response.url}"
                    )
                received.append(response.body())
            verify_received(received[0], received[1], expected)
        finally:
            request.dispose()
    return {"url": url, "httpsVerified": True, "exactPackagedBytes": True, "assets": ["index.html", "sources.json"]}


def browser_acceptance(entry: str, output: Path, expected_page_sha256: str | None = None) -> dict[str, Any]:
    """Reuse the mandatory mission suite instead of maintaining a weaker public smoke test."""
    path = ROOT / "tests/browser/test_successor_alpha_browser.py"
    spec = importlib.util.spec_from_file_location("successor_alpha_browser_acceptance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("The complete flagship browser acceptance module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_acceptance(entry, output.resolve(), expected_page_sha256=expected_page_sha256)
    if not isinstance(result, dict) or result.get("passed") is not True:
        raise ValueError("Full flagship browser acceptance did not pass")
    return result


def checkout_identity() -> tuple[str, str]:
    """Bind the acceptance report to the checked-out release identity."""
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=15).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Acceptance requires an exact Git checkout commit")
    declared = os.environ.get("GITHUB_SHA")
    if declared and declared != commit:
        raise ValueError("The checked-out commit differs from the workflow source identity")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version):
        raise ValueError("Acceptance requires an explicit release version")
    return commit, version


def main() -> None:
    from scripts.successor_alpha_evidence import asset_identity, verify_report

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--url", help="Public gallery base URL or complete SUCCESSOR Alpha URL; HTTPS required")
    parser.add_argument("--output", type=Path, default=Path("evidence/successor-alpha"))
    parser.add_argument("--axe-script", type=Path, default=ROOT / "tests/browser/node_modules/axe-core/axe.min.js")
    args = parser.parse_args()
    args.site = args.site.resolve()
    args.output = args.output.resolve()
    args.axe_script = args.axe_script.resolve()
    if not args.axe_script.is_file():
        raise ValueError("Install the pinned browser accessibility auditor before qualifying the flagship")
    commit, version = checkout_identity()
    expected = verify_packaged(args.site)
    identity = {key: expected[key] for key in ("pageSha256", "manifestSha256", "engineSourceHash", "sourcesChecked")}
    if identity != asset_identity(ROOT):
        raise ValueError("Packaged flagship identity differs from the complete current source closure")
    public_url = flagship_url(args.url) if args.url else None
    public = verify_public(public_url, expected) if public_url else None
    os.environ["AXE_SCRIPT"] = str(args.axe_script.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    journey = browser_acceptance(
        public_url or Path(expected["pagePath"]).as_uri(),
        args.output / "browser",
        expected["pageSha256"] if public_url else None,
    )
    if public_url:
        verify_public(public_url, expected)
    report = {
        "schema": "agialpha.successor-alpha.acceptance.v1",
        "commit": commit,
        "version": version,
        "mode": "public" if public_url else "local",
        "origin": journey["entryUrl"],
        "passed": True,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "sourceIdentity": {
            key: expected[key] for key in ("pageSha256", "manifestSha256", "engineSourceHash", "sourcesChecked")
        },
        "public": public,
        "journey": journey,
    }
    verify_report(report, commit, version, mode=report["mode"])
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": True,
                "pageSha256": expected["pageSha256"],
                "public": public_url,
                "checks": len(journey["checks"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
