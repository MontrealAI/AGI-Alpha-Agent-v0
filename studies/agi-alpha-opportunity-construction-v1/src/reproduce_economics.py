# SPDX-License-Identifier: Apache-2.0
"""Replay only the published economic CLIs in a clean disposable source copy."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "evidence/economics_reproduction.json"
INPUTS = (
    "src/economics.py",
    "src/economic_conditional_supplement.py",
    "src/economic_tables.py",
    "config/commercial_protocol.json",
    "config/commercial_conditional_supplement.json",
    "evidence/commercial_design_proposal.json",
)
OUTPUTS = (
    "results/economics_development.json",
    "results/economics_freeze.json",
    "results/economics_confirmation.json",
    "results/economics_sensitivity.json",
    "results/economics_retention.json",
    "results/economics_example_ledger.json",
    "results/economics_summary.json",
    "results/economics_conditional_supplement.json",
    "results/economics_plot_data.json",
    "results/economics_policy_table.csv",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def freeze_checks(root: Path) -> dict[str, bool]:
    primary = read(root / "results/economics_freeze.json")
    checks = {
        "primary:" + name: sha(root / name) == primary[key]
        for key, name in (
            ("source_sha256", "src/economics.py"),
            ("protocol_sha256", "config/commercial_protocol.json"),
            ("proposal_sha256", "evidence/commercial_design_proposal.json"),
            ("development_sha256", "results/economics_development.json"),
        )
    }
    supplemental = read(root / "config/commercial_conditional_supplement.json")
    checks.update(
        {
            "supplement:" + name: sha(root / name) == expected
            for name, expected in supplemental["source_and_primary_evidence_sha256"].items()
        }
    )
    return checks


def manifest() -> dict[str, str]:
    names = set(INPUTS) | {
        str(path.relative_to(ROOT)) for path in (ROOT / "results").glob("economics*") if path.is_file()
    }
    return {name: sha(ROOT / name) for name in sorted(names)}


def differences(old: Any, new: Any, path: str = "$") -> list[dict[str, Any]]:
    if type(old) is not type(new):
        return [
            {
                "path": path,
                "reason": "type",
                "published_type": type(old).__name__,
                "reproduced_type": type(new).__name__,
            }
        ]
    if isinstance(old, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(old.keys() | new.keys()):
            if key not in old or key not in new:
                result.append({"path": path + "/" + key, "reason": "missing key"})
            else:
                result.extend(differences(old[key], new[key], path + "/" + key))
            if len(result) >= 12:
                break
        return result[:12]
    if isinstance(old, list):
        if len(old) != len(new):
            return [{"path": path, "reason": "length", "published": len(old), "reproduced": len(new)}]
        result = []
        for index, (left, right) in enumerate(zip(old, new, strict=True)):
            result.extend(differences(left, right, path + "/" + str(index)))
            if len(result) >= 12:
                break
        return result[:12]
    return [] if old == new else [{"path": path, "published": old, "reproduced": new}]


def compare(temporary: Path, name: str) -> dict[str, Any]:
    original, replay = ROOT / name, temporary / name
    record: dict[str, Any] = {"file": name, "comparison": "byte-for-byte", "omitted_fields": []}
    if not replay.is_file():
        return {**record, "passed": False, "difference": "Output missing"}
    record.update(
        published_sha256=sha(original),
        reproduced_sha256=sha(replay),
        published_bytes=original.stat().st_size,
        reproduced_bytes=replay.stat().st_size,
    )
    record["passed"] = record["published_sha256"] == record["reproduced_sha256"]
    record["differences"] = []
    if not record["passed"]:
        record["differences"] = (
            differences(read(original), read(replay))
            if original.suffix == ".json"
            else [{"reason": "CSV bytes differ"}]
        )
        if not record["differences"]:
            record["differences"] = [{"reason": "Parsed values agree but bytes differ"}]
    return record


def execute(root: Path, arguments: list[str]) -> dict[str, Any]:
    command = [sys.executable, "-B", *arguments]
    print("RUN python -B " + " ".join(arguments), flush=True)
    started = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"},
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return {
        "command": ["python", "-B", *arguments],
        "cwd": "<TEMP_STUDY>",
        "returncode": process.returncode,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout_sha256": hashlib.sha256(process.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
        "stdout_tail": process.stdout[-16000:].replace(str(root), "<TEMP_STUDY>"),
        "stderr_tail": process.stderr[-16000:].replace(str(root), "<TEMP_STUDY>"),
    }


def run() -> dict[str, Any]:
    started = time.perf_counter()
    before = manifest()
    result: dict[str, Any] = {
        "schema": "agialpha.reserve.economic-reproduction.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Economic CLIs only: self-tests, development, primary confirmation and sensitivities, prospective conditional supplement, and derived publication tables.",
        "evidence": "Replay of supplied frozen seeds and inputs; not new research, independent customer evidence or full-repository CI.",
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "dependencies": "Python standard library only",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        },
        "reproduction_runner_sha256": sha(Path(__file__)),
        "copied_inputs": list(INPUTS),
        "generated_outputs_copied": False,
        "comparison_policy": "All ten outputs must match byte for byte. There are no wall-time, output-path or random-key metadata fields in these deterministic economic artifacts, so no omissions or numerical tolerances are needed.",
        "preserved_but_not_regenerated": [
            "results/economics_upgrade_bound.json (post-result analytic bound)",
            "results/economics_validation.json (historical review receipt)",
        ],
        "original_economic_file_manifest": before,
        "commands": [],
        "comparisons": [],
        "freeze_checks": {},
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
    }
    temporary: Path | None = None
    try:
        result["freeze_checks"]["original_before"] = freeze_checks(ROOT)
        if not all(result["freeze_checks"]["original_before"].values()):
            raise ValueError("An original frozen source/input/result binding is invalid")
        with tempfile.TemporaryDirectory(prefix="agialpha-economic-replay-") as directory:
            temporary = Path(directory) / "study"
            for name in INPUTS:
                destination = temporary / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, destination)
            for arguments in (
                ["src/economics.py", "self-test"],
                ["src/economics.py", "develop"],
                ["src/economics.py", "confirm"],
                ["src/economic_conditional_supplement.py", "run"],
                ["src/economic_tables.py"],
            ):
                command_result = execute(temporary, arguments)
                result["commands"].append(command_result)
                if command_result["returncode"]:
                    raise RuntimeError("Reproduction command failed: " + " ".join(command_result["command"]))
            result["freeze_checks"]["reproduced"] = freeze_checks(temporary)
            result["comparisons"] = [compare(temporary, name) for name in OUTPUTS]
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    result["temporary_tree_deleted"] = temporary is None or not temporary.exists()
    result["freeze_checks"]["original_after"] = freeze_checks(ROOT)
    after = manifest()
    result["original_files_unchanged"] = before == after
    result["original_file_differences"] = differences(before, after)
    result["passed"] = (
        "error" not in result
        and result["temporary_tree_deleted"]
        and result["original_files_unchanged"]
        and len(result["comparisons"]) == len(OUTPUTS)
        and all(c["passed"] for c in result["comparisons"])
        and all(v for checks in result["freeze_checks"].values() for v in checks.values())
    )
    result["comparisons_passed"] = sum(c["passed"] for c in result["comparisons"])
    result["comparisons_total"] = len(result["comparisons"])
    result["elapsed_seconds"] = time.perf_counter() - started
    return result


def main() -> None:
    result = run()
    if RECEIPT.exists():
        previous = read(RECEIPT)
        history = previous.pop("previous_attempts", [])
        result["previous_attempts"] = [*history, previous]
    RECEIPT.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "passed",
                    "comparisons_passed",
                    "comparisons_total",
                    "original_files_unchanged",
                    "temporary_tree_deleted",
                    "elapsed_seconds",
                )
            },
            indent=2,
        )
    )
    if "error" in result:
        print(json.dumps(result["error"], indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
