#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replay archived supporting evidence without rerunning hosted frontier agents.

Default: verify frozen bytes, saved outputs, native fixture controls and economic
summaries. --full-economics additionally re-executes every selected simulation
history. All generated native/verifier files live in a temporary directory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ARMS = ("U", "E", "E_plus")
CASES = ("c1", "c2", "c3", "c4")
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def read(path: Path) -> Any:
    """Read a UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    """Hash a file without loading large event streams into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition: bool, message: str) -> None:
    """Fail explicitly even when Python is invoked with optimization."""
    if not condition:
        raise ValueError(message)


def load(name: str, path: Path) -> Any:
    """Load a verified local source module."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke(arguments: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a bounded local replay, retaining error detail on failure."""
    result = subprocess.run(arguments, cwd=cwd or ROOT, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Replay failed ({result.returncode}): {arguments}\n{result.stdout}\n{result.stderr}")
    return result


def check_pins() -> dict[str, Any]:
    """Check frozen source, input, result and correction commitments first."""
    checks: dict[str, str] = {}

    def pin(path: Path, expected: str) -> None:
        require(path.is_file() and not path.is_symlink(), "Missing ordinary source file: " + str(path))
        actual = sha(path)
        require(actual == expected, "Frozen bytes changed: " + str(path))
        checks[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = actual

    for directory in ("benchmark", "benchmark_composition"):
        for name, digest in read(ROOT / directory / "FREEZE.json")["files"].items():
            pin(ROOT / directory / name, digest)
    for name, digest in read(ROOT / "protocol/CONFIRMATION_FREEZE.json")["files"].items():
        pin(ROOT / name, digest)
    composition = read(ROOT / "results/composition_summary.json")
    pin(ROOT / "protocol/COMPOSITION_FREEZE.json", composition["frozen_protocol_sha256"])
    pin(ROOT / "benchmark_composition/private/evaluate.py", composition["evaluator_sha256"])
    composition_freeze = read(ROOT / "protocol/COMPOSITION_FREEZE.json")
    pin(ROOT / "benchmark_composition/CASE_MANIFEST.json", composition_freeze["benchmark_manifest_sha256"])
    exposure = read(ROOT / "protocol/C5_EXPOSURE_CHECK.json")
    pin(ROOT / "protocol/COMPOSITION_FREEZE.json", exposure["composition_freeze_sha256"])
    correction = read(ROOT / "protocol/history/runner_lock_correction.json")
    pin(ROOT / "protocol/history/trial_runner_initial.py", correction["source_before"])
    pin(ROOT / "protocol/trial_runner.py", correction["source_after"])
    for name, digest in read(ROOT / "economics/history/pre-freeze-001/MANIFEST.json").items():
        pin(ROOT / "economics/history/pre-freeze-001" / name, digest)
    old_offering = read(ROOT / "protocol/history/COMPOSITION_PRELIMINARY_PRICE.json")
    require(bool(old_offering), "Missing preserved preliminary composition hypothesis")

    economic = ROOT / "economics"
    frozen = read(economic / "results/FREEZE.json")
    for name, key in (
        ("run_economics.py", "source_sha256"),
        ("protocol.json", "protocol_sha256"),
        ("results/pilot_input.json", "pilot_sha256"),
        ("../integration/admission.py", "admission_source_sha256"),
    ):
        pin(economic / name, frozen[key])
    completed = read(economic / "results/CONFIRMATION_COMPLETE.json")
    for name, key in (
        ("results/FREEZE.json", "freeze_sha256"),
        ("results/confirmation.json", "results_sha256"),
        ("results/events.jsonl.gz", "event_stream_sha256"),
    ):
        pin(economic / name, completed[key])
    value_freeze = read(economic / "value_results/VALUE_FREEZE.json")
    for name, digest in value_freeze["bindings"].items():
        pin(economic / name, digest)
    value_complete = read(economic / "value_results/VALUE_CONFIRMATION_COMPLETE.json")
    for name, key in (
        ("value_results/VALUE_FREEZE.json", "freeze_sha256"),
        ("value_results/confirmation.json", "confirmation_sha256"),
        ("value_results/events.jsonl.gz", "events_sha256"),
        ("results/confirmation.json", "original_results_sha256_unchanged"),
    ):
        pin(economic / name, value_complete[key])
    pin(
        economic / "prescreen_experiment.py",
        read(economic / "prescreen_results/PRESCREEN_FREEZE.json")["source_sha256"],
    )
    native_protocol = read(ROOT / "integration/results/workflow-v2/protocol.json")
    pin(ROOT / "integration/run_native_integration.py", native_protocol["runner_sha256"])
    upstream = ROOT.parent / "agi-alpha-capability-opportunity-v1/integration"
    for name, digest in native_protocol["upstream_adapter_pins"].items():
        pin(upstream / name, digest)
    closure = read(upstream / "source_manifest.json")
    for entry in closure["files"]:
        path = upstream / entry["local_path"]
        pin(path, entry["sha256"])
        require(path.stat().st_size == entry["bytes"], "Source size mismatch: " + str(path))
    return {
        "checked_distinct_files": len(checks),
        "pins": checks,
        "upstream_adapter_files": len(native_protocol["upstream_adapter_pins"]),
        "upstream_manifest_files": len(closure["files"]),
        "preserved_corrections": ["runner locking", "economic recipient shift and H scope", "C5 price and H scope"],
    }


def check_trials() -> dict[str, Any]:
    """Verify frozen inventories and replay all sixteen archived deliverables."""
    trials = ROOT / "results/trials"
    primary = read(ROOT / "results/pilot_summary.json")
    composition = read(ROOT / "results/composition_summary.json")
    freeze = read(ROOT / "protocol/CONFIRMATION_FREEZE.json")
    c5_freeze = read(ROOT / "protocol/COMPOSITION_FREEZE.json")
    exposure = read(ROOT / "protocol/C5_EXPOSURE_CHECK.json")
    states = {arm: read(trials / arm / "state.json") for arm in ("development", *ARMS, *("C5_" + a for a in ARMS))}
    require(exposure["all_primary_closed"], "C5 exposure declaration is not closed")
    for arm in ARMS:
        require(states[arm]["started_at"] > freeze["utc_epoch"], "Primary participant preceded freeze")
        require(states[arm]["finished_at"] == exposure["primary_finish_times"][arm], "Primary exposure times differ")
        require(states[arm]["finished_at"] < exposure["prepared_at_epoch"], "C5 exposed before primary closure")
        require(states["C5_" + arm]["started_at"] > exposure["prepared_at_epoch"], "C5 participant preceded exposure")
        require(states["C5_" + arm]["started_at"] > c5_freeze["frozen_at_epoch"], "C5 participant preceded freeze")
    require(states["development"]["finished_at"] < freeze["utc_epoch"], "Development did not precede freeze")
    output_rows: list[dict[str, Any]] = []
    inventories: dict[str, Any] = {}
    for arm, state in states.items():
        folder = trials / arm
        require(state["closed"] and state["within_envelope"], "Runner not closed within budget: " + arm)
        require(state["operations"] <= state["operations_limit"], "Operation limit exceeded: " + arm)
        require(state["elapsed_seconds"] <= state["wall_seconds_limit"], "Wall-time limit exceeded: " + arm)
        require(state["token_counts"] is None and state["actual_cost_usd"] is None, "Unmetered cost mislabeled")
        inventory = state["submission_inventory"]
        actual = {
            str(p.relative_to(folder / "frozen_submission"))
            for p in (folder / "frozen_submission").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        require(actual == set(inventory), "Frozen inventory names changed: " + arm)
        for name, entry in inventory.items():
            path = folder / "frozen_submission" / name
            require(
                sha(path) == entry["sha256"] and path.stat().st_size == entry["bytes"],
                "Submission changed: " + str(path),
            )
        events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
        require(len(events) == state["operations"] + 1 and events[-1]["kind"] == "finish", "Runner log/count mismatch")
        require(
            [e["operation"] for e in events[:-1]] == list(range(1, state["operations"] + 1)), "Runner sequence mismatch"
        )
        require(sum(e.get("kind") == "run" for e in events) == state["test_executions"], "Test execution count differs")
        inventories[arm] = {
            "files": len(inventory),
            "logged_operations": state["operations"],
            "elapsed_seconds": state["elapsed_seconds"],
            "failed_logged_test_executions": sum(
                e.get("kind") == "run" and e.get("returncode", 0) != 0 for e in events
            ),
        }
        for case in ("development",) if arm == "development" else (("c5",) if arm.startswith("C5_") else CASES):
            submission = folder / "frozen_submission" / case
            if case == "c5":
                command = [sys.executable, str(ROOT / "benchmark_composition/private/evaluate.py"), str(submission)]
                stored = read(folder / "case_acceptance.json")
                aggregate = composition["arms"][arm[3:]]
                expected_categories = 14
            else:
                command = [sys.executable, str(ROOT / "benchmark/private/evaluate.py"), case, str(submission)]
                stored = (
                    read(ROOT / "results/development_acceptance.json")
                    if case == "development"
                    else read(folder / f"{case}_acceptance.json")
                )
                aggregate = (
                    None
                    if case == "development"
                    else next(r for r in primary["arms"][arm]["per_case"] if r["case"] == case)
                )
                expected_categories = 10
            replay = json.loads(invoke(command).stdout)
            for result in (stored, replay, *([aggregate] if aggregate is not None else [])):
                require(
                    result["accepted"] and result["passed"] == result["total"] == expected_categories,
                    "Acceptance mismatch",
                )
                require(result["source_sha256"] == sha(submission / "engine.py"), "Accepted source binding differs")
            require(
                (submission / "REPAIR.md").is_file() and (submission / "test_regression.py").is_file(),
                "Deliverable incomplete",
            )
            canonical = ROOT / ("benchmark_composition" if case == "c5" else "benchmark") / "cases" / case
            for name in ("CONTRACT.md", "test_public.py"):
                require(
                    (submission / name).read_bytes() == (canonical / name).read_bytes(),
                    "Canonical public material changed",
                )
            if case == "c5":
                require((submission / "OFFERING.md").is_file(), "C5 offering rationale missing")
            output_rows.append(
                {
                    "arm": arm,
                    "case": case,
                    "accepted": True,
                    "categories": expected_categories,
                    "source_sha256": replay["source_sha256"],
                }
            )
    require(
        primary["observed_customer_collections_usd"] == 0 and primary["actual_complete_cost_usd"] is None,
        "Actual cash/cost label changed",
    )
    require(
        primary["operational_acceptance_difference"] == primary["additional_learning_acceptance_difference"] == 0,
        "Primary summary differs",
    )
    require(
        not composition["comparisons"]["newly_feasible_exclusive_offering_demonstrated"],
        "Unsupported C5 crossing claim",
    )
    return {
        "primary_outputs_accepted": 12,
        "composition_outputs_accepted": 3,
        "development_outputs_accepted": 1,
        "independent_primary_task_families": 4,
        "independent_composition_tasks": 1,
        "outputs": output_rows,
        "inventory_and_runner_checks": inventories,
        "limits": "Saved-output replay only; assertions are not independent tasks and elapsed time is not a replicated treatment effect.",
    }


def check_capsule(temporary: Path, native_enabled: bool) -> dict[str, Any]:
    """Compare actual bytes and optionally repeat the synthetic-authority fixture."""
    capsule = ROOT / "workflows/workflow_capsule.zip"
    expected = capsule.read_bytes()
    stored = ROOT / "integration/results/workflow-v2"
    for name in ("source-workflow.zip", "received-workflow.bin", "ordinary-library-workflow.bin"):
        require((stored / name).read_bytes() == expected, "Capability byte mismatch: " + name)
    with zipfile.ZipFile(capsule) as bundle:
        require(
            set(bundle.namelist()) == {"expert_v1.json", "learned_v2.json", "contract_probes.py", "CAPABILITY.md"},
            "Unexpected capsule contents",
        )
        for name in bundle.namelist():
            require(bundle.read(name) == (ROOT / "workflows" / name).read_bytes(), "Capsule member changed: " + name)
    helper = (ROOT / "workflows/contract_probes.py").read_bytes()
    for relative in (
        "development/frozen_submission/development/contract_probes.py",
        "E_plus/contract_probes.py",
        "C5_E_plus/contract_probes.py",
    ):
        require(
            (ROOT / "results/trials" / relative).read_bytes() == helper, "Development/recipient helper lineage differs"
        )
    archived = read(stored / "summary.json")
    require(
        archived["passed"] == archived["total"] == 31 and all(c["passed"] for c in archived["checks"]),
        "Archived controls fail",
    )
    require(
        archived["live_ens_authentications"]
        == archived["frontier_calls_in_this_fixture"]
        == archived["actual_collections_usd"]
        == 0,
        "Fixture/actual boundary changed",
    )
    require(
        archived["actual_complete_cost_profit"] is None and not archived["empirical_alpha_admission"],
        "Unsupported admission/profit",
    )
    decision = read(ROOT / "integration/actual_admission_decision.json")
    require(
        decision["observed_independent_mission_clusters"] == 4 and decision["existing_minimum_paired_clusters"] == 6,
        "Admission gate changed",
    )
    require(not decision["assessment_purchased"] and not decision["costs_complete"], "Actual admission status changed")
    result: dict[str, Any] = {
        "capsule_sha256": sha(capsule),
        "capsule_bytes": len(expected),
        "archived_controls": 31,
        "native_replay": "skipped by explicit flag",
        "live_authentication": False,
        "actual_profit": None,
    }
    if native_enabled:
        destination = temporary / "native-fixture"
        invoke(
            [
                sys.executable,
                str(ROOT / "integration/run_native_integration.py"),
                "--artifact",
                str(capsule),
                "--out",
                str(destination),
            ]
        )
        fresh = read(destination / "summary.json")
        require(fresh["passed"] == fresh["total"] == 31, "Fresh native fixture failed")
        require(
            [(c["name"], c["passed"]) for c in fresh["checks"]]
            == [(c["name"], c["passed"]) for c in archived["checks"]],
            "Native control semantics/count differ",
        )
        require((destination / "received-workflow.bin").read_bytes() == expected, "Fresh transported bytes differ")
        result.update(native_replay="31/31 passed under simulated authority", source_files=fresh["source_files"])
    return result


def row_identity(row: dict[str, Any]) -> None:
    """Independently reconcile each stored economic outcome's principal identities."""
    require(row["cash_cents"] == row["seed_capital_cents"] + row["profit_cents"], "Cash/capital/profit differs")
    require(row["profit_cents"] == row["net_collections_cents"] - row["total_cost_cents"], "Profit identity fails")
    require(
        row["net_collections_cents"] == row["collections_cents"] - row["refunds_cents"],
        "Collection/refund identity fails",
    )
    require(
        row["total_cost_cents"] == sum(sum(bucket.values()) for bucket in row["costs_cents"].values()),
        "Disjoint bucket sum fails",
    )
    require(row["attempted"] == row["accepted"] + row["failed"], "Job denominator differs")
    require(
        row["available_cents"] == row["cash_cents"] - row["reserve_cents"] - row["obligations_cents"],
        "Available funds differ",
    )
    require(row["receivables_cents"] == row["obligations_cents"] == 0, "Unsettled final obligations")
    require(
        row["actual_collections_cents"] == 0
        and row["actual_complete_cost_cents"] is None
        and row["actual_profit_cents"] is None,
        "Simulated money relabeled actual",
    )


def check_economics(temporary: Path, full: bool) -> dict[str, Any]:
    """Regenerate summaries, use the existing verifier and optionally re-simulate."""
    economic = ROOT / "economics"
    module = load("supporting_original_economics", economic / "run_economics.py")
    value = load("supporting_value_controller", economic / "value_controller.py")
    original_rows = read(economic / "results/confirmation.json")
    value_rows = read(economic / "value_results/confirmation.json")
    require(len(original_rows) == 4608 and len(value_rows) == 9216, "Stored history count changed")
    for row in original_rows + value_rows:
        row_identity(row)
    require(
        module.aggregate(original_rows) == read(economic / "results/summary.json"),
        "Original aggregate differs from rows",
    )
    require(
        value.summary(module, value_rows) == read(economic / "value_results/summary.json"),
        "Value aggregate differs from rows",
    )
    for rows, key_fields in (
        (original_rows, ("profile", "seed", "policy")),
        (value_rows, ("profile", "seed", "policy", "controller")),
    ):
        keys = [tuple(row[k] for k in key_fields) for row in rows]
        require(len(keys) == len(set(keys)), "Duplicate simulation history")

    # The existing verifier writes validation.json. Execute its unchanged source
    # in a minimal temporary tree so original evidence remains read-only.
    names = [
        "economics/verify_value_results.py",
        "economics/value_controller.py",
        "economics/value_protocol.json",
        "economics/run_economics.py",
        "economics/protocol.json",
        "integration/admission.py",
        "economics/results/FREEZE.json",
        "economics/results/pilot_input.json",
        "economics/results/confirmation.json",
        "economics/value_results/VALUE_FREEZE.json",
        "economics/value_results/confirmation.json",
    ]
    verifier_root = temporary / "existing-value-verifier"
    for name in names:
        target = verifier_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    invoke([sys.executable, str(verifier_root / "economics/verify_value_results.py")], verifier_root)
    existing = read(verifier_root / "economics/value_results/validation.json")
    require(existing == read(economic / "value_results/validation.json"), "Existing value verifier output differs")
    rerun_count = 0
    if full:
        config = read(economic / "protocol.json")
        pilot = module.load_pilot(economic / "results/pilot_input.json")
        original_freeze = read(economic / "results/FREEZE.json")
        value_freeze = read(economic / "value_results/VALUE_FREEZE.json")
        for stored in original_rows:
            fresh = module.simulate(
                pilot,
                config,
                stored["seed"],
                stored["profile"],
                stored["policy"],
                original_freeze["selection"][stored["policy"]],
            )
            fresh.pop("events", None)
            require(
                fresh == stored,
                "Full original rerun differs at " + str((stored["profile"], stored["seed"], stored["policy"])),
            )
            rerun_count += 1
        for stored in value_rows:
            policy = stored["policy"]
            if stored["controller"] == "value_selected":
                fresh = value.execute(
                    module, pilot, config, stored["seed"], stored["profile"], policy, value_freeze["selection"][policy]
                )
            else:
                fresh = module.simulate(
                    pilot, config, stored["seed"], stored["profile"], policy, original_freeze["selection"][policy]
                )
                fresh.update(
                    requested_policy=policy,
                    operative_policy=policy,
                    controller_mode="assess" if policy in value.OPTIONAL else "control",
                )
            fresh.pop("events", None)
            fresh["controller"] = stored["controller"]
            require(
                fresh == stored,
                "Full value rerun differs at " + str((stored["profile"], stored["seed"], policy, stored["controller"])),
            )
            rerun_count += 1
    return {
        "original_histories": len(original_rows),
        "value_histories": len(value_rows),
        "original_unique_profile_seed_worlds": len({(r["profile"], r["seed"]) for r in original_rows}),
        "value_unique_profile_seed_worlds": len({(r["profile"], r["seed"]) for r in value_rows}),
        "summary_reconstruction": "exact JSON equality for both editions",
        "all_history_accounting_identities": len(original_rows) + len(value_rows),
        "existing_value_verifier": existing,
        "full_selected_history_reruns": rerun_count,
        "event_stream_verification": "Both compressed stream SHA-256 bindings checked; individual events are not independently re-audited by this script.",
        "limits": "All economic histories are conditional simulations. Re-execution does not validate assumptions or recreate frontier behavior.",
    }


def check_prescreen(temporary: Path) -> dict[str, Any]:
    """Repeat the separately frozen artificial pre-assay-feasibility experiment."""
    source = ROOT / "economics/prescreen_results"
    destination = temporary / "prescreen"
    destination.mkdir()
    shutil.copyfile(source / "PRESCREEN_FREEZE.json", destination / "PRESCREEN_FREEZE.json")
    invoke([sys.executable, str(ROOT / "economics/prescreen_experiment.py"), "confirm", "--out", str(destination)])
    for name in ("prescreen_confirmation.json", "prescreen_summary.json"):
        require(read(destination / name) == read(source / name), "Prospective prescreen replay differs: " + name)
    return {
        "histories": len(read(destination / "prescreen_confirmation.json")),
        "worlds": read(destination / "prescreen_summary.json")["worlds"],
        "replay": "exact confirmation and summary equality",
        "limit": "New artificial candidate process; not repaired historical profit or empirical skill value.",
    }


def environment() -> dict[str, Any]:
    """Record actual versions; do not silently install packages or access networks."""
    packages: dict[str, str | None] = {}
    for name in ("pydantic", "cryptography"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    node = shutil.which("node")
    return {
        "python": sys.version,
        "executable": sys.executable,
        "node": invoke([node, "--version"]).stdout.strip() if node else None,
        "packages": packages,
    }


def run(full_economics: bool = False, native_enabled: bool = True) -> dict[str, Any]:
    """Run the requested supporting evidence checks without changing source data."""
    started = time.perf_counter()
    report: dict[str, Any] = {
        "schema": "operational-alpha-supporting-reproduction/v1",
        "reproducer_sha256": sha(Path(__file__)),
        "scope": "Supporting studies only; excludes later opportunity-led extensions and publication/release validation.",
        "environment": environment(),
    }
    try:
        report["source_and_input_pins"] = check_pins()
        with tempfile.TemporaryDirectory(prefix="alpha-supporting-replay-") as directory:
            temporary = Path(directory)
            report["archived_output_replay"] = check_trials()
            report["capability_and_native"] = check_capsule(temporary, native_enabled)
            report["conditional_economics"] = check_economics(temporary, full_economics)
            report["prospective_prescreen"] = check_prescreen(temporary)
        report["passed"] = True
    except Exception as exc:
        report.update(passed=False, failure_type=type(exc).__name__, failure=str(exc))
    report["elapsed_seconds"] = time.perf_counter() - started
    report["not_claimed"] = [
        "new hosted model calls",
        "independent external replication",
        "complete actual monetary cost",
        "live ENS authentication",
        "customer revenue",
        "production admission",
        "full repository CI",
    ]
    return report


def main() -> None:
    """Parse the replay options and emit a fresh review artifact on request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-economics",
        action="store_true",
        help="Re-simulate all 13,824 selected histories; does not rerun policy search or frontier agents.",
    )
    parser.add_argument(
        "--skip-native",
        action="store_true",
        help="Skip fresh Node/cryptography fixture execution, while verifying archived controls and pinned closure.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional new JSON report path; refuses to overwrite existing files or frozen study directories.",
    )
    args = parser.parse_args()
    if args.report is not None:
        path = args.report.resolve()
        if path.exists() or (path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / "validation")):
            parser.error("report must be a new file outside frozen study directories (validation is allowed)")
    report = run(args.full_economics, not args.skip_native)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
