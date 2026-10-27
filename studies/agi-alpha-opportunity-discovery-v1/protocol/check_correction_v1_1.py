# SPDX-License-Identifier: Apache-2.0
"""Freeze-first generation and execution for the prospective snapshot correction."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def verify_freeze() -> dict[str, Any]:
    freeze = json.loads((ROOT / "protocol/correction-freeze-v1_1.json").read_text())
    for entry in freeze["files"] + freeze["preserved_v1_files"]:
        if sha(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"Frozen bytes changed: {entry['path']}")
    return freeze


def generate(out: Path) -> None:
    freeze = verify_freeze()
    requirements = json.loads(
        (ROOT / "protocol/correction_requirements_v1_1.json").read_text()
    )
    rng = random.Random(requirements["seed"])
    packet = json.loads(
        (ROOT / "results/confirmation-v1/raudenbush1985-packet.json").read_text()
    )
    ids = [row["id"] for row in packet["rows"]]
    cases: list[dict[str, Any]] = []

    def add(family: str, event: Any, **extra: Any) -> None:
        cases.append(
            {
                "case_id": f"fresh-{len(cases) + 1:03d}",
                "family": family,
                "event": event,
                "expected_status": requirements["expected_family_states"][family],
                **extra,
            }
        )

    def correction() -> dict[str, Any]:
        return {
            "id": f"event-{rng.getrandbits(48):012x}",
            "kind": "corrected_estimate",
            "row_ids": [rng.choice(ids)],
            "scope_confirmed": True,
            "replacement": {
                "yi": rng.uniform(-0.8, 0.9),
                "vi": rng.uniform(0.006, 0.19),
            },
        }

    for _ in range(8):
        event = correction()
        event[f"unqualified_{rng.getrandbits(40):010x}"] = rng.choice(
            [True, False, "new interpretation"]
        )
        add("unknown_field", event)
    for field in [
        "covariance",
        "correlation",
        "cluster_id",
        "shared_control",
        "dependence_disclosed",
    ]:
        event = correction()
        event[field] = {"related_row": rng.choice(ids), "value": rng.uniform(0.01, 0.6)}
        add("unsupported_covariance", event)
    for _ in range(4):
        event = correction()
        event["source_id"] = f"unqualified-source:{rng.getrandbits(48):012x}"
        add("correction_source_id", event)
    add(
        "unknown_background_source",
        {"kind": "background_notice", "source_id": f"other:{rng.getrandbits(48):012x}"},
    )
    add(
        "unknown_no_change_source",
        {"kind": "no_change", "source_id": f"other:{rng.getrandbits(48):012x}"},
    )
    for field in ["sequence_id", "previous_event_digest", "apply_after", "cumulative"]:
        event = correction()
        event[field] = f"prior-{rng.getrandbits(40):010x}"
        add("sequential_event_fields", event)
    for malformed in [None, ["corrected_estimate"], "no_change"]:
        add("malformed_event", malformed)
    add(
        "event_purpose_drift",
        {"kind": "no_change", "purpose_digest": f"other-{rng.getrandbits(64):016x}"},
    )
    for field in ["execute_authorized", "rights_current", "purpose"]:
        add("mission_authority_drift", {"kind": "no_change"}, mutation=field)
    add("packet_drift", {"kind": "no_change"}, packet_delta=rng.uniform(0.2, 0.4))
    event = correction()
    event["replacement"]["covariance"] = rng.uniform(0.001, 0.01)
    add("replacement_extra_field", event)
    for _ in range(6):
        add("valid_fresh_correction", correction())
    for count in [1, 3]:
        add(
            "valid_fresh_withdrawal",
            {
                "id": f"withdraw-{rng.getrandbits(48):012x}",
                "kind": "withdrawal",
                "row_ids": rng.sample(ids, count),
                "scope_confirmed": True,
            },
        )
    add("explicit_overlap", {"kind": "overlap_disclosed"})
    add("explicit_no_change", {"kind": "no_change"})
    for mode in ["sequential", "cumulative", f"other-{rng.getrandbits(32):08x}"]:
        add("sequential_batch", [correction()], mode=mode)
    withdrawn = rng.choice(ids)
    event = correction()
    event["row_ids"] = [
        rng.choice([identity for identity in ids if identity != withdrawn])
    ]
    add(
        "independent_batch",
        [
            {"kind": "withdrawal", "row_ids": [withdrawn], "scope_confirmed": True},
            event,
        ],
        mode="independent-snapshots",
    )
    out.mkdir(parents=True, exist_ok=False)
    write(out / "fresh-cases.json", cases)
    write(
        out / "generation.json",
        {
            "generated_at_utc": now(),
            "code_frozen_at_utc": freeze["frozen_at_utc"],
            "seed": requirements["seed"],
            "case_count": len(cases),
            "cases_sha256": sha(out / "fresh-cases.json"),
            "freeze_sha256": sha(ROOT / "protocol/correction-freeze-v1_1.json"),
            "instrument_executed_during_generation": False,
        },
    )
    print(
        json.dumps(
            {"stage": "generated-not-executed", "count": len(cases), "out": str(out)}
        )
    )


def oracle(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    selected = [row for row in rows if row["active"]]
    y = np.array([row["yi"] for row in selected])
    v = np.array([row["vi"] for row in selected])

    def score(t: float) -> float:
        w = 1 / (v + t)
        mean = float(sum(w * y) / sum(w))
        return float(sum(w * w * (y - mean) ** 2) - sum(w) + sum(w * w) / sum(w))

    upper = 1.0
    while score(upper) > 0:
        upper *= 2
    tau = 0.0 if score(0) <= 0 else float(brentq(score, 0, upper, xtol=1e-13))
    w = 1 / (v + tau)
    mean, se = float(sum(w * y) / sum(w)), float(1 / np.sqrt(sum(w)))
    return {
        "k": len(selected),
        "estimate": mean,
        "se": se,
        "tau2": tau,
        "ci_lower": mean - 1.959963984540054 * se,
        "ci_upper": mean + 1.959963984540054 * se,
    }


def execute(out: Path) -> None:
    freeze = verify_freeze()
    generation = json.loads((out / "generation.json").read_text())
    if sha(out / "fresh-cases.json") != generation["cases_sha256"]:
        raise ValueError("Generated case bytes changed")
    if (
        sha(ROOT / "protocol/correction-freeze-v1_1.json")
        != generation["freeze_sha256"]
    ):
        raise ValueError("Freeze manifest changed")
    spec = importlib.util.spec_from_file_location(
        "continuity_v1_1", ROOT / "instrument/continuity_v1_1.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Candidate module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    packet = json.loads(
        (ROOT / "results/confirmation-v1/raudenbush1985-packet.json").read_text()
    )
    mission = json.loads(
        (ROOT / "results/confirmation-v1/raudenbush1985-mission.json").read_text()
    )
    results = []
    for case in json.loads((out / "fresh-cases.json").read_text()):
        p, m = copy.deepcopy(packet), copy.deepcopy(mission)
        if "mutation" in case:
            field = case["mutation"]
            m[field] = {"new": "purpose"} if field == "purpose" else False
        if "packet_delta" in case:
            p["rows"][0]["yi"] += case["packet_delta"]
        event = case["event"]
        result = (
            module.process_snapshot_batch(p, m, event, case["mode"])
            if "mode" in case
            else module.process(p, m, event)
        )
        correct = result["status"] == case["expected_status"]
        correct &= (
            result["commercial_acceptance"] is False
            and result["production_admission"] is False
        )
        correct &= result["cumulative_history"] is False
        reference = None
        if result["status"] in ["hold", "reject"]:
            correct &= result.get("numeric_result") is None
            if "mode" in case:
                correct &= result["results"] == []
        if result["status"] in ["recomputed", "unchanged"]:
            expected_rows = copy.deepcopy(packet["rows"])
            if event["kind"] == "corrected_estimate":
                for row in expected_rows:
                    if row["id"] == event["row_ids"][0]:
                        row.update(event["replacement"])
            elif event["kind"] == "withdrawal":
                for row in expected_rows:
                    if row["id"] in event["row_ids"]:
                        row["active"] = False
            reference = oracle(expected_rows)
            correct &= all(
                abs(result["numeric_result"][key] - value) < 2e-6
                for key, value in reference.items()
            )
        if case["family"] == "independent_batch":
            correct &= [item["numeric_result"]["k"] for item in result["results"]] == [
                18,
                19,
            ]
            correct &= all(
                item["packet_digest"] == module.digest(packet)
                for item in result["results"]
            )
            correct &= all(
                item["commercial_acceptance"] is False
                and item["production_admission"] is False
                and item["cumulative_history"] is False
                for item in result["results"]
            )
        results.append(
            {
                "case": case,
                "result": result,
                "independent_numeric_reference": reference,
                "passed": bool(correct),
            }
        )
    regressions = []
    for old in json.loads(
        (ROOT / "results/confirmation-v1/events-and-results.json").read_text()
    ):
        name = old["dataset"]
        p = json.loads(
            (ROOT / f"results/confirmation-v1/{name}-packet.json").read_text()
        )
        m = json.loads(
            (ROOT / f"results/confirmation-v1/{name}-mission.json").read_text()
        )
        if old["mission_mutation"]:
            field = old["mission_mutation"]
            m[field] = {"new": "purpose"} if field == "purpose" else False
        result = module.process(p, m, old["event"])
        correct = result["status"] == old["expected_status"]
        correct &= (
            result["commercial_acceptance"] is False
            and result["production_admission"] is False
        )
        if result["numeric_result"]:
            correct &= all(
                abs(
                    result["numeric_result"][key] - old["result"]["numeric_result"][key]
                )
                < 2e-6
                for key in ["k", "estimate", "se", "tau2", "ci_lower", "ci_upper"]
            )
        else:
            correct &= old["result"]["numeric_result"] is None
        regressions.append(
            {
                "dataset": name,
                "event_id": old["event"]["id"],
                "expected_status": old["expected_status"],
                "actual_status": result["status"],
                "passed": bool(correct),
            }
        )
    verify_freeze()
    write(out / "fresh-results.json", results)
    write(out / "regressions.json", regressions)
    summary = {
        "schema": "prospective-snapshot-correction-results/v1.1",
        "executed_at_utc": now(),
        "frozen_at_utc": freeze["frozen_at_utc"],
        "generated_at_utc": generation["generated_at_utc"],
        "candidate_sha256": sha(ROOT / "instrument/continuity_v1_1.py"),
        "fresh_cases": len(results),
        "fresh_passed": sum(row["passed"] for row in results),
        "regression_cases": len(regressions),
        "regression_passed": sum(row["passed"] for row in regressions),
        "all_conformant": all(row["passed"] for row in results + regressions),
        "preserved_v1_bytes_unchanged": True,
        "fresh_recipient_transfer": False,
        "commercial_acceptance": False,
        "production_admission": False,
        "scope": "Bounded independent snapshot conformance; no cumulative ledger, source-event detection or real authentication",
        "interpretation": "Prospective correction after preserved v1 review; not retrospective recovery of profit or performance",
    }
    write(out / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["generate", "execute"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    generate(args.out) if args.stage == "generate" else execute(args.out)
