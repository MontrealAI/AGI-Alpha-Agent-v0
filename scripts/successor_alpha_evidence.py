# SPDX-License-Identifier: Apache-2.0
"""Bind flagship acceptance to the complete exact local or public release journey."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agialpha.successor-alpha.acceptance.v1"
PUBLIC_ORIGIN = "https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/alpha/"
REQUIRED_CHECKS = {
    "first-use-and-keyboard-focus",
    "exact-csv-artifacts",
    "all-competitive-comparisons",
    "separate-unfunded-routes-and-current-contracts",
    "portable-offline-french-english-rerun",
    "historical-restore-and-cancel",
    "malformed-and-stale-input-rejection",
    "constructed-program-and-frozen-commitment",
    "downloaded-tool-on-changed-inputs",
    "complete-discrepancy-actions",
    "native-sdk-and-node-host-return-import",
    "learning-archive-and-offline-continuity",
    "bounded-local-improvement-and-hold",
    "worker-disabled-fallback",
    "mobile-and-french",
    "no-page-errors-no-csp-violations-no-external-dependencies",
}
MODULE_ROOTS = (
    "examples/successor-alpha/engine.mjs",
    "examples/successor-alpha/project.mjs",
    "examples/successor-alpha/research.mjs",
    "examples/successor-alpha/continuity.mjs",
    "examples/successor-alpha/capability.mjs",
    "docs/assets/successor/engine.mjs",
)
HASH = re.compile(r"[0-9a-f]{64}\Z")


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Flagship evidence contains duplicate JSON fields")
        result[name] = value
    return result


def _read(path: Path, maximum: int = 2_000_000) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError(f"Flagship evidence requires a bounded ordinary file: {path}")
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError("Flagship evidence exceeded its byte budget")
    return raw


def load_report(path: Path) -> dict[str, Any]:
    """Require a complete ordinary JSON report rather than optional missing evidence."""
    try:
        value = json.loads(_read(path).decode("utf-8"), object_pairs_hook=_unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Flagship acceptance report is missing or malformed") from error
    if not isinstance(value, dict):
        raise ValueError("Flagship acceptance report must be a JSON object")
    return value


def asset_identity(root: Path = ROOT) -> dict[str, Any]:
    """Independently check every source and the complete generated implementation commitment."""
    root = root.resolve()
    page = _read(root / "docs/successor/alpha/index.html", 8_000_000)
    manifest_raw = _read(root / "docs/successor/alpha/sources.json", 200_000)
    manifest = json.loads(manifest_raw.decode("utf-8"), object_pairs_hook=_unique)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema", "sources", "engineSourceHash", "pageSha256"}
        or manifest["schema"] != "successor-alpha-source/v1"
        or not HASH.fullmatch(str(manifest["engineSourceHash"]))
        or not HASH.fullmatch(str(manifest["pageSha256"]))
        or manifest["pageSha256"] != hashlib.sha256(page).hexdigest()
        or not isinstance(manifest["sources"], dict)
        or not manifest["sources"]
    ):
        raise ValueError("Flagship generated page/source identity is invalid or stale")
    recorded = manifest["sources"]
    sources: dict[str, str] = {}

    def module(path: Path) -> None:
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError("Flagship source imports must remain inside the repository")
        name = resolved.relative_to(root).as_posix()
        if name in sources:
            return
        source = _read(resolved).decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        sources[name] = hashlib.sha256(source.encode()).hexdigest()
        first_export = re.search(r"^export\s+", source, flags=re.MULTILINE)
        prefix = source[: first_export.start() if first_export else 0]
        for match in re.finditer(r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];", prefix, flags=re.MULTILINE):
            location = match[2]
            if not location.startswith("."):
                raise ValueError("Flagship implementation imports must be repository-local")
            module(resolved.parent / location)

    for name in MODULE_ROOTS:
        module(root / name)
    implementation = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if implementation != manifest["engineSourceHash"]:
        raise ValueError("Flagship implementation source commitment is stale")
    for name, expected in recorded.items():
        if not isinstance(name, str) or not isinstance(expected, str) or not HASH.fullmatch(expected):
            raise ValueError("Invalid flagship source inventory entry")
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or str(relative) != name:
            raise ValueError("Unsafe flagship source inventory path")
        path = root / name
        if not path.resolve().is_relative_to(root):
            raise ValueError("Flagship source inventory escapes the checkout")
        observed = sources[name] if name in sources else hashlib.sha256(_read(path, 8_000_000)).hexdigest()
        if observed != expected:
            raise ValueError(f"Flagship source inventory differs from the current checkout: {name}")
    if not sources.keys() <= recorded.keys():
        raise ValueError("Flagship source inventory omits reviewed implementation dependencies")
    return {
        "pageSha256": hashlib.sha256(page).hexdigest(),
        "manifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
        "engineSourceHash": implementation,
        "sourcesChecked": len(recorded),
    }


def verify_report(report: dict[str, Any], commit: str, version: str, *, mode: str, root: Path = ROOT) -> None:
    """Fail closed on stale, partial, unaudited or wrong-origin local/public evidence."""
    if mode not in {"local", "public"}:
        raise ValueError("Flagship acceptance mode must be local or public")
    if not isinstance(report, dict):
        raise ValueError("Flagship acceptance report must be a JSON object")
    expected = asset_identity(root)
    origin = report.get("origin")
    if not isinstance(origin, str):
        raise ValueError("Flagship acceptance must identify its actual entry URL")
    parsed = urlsplit(origin)
    if mode == "public":
        valid_origin = origin == PUBLIC_ORIGIN
    else:
        valid_origin = (
            parsed.scheme == "file"
            and parsed.netloc in {"", "localhost"}
            and parsed.path.endswith("/successor/alpha/index.html")
            and not parsed.query
            and not parsed.fragment
        )
    journey = report.get("journey")
    if (
        report.get("schema") != SCHEMA
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("mode") != mode
        or not valid_origin
        or report.get("sourceIdentity") != expected
        or not isinstance(journey, dict)
    ):
        raise ValueError("Flagship must pass against the exact release, source bytes and required origin")
    checks = journey.get("checks")
    if (
        journey.get("passed") is not True
        or journey.get("entryUrl") != origin
        or journey.get("accessibilityAudited") is not True
        or journey.get("languages") != ["en", "fr"]
        or journey.get("viewports") != [1440, 390, 320]
        or any(journey.get(name) != [] for name in ("errors", "browser_errors", "http_failures"))
        or not isinstance(checks, list)
        or not all(isinstance(item, str) for item in checks)
        or not REQUIRED_CHECKS.issubset(checks)
    ):
        raise ValueError(
            "Flagship requires complete exact-output, research, host-return, offline and accessibility journeys"
        )
    public = report.get("public")
    if mode == "local":
        if public is not None:
            raise ValueError("Local flagship acceptance cannot replace public HTTPS acceptance")
    elif public != {
        "url": PUBLIC_ORIGIN,
        "httpsVerified": True,
        "exactPackagedBytes": True,
        "assets": ["index.html", "sources.json"],
    }:
        raise ValueError("Public flagship acceptance requires the exact packaged HTTPS page and source manifest")


def require_local_reports(evidence: Path, commit: str, version: str, root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Require both downloaded gallery matrix reports before creating release assets."""
    reports = {}
    for kind in ("minimal", "full"):
        report = load_report(evidence / f"gallery-{kind}" / "successor-alpha" / "report.json")
        verify_report(report, commit, version, mode="local", root=root)
        reports[kind] = report
    return reports


def verify_release_workspace(record: Any, folder: Path, commit: str, version: str, root: Path = ROOT) -> None:
    """Require the accepted standalone page and both local reports in the release being finalized."""
    if not isinstance(record, dict) or set(record) != {"local_acceptance", "workspace"}:
        raise ValueError("The release must retain its flagship workspace and both local acceptance reports")
    local = record["local_acceptance"]
    if not isinstance(local, dict) or set(local) != {"minimal", "full"}:
        raise ValueError("The release must retain both flagship gallery acceptance reports")
    for report in local.values():
        verify_report(report, commit, version, mode="local", root=root)
    raw = _read(folder / "successor-alpha-workspace.html", 8_000_000)
    expected = {
        "name": "successor-alpha-workspace.html",
        "bytes": len(raw),
        "sha256": asset_identity(root)["pageSha256"],
    }
    if record["workspace"] != expected or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError("The standalone flagship workspace differs from the exact accepted page")
