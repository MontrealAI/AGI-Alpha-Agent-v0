# SPDX-License-Identifier: Apache-2.0
"""Supplementary stricter-contract and hypothetical Beta-catch-up sensitivity."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import economics

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "expansion_frontier_protocol.json"
POLICIES = ("beta", "private", "shared", "shared_gym", "opportunity", "beta_open", "private_open", "library")
MARKETS = ("central", "thin_demand")
BETA_SETTINGS = ("executed_portfolio", "hypothetical_best_capability_catchup")
PAIRS = (("private", "beta"), ("shared", "beta"), ("shared_gym", "shared"),
         ("opportunity", "shared_gym"), ("opportunity", "beta_open"),
         ("opportunity", "private_open"), ("opportunity", "library"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def tier_calibration(raw: dict[str, Any], tier: float, catchup: bool = False) -> dict[str, Any]:
    """Apply one new contract to every method; never overwrite primary evidence."""
    result = copy.deepcopy(raw)
    for offering, modes in result["offerings"].items():
        original = raw["offerings"][offering]
        for split in ("development", "confirmation"):
            key = split + "_records"
            maps = {mode: {row["case_id"]: row for row in data[key]} for mode, data in original.items()}
            case_ids = set(maps["beta"])
            if any(set(rows) != case_ids or len(rows) != len(original[mode][key]) for mode, rows in maps.items()):
                raise ValueError("mode comparison requires identical unique cases")
            if catchup:
                for row in modes["beta"][key]:
                    options = [(entry["objective_ratio"], mode, entry) for mode, entries in maps.items()
                               if (entry := entries[row["case_id"]])["valid"]]
                    if options:
                        ratio, selected_mode, selected = min(options, key=lambda item: (item[0], item[1]))
                        row.update(objective_ratio=ratio, objective=selected["objective"], valid=True,
                                   hypothetical_beta=True, catchup_source_mode=selected_mode)
                    else:
                        row.update(valid=False, hypothetical_beta=True, catchup_source_mode=None)
            for mode, data in modes.items():
                for row in data[key]:
                    row["primary_accepted"] = row["accepted"]
                    row["accepted"] = bool(row["valid"] and row["objective_ratio"] <= 1.0 - tier)
                    row["supplemental_required_improvement"] = tier
                data[split + "_n"] = len(data[key])
                data[split + "_successes"] = sum(row["accepted"] for row in data[key])
    result["supplemental_contract"] = {"required_improvement_over_edd": tier, "catchup": catchup,
                                       "primary_evidence_changed": False}
    return result


def freeze(repetitions: int) -> dict[str, Any]:
    if PROTOCOL_PATH.exists():
        raise FileExistsError("supplemental protocol already frozen; do not silently replace it")
    grid_path = ROOT / "config" / "numerical_quality_frontier.json"
    numerical_path = ROOT / "evidence" / "numerical" / "economic_calibration.json"
    grid = json.loads(grid_path.read_text())
    inputs = [Path(__file__), Path(economics.__file__), ROOT / "config/economics.json",
              ROOT / "config/economic_protocol.json", grid_path, numerical_path]
    protocol = {
        "schema": "next-advantage-expansion-supplement/v1", "freeze_utc": datetime.now(timezone.utc).isoformat(),
        "registration_status": "Supplementary economic analysis declared after initial primary technical results. The quality grid itself was frozen before inspection of confirmation outcomes; this is not a prespecified primary economic test.",
        "grid": grid["grid_improvement_over_edd"], "policies": list(POLICIES), "markets": list(MARKETS),
        "beta_settings": list(BETA_SETTINGS), "repetitions": repetitions,
        "seeds": list(range(120000, 120000 + repetitions)),
        "matched_design": "Same seeds, initial resources, opportunity process, monetary configuration and frozen commercial controller within every comparison. All tiers reported; no favorable-tier selection.",
        "technical_contract": "Hard-constraint validity and objective_ratio <= 1-required_improvement. Same original scheduling objective and EDD reference; stricter or different quality contracts, not retroactive changes to primary acceptance.",
        "price_and_demand": "Original human-service references, price grid, buyer model, demand and cost assumptions retained. Buyers' willingness to pay for stricter quality is NOT independently calibrated; this is an explicit conditional sensitivity.",
        "catchup": "Hypothetical future no-retention Beta receives the per-case best valid objective among all six executed methods, separately in development and confirmation, at unchanged modeled serving cost. This optimistic oracle envelope is an assumed absorption of existing methods, not an observed model upgrade, a trained model, or a demonstrated equal-compute implementation. The decision policy sees development priors and past observations only; confirmation supplies realization after commitment.",
        "candidate_costs": "All original A/B/C costs, source-eight gate, campaign failures, retirement, invocation and maintenance charges remain unchanged. Skipped optional actions incur no optional charge.",
        "representative_records": "First seed, central market, opportunity and beta_open, every tier and both Beta settings; full ledgers retained without selecting favorable worlds.",
        "uncertainty": "Paired Monte Carlo intervals conditional on the fixed numerical case pool and assumptions, not confidence intervals for actual markets or for general frontier capability. Numerical cases are reused, not new empirical samples.",
        "inputs": {str(path.relative_to(ROOT)): sha(path) for path in inputs},
        "expected_histories": len(grid["grid_improvement_over_edd"]) * len(POLICIES) * len(MARKETS) * len(BETA_SETTINGS) * repetitions,
    }
    write(PROTOCOL_PATH, protocol)
    return protocol


def check_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text())
    for path, expected in protocol["inputs"].items():
        if sha(ROOT / path) != expected:
            raise ValueError("supplemental frozen source/input changed: " + path)
    return protocol


def paired(rows: list[dict[str, Any]], controls: list[dict[str, Any]]) -> dict[str, Any]:
    if [row["seed"] for row in rows] != [row["seed"] for row in controls]:
        raise ValueError("counterfactual seeds are not matched")
    delta = np.array([row["profit_usd"] - control["profit_usd"] for row, control in zip(rows, controls)])
    se = float(delta.std(ddof=1) / np.sqrt(len(delta)))
    mean = float(delta.mean())
    return {"n": len(delta), "mean_profit_difference_usd": mean,
            "paired_mc_95": [mean - 1.96 * se, mean + 1.96 * se],
            "probability_outperforming": float(np.mean(delta > 0)),
            "q05_difference_usd": float(np.quantile(delta, 0.05)),
            "q95_difference_usd": float(np.quantile(delta, 0.95))}


def run(output: Path) -> dict[str, Any]:
    protocol = check_protocol()
    raw = json.loads((ROOT / "evidence/numerical/economic_calibration.json").read_text())
    cfg = json.loads((ROOT / "config/economics.json").read_text())
    policies = {policy.name: policy for policy in economics.POLICIES}
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "expansion_frontier.json"
    raw_path = output / "expansion_frontier_runs.jsonl"
    if result_path.exists() or raw_path.exists():
        raise FileExistsError("choose a new output directory; original supplemental evidence must be preserved")
    summaries, comparisons, calibrations, catchup_comparisons = [], [], [], []
    aggregate_checks = 0
    counts = 0
    matched_cache: dict[tuple[float, str, str, str], list[dict[str, Any]]] = {}
    with raw_path.open("w") as stream:
        for tier in protocol["grid"]:
            for beta_setting in protocol["beta_settings"]:
                altered = tier_calibration(raw, tier, beta_setting != "executed_portfolio")
                cal = economics.normalize_calibration(altered)
                for offering, modes in altered["offerings"].items():
                    for mode, data in modes.items():
                        calibrations.append({"tier": tier, "beta_setting": beta_setting, "offering": offering,
                                             "mode": mode, "development_successes": data["development_successes"],
                                             "development_n": data["development_n"],
                                             "confirmation_successes": data["confirmation_successes"],
                                             "confirmation_n": data["confirmation_n"]})
                for market in protocol["markets"]:
                    matched = {}
                    for name in protocol["policies"]:
                        rows = []
                        for seed in protocol["seeds"]:
                            record = seed == protocol["seeds"][0] and market == "central" and name in {"opportunity", "beta_open"}
                            row = economics.simulate(policies[name], economics.SCENARIOS[market], seed, cal, cfg, record=record)
                            if abs(row["ending_cash_usd"] - (row["capital_usd"] + row["collections_usd"] - row["expenses_usd"])) > 1e-6:
                                raise AssertionError("supplemental cash reconstruction failed")
                            if abs(row["earned_usd"] - row["collections_usd"] - row["receivables_usd"]) > 1e-6:
                                raise AssertionError("supplemental receivable reconstruction failed")
                            if abs(sum(row["buckets"].values()) - row["expenses_usd"]) > 1e-6:
                                raise AssertionError("supplemental disjoint cost reconstruction failed")
                            aggregate_checks += 3
                            context = {"tier": tier, "market": market, "beta_setting": beta_setting}
                            if record:
                                tag = str(tier).replace(".", "p")
                                write(output / "expansion_representatives" / f"tier-{tag}-{beta_setting}-{name}.json",
                                      {**context, **row})
                            compact = {k: v for k, v in row.items() if k not in {"events"}}
                            compact["actions"] = [action for action in compact["actions"] if action["action"] != "production"]
                            stream.write(json.dumps({**context, **compact}, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                            rows.append(compact)
                            counts += 1
                        matched[name] = rows
                        matched_cache[tier, beta_setting, market, name] = rows
                        summaries.append({"tier": tier, "beta_setting": beta_setting, "market": market,
                                          "policy": name, "n": len(rows), **economics.summarize(rows)})
                    for intervention, control in PAIRS:
                        comparisons.append({"tier": tier, "beta_setting": beta_setting, "market": market,
                                            "intervention": intervention, "control": control,
                                            **paired(matched[intervention], matched[control])})
                    for a, b in zip(matched["opportunity"], matched["library"]):
                        if any(a[key] != b[key] for key in ("profit_usd", "cash_profit_usd", "collections_usd", "buckets", "accepted", "stats")):
                            raise AssertionError("ordinary library contents/permissions comparison unexpectedly differs")
                        aggregate_checks += 1
                    print(json.dumps({"tier": tier, "beta": beta_setting, "market": market, "histories_complete": counts}), flush=True)
    for tier in protocol["grid"]:
        for market in protocol["markets"]:
            base_key = (tier, "executed_portfolio", market)
            upgraded_key = (tier, "hypothetical_best_capability_catchup", market)
            original = [a["profit_usd"] - b["profit_usd"] for a, b in zip(matched_cache[*base_key, "opportunity"], matched_cache[*base_key, "beta_open"])]
            upgraded = [a["profit_usd"] - b["profit_usd"] for a, b in zip(matched_cache[*upgraded_key, "opportunity"], matched_cache[*upgraded_key, "beta_open"])]
            delta = np.array(upgraded) - np.array(original)
            mean = float(delta.mean())
            se = float(delta.std(ddof=1) / np.sqrt(len(delta)))
            catchup_comparisons.append({"tier": tier, "market": market, "original_retention_increment_mean_usd": float(np.mean(original)),
                                       "catchup_retention_increment_mean_usd": float(np.mean(upgraded)),
                                       "change_in_increment_mean_usd": mean, "paired_mc_95": [mean - 1.96 * se, mean + 1.96 * se]})
    if counts != protocol["expected_histories"]:
        raise AssertionError("supplemental history count does not match frozen design")
    check_protocol()
    result = {"schema": "next-advantage-expansion-frontier/v1", "protocol": protocol,
              "protocol_sha256": sha(PROTOCOL_PATH), "histories": counts, "aggregate_checks": aggregate_checks,
              "raw_runs_sha256": sha(raw_path), "calibration_counts": calibrations,
              "summaries": summaries, "paired_comparisons": comparisons, "catchup_comparisons": catchup_comparisons,
              "status": "SUPPLEMENTARY_CONDITIONAL_SIMULATION", "primary_acceptance_unchanged": True,
              "real_customer_sales": 0, "actual_frontier_model_trials": 0}
    write(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--repetitions", type=int, default=64)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence")
    args = parser.parse_args()
    if args.freeze:
        protocol = freeze(args.repetitions)
        print(json.dumps({"frozen": str(PROTOCOL_PATH), "histories": protocol["expected_histories"]}))
    else:
        result = run(args.output)
        print(json.dumps({"status": "PASS", "histories": result["histories"], "checks": result["aggregate_checks"]}))


if __name__ == "__main__":
    main()
