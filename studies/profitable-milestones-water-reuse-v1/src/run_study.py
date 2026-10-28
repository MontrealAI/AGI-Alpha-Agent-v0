# SPDX-License-Identifier: Apache-2.0
"""Freeze once, confirm once, and replay the preserved confirmation without retuning."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import expert
import ordinary
import verifier
from confirmation_cases import decode_cases, encode_cases, generate_cases

ROOT = Path(__file__).resolve().parents[1]
FROZEN = [
    "protocol/acceptance.json",
    "inputs/published_case.json",
    "src/expert.py",
    "src/ordinary.py",
    "src/verifier.py",
    "src/confirmation_cases.py",
]


def save(path: str, value: Any) -> None:
    """Write ordinary strict JSON with no special nonfinite tokens."""
    (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def same_numbers(left: Any, right: Any) -> bool:
    """Compare numerical outputs at the preregistered tolerance."""
    if left is None or right is None:
        return left is right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_numbers(a, b) for a, b in zip(left, right))
    return math.isclose(float(left), float(right), rel_tol=1e-8, abs_tol=1e-6)


def main() -> None:
    """Produce preserved results, claims and timing for all three arms."""
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FROZEN}
    freeze_path = ROOT / "protocol/implementation_freeze.json"
    fresh = not (ROOT / "inputs/confirmation.json").exists()
    if freeze_path.exists():
        frozen = json.loads(freeze_path.read_text())
        if hashes != frozen["sha256"]:
            raise SystemExit(
                "Frozen source changed; preserve the original edition and create a new diagnostic revision."
            )
    else:
        if not fresh:
            raise SystemExit("Confirmation exists without source freeze")
        save(
            "protocol/implementation_freeze.json",
            {
                "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
                "sha256": hashes,
                "confirmation_seed": 2026102719,
                "confirmation_generated": False,
                "policy": "One confirmation round; later runs replay the same cases, not a new holdout.",
            },
        )
    if fresh:
        cases = generate_cases(seed=2026102719)
        save("inputs/confirmation.json", encode_cases(cases))
    else:
        cases = decode_cases(json.loads((ROOT / "inputs/confirmation.json").read_text()))
    rows: list[dict[str, Any]] = []
    all_outputs: list[dict[str, Any]] = []
    totals: dict[str, Any] = {}
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    for arm, module in [("ordinary", ordinary), ("expert", expert), ("conventional", verifier)]:
        arm_start_cpu, arm_start_wall = time.process_time(), time.perf_counter()
        for record in cases:
            case = record["case"]
            try:
                answer = module.evaluate(case)
            except Exception as error:
                answer = {"decision": "EXCEPTION", "error": type(error).__name__ + ": " + str(error)}
            reference = verifier.evaluate(case)
            declared = record.get("expected_decision")
            semantic_match = declared is None or answer.get("decision") == declared
            decision_match = answer.get("decision") == reference["decision"]
            numeric_match = all(
                same_numbers(answer.get(k), reference.get(k))
                for k in ("cash_margin", "accounting_margin", "npv", "simple_payback")
            )
            refusal_clean = answer.get("decision") not in ("INVALID_INPUT", "OUT_OF_SCOPE") or all(
                answer.get(k) is None for k in ("cash_margin", "accounting_margin", "npv", "simple_payback")
            )
            status = record.get("protocol_status", "clear")
            passed = semantic_match and decision_match and numeric_match and refusal_clean
            rows.append(
                {
                    "arm": arm,
                    "case_id": record["id"],
                    "category": record.get("category", ""),
                    "protocol_status": status,
                    "expected": declared,
                    "actual": answer.get("decision"),
                    "semantic_match": semantic_match,
                    "decision_match": decision_match,
                    "numeric_match": numeric_match,
                    "refusal_clean": refusal_clean,
                    "passed": passed,
                }
            )
            all_outputs.append(
                {"arm": arm, "case_id": record["id"], "result": answer, "independent_reference": reference}
            )
        own = [r for r in rows if r["arm"] == arm]
        totals[arm] = {
            "cases": len(own),
            "passed": sum(r["passed"] for r in own),
            "decision_counts": dict(Counter(r["actual"] for r in own)),
            "cpu_seconds_including_oracle": time.process_time() - arm_start_cpu,
            "wall_seconds_including_oracle": time.perf_counter() - arm_start_wall,
        }
    with (ROOT / "results/confirmation.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    save("results/confirmation_outputs.json", all_outputs)
    save(
        "results/published_case_result.json",
        expert.evaluate(json.loads((ROOT / "inputs/published_case.json").read_text())),
    )
    summary = {
        "evidence_level": "executed software on synthetic confirmation cases",
        "fresh_generation_this_run": fresh,
        "case_count": len(cases),
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_seconds": time.process_time() - start_cpu,
        "wall_seconds": time.perf_counter() - start_wall,
        "arms": totals,
        "failures": [r for r in rows if not r["passed"]],
        "source_sha256": hashes,
        "confirmation_sha256": hashlib.sha256((ROOT / "inputs/confirmation.json").read_bytes()).hexdigest(),
        "actual_customers": 0,
        "actual_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "model_usage_and_billing": None,
    }
    if fresh:
        save("evidence/first_confirmation.json", summary)
    save("results/confirmation_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
