# SPDX-License-Identifier: Apache-2.0
"""Verify exact companion identities without installing packages or using a network.

Optional wheel bootstrap requires both --bootstrap-wheels and --allow-network.
Primary historical command paths are preserved as evidence, never rewritten.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "COMPANION_MANIFEST.json"
EXCLUDED_PARTS = {"__pycache__", "selected-wheels", "node_modules", ".git", ".venv", "screenshots"}
TEX_TEMP_SUFFIXES = {".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".out", ".synctex.gz", ".toc"}


def require(condition: Any, message: str) -> None:
    """Raise an integrity failure with an explicit reason."""
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    """Hash potentially large ledger archives with bounded memory."""
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def local(root: Path, value: str | Path) -> Path:
    """Resolve a relative artifact path inside one companion tree."""
    value = Path(value)
    require(not value.is_absolute(), f"Relative companion path required: {value}")
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes companion: {value}")
    return path


def data(path: Path, expected: str | None = None) -> dict[str, Any]:
    """Read an identity-bound JSON record."""
    if expected is not None:
        require(digest(path) == expected, f"SHA-256 mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def exclusion(path: Path, edition: str) -> str | None:
    """Describe transparent package exclusions, keeping logs and scientific figures."""
    parts = path.parts
    if path.as_posix() == MANIFEST:
        return "manifest self-reference"
    if any(part in EXCLUDED_PARTS or part.startswith(".") for part in parts):
        return "generated cache, duplicate wheel view, hidden environment or screenshot directory"
    if path.suffix in {".pyc", ".pyo", ".zip"}:
        return "compiled Python or generated archive"
    if path.suffix in TEX_TEMP_SUFFIXES or path.name.endswith(".synctex.gz"):
        return "LaTeX temporary output"
    if path.suffix == ".log" and "publication" in parts:
        return "LaTeX temporary log; retained build stdout/stderr remain included"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and (
        "screenshot" in path.name.lower() or "resources/rendering" in path.as_posix()
    ):
        return "layout screenshot"
    if parts[0] == "tools" and "library" in path.name.lower():
        return "private persistence helper"
    if edition == "github" and path.suffix == ".whl":
        return "wheel binary omitted from GitHub evidence edition"
    return None


def included_files(root: Path, edition: str) -> tuple[list[Path], list[dict[str, str]]]:
    """Inventory the chosen edition without following symlinks."""
    included, omitted = [], []
    hashes: dict[tuple[int, int, int, int], str] = {}

    def cached_hash(path: Path) -> str:
        stat = path.stat()
        key = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if key not in hashes:
            hashes[key] = digest(path)
        return hashes[key]

    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"Symlink not permitted in companion: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        reason = exclusion(relative, edition)
        if "selected-wheels" in relative.parts and path.suffix == ".whl":
            canonical = root / "inputs/wheels" / path.name
            if canonical.is_file() and cached_hash(path) == cached_hash(canonical):
                reason = "exact duplicate view of inputs/wheels/" + path.name
            else:
                without_view = Path(*(part for part in relative.parts if part != "selected-wheels"))
                reason = exclusion(without_view, edition)
        if reason:
            omitted.append({"path": relative.as_posix(), "reason": reason})
        else:
            included.append(path)
    return included, omitted


def check_files(root: Path, rows: list[dict[str, Any]]) -> int:
    """Verify a unique list of exact file identities."""
    seen = set()
    for row in rows:
        require(row["path"] not in seen, f"Duplicate identity entry: {row['path']}")
        seen.add(row["path"])
        path = local(root, row["path"])
        require(path.is_file(), f"Missing evidence file: {row['path']}")
        require(digest(path) == row["sha256"], f"File bytes changed: {row['path']}")
        if "bytes" in row:
            require(path.stat().st_size == row["bytes"], f"File size changed: {row['path']}")
    return len(seen)


def verify_jobs(root: Path, edition: str) -> dict[str, Any]:
    """Verify the six registered jobs, baseline and the 47 distinct research wheels."""
    manifest = data(root / "protocol/confirmation-jobs.json")
    require(len(manifest["jobs"]) == 6, "Expected six registered research questions")
    require(digest(root / "protocol/selected-inputs.json") == manifest["selection_sha256"], "Selection changed")
    baseline_path = root / "inputs/development/job.json"
    jobs = [(baseline_path, data(baseline_path))]
    for entry in manifest["jobs"]:
        require(entry["status"] == "READY", "A registered job is not READY")
        path = local(root, entry["job"])
        job = data(path, entry["job_sha256"])
        require(job["id"] == entry["id"], "Registered job identity changed")
        jobs.append((path, job))
    wheels: dict[str, str] = {}
    missing = []
    target = jobs[0][1]["target_environment"]
    for path, job in jobs:
        require(job["schema"] == "agialpha-lock-job/v1", "Unexpected job schema")
        require(job["target_environment"] == target, "Registered native targets differ")
        for key in ["lock", "pyproject"]:
            relative = job[f"{key}_path"]
            require(not Path(relative).is_absolute(), "Job input contains an absolute path")
            artifact = local(root, (path.parent / relative).resolve().relative_to(root))
            require(digest(artifact) == job[f"{key}_sha256"], f"Job {key} changed: {job['id']}")
        require(len(job["wheels"]) == 41, "Each job must retain exactly 41 selected wheels")
        require(not Path(job["wheelhouse_path"]).is_absolute(), "Wheelhouse must be relative")
        wheelhouse = local(root, (path.parent / job["wheelhouse_path"]).resolve().relative_to(root))
        for wheel in job["wheels"]:
            require(Path(wheel["filename"]).name == wheel["filename"], "Wheel basename required")
            wheel_path = wheelhouse / wheel["filename"]
            relative = wheel_path.relative_to(root).as_posix()
            require(relative not in wheels or wheels[relative] == wheel["sha256"], "Wheel identity collision")
            wheels[relative] = wheel["sha256"]
    require(len(wheels) == 47, "Expected 41 baseline wheels plus six exact alternatives")
    for relative, expected in wheels.items():
        path = local(root, relative)
        if path.is_file():
            require(digest(path) == expected, f"Wheel changed: {relative}")
        else:
            require(edition == "github", f"Offline research wheel missing: {relative}")
            missing.append(relative)
    return {"registered_jobs": 6, "baseline_jobs": 1, "pins_per_job": 41, "unique_research_wheels": 47,
            "missing_research_wheels": missing, "target_environment": target}


def verify_tools(root: Path, edition: str, check_runtime: bool, target: dict[str, str]) -> dict[str, Any]:
    """Verify the separate post-confirmation execution closure and optional host match."""
    closure = data(root / "inputs/execution-tools/tool-closure.json")
    require({row["name"]: row["version"] for row in closure["wheels"]} ==
            {"pip": "26.2.2", "packaging": "26.3"}, "Execution-tool versions differ from primary receipts")
    missing = []
    for row in closure["wheels"]:
        data(local(root, row["pypi_version_json"]), row["pypi_version_json_sha256"])
        path = root / "inputs/execution-tools" / row["filename"]
        if not path.is_file():
            require(edition == "github", f"Offline execution tool missing: {row['filename']}")
            missing.append(path.relative_to(root).as_posix())
            continue
        require(digest(path) == row["sha256"], "Execution wheel changed")
        with zipfile.ZipFile(path) as archive:
            for license_record in row["license_members"]:
                raw = archive.read(license_record["wheel_member"])
                require(hashlib.sha256(raw).hexdigest() == license_record["sha256"], "License member changed")
    sources = data(root / "inputs/wheel-sources.json")
    require(len(sources["source"]) == 49, "Saved source list must include 47 research and two tool wheels")
    for row in sources["source"]:
        data(local(root, row["source_record"]), row["source_sha256"])
        require(urllib.parse.urlsplit(row["url"]).hostname == "files.pythonhosted.org", "Unexpected wheel host")
        path = local(root, row["path"])
        if path.is_file():
            require(digest(path) == row["sha256"], "Wheel URL provenance does not match preserved bytes")
    expected = closure["recorded_runtime"]
    require(expected["target_environment"] == target, "Recorded execution target differs from frozen jobs")
    observed = None
    if check_runtime:
        from packaging.markers import default_environment

        observed = {"python": platform.python_version(), "implementation": platform.python_implementation(),
                    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
                    "target_environment": default_environment(),
                    "pip": importlib.metadata.version("pip"), "packaging": importlib.metadata.version("packaging")}
        for key, value in expected.items():
            require(observed[key] == value, f"Runtime prerequisite mismatch: {key}")
        require(observed["pip"] == "26.2.2" and observed["packaging"] == "26.3", "Python tool mismatch")
    return {"execution_tools": 2, "missing_execution_wheels": missing,
            "runtime_checked": check_runtime, "observed_runtime": observed, "required_runtime": expected}


def verify_production(root: Path) -> dict[str, Any]:
    """Bind every primary receipt, certificate and pip capture without rewriting old paths."""
    campaign_path = root / "results/confirmation-01/campaign.json"
    campaign = data(campaign_path)
    freeze_hash = digest(root / "protocol/production-freeze.json")
    require(not campaign["partial"] and campaign["phase"] == "fresh-confirmation", "Primary campaign incomplete")
    require(campaign["source_freeze_sha256"] == freeze_hash, "Production freeze binding changed")
    require(campaign["job_manifest_sha256"] == digest(root / "protocol/confirmation-jobs.json"), "Jobs changed")
    require(len(campaign["rows"]) == 18 and campaign["new_customer_orders"] == 0, "Primary campaign count changed")
    seen = set()
    versions = {"python": "3.12.14", "pip": "26.2.2", "packaging": "26.3"}
    for row in campaign["rows"]:
        slot = (row["family"], row["arm"])
        require(slot not in seen, "Duplicate primary comparison slot")
        seen.add(slot)
        result_path, cert_path = local(root, row["result_path"]), local(root, row["verification_path"])
        result, cert = data(result_path, row["result_sha256"]), data(cert_path, row["verification_sha256"])
        require(row["accepted"] and row["registered_job_binding"] and cert["status"] == "COMPLETE",
                "Primary acceptance status changed")
        require(result["job_sha256"] == cert["job_sha256"] == row["job_sha256"], "Primary job binding changed")
        require(cert["result_sha256"] == row["result_sha256"], "Certificate-to-result binding changed")
        require(cert["verdict"] == row["decision"] == result["decision"], "Primary verdict changed")
        require(result["tool_versions"] == versions, "Recorded primary runtime differs")
        require(cert["verifier"]["source_sha256"] == digest(root / "production/verify.py"), "Verifier source changed")
        for file_key, hash_key in [("stdout", "stdout_sha256"), ("stderr", "stderr_sha256"),
                                   ("report", "pip_report_sha256")]:
            name = result["files"].get(file_key)
            if name:
                require(digest(result_path.parent / name) == cert["evidence"][hash_key], "Pip capture changed")
    summary_path = root / "results/production-summary.json"
    summary = data(summary_path)
    require(summary["campaign_sha256"] == digest(campaign_path), "Production summary binding changed")
    effects = data(root / "market/effect-profile.json")
    require(effects["campaign_sha256"] == digest(campaign_path), "Effect/campaign identity changed")
    require(effects["production_summary_sha256"] == digest(summary_path), "Effect/summary identity changed")
    for arm in ["B", "C"]:
        asset_path = root / "protocol" / f"asset-{arm}.json"
        asset = data(asset_path, effects["arms"][arm]["assetSHA256"])
        require(asset["source_freeze_sha256"] == freeze_hash, "Asset/freeze identity changed")
        check_files(root, asset["files"])
        require(effects["arms"][arm]["acceptanceEvidenceSHA256"] == digest(campaign_path), "Acceptance changed")
    return {"accepted_primary_evaluations": 18, "research_questions": 6, "new_customer_orders": 0,
            "campaign_sha256": digest(campaign_path), "asset_and_effect_bindings": True,
            "historical_absolute_command_paths": "preserved byte for byte, never used as relocated replay inputs"}


def verify_market(root: Path, final: bool) -> dict[str, Any]:
    """Verify frozen market inputs and complete raw ledgers when available."""
    freeze_path = root / "market/campaign-freeze.json"
    require(freeze_path.is_file(), "Market source freeze is missing")
    freeze = data(freeze_path)
    count = check_files(root / "market", freeze["files"])
    completed = []
    for path in sorted((root / "market/results").glob("*/completion.json")):
        receipt = data(path)
        require(receipt["sourceFreezeSHA256"] == digest(freeze_path), "Market result freeze binding changed")
        mapping = {"complete-paired-worlds.jsonl.gz": "completePairedWorldsGzipSHA256",
                   "summary.json": "summarySHA256", "compact-worlds.jsonl": "compactWorldsSHA256"}
        for filename, key in mapping.items():
            require(digest(path.parent / filename) == receipt[key], f"Market artifact changed: {filename}")
        if receipt["complete"]:
            result_hash, lines = hashlib.sha256(), 0
            with gzip.open(path.parent / "complete-paired-worlds.jsonl.gz", "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    result_hash.update(chunk)
                    lines += chunk.count(b"\n")
            require(result_hash.hexdigest() == receipt["completePairedWorldsRawSHA256"], "Raw ledger identity changed")
            require(lines == receipt["completedWorlds"] == receipt["expectedPairedWorlds"],
                    "Ledger world count changed")
            completed.append({"path": path.relative_to(root).as_posix(), "complete_paired_worlds": lines})
    if final:
        require(bool(completed), "Final companion needs the completed market campaign")
        require((root / "README.md").is_file(), "Final companion README is missing")
        require(any((root / "publication").rglob("*.pdf")), "Final publication PDF is missing")
        require(any((root / "publication").rglob("*.tex")), "Final publication LaTeX is missing")
    return {"market_frozen_files": count, "complete_campaigns": completed,
            "final_publication_gate_checked": final}


def verify_manifest(root: Path, edition: str) -> dict[str, Any]:
    """Check every written file except the manifest's necessarily external self-identity."""
    path = root / MANIFEST
    if not path.is_file():
        return {"present": False, "note": "A final manifest is generated for each staged or archived edition."}
    manifest = data(path)
    require(manifest["edition"] == edition, "Wrong edition selected for manifest verification")
    count = check_files(root, manifest["files"])
    expected = {row["path"] for row in manifest["files"]}
    actual = {p.relative_to(root).as_posix() for p in included_files(root, edition)[0]}
    require(expected == actual, f"Unmanifested or missing files: {sorted(actual ^ expected)[:12]}")
    return {"present": True, "files_verified": count, "all_written_files_covered": True,
            "manifest_self_identity": "Excluded from itself; bind with the outer archive SHA-256."}


def verify(root: Path, edition: str = "full", check_runtime: bool = False, final: bool = False) -> dict[str, Any]:
    """Verify a companion without mutating its files or executing research missions."""
    root = root.resolve()
    production_freeze = data(root / "protocol/production-freeze.json")
    require(len(production_freeze["files"]) == 25, "Expected the exact 25-file production freeze")
    frozen = check_files(root, production_freeze["files"])
    jobs = verify_jobs(root, edition)
    tools = verify_tools(root, edition, check_runtime, jobs["target_environment"])
    production = verify_production(root)
    market = verify_market(root, final)
    manifest = verify_manifest(root, edition)
    return {"schema": "agi-alpha-companion-verification/v1", "passed": True, "edition": edition,
            "production_frozen_files": frozen, "jobs": jobs, "execution": tools, "production": production,
            "market": market, "manifest": manifest, "network_requests": 0, "new_research_missions": 0,
            "offline_wheel_closure_present": not jobs["missing_research_wheels"] and
            not tools["missing_execution_wheels"]}


def bootstrap(root: Path, allowed: bool) -> dict[str, Any]:
    """Download only saved public URLs, explicitly requested, with exact hash checks."""
    require(allowed, "No network by default. Bootstrap also requires --allow-network.")
    sources = data(root / "inputs/wheel-sources.json")
    downloaded, existing = [], []
    for row in sources["source"]:
        path = local(root, row["path"])
        require(path.parent in [root / "inputs/wheels", root / "inputs/execution-tools"], "Invalid wheel destination")
        require(path.suffix == ".whl", "Wheel bootstrap cannot write executable helpers")
        if path.is_file():
            require(digest(path) == row["sha256"], "Existing wheel differs; refusing to overwrite")
            existing.append(row["path"])
            continue
        url = urllib.parse.urlsplit(row["url"])
        require(url.scheme == "https" and url.hostname == "files.pythonhosted.org", "Unexpected source URL")
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(row["url"], timeout=60) as response:
            require(urllib.parse.urlsplit(response.url).hostname == "files.pythonhosted.org", "Unexpected redirect")
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".download", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
        require(digest(temporary_path) == row["sha256"], f"Downloaded hash mismatch; retained {temporary_path.name}")
        require(temporary_path.stat().st_size == row["bytes"], "Downloaded size mismatch")
        temporary_path.replace(path)
        downloaded.append(row["path"])
    return {"explicit_network_bootstrap": True, "downloaded": downloaded, "already_verified": existing,
            "packages_installed": False, "fresh_research_inputs_selected": False}


def main() -> None:
    """Expose a read-only default verifier and separate explicit bootstrap."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--edition", choices=["full", "github"], default="full")
    parser.add_argument("--runtime", action="store_true", help="Require the exact recorded host and tool versions")
    parser.add_argument("--final", action="store_true",
                        help="Require completed market results and LaTeX/PDF publication")
    parser.add_argument("--bootstrap-wheels", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if args.bootstrap_wheels:
        result = bootstrap(args.root.resolve(), args.allow_network)
    else:
        require(not args.allow_network, "--allow-network is meaningful only with --bootstrap-wheels")
        result = verify(args.root, args.edition, args.runtime, args.final)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ImportError, subprocess.SubprocessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}), file=sys.stderr)
        sys.exit(1)
