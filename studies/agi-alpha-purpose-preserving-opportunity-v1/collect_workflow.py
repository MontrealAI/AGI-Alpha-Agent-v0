# SPDX-License-Identifier: Apache-2.0
"""Preserve completed workflow evidence and grade it without changing any output."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=Path, required=True)
    args = parser.parse_args()
    destination = ROOT / "workflow_evidence"
    destination.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location("grading_oracle", ROOT / "evaluation/oracle.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("oracle unavailable")
    oracle = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = oracle
    spec.loader.exec_module(oracle)
    catalog = read(ROOT / "data/catalog.json")
    manifest: dict[str, Any] = {}
    rows = []
    for arm in ("U", "E", "Eplus"):
        target = destination / arm
        target.mkdir()
        for source in sorted((args.trials / arm).iterdir()):
            if not source.is_file():
                continue
            # Trial-created code is immutable archival evidence, not active package code.
            name = source.name + ".txt" if source.suffix == ".py" else source.name
            shutil.copyfile(source, target / name)
            manifest[f"{arm}/{name}"] = {
                "original_name": source.name,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "bytes": source.stat().st_size,
            }
        for packet in ("a", "b"):
            tasks = read(target / f"packet_{packet}.json")["tasks"]
            reports = read(target / f"reports_{packet}.json")
            receipt = read(target / f"receipt_{packet}.json")
            if len(tasks) != len(reports):
                raise ValueError(f"report count mismatch: {arm}/{packet}")
            grades = [oracle.check_report(t, catalog, r) for t, r in zip(tasks, reports, strict=True)]
            rows.append(
                {
                    "condition": "E+" if arm == "Eplus" else arm,
                    "packet": packet.upper(),
                    "accepted": sum(bool(g["accepted"]) for g in grades),
                    "total": len(tasks),
                    "elapsed_seconds": receipt["elapsed_seconds"],
                    "underlying_exec_operations": receipt.get(
                        "tool_call_count", receipt.get("logical_tool_operations")
                    ),
                    "budget_seconds": 480,
                    "external_feedback_before_output": False,
                    "post_grading_corrections_counted": 0,
                    "provider_tokens": None,
                    "complete_billed_cost_usd": None,
                    "customer_effort_observed": False,
                    "receipt_path": f"workflow_evidence/{arm}/receipt_{packet}.json",
                    "grades": grades,
                }
            )
    totals = {
        arm: {
            "accepted": sum(row["accepted"] for row in rows if row["condition"] == arm),
            "total": sum(row["total"] for row in rows if row["condition"] == arm),
            "elapsed_seconds": sum(row["elapsed_seconds"] for row in rows if row["condition"] == arm),
        }
        for arm in ("U", "E", "E+")
    }
    output = {
        "schema": "agialpha.workflow-observations.v1",
        "evidence_class": "observed_same_session_execution_and_independent_implementation_check",
        "method": "WORKFLOW_PROTOCOL.json",
        "one_actor_per_condition": True,
        "representative_user_population": False,
        "model_upgrade_tested": False,
        "model": "inherited same session GPT-6 Astra Pro identity; no controlled API model response IDs",
        "rows": rows,
        "totals": totals,
        "ordinary_baseline_retained_own_work": True,
        "expert_baseline_retained_own_work": True,
        "Eplus_used_immutable_actual_compiler": True,
        "interpretation": "All conditions qualified on every frozen audit at the same 480-second packet cap. The E+ artifact transferred; quality advantage and newly feasible work were not established. E+ was faster than E in this realization but slower than U in total. n=1 per condition, unequal verification details, missing dispatch timing and unknown billing prevent a robust complete-cost Alpha estimate.",
        "actual_customer_acceptance": False,
        "actual_collections_usd": 0,
        "actual_complete_profit_usd": None,
    }
    (destination / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "results/workflow_assay.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
