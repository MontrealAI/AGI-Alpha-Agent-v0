# SPDX-License-Identifier: Apache-2.0
"""Verify exact packaged/public Discovery Lab bytes and run the same complete synthetic journey."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_PAGE_BYTES = 8_000_000
MAX_MANIFEST_BYTES = 200_000
MAX_SOURCE_BYTES = 8_000_000
HASH = re.compile(r"[0-9a-f]{64}\Z")
GENERATOR = "scripts/generate_successor_capability.py"
ASSET = "successor/capabilities/index.html"
AXE_VERSION = "4.10.3"
AXE_SHA256 = "880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb"
AXE_INTEGRITY = "sha512-Xm7bpRXnDSX2YE2YFfBk2FnF0ep6tmG7xPh8iHee8MIcrgq762Nkce856dYtJYLkuIoYZvGfTs/PbZhideTcEg=="


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def discovery_url(value: str) -> str:
    """Accept an exact Discovery Lab route or gallery base with a strict public HTTPS boundary."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or "?" in value
        or "#" in value
        or "\\" in value
        or any(ord(char) <= 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("Public acceptance requires HTTPS without credentials, query, fragment or backslash")
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("Public acceptance requires a valid HTTPS authority") from error
    if parsed.path.endswith("/successor/capabilities/index.html"):
        return value.removesuffix("index.html")
    if parsed.path.endswith("/successor/capabilities/"):
        return value
    if parsed.path.endswith("/successor/capabilities"):
        return value + "/"
    return urljoin(value.rstrip("/") + "/", "successor/capabilities/")


def manifest_data(raw: bytes) -> dict[str, Any]:
    """Validate the finite source language and independently recompute its catalogue commitment."""
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Discovery Lab manifest exceeds its byte cap")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate source manifest key")
            result[key] = value
        return result

    value: Any = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "sourceHash", "sources"}
        or value["schema"] != "successor-capability-source/v1"
        or not isinstance(value["sourceHash"], str)
        or not HASH.fullmatch(value["sourceHash"])
        or not isinstance(value["sources"], dict)
        or not value["sources"]
    ):
        raise ValueError("Unsupported Discovery Lab source manifest")
    for name, digest in value["sources"].items():
        if not isinstance(name, str) or not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("Invalid Discovery Lab source identity")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name or not name or name == ".":
            raise ValueError("Discovery Lab source paths must stay inside the repository")
    commitment = sha256(json.dumps(value["sources"], sort_keys=True, separators=(",", ":")).encode())
    if commitment != value["sourceHash"]:
        raise ValueError("Discovery Lab catalogue source hash differs")
    return dict(value)


def verify_packaged(site: Path, source_root: Path = ROOT) -> dict[str, Any]:
    """Rebuild the fixed generator in a temporary source copy and compare exact packaged bytes."""
    site, source_root = site.resolve(), source_root.resolve()
    page_path = site / ASSET
    manifest_path = page_path.with_name("sources.json")
    if not page_path.resolve().is_relative_to(site) or not manifest_path.resolve().is_relative_to(site):
        raise ValueError("Packaged Discovery Lab paths escape the supplied site")
    page, manifest_raw = page_path.read_bytes(), manifest_path.read_bytes()
    if len(page) > MAX_PAGE_BYTES:
        raise ValueError("Discovery Lab page exceeds its byte cap")
    manifest = manifest_data(manifest_raw)
    if GENERATOR not in manifest["sources"]:
        raise ValueError("Discovery Lab manifest omits its deterministic generator")
    captured: dict[str, bytes] = {}
    total = 0
    for name, digest in manifest["sources"].items():
        path = (source_root / name).resolve()
        if not path.is_relative_to(source_root) or not path.is_file():
            raise ValueError("Discovery Lab source escapes or is missing: " + name)
        raw = path.read_bytes()
        total += len(raw)
        if total > MAX_SOURCE_BYTES or sha256(raw) != digest:
            raise ValueError("Discovery Lab source differs from checkout: " + name)
        captured[name] = raw
    with tempfile.TemporaryDirectory(prefix="discovery-lab-generation-") as temporary:
        destination = Path(temporary)
        for name, raw in captured.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        subprocess.run(
            [sys.executable, str(destination / GENERATOR)], cwd=destination, check=True, capture_output=True, timeout=30
        )
        generated = destination / "docs" / ASSET
        if page != generated.read_bytes() or manifest_raw != generated.with_name("sources.json").read_bytes():
            raise ValueError("Packaged Discovery Lab differs from exact generated checkout bytes")
    checkout_page = source_root / "docs" / ASSET
    if page != checkout_page.read_bytes() or manifest_raw != checkout_page.with_name("sources.json").read_bytes():
        raise ValueError("Packaged Discovery Lab differs from the current generated checkout")
    return {
        "page": page,
        "manifest": manifest_raw,
        "pagePath": str(page_path),
        "pageSha256": sha256(page),
        "manifestSha256": sha256(manifest_raw),
        "sourceHash": manifest["sourceHash"],
        "sourcesChecked": len(captured),
    }


def verify_received(page: bytes, manifest: bytes, expected: dict[str, Any]) -> None:
    """Refuse even a self-consistent older public page or differently encoded source manifest."""
    manifest_data(manifest)
    if len(page) > MAX_PAGE_BYTES or page != expected["page"] or manifest != expected["manifest"]:
        raise ValueError("Public Discovery Lab differs from the exact packaged/generated bytes")


def verify_public(url: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Verify certificate-checked, nonredirected HTTPS responses before and after the full journey."""
    from playwright.sync_api import sync_playwright

    url = discovery_url(url)
    with sync_playwright() as playwright:
        request = playwright.request.new_context(ignore_https_errors=False)
        try:
            received: list[bytes] = []
            for destination, media in ((url, "text/html"), (urljoin(url, "sources.json"), "application/json")):
                response = request.get(
                    destination, headers={"Cache-Control": "no-cache"}, timeout=60_000, max_redirects=0
                )
                if response.status != 200 or response.url != destination:
                    raise ValueError("Public Discovery Lab response is missing, redirected or unsuccessful")
                if response.headers.get("content-type", "").split(";", 1)[0].strip().lower() != media:
                    raise ValueError("Public Discovery Lab response has the wrong media type")
                received.append(response.body())
            verify_received(received[0], received[1], expected)
        finally:
            request.dispose()
    return {
        "url": url,
        "httpsVerified": True,
        "exactPackagedBytes": True,
        "redirected": False,
        "assets": ["index.html", "sources.json"],
    }


def browser_acceptance(entry: str, output: Path, expected_page_sha256: str) -> dict[str, Any]:
    """Load one complete suite for packaged and public acceptance, with no reduced smoke path."""
    if sys.flags.optimize:
        raise RuntimeError("Discovery Lab acceptance requires Python assertion checks enabled")
    path = ROOT / "tests/browser/test_discovery_lab_browser.py"
    spec = importlib.util.spec_from_file_location("discovery_lab_browser_acceptance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("The complete Discovery Lab browser suite is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
        result = module.run_acceptance(entry, output.resolve(), expected_page_sha256=expected_page_sha256)
    finally:
        sys.path.pop(0)
    required = {
        "budget-inconclusive",
        "six-stage-accepted",
        "both-zero-cap-drafts",
        "edited-constraint-rejected",
        "retained-campaign-selection",
        "stronger-successor",
        "history-reload",
        "resolved-accessibility",
        "responsive-390-320",
        "keyboard",
        "no-external-requests",
        "exact-page-before-and-after",
    }
    if (
        not isinstance(result, dict)
        or result.get("passed") is not True
        or result.get("entryUrl") != entry
        or result.get("pageSha256") != expected_page_sha256
        or result.get("campaigns") != 4
        or not isinstance(result.get("checks"), list)
        or not required.issubset(result["checks"])
    ):
        raise ValueError("The complete Discovery Lab journey did not pass")
    return result


def checkout_identity() -> tuple[str, str, str]:
    """Retain exact Git commit/tree and declared software version without claiming release approval."""

    def git(value: str) -> str:
        return subprocess.check_output(["git", "rev-parse", value], cwd=ROOT, text=True, timeout=15).strip()

    commit, tree = git("HEAD"), git("HEAD^{tree}")
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (commit, tree)):
        raise ValueError("Discovery Lab acceptance requires an exact Git identity")
    if os.environ.get("GITHUB_SHA") not in (None, commit):
        raise ValueError("Discovery Lab checkout differs from the declared workflow commit")
    catalog = manifest_data((ROOT / "docs/successor/capabilities/sources.json").read_bytes())
    relevant = set(catalog["sources"]) | {
        "docs/" + ASSET,
        "docs/successor/capabilities/sources.json",
        "scripts/validate_discovery_lab.py",
        "tests/browser/test_discovery_lab_browser.py",
        "tests/browser/test_successor_capability_accessibility.py",
        "pyproject.toml",
        "tests/browser/package.json",
        "tests/browser/package-lock.json",
    }
    for name in sorted(relevant):
        try:
            committed = subprocess.check_output(
                ["git", "show", commit + ":" + name], cwd=ROOT, timeout=15, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as error:
            raise ValueError(
                "Discovery Lab acceptance input is absent from the exact checkout commit: " + name
            ) from error
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or path.read_bytes() != committed:
            raise ValueError("Discovery Lab acceptance input differs from the exact checkout commit: " + name)
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version):
        raise ValueError("Discovery Lab software version is missing")
    return commit, tree, version


def validate_auditor(script: Path, source_root: Path = ROOT) -> dict[str, Any]:
    """Bind the installed auditor to the integrity-checked axe-core 4.10.3 distribution member."""
    lock_raw = (source_root / "tests/browser/package-lock.json").read_bytes()
    lock = json.loads(lock_raw)
    package = lock.get("packages", {}).get("node_modules/axe-core", {})
    if (
        package.get("version") != AXE_VERSION
        or package.get("integrity") != AXE_INTEGRITY
        or package.get("resolved") != "https://registry.npmjs.org/axe-core/-/axe-core-4.10.3.tgz"
    ):
        raise ValueError("The accessibility auditor differs from the reviewed package lock")
    raw = script.resolve().read_bytes()
    if sha256(raw) != AXE_SHA256:
        raise ValueError("The accessibility auditor bytes differ from pinned axe-core 4.10.3")
    return {
        "package": "axe-core",
        "version": AXE_VERSION,
        "scriptSha256": AXE_SHA256,
        "packageIntegrity": AXE_INTEGRITY,
        "packageLockSha256": sha256(lock_raw),
    }


def main() -> None:
    if sys.flags.optimize:
        raise RuntimeError("Discovery Lab acceptance requires Python assertion checks enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--url", help="Public gallery base or complete Discovery Lab HTTPS URL")
    parser.add_argument("--output", type=Path, default=Path("evidence/discovery-lab"))
    parser.add_argument("--axe-script", type=Path, default=ROOT / "tests/browser/node_modules/axe-core/axe.min.js")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.axe_script.resolve().is_file():
        raise ValueError("Install the pinned accessibility auditor before Discovery Lab acceptance")
    identity = checkout_identity()
    auditor = validate_auditor(args.axe_script.resolve())
    expected = verify_packaged(args.site.resolve())
    public_url = discovery_url(args.url) if args.url else None
    before = verify_public(public_url, expected) if public_url else None
    with tempfile.TemporaryDirectory(prefix="discovery-pinned-auditor-") as temporary:
        snapshot = Path(temporary) / "axe.min.js"
        auditor_bytes = args.axe_script.resolve().read_bytes()
        if sha256(auditor_bytes) != auditor["scriptSha256"]:
            raise ValueError("The pinned accessibility auditor changed during capture")
        snapshot.write_bytes(auditor_bytes)
        os.environ["AXE_SCRIPT"] = str(snapshot)
        journey = browser_acceptance(
            public_url or Path(expected["pagePath"]).as_uri(), args.output / "browser", expected["pageSha256"]
        )
    if validate_auditor(args.axe_script.resolve()) != auditor:
        raise ValueError("The pinned accessibility auditor changed during acceptance")
    after = verify_public(public_url, expected) if public_url else None
    repeated = verify_packaged(args.site.resolve())
    if (
        identity != checkout_identity()
        or repeated["page"] != expected["page"]
        or repeated["manifest"] != expected["manifest"]
    ):
        raise ValueError("Discovery Lab source/package changed during acceptance")
    report = {
        "schema": "agialpha.discovery-lab.acceptance/v1",
        "passed": True,
        "commit": identity[0],
        "tree": identity[1],
        "version": identity[2],
        "mode": "public" if public_url else "packaged-local",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "sourceIdentity": {
            key: expected[key] for key in ("pageSha256", "manifestSha256", "sourceHash", "sourcesChecked")
        },
        "accessibilityAuditor": auditor,
        "publicBefore": before,
        "publicAfter": after,
        "journey": journey,
        "scope": (
            "Exact generated-byte and complete synthetic browser acceptance only. "
            "No external execution, payment or broader release qualification."
        ),
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": True,
                "mode": report["mode"],
                "sourceHash": expected["sourceHash"],
                "checks": len(journey["checks"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
