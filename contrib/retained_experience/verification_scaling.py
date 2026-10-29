# SPDX-License-Identifier: Apache-2.0
"""Measure verifier scaling on exposed evidence without changing its acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import resource
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.retained_experience import verifier
from alpha_factory_v1.core.runtime.retained_experience.operator import check_seal as check_seal

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = "alpha_factory_v1/core/runtime/retained_experience/verifier.py"
CRITICAL = (
    VERIFIER,
    "alpha_factory_v1/core/runtime/structural_transfer/eadarp_check.py",
    "contrib/invention_automation/readonly.py",
)
INPUTS = (
    "base.json",
    "cost-policy.json",
    "history.json",
    "memory.json",
    "candidate-freeze.json",
    "ordinary-cache.json",
    "lifecycle.json",
    "training-tasks.json",
    "development.json",
)
STABLE = (
    "schema",
    "freeze_verified",
    "planned",
    "observed",
    "accepted",
    "feasible_schedules",
    "rejected",
    "memory_hash",
    "tasks_hash",
    "observations_sha256",
    "costs_sha256",
    "confirmation",
    "independence",
    "candidate_write_denied_by_os",
    "new_socket_denied_by_os",
    "candidate_imported",
    "restrictions",
)


def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular evidence files required")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(verifier.canonical(value) + b"\n")


def snapshot_identity(source: Path, root: Path = ROOT) -> dict[str, str]:
    freeze = verifier.read(source / "freeze.json")
    snapshot = source / "source-snapshot"
    entries = list(snapshot.rglob("*"))
    if any(p.is_symlink() for p in entries) or {str(p.relative_to(snapshot)) for p in entries if p.is_file()} != set(
        freeze["sources"]
    ):
        raise ValueError("archived source file set differs from the frozen closure")
    for name, expected in freeze["sources"].items():
        path = Path(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(p.is_symlink() for p in (source / "source-snapshot" / path).parents if p != p.parent)
        ):
            raise ValueError("unsupported archived source path")
        if sha(source / "source-snapshot" / path) != expected:
            raise ValueError("archived source snapshot changed")
    for name in CRITICAL:
        if freeze["sources"].get(name) != sha(root / name):
            raise ValueError("archived checker/filter differs from the current trusted implementation")
    return dict(freeze["sources"])


def derive_panel(source: Path, destination: Path, cases_per_regime: int, source_seal: str) -> str:
    protocol = verifier.read(source / "protocol.json")
    original_count = protocol["cases_per_regime"]
    if type(cases_per_regime) is not int or not 1 <= cases_per_regime <= original_count:
        raise ValueError("bounded source subset required")
    tasks = verifier.read(source / "tasks.json")
    if len(tasks) != original_count * len(protocol["regimes"]):
        raise ValueError("source task denominator differs")
    selected = [task for i, task in enumerate(tasks) if i % original_count < cases_per_regime]
    keys = {verifier.hash_value(task) for task in selected}
    if len(keys) != cases_per_regime * len(protocol["regimes"]):
        raise ValueError("source contains duplicate task identities")
    destination.mkdir(exist_ok=False)
    for name in INPUTS:
        shutil.copyfile(source / name, destination / name)
    shutil.copytree(source / "source-snapshot", destination / "source-snapshot")
    protocol["cases_per_regime"] = cases_per_regime
    protocol["freshness"] = "exposed historical subset; resource diagnosis only, no fresh confirmation"
    protocol["confirmation"] = False
    write(destination / "protocol.json", protocol)
    write(destination / "tasks.json", selected)
    for name in ("observations.jsonl", "costs.jsonl"):
        with (destination / name).open("xb") as output:
            for line in (source / name).read_bytes().splitlines():
                row = json.loads(line, object_pairs_hook=verifier._pairs)
                if row["task_hash"] in keys:
                    output.write(line + b"\n")
    freeze = verifier.read(source / "freeze.json")
    freeze.update({"protocol_hash": verifier.hash_value(protocol), "frozen_at_ns": time.time_ns()})
    write(destination / "freeze.json", freeze)
    write(destination / "origin.json", {"source_evidence_seal_sha256": source_seal, "reproduction_only": True})
    return sha(destination / "freeze.json")


def invoke(panel: Path, expected: str, metered: bool, failure_output: Path | None = None) -> dict[str, Any]:
    script = Path(__file__).with_name("verification_meter.py") if metered else panel / "source-snapshot" / VERIFIER
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall = time.monotonic_ns()
    process = subprocess.run(
        [sys.executable, "-B", str(script.resolve()), str(panel.resolve()), "--freeze-sha256", expected],
        cwd=panel / "source-snapshot",
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "PYTHONPATH": str((panel / "source-snapshot").resolve()),
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        },
    )
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = int((after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime) * 10**9)
    if failure_output is not None:
        write(
            failure_output,
            {
                "exit_code": process.returncode,
                "stdout": process.stdout[:2_000_000],
                "stderr": process.stderr[:200_000],
                "process_cpu_ns": cpu,
            },
        )
    if len(process.stdout) > 2_000_000 or len(process.stderr) > 200_000:
        raise ValueError("verifier response exceeded its bound")
    receipt = json.loads(process.stdout, object_pairs_hook=verifier._pairs)
    receipt.update({"process_cpu_ns": cpu, "process_wall_ns": time.monotonic_ns() - wall})
    if process.returncode != 0 or receipt.get("freeze_verified") is not True or receipt.get("rejected"):
        raise ValueError("original verifier refused the derived panel")
    return dict(receipt)


def reconcile_pair(original: dict[str, Any], metered: dict[str, Any]) -> None:
    if any(original.get(name) != metered.get(name) for name in STABLE):
        raise ValueError("metering changed the original verifier's acceptance")
    if (
        not original["candidate_write_denied_by_os"]
        or not original["new_socket_denied_by_os"]
        or original["candidate_imported"]
    ):
        raise ValueError("original verifier restrictions not demonstrated")
    if original["planned"] != original["observed"] or original["observed"] != original["accepted"]:
        raise ValueError("verification denominator incomplete")


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    panels: dict[str, Any] = {}
    for count in sorted({row["tasks"] for row in records}):
        selected = [row for row in records if row["tasks"] == count]
        native = [row["receipt"] for row in selected if row["mode"] == "native"]
        metered = [row["receipt"] for row in selected if row["mode"] == "metered"]
        if not native or len(native) != len(metered):
            raise ValueError("paired native/metered observations required")
        for a, b in zip(native, metered):
            reconcile_pair(a, b)
        common = [r["process_cpu_ns"] - sum(r["arm_check_cpu_ns"].values()) for r in native]
        fixed = [
            sum(r["meter"]["call_cpu_ns"][k] for k in ("history_outputs", "development_outputs", "memory"))
            for r in metered
        ]
        if min(common) < 0 or any(r["meter"]["unclassified_verify_cpu_ns"] < 0 for r in metered):
            raise ValueError("negative verification accounting remainder")
        panels[str(count)] = {
            "outputs_per_audit": native[0]["planned"],
            "samples_per_mode": len(native),
            "native_process_cpu_ns_median": int(statistics.median(r["process_cpu_ns"] for r in native)),
            "native_common_cpu_ns_range": [min(common), max(common)],
            "measured_history_development_memory_cpu_ns_range": [min(fixed), max(fixed)],
            "metered_unclassified_verify_cpu_ns_range": [
                min(r["meter"]["unclassified_verify_cpu_ns"] for r in metered),
                max(r["meter"]["unclassified_verify_cpu_ns"] for r in metered),
            ],
            "metering_process_cpu_ratio": str(
                statistics.median(r["process_cpu_ns"] for r in metered)
                / statistics.median(r["process_cpu_ns"] for r in native)
            ),
            "native_arm_check_cpu_ns_medians": {
                arm: int(statistics.median(r["arm_check_cpu_ns"][arm] for r in native))
                for arm in native[0]["arm_check_cpu_ns"]
            },
            "fixed_call_counts": {
                k: metered[0]["meter"]["calls"][k] for k in ("history_outputs", "development_outputs", "memory")
            },
        }
    return {
        "schema": "agialpha/verification-scaling/v1",
        "panels": panels,
        "decision": "MEASURED_FIXED_RECHECKS_REMAINDER_UNCLASSIFIED",
        "complete_cost_advantage": None,
        "profit_established": False,
        "fresh_confirmation": False,
        "authority_granted": False,
        "production_default_changed": False,
        "constraint": "Only measured fixed call costs may be considered fixed for this exact history; retain every residual cost.",
        "limits": [
            "Exposed fixed-route cases, no new scientific sample or generalization claim.",
            "Metered timings include wrapper overhead; paired unmodified native audits remain authoritative.",
            "No human effort, hosting invoice, demand, revenue or complete monetary cost is measured.",
            "This resource diagnostic neither requalifies current runtime code nor demonstrates a profitable flywheel.",
        ],
    }


def run(source: Path, expected_seal: str, output: Path, samples: int = 3) -> dict[str, Any]:
    if type(samples) is not int or not 1 <= samples <= 3:
        raise ValueError("one to three timing samples per mode required")
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("new regular output directory required")
    source, output = source.resolve(), output.absolute()
    check_seal(source, expected_seal)
    identities = snapshot_identity(source)
    protocol = verifier.read(source / "protocol.json")
    if protocol["cases_per_regime"] != 16 or protocol["repeats"] != 3:
        raise ValueError("expected the preserved 64-case, three-repeat source panel")
    if shutil.disk_usage(output.parent).free < 2 * 1024**3:
        raise ValueError("two GiB free reserve required")
    output.mkdir()
    diagnostic_sources = {p.name: sha(p) for p in (Path(__file__), Path(__file__).with_name("verification_meter.py"))}
    write(
        output / "protocol.json",
        {
            "source_evidence_seal_sha256": expected_seal,
            "source_identities": identities,
            "diagnostic_sources": diagnostic_sources,
            "cases_per_regime": [1, 4, 16],
            "samples_per_mode": samples,
            "confirmation": False,
            "numerical_acceptance_changed": False,
            "maximum_child_wall_seconds": 120,
            "maximum_campaign_wall_seconds": 900,
        },
    )
    started, records = time.monotonic(), []
    for count in (1, 4, 16):
        panel = output / f"panel-{count * len(protocol['regimes'])}"
        expected = derive_panel(source, panel, count, expected_seal)
        before = {str(p.relative_to(panel)): sha(p) for p in panel.rglob("*") if p.is_file()}
        for sample in range(samples):
            modes = [False, True]
            random.Random(20261029 + count * 10 + sample).shuffle(modes)
            pair = {}
            for metered in modes:
                mode = "metered" if metered else "native"
                receipt = invoke(panel, expected, metered, output / f"transcript-{count}-{sample}-{mode}.json")
                pair[mode] = receipt
                record = {"tasks": count * len(protocol["regimes"]), "sample": sample, "mode": mode, "receipt": receipt}
                records.append(record)
                write(output / f"audit-{count}-{sample}-{mode}.json", record)
                if time.monotonic() - started > 900:
                    raise TimeoutError("bounded scaling campaign deadline; preserve partial outputs")
            reconcile_pair(pair["native"], pair["metered"])
        if before != {str(p.relative_to(panel)): sha(p) for p in panel.rglob("*") if p.is_file()}:
            raise ValueError("verification changed the derived evidence")
    result = summarize(records)
    check_seal(source, expected_seal)
    if diagnostic_sources != {
        p.name: sha(p) for p in (Path(__file__), Path(__file__).with_name("verification_meter.py"))
    }:
        raise ValueError("diagnostic source changed during measurement")
    result["source_evidence_seal_sha256"] = expected_seal
    result["actual_external_spending_usd"] = "0"
    write(output / "summary.json", result)
    write(
        output / "seal.json",
        {
            "files": {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()},
            "fresh_confirmation": False,
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--seal-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    result = run(args.source, args.seal_sha256, args.output, args.samples)
    print(
        json.dumps(
            {"decision": result["decision"], "seal_sha256": sha(args.output / "seal.json"), "panels": result["panels"]},
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
