# SPDX-License-Identifier: Apache-2.0
"""Rejected portfolio and forced counterfactual lineage; no earned surplus."""

from __future__ import annotations

import hashlib
import json
import statistics
from typing import Any
from dataclasses import replace

from model import ROOT, Scenario, choose, needs, realize


def admission() -> dict[str, Any]:
    s = replace(Scenario(), common_build=0, retention=100)
    increments = []
    for seed in range(110, 122):
        bs = needs(seed, s)
        e = choose(bs, s, "expert_arranged")
        ep = choose(bs, s, "retained_arranged")
        increments.append(max(e["expected_profit"], ep["expected_profit"]) - e["expected_profit"])
    gain = statistics.mean(increments)
    # Six horizons were declared before fresh tests, not increased to force admission.
    construction = 2400
    additional_retention = 400
    transfer = 150
    benefit = 6 * gain
    return {
        "status": "admit" if benefit > construction + additional_retention + transfer else "reject",
        "development_seeds": [110, 121],
        "horizons": 6,
        "expected_increment_per_horizon": gain,
        "favorable_expected_six_horizon_increment": benefit,
        "construction_C": construction,
        "initial_retention_B": additional_retention,
        "fresh_recipient_transfer_B": transfer,
        "increments": increments,
        "reason": "Prospective finite-horizon expected benefit must exceed all additional costs; no future-demand oracle.",
        "limitation": "Assumed distributions and small development sample; not empirical market evidence. Benefit omits adverse opening-cash friction, so rejection is not repaired by adding it.",
    }


def confirm() -> None:
    manifest = json.loads((ROOT / "freeze.json").read_text())
    for name, digest in manifest["files"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("prospective freeze mismatch: " + name)
    decision = json.loads((ROOT / "admission.json").read_text())
    rows: list[dict[str, Any]] = []
    for path in range(20):
        e_cash, ep_cash = 6000.0, 6000.0 - 2800
        cumulative = -2800.0
        rows.append(
            {
                "path": path,
                "stage": 0,
                "incremental_net_value": cumulative,
                "baseline_cash": e_cash,
                "enhanced_cash": ep_cash,
                "status": "forced_counterfactual_not_policy_admission",
            }
        )
        for stage in range(1, 7):
            seed = 22000 + path * 6 + stage - 1
            if stage == 4:
                ep_cash -= 150
                cumulative -= 150
            bs = needs(seed, Scenario())
            s_e = replace(Scenario(), seed_cash=max(0, min(6000, e_cash)))
            s_ep = replace(Scenario(), common_build=0, retention=100, seed_cash=max(0, min(6000, ep_cash)))
            p_e = choose(bs, s_e, "expert_arranged")
            alternatives = [choose(bs, s_ep, arm) for arm in ("expert_arranged", "retained_arranged")]
            p_ep = max(alternatives, key=lambda p: (p["expected_profit"], -p["required_opening_cash"]))
            r_e = realize(p_e, bs, s_e, seed)
            r_ep = realize(p_ep, bs, s_ep, seed)
            e_cash += r_e["profit"]
            ep_cash += r_ep["profit"]
            cumulative += r_ep["profit"] - r_e["profit"]
            rows.append(
                {
                    "path": path,
                    "stage": stage,
                    "seed": seed,
                    "incremental_net_value": cumulative,
                    "baseline_cash": e_cash,
                    "enhanced_cash": ep_cash,
                    "baseline_profit": r_e["profit"],
                    "enhanced_profit": r_ep["profit"],
                    "baseline_accepted": r_e["accepted"],
                    "enhanced_accepted": r_ep["accepted"],
                    "enhanced_action": p_ep["arm"],
                    "same_content_library_increment": 0,
                    "status": "forced_counterfactual_not_policy_admission",
                }
            )
    summary = []
    for stage in range(7):
        vals = sorted(x["incremental_net_value"] for x in rows if x["stage"] == stage)
        summary.append(
            {
                "stage": stage,
                "mean": statistics.mean(vals),
                "median": statistics.median(vals),
                "scenario_p10": vals[2],
                "scenario_p90": vals[17],
                "nonnegative_paths": sum(v >= 0 for v in vals),
                "paths": len(vals),
            }
        )
    output = {
        "policy_decision": decision,
        "actual_policy_incremental_investment": 0,
        "actual_policy_incremental_gain": 0,
        "diagnostic_status": "Forced construction rejected prospectively; hypothetical realized paths are not admitted or recovered profit.",
        "fixed_resources": {"max_cash_per_horizon": 6000, "hours_per_horizon": 80},
        "rows": rows,
        "summary": summary,
    }
    (ROOT / "confirmation" / "lineage.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "admission": decision["status"],
                "paths": 20,
                "stages": 6,
                "diagnostic_final": summary[-1],
                "actual_revenue": 0,
            }
        )
    )


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["development"]:
        result = admission()
        (ROOT / "admission.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    elif sys.argv[1:] == ["confirmation"]:
        confirm()
    else:
        raise SystemExit("use development or confirmation")
