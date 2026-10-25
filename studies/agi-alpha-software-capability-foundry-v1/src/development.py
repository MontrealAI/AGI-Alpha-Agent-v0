# SPDX-License-Identifier: Apache-2.0
"""One bounded, pre-confirmation development selection on pinned source."""
from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

from callsite_adapters import committed_files, expected_workers
from constructor import ROOT, identity, load, retain_reader
from measurement import measured

COMMIT = "f836f06e8351e64db1da770e16e304b5feb01f28"
ORDER_SEED = 304971
REPEATS = 5


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def inventory(files: dict[str, bytes]) -> dict[str, dict[str, object]]:
    return {name: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for name, body in sorted(files.items())}


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def observed(operation) -> tuple[object, dict, list[list[str]]]:
    calls = []
    original = subprocess.Popen

    def launch(args, *pargs, **kwargs):
        calls.append([str(word) for word in args])
        return original(args, *pargs, **kwargs)

    with patch.object(subprocess, "Popen", launch):
        value, cost = measured(operation)
    categories = collections.Counter()
    for command in calls:
        if command[0] != "git":
            raise ValueError("Unexpected benchmark child process")
        category = "cat-file" if "cat-file" in command else "ls-tree" if "ls-tree" in command else "show" if "show" in command else "other"
        categories[category] += 1
    cost.update(subprocesses=len(calls), git_subcommands=dict(categories))
    return value, cost, calls


def append(path: Path, row: dict) -> None:
    with path.open("a") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")


def make_patches(destination: Path, selected: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    source = selected.read_text()
    adapter = (ROOT / "src/callsite_adapters.py").read_text()
    changes = []
    for name, text in [("scripts/foundry_snapshot_reader.py", source), ("scripts/foundry_snapshot_adapters.py", adapter)]:
        changes.extend(difflib.unified_diff([], text.splitlines(keepends=True), fromfile="/dev/null", tofile="b/" + name))
    (destination / "0001-add-bounded-snapshot-reader-and-adapters.patch").write_text("".join(changes))
    (destination / "README.md").write_text(
        "# Additive snapshot-reader patch\n\n"
        "This patch adds two files only. It does not replace a publisher, change a security gate, or modify the original release/verifier implementation. "
        "The source helper is byte-identical to the development-selected retained reader. The adapters were executed against pinned original functions on commit `" + COMMIT + "`.\n\n"
        "Review/apply through the existing source owner. Explicit call sites may use:\n\n```python\n"
        "from scripts.foundry_snapshot_reader import read\n"
        "from scripts.foundry_snapshot_adapters import committed_files, expected_workers\n"
        "files = committed_files(root, exact_commit, read)\n"
        "workers = expected_workers(root, exact_commit, exact_inventory, read, is_cache_asset, render_scripts, MAX_BLOB)\n```\n\n"
        "The paper adapter keeps mode `100644`, the original MAX_BLOB and renderer. The companion adapter preserves configuration-derived payload names and per-file bounds. "
        "Calls split at 256 paths. Total limits are the original per-file bound times the bounded chunk size; actual measured inventories are much smaller. "
        "The reader refuses its documented unsupported path forms. Do not silently expand its applicability; retain the original route or obtain explicit review for other inputs. "
        "Production integration, full platform/release qualification, merge and deployment have not been performed by this patch.\n"
    )


def run(repo: Path) -> dict:
    started = time.perf_counter()
    destination = ROOT / "development/callsite-benchmark"
    if destination.exists() or (ROOT / "protocol/selection.json").exists():
        raise ValueError("Development selection already exists; preserve the original boundary")
    destination.mkdir(parents=True)
    actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if actual != COMMIT:
        raise ValueError("Pinned development checkout changed")
    sources = {name: identity(ROOT / name) for name in ["src/snapshot_reader.py", "review/specialist.py", "src/callsite_adapters.py", "src/development.py", "src/measurement.py", "src/constructor.py"]}
    sources.update({"upstream/" + name: identity(repo / name) for name in ["scripts/strategy_engineering_release.py", "scripts/paper_changes.py", "scripts/build_service_worker.py"]})
    rng = random.Random(ORDER_SEED)
    orders = []
    for repeat in range(REPEATS):
        names = ["original", "candidate", "specialist", "sequential"]
        rng.shuffle(names)
        orders.append(names)
    plan = {"schema": "foundry-development-plan/v1", "commit": COMMIT, "source_identities": sources,
            "selection_rule": "Select the lower median complete operation total CPU among correct candidate and independent specialist on A only; five repeats; tie goes to specialist; no B reselection.",
            "repeats": REPEATS, "order_seed": ORDER_SEED, "A_order": orders,
            "measurement_scope": "Original/adapter invocation, exact output equality against original, and returned output SHA-256 inventory. Preparation/import/reference costs are separately retained.",
            "cache_scope": "Interleaved in-process repetitions on a shared OS page cache; no disk-cold claim.",
            "hardware": {"platform": platform.platform(), "machine": platform.machine(), "cpu_count": os.cpu_count(), "python": sys.version, "git": subprocess.check_output(["git", "--version"], text=True).strip()},
            "not_confirmation": True, "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write(destination / "plan.json", plan)

    def prepare():
        sys.path.insert(0, str(repo))
        from scripts import strategy_engineering_release, paper_changes
        candidate = load(ROOT / "src/snapshot_reader.py")
        specialist = load(ROOT / "review/specialist.py")
        return strategy_engineering_release, paper_changes, candidate, specialist

    (strategy, papers, candidate, specialist), prep_cost = measured(prepare)
    reference, reference_cost, reference_calls = observed(lambda: strategy._committed_files(repo, COMMIT))
    reference_identity = inventory(reference)
    write(destination / "A-reference.json", {"files": reference_identity, "cost": reference_cost, "command_trace": reference_calls})
    methods = {"original": lambda: strategy._committed_files(repo, COMMIT),
               "candidate": lambda: committed_files(repo, COMMIT, candidate.read),
               "specialist": lambda: committed_files(repo, COMMIT, specialist.read),
               "sequential": lambda: committed_files(repo, COMMIT, candidate.sequential)}
    rows = []
    for repeat, order in enumerate(orders):
        for method in order:
            def operation():
                actual_files = methods[method]()
                if actual_files != reference:
                    raise ValueError("Mission A output differs from unmodified original")
                return inventory(actual_files)

            proof, cost, calls = observed(operation)
            row = {"mission": "A", "repeat": repeat, "ordinal": len(rows), "method": method, "passed": proof == reference_identity, "output_inventory_sha256": digest(proof), **cost}
            rows.append(row)
            append(destination / "A-raw.jsonl", row)
            append(destination / "A-command-traces.jsonl", {"ordinal": row["ordinal"], "method": method, "commands": calls})
    summary_a = {method: {"median_total_cpu_seconds": statistics.median(row["total_cpu_seconds"] for row in rows if row["method"] == method),
                          "median_wall_seconds": statistics.median(row["wall_seconds"] for row in rows if row["method"] == method),
                          "correct_repeats": sum(row["passed"] for row in rows if row["method"] == method),
                          "subprocesses_per_repeat": sorted({row["subprocesses"] for row in rows if row["method"] == method})}
                 for method in methods}
    eligible = [method for method in ["specialist", "candidate"] if summary_a[method]["correct_repeats"] == REPEATS]
    if not eligible:
        raise ValueError("No bounded reader qualified")
    selected_method = min(eligible, key=lambda method: summary_a[method]["median_total_cpu_seconds"])
    chosen = ROOT / ("src/snapshot_reader.py" if selected_method == "candidate" else "review/specialist.py")
    equivalent = "review/specialist.py" if selected_method == "candidate" else "src/snapshot_reader.py"
    acceptance = {"schema": "foundry-development-A-acceptance/v1", "passed": True, "source_commit": COMMIT,
                  "selected_method": selected_method, "parent_sha256": identity(chosen), "source_path": str(chosen.relative_to(ROOT)),
                  "files": reference_identity, "output_inventory_sha256": digest(reference_identity),
                  "selection_summary": summary_a, "raw_results_sha256": identity(destination / "A-raw.jsonl"),
                  "plan_sha256": identity(destination / "plan.json"), "qualification": "Exact original outputs across five interleaved development repeats; no protected confirmation claim"}
    acceptance_path = ROOT / "development/mission-a-acceptance.json"
    write(acceptance_path, acceptance)
    retained, retention_cost = measured(lambda: retain_reader(chosen, ROOT / "assets/reader", acceptance))
    selection = {"schema": "foundry-selection/v1", "selected_method": selected_method,
                 "selected_source": "assets/reader/reader.py", "selected_source_sha256": retained["sha256"],
                 "template_source": str(chosen.relative_to(ROOT)), "equivalent_source": equivalent,
                 "qualification_path": str(acceptance_path.relative_to(ROOT)), "qualification_sha256": identity(acceptance_path),
                 "selection_rule": plan["selection_rule"], "selection_summary": summary_a,
                 "frozen_before_mission_B": True, "source_identities": sources}
    write(ROOT / "protocol/selection.json", selection)
    selected = load(ROOT / "assets/reader/reader.py")
    listing, tree_cost, tree_calls = observed(lambda: papers.tree(repo, COMMIT))
    reference_b, reference_b_cost, reference_b_calls = observed(lambda: papers.expected_workers(repo, listing))
    identity_b = inventory(reference_b)
    write(destination / "B-reference.json", {"workers": identity_b, "tree_preparation_cost": tree_cost, "reference_cost": reference_b_cost, "tree_commands": tree_calls, "reference_commands": reference_b_calls})
    b_order = []
    for repeat in range(REPEATS):
        order = ["original", "selected"]
        rng.shuffle(order)
        b_order.append(order)
    write(destination / "B-plan.json", {"orders": b_order, "selection_sha256": identity(ROOT / "protocol/selection.json"), "no_reselection": True})
    rows_b = []
    for repeat, order in enumerate(b_order):
        for method in order:
            def operation():
                if method == "original":
                    value = papers.expected_workers(repo, listing)
                else:
                    value = expected_workers(repo, COMMIT, listing, selected.read, papers.is_cache_asset, papers.render_scripts, papers.MAX_BLOB)
                if value != reference_b:
                    raise ValueError("Mission B rendered bytes differ from unmodified original")
                return inventory(value)

            proof, cost, calls = observed(operation)
            row = {"mission": "B", "repeat": repeat, "ordinal": len(rows_b), "method": method,
                   "passed": proof == identity_b, "rendered_inventory_sha256": digest(proof), "parent_sha256": retained["sha256"] if method == "selected" else None, **cost}
            rows_b.append(row)
            append(destination / "B-raw.jsonl", row)
            append(destination / "B-command-traces.jsonl", {"ordinal": row["ordinal"], "method": method, "commands": calls})
    summary_b = {method: {"median_total_cpu_seconds": statistics.median(row["total_cpu_seconds"] for row in rows_b if row["method"] == method),
                          "median_wall_seconds": statistics.median(row["wall_seconds"] for row in rows_b if row["method"] == method),
                          "correct_repeats": sum(row["passed"] for row in rows_b if row["method"] == method),
                          "subprocesses_per_repeat": sorted({row["subprocesses"] for row in rows_b if row["method"] == method})}
                 for method in ["original", "selected"]}
    b_acceptance = {"schema": "foundry-development-B-acceptance/v1", "passed": summary_b["selected"]["correct_repeats"] == REPEATS,
                    "parent_sha256": retained["sha256"], "source_commit": COMMIT, "rendered_outputs": identity_b,
                    "raw_results_sha256": identity(destination / "B-raw.jsonl"), "selection_sha256": identity(ROOT / "protocol/selection.json"),
                    "selected_execution": True, "parent_invocations_per_repeat": 3,
                    "scope": "One exact catalog read and two bounded asset chunks, consuming a prior accepted reader; no B tuning or selection"}
    write(ROOT / "development/mission-b-acceptance.json", b_acceptance)
    make_patches(ROOT / "patches", chosen)
    for name, expected in sources.items():
        target = repo / name.removeprefix("upstream/") if name.startswith("upstream/") else ROOT / name
        if identity(target) != expected:
            raise ValueError("Source changed during development; evidence boundary is invalid")
    summary = {"schema": "foundry-callsite-development/v1", "commit": COMMIT, "source_identities": sources,
               "selected_method": selected_method, "selected_sha256": retained["sha256"], "A": summary_a, "B": summary_b,
               "preparation_cost": prep_cost, "reference_A_cost": reference_cost, "retention_cost": retention_cost,
               "B_tree_cost": tree_cost, "reference_B_cost": reference_b_cost,
               "measured_attempts_total_cpu_seconds": sum(row["total_cpu_seconds"] for row in rows + rows_b),
               "measured_attempts_wall_seconds": sum(row["wall_seconds"] for row in rows + rows_b),
               "complete_invocation_wall_seconds": time.perf_counter() - started,
               "model_construction_cost": None, "human_seconds": None, "money": None, "maintenance_cost": None,
               "status": "DEVELOPMENT_ONLY_FROZEN_SELECTION_NOT_CONFIRMATION"}
    write(destination / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    run(parser.parse_args().repo.resolve())
