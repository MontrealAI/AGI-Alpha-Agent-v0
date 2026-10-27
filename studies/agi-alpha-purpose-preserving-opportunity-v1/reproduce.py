# SPDX-License-Identifier: Apache-2.0
"""Replay frozen source-screen and accounting experiments without paid services."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_files(root: Path) -> dict[str, Any]:
    """Verify the linked method and confirmation manifests before execution."""
    method_path = root / "METHOD_FREEZE.json"
    method = read(method_path)
    confirmation = read(root / "evaluation/CONFIRMATION_FREEZE.json")
    if digest(method_path) != confirmation["method_freeze_sha256"]:
        raise ValueError("confirmation-to-method manifest link drift")
    for label, manifest in (("method", method), ("confirmation", confirmation)):
        for relative, metadata in manifest["files"].items():
            path = (root / relative).resolve()
            if root.resolve() not in path.parents:
                raise ValueError("manifest path must remain inside study: " + relative)
            if digest(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
                raise ValueError(f"frozen {label} drift: {relative}")
    if digest(root / "data/catalog.json") != confirmation["catalog_sha256"]:
        raise ValueError("confirmation catalog commitment drift")
    if digest(root / "evaluation/oracle.py") != confirmation["oracle_sha256"]:
        raise ValueError("confirmation oracle commitment drift")
    if digest(root / "capability/catalog.json") != confirmation["catalog_sha256"]:
        raise ValueError("distributed catalog differs from frozen research catalog")
    expected_packets = {
        root / relative for relative in confirmation["files"] if relative.startswith("evaluation/packets/")
    }
    actual_packets = set((root / "evaluation/packets").glob("packet_*.json"))
    if actual_packets != expected_packets:
        raise ValueError("packet directory differs from frozen confirmation membership")
    return dict(confirmation)


def grade_saved_workflows(root: Path, catalog: Any, oracle: ModuleType) -> dict[str, Any]:
    """Regrade recorded outputs; this does not rerun or retime frontier agents."""
    evidence = root / "workflow_evidence"
    if not evidence.exists():
        return {"status": "recorded_workflow_evidence_not_present", "agents_rerun": False}
    for relative, metadata in read(evidence / "MANIFEST.json").items():
        path = (evidence / relative).resolve()
        if evidence.resolve() not in path.parents:
            raise ValueError("workflow manifest path escapes evidence directory")
        if digest(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
            raise ValueError("recorded workflow evidence drift: " + relative)
    if digest(evidence / "Eplus/obligation_compiler.py.txt") != digest(root / "capability/obligation_compiler.py"):
        raise ValueError("recipient E+ did not receive identical retained source bytes")
    rows = []
    for condition in ("U", "E", "Eplus"):
        directory = evidence / condition
        if digest(directory / "catalog.json") != digest(root / "data/catalog.json"):
            raise ValueError("workflow catalog drift: " + condition)
        for packet in ("a", "b"):
            frozen_packet = root / f"evaluation/packets/packet_{packet}.json"
            if digest(directory / f"packet_{packet}.json") != digest(frozen_packet):
                raise ValueError(f"workflow packet drift: {condition}/{packet}")
            tasks = read(frozen_packet)["tasks"]
            reports = read(directory / f"reports_{packet}.json")
            if not isinstance(reports, list):
                raise ValueError("workflow report must be a list")
            indexed = {report["task_id"]: report for report in reports}
            if len(indexed) != len(reports) or set(indexed) != {task["id"] for task in tasks}:
                raise ValueError(f"workflow output membership drift: {condition}/{packet}")
            decisions = [oracle.check_report(task, catalog, indexed[task["id"]]) for task in tasks]
            rows.append(
                {
                    "condition": condition,
                    "packet": packet,
                    "accepted": sum(decision["accepted"] for decision in decisions),
                    "total": len(decisions),
                    "decisions": decisions,
                }
            )
    return {
        "status": "saved_outputs_regraded",
        "agents_rerun": False,
        "latency_remeasured": False,
        "rows": rows,
        "accepted": sum(row["accepted"] for row in rows),
        "total": sum(row["total"] for row in rows),
    }


def replay_feasible_policy(root: Path, output: Path) -> dict[str, Any]:
    """Replay the separately frozen post-review policy, preserving original economics."""
    freeze_path = root / "economics/FEASIBLE_POLICY_FREEZE.json"
    if not freeze_path.exists():
        return {"status": "policy_addendum_not_present"}
    policy_freeze = read(freeze_path)
    cases = root / "review/policy_cases"
    case_freeze = read(cases / "FREEZE.json")
    if case_freeze["policy_freeze_record"] != policy_freeze:
        raise ValueError("policy case-to-method freeze link drift")
    if datetime.fromisoformat(case_freeze["created_at_utc"]) <= datetime.fromisoformat(policy_freeze["frozen_at_utc"]):
        raise ValueError("policy diagnostic cases must follow policy source freeze")
    for relative, metadata in policy_freeze["files"].items():
        path = (root / relative).resolve()
        if root.resolve() not in path.parents:
            raise ValueError("policy manifest path escapes study")
        if digest(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
            raise ValueError("frozen policy drift: " + relative)
    policy_path = root / "economics/feasible_policy.py"
    if digest(policy_path) != case_freeze["policy_source_sha256"]:
        raise ValueError("policy source differs from diagnostic commitment")
    for relative, commitment in case_freeze["files_sha256"].items():
        path = (cases / relative).resolve()
        if cases.resolve() not in path.parents or digest(path) != commitment:
            raise ValueError("policy diagnostic drift: " + relative)
    expected = read(cases / "EXPECTED.json")
    expected_files = {item["file"] for item in expected}
    committed_files = set(case_freeze["files_sha256"]) - {"EXPECTED.json"}
    if len(expected_files) != len(expected) or expected_files != committed_files:
        raise ValueError("policy diagnostic membership differs from frozen expectations")
    module = load_module("frozen_feasible_policy", policy_path)
    saved_validation = read(root / "review/policy_results/validation.json")
    saved_hashes = {case["file"]: case["output_sha256"] for case in saved_validation["cases"]}
    target = output / "feasible_policy"
    target.mkdir()
    decisions = []
    for item in expected:
        name = item["file"]
        result = module.select(read(cases / name))
        saved = root / "review/policy_results" / name
        if digest(saved) != saved_hashes[name] or result != read(saved):
            raise ValueError("policy output differs from preserved result: " + name)
        accepted = (
            result["selected_id"] == item["selected_id"] and result["eligible_ranking"] == item["eligible_ranking"]
        )
        write(target / name, result)
        decisions.append({"file": name, "accepted": accepted, "selected_id": result["selected_id"]})
    summary = {
        "status": "separate_frozen_policy_replayed",
        "passed": sum(decision["accepted"] for decision in decisions),
        "total": len(decisions),
        "all_hashes_and_freeze_order_verified": True,
        "preserved_outputs_identical": True,
        "cases": decisions,
        "scope": "constructed hypothetical decision diagnostics; no actual profit or live authority",
    }
    write(target / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--native", action="store_true", help="requires the pinned parent repository and native dependencies"
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("replay output must remain outside the preserved research directory")
    confirmation = verify_frozen_files(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    core = load_module("retained_obligation_compiler", ROOT / "capability/obligation_compiler.py")
    oracle = load_module("independent_obligation_oracle", ROOT / "evaluation/oracle.py")
    catalog = read(ROOT / "data/catalog.json")
    reports, decisions = [], []
    for path in sorted((ROOT / "evaluation/packets").glob("packet_*.json")):
        packet = path.stem.removeprefix("packet_")
        tasks = read(path)["tasks"]
        expected = read(ROOT / f"evaluation/protected/expected_{packet}.json")["reports"]
        if len(tasks) != confirmation["case_count"][packet.upper()] or len(tasks) != len(expected):
            raise ValueError("frozen packet count differs from manifest")
        for task, frozen_expected in zip(tasks, expected, strict=True):
            if oracle.reference_report(task, catalog) != frozen_expected:
                raise ValueError("frozen oracle answer drift for " + task["id"])
            report = core.audit(task, catalog)
            decision = oracle.check_report(task, catalog, report)
            reports.append({"packet": path.stem, "task": task, "report": report, "acceptance": decision})
            decisions.append(decision)
    with tempfile.TemporaryDirectory(prefix="ordinary-library-") as temporary:
        copied = Path(temporary) / "obligation_compiler.py"
        shutil.copyfile(ROOT / "capability/obligation_compiler.py", copied)
        ordinary = load_module("ordinary_library_copy", copied)
        parity = all(ordinary.audit(row["task"], catalog) == row["report"] for row in reports)
    write(output / "fresh_reports.json", reports)
    workflow = grade_saved_workflows(ROOT, catalog, oracle)
    write(output / "workflow_regrade.json", workflow)
    feasible_policy = replay_feasible_policy(ROOT, output)
    write(
        output / "summary.json",
        {
            "schema": "agialpha.replay.v1",
            "accepted": sum(d["accepted"] for d in decisions),
            "total": len(decisions),
            "ordinary_same_content_library_identical": parity,
            "frozen_confirmation_manifest_sha256": hashlib.sha256(
                (ROOT / "evaluation/CONFIRMATION_FREEZE.json").read_bytes()
            ).hexdigest(),
            "confirmation_hashes_verified": True,
            "linked_method_manifest_verified": True,
            "frozen_answers_reproduced": True,
            "recorded_workflow_outputs": {key: value for key, value in workflow.items() if key != "rows"},
            "feasible_policy_addendum": {key: value for key, value in feasible_policy.items() if key != "cases"},
            "scope": "source-screen artifact correctness; no customers, ecology, API billing or live ENS claims",
        },
    )
    economics = ROOT / "economics/economics.py"
    subprocess.run(
        [
            sys.executable,
            str(economics),
            "--inputs",
            str(ROOT / "economics/inputs.json"),
            "--output",
            str(output / "economics"),
        ],
        check=True,
    )
    if args.native:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "integration/native_adapter.py"),
                "--artifact",
                str(ROOT / "capability/obligation_compiler.py"),
                "--output",
                str(output / "native.json"),
            ],
            check=True,
        )
    print(json.dumps(read(output / "summary.json")))


if __name__ == "__main__":
    main()
