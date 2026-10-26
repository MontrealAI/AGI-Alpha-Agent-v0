# SPDX-License-Identifier: Apache-2.0
"""Prepare exact portable editions; default is an inventory plan, not an archive.

--stage creates a disposable tree. --archive additionally requires --final.
Neither mode downloads, installs, runs confirmation or starts an application.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

from verify_companion import MANIFEST, ROOT, digest, included_files, require, verify, verify_manifest


def edition_note(edition: str) -> dict[str, Any]:
    """Explain exactly what each edition can reproduce without external downloads."""
    return {
        "schema": "agi-alpha-companion-edition/v1",
        "edition": edition,
        "presentation_and_packaging_added_after_confirmation": True,
        "original_primary_artifacts": "Exact preserved bytes, including historical absolute command and report URLs.",
        "portable_replay_inputs": "Relative job paths; the frozen runner resolves its new study location.",
        "research_wheels": "47 exact wheel binaries included once in inputs/wheels." if edition == "full" else
        "All wheel binaries omitted. Optional explicit bootstrap retrieves the 47 exact research wheels and two tools.",
        "execution_tools": "pip 26.2.2 and packaging 26.3 are separately identified post-confirmation support.",
        "host_prerequisites": "Recorded CPython 3.12.14, Node 24.22.1 and the exact native target environment. "
        "Interpreter, Node and OS binaries are not redistributed. See inputs/execution-tools/tool-closure.json.",
        "default_network_behavior": "No network. No automatic package installation or confirmation rerun.",
        "verify": "python tools/verify_companion.py --edition " + edition,
        "verify_runtime": "python tools/verify_companion.py --edition " + edition + " --runtime",
        "explicit_github_wheel_bootstrap":
        "python tools/verify_companion.py --bootstrap-wheels --allow-network",
        "synthetic_fixture_wheels": "Retained in the full edition as failure evidence; omitted from GitHub. "
        "Public-wheel bootstrap restores primary reproduction dependencies, not every synthetic failure fixture.",
        "reproduction": "python tools/run_confirmation.py --phase reproduction --out results/reproduction-new",
        "reproduction_interpretation": "Reuses the same six registered questions for 18 branch evaluations; "
        "creates zero new research missions or customer orders. Use a fresh disposable copy.",
        "full_market_ledgers": "Included unchanged when present, with raw and compressed identities checked.",
        "manifest": "Every included file is hashed. The manifest excludes itself; the outer archive hash binds it.",
    }


def inventory(root: Path, edition: str) -> dict[str, Any]:
    """Plan a package without producing a final artifact."""
    files, excluded = included_files(root, edition)
    binaries = [p for p in files if p.suffix == ".whl"]
    return {"schema": "agi-alpha-companion-build-plan/v1", "edition": edition,
            "included_files": len(files), "included_bytes": sum(p.stat().st_size for p in files),
            "wheel_files": len(binaries),
            "canonical_research_wheels": sum(p.parent == root / "inputs/wheels" for p in binaries),
            "execution_tool_wheels": sum(p.parent == root / "inputs/execution-tools" for p in binaries),
            "synthetic_fixture_wheels": sum("resources" in p.relative_to(root).parts for p in binaries),
            "excluded_files": len(excluded), "files": [p.relative_to(root).as_posix() for p in files],
            "exclusions": excluded, "network_requests": 0, "research_executions": 0}


def stage(root: Path, target: Path, edition: str, final: bool = False) -> dict[str, Any]:
    """Copy a coherent snapshot, preserving every included byte and exposing exclusions."""
    root, target = root.resolve(), target.resolve()
    require(not target.is_relative_to(root), "Stage must be outside the source study")
    require(not target.exists(), "Refusing to overwrite an existing companion stage")
    source_check = verify(root, "full", final=final)
    files, excluded = included_files(root, edition)
    target.mkdir(parents=True)
    for source in files:
        relative = source.relative_to(root)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        require(digest(source) == digest(destination), f"Source changed while copying: {relative}")
    (target / "COMPANION_EDITION.json").write_text(json.dumps(edition_note(edition), indent=2) + "\n")
    staged_check = verify(target, edition, final=final)
    copied = included_files(target, edition)[0]
    rows = [{"path": path.relative_to(target).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
            for path in copied]
    omissions = []
    if edition == "github":
        for excluded_file in excluded:
            path = root / excluded_file["path"]
            if path.suffix == ".whl" and not excluded_file["reason"].startswith("exact duplicate"):
                omissions.append({"path": excluded_file["path"], "bytes": path.stat().st_size,
                                  "sha256": digest(path), "reason": excluded_file["reason"]})
    manifest = {"schema": "agi-alpha-portable-companion-manifest/v1", "edition": edition,
                "study": "agi-alpha-second-investment-v1", "files": rows, "omitted_wheel_binaries": omissions,
                "exclusions": excluded,
                "production_freeze_sha256": digest(target / "protocol/production-freeze.json"),
                "market_freeze_sha256": digest(target / "market/campaign-freeze.json"),
                "primary_campaign_sha256": digest(target / "results/confirmation-01/campaign.json"),
                "source_and_staged_semantic_checks_passed": source_check["passed"] and staged_check["passed"],
                "self_reference": "This manifest cannot contain its own SHA-256. Bind it with the outer archive hash.",
                "network_requests": 0, "research_executions": 0}
    (target / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    verification = verify_manifest(target, edition)
    return {"edition": edition, "staged_files": len(rows) + 1,
            "staged_bytes": sum(row["bytes"] for row in rows) + (target / MANIFEST).stat().st_size,
            "manifest_sha256": digest(target / MANIFEST), "verification": verification,
            "primary_artifacts_byte_identical": True, "network_requests": 0, "research_executions": 0}


def archive(root: Path, output: Path, edition: str, final: bool) -> dict[str, Any]:
    """Build a deterministic final ZIP only after all final-completeness checks pass."""
    root, output = root.resolve(), output.resolve()
    require(final, "Final archive creation requires --final; use --stage for work in progress")
    require(not output.is_relative_to(root), "Archive output must be outside the study source tree")
    require(not output.exists(), "Refusing to overwrite an archive")
    require(output.suffix == ".zip", "Use a .zip archive output")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agialpha-companion-build-") as temporary:
        staged = Path(temporary) / "agi-alpha-second-investment-v1"
        result = stage(root, staged, edition, final=True)
        partial = output.with_suffix(".zip.partial")
        require(not partial.exists(), "A previous partial archive exists; preserve it and choose a new output")
        with zipfile.ZipFile(partial, "x", allowZip64=True) as bundle:
            for path in sorted(staged.rglob("*")):
                if not path.is_file():
                    continue
                relative = Path(staged.name) / path.relative_to(staged)
                info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 10, 26, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = (
                    zipfile.ZIP_STORED if path.suffix in {".whl", ".gz", ".pdf"} else zipfile.ZIP_DEFLATED
                )
                with path.open("rb") as source, bundle.open(info, "w", force_zip64=True) as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
        partial.replace(output)
    result.update({"archive": str(output), "archive_sha256": digest(output), "archive_bytes": output.stat().st_size})
    return result


def main() -> None:
    """Plan by default; stage or archive only through explicit arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--edition", choices=["full", "github"], default="full")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--stage", type=Path)
    action.add_argument("--archive", type=Path)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    started, cpu = time.perf_counter(), time.process_time()
    if args.stage:
        result = stage(args.root, args.stage, args.edition, args.final)
    elif args.archive:
        result = archive(args.root, args.archive, args.edition, args.final)
    else:
        result = inventory(args.root.resolve(), args.edition)
    result["elapsed_wall_seconds"] = time.perf_counter() - started
    result["process_cpu_seconds"] = time.process_time() - cpu
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(json.dumps({"passed": False, "error": str(error)})) from error
