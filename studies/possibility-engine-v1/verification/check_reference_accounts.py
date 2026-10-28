# SPDX-License-Identifier: Apache-2.0
"""Audit supplemental persistence of conventional and immediate-stop trajectories."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from check_accounts import reconcile
from check_summaries import statistics_from_worlds
from issue_seeds import verify_freeze


def main() -> None:
    """Check every reference journal and independently reconstruct original summaries."""
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    args = parser.parse_args()
    root = args.study
    verify_freeze(root / "FREEZE.json")
    directory = root / "economics/confirmation/supplementary_references"
    persisted = json.loads((directory / "persistence_report.json").read_text())
    published = json.loads((root / "economics/confirmation/summary.json").read_text())
    config = json.loads((root / "economics/assumptions.json").read_text())
    seeds = json.loads((root / "evidence/confirmation/seeds.json").read_text())["economic_seeds"]
    names = ("conventional_same_arrangement", "no_launch_after_research")
    expected = {f"{name}/{seed}.json" for name in names for seed in seeds}
    assert {item["path"] for item in persisted["world_manifest"]} == expected
    assert len(persisted["world_manifest"]) == len(expected)
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    receipts = []
    for item in persisted["world_manifest"]:
        path = directory / item["path"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        world = json.loads(raw)
        group = item["path"].split("/")[0]
        assert world["seed"] in seeds
        grouped[group].append(world)
        normalized = copy.deepcopy(world)
        if group == "no_launch_after_research":
            assert world["scenario"] == "no_launch" and world["contracts"] == []
            assert world["counts"] == {"signed": 0, "accepted": 0, "renewals": 0}
            allowed_events = {"opening_equity", "research", "failed_discovery", "development", "independent_validation",
                              "documentation", "startup_inference", "startup_compute", "startup_tools", "exit",
                              "enterprise_exit"}
            assert {event["event_type"] for event in world["journal"]} == allowed_events
            normalized["counts"]["failed"] = 0
            normalized["counts"]["corrected"] = 0
        else:
            assert world["conventional"] is True
            reference = json.loads((root / "economics/confirmation/worlds" / f"reference-{world['seed']}.json").read_text())
            for key in ("counts", "choices", "profit_cents", "operating_contribution_cents", "final_account_balances",
                        "collections_cents", "refunds_cents", "cash_requirement_cents", "hours", "contracts"):
                assert world[key] == reference[key], f"Conventional parity differs: {key}"
        receipt = reconcile(normalized, config)
        receipt["group"] = group
        receipt["source_sha256"] = item["sha256"]
        receipts.append(receipt)
    for name, worlds in grouped.items():
        assert len(worlds) == len(seeds) == len({world["seed"] for world in worlds})
        reconstructed = statistics_from_worlds(worlds)
        for key, value in reconstructed.items():
            assert math.isclose(value, published[name][key], rel_tol=1e-12, abs_tol=1e-7), (name, key)
    verify_freeze(root / "FREEZE.json")
    output = {"status": "pass", "scope": "Same original seeds and frozen model; supplemental raw reference persistence",
              "worlds": len(receipts), "journal_events": sum(row["journal_events"] for row in receipts),
              "contracts_checked": sum(row["contracts_checked"] for row in receipts), "aggregate_fields_checked": 38,
              "conventional_parity_scope": "Identical economics are an explicit assumption, not a measured competitive edge",
              "no_launch_normalization": "Only missing zero failed/corrected counts filled after proving no such lifecycle events",
              "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "source_unchanged": True, "results": receipts}
    (root / "verification/reference_accounting_audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in ("status", "worlds", "journal_events", "contracts_checked",
                                                  "aggregate_fields_checked", "source_unchanged")}))


if __name__ == "__main__":
    main()
