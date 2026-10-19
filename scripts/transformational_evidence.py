# SPDX-License-Identifier: Apache-2.0
"""Bind bounded TI browser acceptance and release assets to exact source bytes."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 8_000_000
HASH = re.compile(r"[0-9a-f]{64}\Z")
CHECKS = frozenset(
    {
        "fixed-artifact-and-controls",
        "native-request-result-project-handoff",
        "prefix-and-utf8-import-recovery",
        "concurrent-edit-preserved",
        "credential-shaped-input-refused",
        "saved-offline-english-french",
        "keyboard-and-mobile",
    }
)


def read_regular(path: Path, maximum: int = MAX_BYTES) -> bytes:
    """Refuse linked, absent, oversized or changing release inputs."""
    if any(parent.is_symlink() for parent in (path, *path.parents)) or not path.is_file():
        raise ValueError("TI release input must be an ordinary file")
    before = path.stat()
    if not 0 < before.st_size <= maximum:
        raise ValueError("TI release input exceeds its byte bound")
    raw = path.read_bytes()
    after = path.stat()
    if len(raw) != before.st_size or (before.st_ino, before.st_mtime_ns) != (after.st_ino, after.st_mtime_ns):
        raise ValueError("TI release input changed during inspection")
    return raw


def load_report(path: Path) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate TI evidence field")
            value[key] = item
        return value

    value = json.loads(read_regular(path).decode("utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("TI evidence must be an object")
    return value


def asset_identity(root: Path = ROOT, *, site: Path | None = None) -> dict[str, Any]:
    """Inspect every declared source and the exact self-contained page."""
    root = root.resolve()
    directory = (site or root / "docs") / "transformational-intelligence"
    manifest = load_report(directory / "sources.json")
    if (
        set(manifest) != {"schema_version", "sources", "page_sha256", "scope"}
        or manifest["schema_version"] != "ti-browser-source/v1"
        or not isinstance(manifest["sources"], dict)
        or not 1 <= len(manifest["sources"]) <= 100
    ):
        raise ValueError("Invalid TI browser source manifest")
    sources = manifest["sources"]
    if (
        not {
            "scripts/templates/transformational-intelligence/app.js",
            "scripts/generate_transformational_intelligence.py",
            "examples/transformational-intelligence/inspector.mjs",
            "examples/transformational-intelligence/project-bridge.mjs",
        }
        <= sources.keys()
    ):
        raise ValueError("TI browser source closure is incomplete")
    for name, expected in sources.items():
        if not isinstance(name, str) or not isinstance(expected, str) or not HASH.fullmatch(expected):
            raise ValueError("Invalid TI source identity")
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or str(relative) != name:
            raise ValueError("TI source path must stay within the repository")
        if hashlib.sha256(read_regular(root / name)).hexdigest() != expected:
            raise ValueError("TI browser source differs from the manifest")
    page = read_regular(directory / "index.html")
    from scripts.generate_transformational_intelligence import render

    expected_page, expected_manifest = render(root)
    page_hash = hashlib.sha256(page).hexdigest()
    if page_hash != manifest["page_sha256"] or page != expected_page.encode("utf-8") or manifest != expected_manifest:
        raise ValueError("TI workspace differs from its source manifest")
    return {
        "pageSha256": page_hash,
        "manifestSha256": hashlib.sha256(read_regular(directory / "sources.json")).hexdigest(),
        "sourcesChecked": len(sources),
    }


def verify_report(report: Any, commit: str, version: str, *, mode: str, root: Path = ROOT) -> dict[str, Any]:
    """A report is useful only for the exact source, complete journey and requested mode."""
    fields = {"schema", "commit", "version", "mode", "origin", "passed", "sourceIdentity", "checks", "public"}
    if (
        not isinstance(report, dict)
        or set(report) != fields
        or report["schema"] != "agialpha.transformational.acceptance.v1"
        or report["commit"] != commit
        or report["version"] != version
        or report["mode"] != mode
        or mode not in {"local", "public"}
        or report["passed"] is not True
        or report["sourceIdentity"] != asset_identity(root)
        or not isinstance(report["checks"], list)
        or not all(isinstance(item, str) for item in report["checks"])
        or len(report["checks"]) != len(CHECKS)
        or set(report["checks"]) != CHECKS
        or not isinstance(report["origin"], str)
    ):
        raise ValueError("Missing or stale complete TI browser acceptance")
    if mode == "public":
        from urllib.parse import urlsplit

        parts = urlsplit(report["origin"])
        if (
            parts.scheme != "https"
            or parts.netloc != "montrealai.github.io"
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path != "/AGI-Alpha-Agent-v0/transformational-intelligence/"
            or not isinstance(report["public"], dict)
            or set(report["public"]) != {"httpsVerified", "exactPackagedBytes", "savedOfflineJourney"}
            or any(value is not True for value in report["public"].values())
        ):
            raise ValueError("TI public readback is incomplete")
    elif report["public"] is not None or not report["origin"].startswith("file:"):
        raise ValueError("Invalid local TI acceptance origin")
    return report


def package_workspace(root: Path, output: Path) -> dict[str, Any]:
    """Copy the exact portable page, refusing existing destinations."""
    identity = asset_identity(root)
    destination = output / "transformational-intelligence-workspace.html"
    with destination.open("xb") as stream:
        stream.write(read_regular(root / "docs/transformational-intelligence/index.html"))
    return {"name": destination.name, "bytes": destination.stat().st_size, "sha256": identity["pageSha256"]}


def verify_release_workspace(record: Any, folder: Path, commit: str, version: str, *, root: Path = ROOT) -> None:
    if not isinstance(record, dict) or set(record) != {"local_acceptance", "workspace"}:
        raise ValueError("TI release lacks workspace acceptance")
    verify_report(record["local_acceptance"], commit, version, mode="local", root=root)
    name = "transformational-intelligence-workspace.html"
    raw = read_regular(folder / name)
    expected = {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if record["workspace"] != expected or expected["sha256"] != asset_identity(root)["pageSha256"]:
        raise ValueError("Packaged TI workspace differs from the accepted bytes")
