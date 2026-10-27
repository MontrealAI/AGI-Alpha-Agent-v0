# SPDX-License-Identifier: Apache-2.0
"""Construct fresh policy diagnostics after the separate selector source freeze."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "policy_cases"


def plan(name: str, price: int = 100, a: int = 60, b: int = 0, c: int = 0) -> dict[str, Any]:
    total = a + b + c
    return {
        "id": name,
        "proposer": "constructed-proposer",
        "configuration": "E+" if b or c else "E",
        "production_plan": "fictional audit; no real customer",
        "retention_choice": "retain" if b else "decline",
        "development_choice": "develop" if c else "decline",
        "price_usd": price,
        "deposit_fraction": 0,
        "independent_evidence": {
            k: {
                "passed": True,
                "independent": True,
                "attestor": "fixture-evaluator",
                "reference": "assumed-diagnostic-only",
                "scope": "constructed fixed acceptance; not actual customer proof",
            }
            for k in ("readiness", "acceptance")
        },
        "scenarios": [
            {
                "world_id": world,
                "costs_complete": True,
                "cash_path_complete": True,
                "earned_revenue_usd": price if world == "success" else 0,
                "costs": {
                    key: {"monetary_expense_usd": value, "opportunity_cost_usd": 0}
                    for key, value in (("A", a), ("B", b), ("C", c))
                },
                "cash_path": [
                    {
                        "label": "opening",
                        "cash_balance_usd": 120,
                        "restricted_for_obligations_usd": 0,
                        "operating_reserve_usd": 10,
                    },
                    {
                        "label": "complete payment before collection",
                        "cash_balance_usd": 120 - total,
                        "restricted_for_obligations_usd": 0,
                        "operating_reserve_usd": 10,
                    },
                    {
                        "label": "closing",
                        "cash_balance_usd": 120 - total + (price if world == "success" else 0),
                        "restricted_for_obligations_usd": 0,
                        "operating_reserve_usd": 10,
                    },
                ],
            }
            for world in ("success", "failure")
        ],
    }


def packet(name: str, alternatives: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "agialpha.feasible-policy-input.v1",
        "information_set_id": name,
        "world_weights_evidence": "assumed diagnostic weights; no market calibration",
        "opening_cash_usd": 120,
        "worlds": [{"id": "success", "probability": 0.8}, {"id": "failure", "probability": 0.2}],
        "alternatives": alternatives,
    }


def main() -> None:
    freeze = json.loads((ROOT / "economics/FEASIBLE_POLICY_FREEZE.json").read_text())
    source_hash = hashlib.sha256((ROOT / "economics/feasible_policy.py").read_bytes()).hexdigest()
    if source_hash != "5a5bfb3ddd4ab6ea341e214b9cfc8177812e4e53534fc9d2cbeeb7c512ec0c28":
        raise ValueError("unexpected policy source")
    OUT.mkdir(exist_ok=False)
    good = plan("funded-service")  # 0.8*100 - 60 = 20.
    illiquid = plan("higher-contribution-unfunded", 250, 130)  # 70, but cash prefix -10.
    unknown = plan("unknown-cost")
    unknown["scenarios"][0]["costs"]["B"]["monetary_expense_usd"] = None
    self_attested = plan("self-attested")
    self_attested["independent_evidence"]["readiness"]["attestor"] = "constructed-proposer"
    incomplete = plan("incomplete-costs")
    incomplete["scenarios"][0]["costs_complete"] = False
    cash_unknown = plan("incomplete-cash-path")
    cash_unknown["scenarios"][0]["cash_path_complete"] = False
    no_acceptance = plan("no-acceptance")
    no_acceptance["independent_evidence"]["acceptance"]["passed"] = False
    restricted = plan("restricted-money")
    restricted["scenarios"][0]["cash_path"][1]["restricted_for_obligations_usd"] = 55
    retained = plan("worthwhile-retention", 150, 70, 5, 5)  # 120-80=40; funded.
    costly = plan("unprofitable-retention", 100, 60, 25, 20)  # 80-105=-25.
    no_demand = plan("unknown-readiness", 250, 60)
    no_demand["independent_evidence"]["readiness"]["passed"] = None
    improved_baseline = plan("improved-conventional", 150, 45)  # 120-45=75.
    zero_stress = packet("six-zero-weight-stress", [copy.deepcopy(good)])
    zero_stress["worlds"].append({"id": "stress", "probability": 0})
    stress = copy.deepcopy(good["scenarios"][1])
    stress["world_id"] = "stress"
    stress["cash_path"][1]["cash_balance_usd"] = 5
    zero_stress["alternatives"][0]["scenarios"].append(stress)
    cases = [
        (
            "01-funding-and-evidence",
            packet(
                "one-fixed-resources",
                [good, illiquid, unknown, self_attested, incomplete, cash_unknown, no_acceptance, restricted, costly],
            ),
            "funded-service",
            ["funded-service"],
        ),
        (
            "02-retention-can-qualify",
            packet("two-fixed-resources", [good, retained, costly, illiquid]),
            "worthwhile-retention",
            ["worthwhile-retention", "funded-service"],
        ),
        ("03-negative-contribution-stop", packet("three-fixed-resources", [plan("loss", 20, 60), costly]), None, []),
        ("04-unknown-demand-stop", packet("four-fixed-resources", [no_demand]), None, []),
        (
            "05-baseline-progress",
            packet("five-fixed-resources", [good, retained, improved_baseline]),
            "improved-conventional",
            ["improved-conventional", "worthwhile-retention", "funded-service"],
        ),
        ("06-zero-weight-stress", zero_stress, None, []),
    ]
    expected = []
    hashes = {}
    for name, data, selected, ranking in cases:
        file = OUT / f"{name}.json"
        file.write_text(json.dumps(data, indent=2) + "\n")
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
        expected.append({"file": file.name, "selected_id": selected, "eligible_ranking": ranking})
    expected_file = OUT / "EXPECTED.json"
    expected_file.write_text(json.dumps(expected, indent=2) + "\n")
    hashes[expected_file.name] = hashlib.sha256(expected_file.read_bytes()).hexdigest()
    (OUT / "FREEZE.json").write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(UTC).isoformat(),
                "policy_source_sha256": source_hash,
                "policy_freeze_record": freeze,
                "files_sha256": hashes,
                "observed_real_customer_evidence": False,
                "purpose": "prospective constructed decision diagnostics after policy freeze; no retrospective profit",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"fixtures": len(cases), "policy_sha256": source_hash}))


if __name__ == "__main__":
    main()
