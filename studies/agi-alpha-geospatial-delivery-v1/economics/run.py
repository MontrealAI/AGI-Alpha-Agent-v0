# SPDX-License-Identifier: Apache-2.0
"""Frozen, paired commercial scenarios for the complete geospatial service."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def human_reference(config: dict[str, Any], hours: float | None = None) -> list[dict[str, float | str]]:
    h = config["human"]
    rows = []
    for i, label in enumerate(["low", "central", "high"]):
        wage = h["gis_share"] * h["gis_wage"][i] + (1 - h["gis_share"]) * h["writer_wage"][i]
        effort = float(hours if hours is not None else h["hours"][i])
        production = effort * wage * h["composite_load"][i] + h["tools"][i]
        rows.append(
            {
                "scenario": label,
                "hours": effort,
                "weighted_wage": wage,
                "production_cost": production,
                "service_reference": production / (1 - h["service_margin"][i]),
            }
        )
    return rows


def cost_reference(config: dict[str, Any]) -> dict[str, Any]:
    inference = config["inference"]
    rows = []
    for component in inference["components"]:
        usd = (
            component["input_tokens"] * component["input_usd_per_million"]
            + component["output_tokens"] * component["output_usd_per_million"]
        ) / 1e6
        rows.append({"stage": component["stage"], "usd": usd, "cad": usd * inference["fx_cad_per_usd"]})
    a = config["A"]
    first = sum(row["cad"] for row in rows) + sum(
        a[k]
        for k in ["tools_compute", "source_access", "packaging_storage", "automated_support", "operational_recovery"]
    )
    return {
        "inference_components": rows,
        "inference_total_cad": sum(row["cad"] for row in rows),
        "first_attempt_delivery": first,
        "expected_retry": a["first_retry_probability"] * a["retry_cost"],
        "expected_warranty": a["latent_defect_probability"] * a["warranty_cost"],
        "expected_delivery_before_payment_fees": first
        + a["first_retry_probability"] * a["retry_cost"]
        + a["latent_defect_probability"] * a["warranty_cost"],
    }


def worlds(config: dict[str, Any], count: int, seed: int, uncertain: bool = False) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    m = config["market"]
    shape = (count, m["months"], 96)
    draws = {name: rng.random(shape) for name in ["success", "default", "retry", "defect", "inhouse"]}
    for name, key in [
        ("value", "value_reference_multipliers"),
        ("owncost", "inhouse_cost_reference_multipliers"),
        ("budget", "budget_reference_multipliers"),
        ("friction", "buyer_integration_cost"),
    ]:
        lo, mode, hi = m[key]
        draws[name] = rng.triangular(lo, mode, hi, shape)
    draws["outage"] = rng.random((count, m["months"]))
    if uncertain:
        draws["quality"] = rng.triangular(0.72, m["quality"], 0.99, count)
        draws["perceived"] = rng.triangular(0.70, m["perceived_quality"], 0.98, count)
        draws["leads"] = np.rint(rng.triangular(4, m["qualified_invitations_per_month"], 48, count)).astype(int)
        draws["cost_scale"] = rng.triangular(0.65, 1.0, 2.5, count)
        draws["cac_scale"] = rng.triangular(0.6, 1.0, 2.5, count)
        draws["overhead_scale"] = rng.triangular(0.7, 1.0, 2.0, count)
    else:
        draws["quality"] = np.full(count, m["quality"])
        draws["perceived"] = np.full(count, m["perceived_quality"])
        draws["leads"] = np.full(count, m["qualified_invitations_per_month"], dtype=int)
        for k in ["cost_scale", "cac_scale", "overhead_scale"]:
            draws[k] = np.ones(count)
    return draws


def simulate(
    config: dict[str, Any],
    policy: dict[str, Any],
    draws: dict[str, np.ndarray],
    reference_override: float | None = None,
) -> dict[str, np.ndarray]:
    m, a = config["market"], config["A"]
    n = len(draws["quality"])
    href = float(human_reference(config)[1]["service_reference"] if reference_override is None else reference_override)
    price = href * policy["price_ratio"]
    deposit_fraction = m["deposit_fraction"] if policy["arrangement"] == "conditional_deposit" else 0
    first = cost_reference(config)["first_attempt_delivery"]
    cash: np.ndarray[Any, Any] = np.full(n, m["opening_financing"] - a["launch_configuration"], dtype=float)
    minimum_cash = cash.copy()
    pending = np.zeros(n)
    active: np.ndarray[Any, Any] = np.ones(n, dtype=bool)
    keys = [
        "attempts",
        "accepted",
        "unserved_buyers",
        "participating_buyers",
        "invitations",
        "revenue",
        "collections",
        "bad_debt",
        "delivery_cost",
        "acquisition_cost",
        "fixed_cost",
        "payment_cost",
        "refunded_deposits",
        "deposit_receipts",
        "customer_savings",
        "stopped",
        "common_outage_months",
    ]
    out = {k: np.zeros(n) for k in keys}
    out["launch_cost"] = np.full(n, a["launch_configuration"])
    for month in range(m["months"]):
        cash += pending
        out["collections"] += pending
        pending = np.zeros(n)
        fixed = a["monthly_business_overhead"] * draws["overhead_scale"]
        acquire = draws["leads"] * a["cost_per_qualified_invitation"] * draws["cac_scale"]
        affordable = cash >= fixed + acquire
        out["stopped"] = np.maximum(out["stopped"], active & ~affordable)
        active &= affordable
        out["fixed_cost"] += fixed * active
        out["acquisition_cost"] += acquire * active
        out["invitations"] += draws["leads"] * active
        cash -= (fixed + acquire) * active
        value_anchor = float(human_reference(config)[1]["service_reference"])
        value = value_anchor * draws["value"][:, month, :]
        friction = draws["friction"][:, month, :]
        perceived = draws["perceived"][:, None]
        ai = perceived * (value - price) - friction - (1 - perceived) * m["failure_delay_cost"]
        if deposit_fraction:
            ai -= m["deposit_friction"]
        human = m["human_quality"] * (value - href) - friction - (1 - m["human_quality"]) * m["failure_delay_cost"]
        own = m["conventional_quality"] * value - href * draws["owncost"][:, month, :]
        own -= (1 - m["conventional_quality"]) * m["failure_delay_cost"]
        own = np.where(draws["inhouse"][:, month, :] < m["inhouse_fraction"], own, -np.inf)
        outside = np.maximum(0, np.maximum(human, own))
        invited = np.arange(96)[None, :] < draws["leads"][:, None]
        buys = (ai > outside) & (value_anchor * draws["budget"][:, month, :] >= price) & invited & active[:, None]
        willing = buys.sum(axis=1)
        out["participating_buyers"] += willing
        bounded_cost = draws["cost_scale"] * (first + a["retry_cost"] + a["warranty_cost"])
        bounded_cost += a["payment_fraction"] * price + 2 * a["payment_fixed"]
        funds_capacity = np.floor(np.maximum(0, cash) / bounded_cost).astype(int)
        capacity = np.minimum(m["capacity_attempts_per_month"], funds_capacity)
        selected = buys & (np.cumsum(buys, axis=1) <= capacity[:, None])
        count = selected.sum(axis=1)
        out["attempts"] += count
        out["unserved_buyers"] += willing - count
        outage = draws["outage"][:, month] < m["common_outage_probability"]
        out["common_outage_months"] += outage * active
        success = selected & (draws["success"][:, month, :] < draws["quality"][:, None]) & ~outage[:, None]
        accepted = success.sum(axis=1)
        defaults = success & (draws["default"][:, month, :] < m["nonpayment_probability"])
        default_count = defaults.sum(axis=1)
        retries = (selected & (draws["retry"][:, month, :] < a["first_retry_probability"])).sum(axis=1)
        defects = (success & (draws["defect"][:, month, :] < a["latent_defect_probability"])).sum(axis=1)
        expense = draws["cost_scale"] * (count * first + retries * a["retry_cost"] + defects * a["warranty_cost"])
        deposit = price * deposit_fraction
        out["deposit_receipts"] += count * deposit
        out["refunded_deposits"] += (count - accepted) * deposit
        residual = price - deposit
        settlement = (accepted - default_count) * residual
        deposit_earned = accepted * deposit
        fees = a["payment_fraction"] * (count * deposit + settlement)
        fees += a["payment_fixed"] * ((count if deposit else 0) + accepted - default_count)
        minimum_cash = np.minimum(minimum_cash, cash - expense - fees)
        cash += deposit_earned - expense - fees
        pending = settlement
        out["accepted"] += accepted
        out["revenue"] += price * accepted
        out["collections"] += deposit_earned
        out["bad_debt"] += default_count * residual
        out["delivery_cost"] += expense
        out["payment_cost"] += fees
        out["customer_savings"] += accepted * (href - price)
    cash += pending
    out["collections"] += pending
    out["A_total"] = np.sum(
        [out[k] for k in ["delivery_cost", "acquisition_cost", "fixed_cost", "payment_cost", "launch_cost"]], axis=0
    )
    out["operating_profit"] = out["revenue"] - out["bad_debt"] - out["A_total"]
    out["after_assessment"] = out["operating_profit"] - config["B"]["assessment"]
    out["after_optional_gym"] = out["after_assessment"] - config["C"]["optional_gym"]
    out["closing_cash_before_B_C"] = cash
    out["minimum_cash"] = minimum_cash
    out["ending_customer_obligations"] = np.zeros(n)
    out["ending_receivables_after_runoff"] = np.zeros(n)
    out["reserve"] = m["reserve_months"] * (
        a["monthly_business_overhead"] * draws["overhead_scale"]
        + draws["leads"] * a["cost_per_qualified_invitation"] * draws["cac_scale"]
        + m["capacity_attempts_per_month"]
        * cost_reference(config)["expected_delivery_before_payment_fees"]
        * draws["cost_scale"]
    )
    out["growth_funds_after_assessment"] = np.maximum(
        0, cash - m["opening_financing"] - config["B"]["assessment"] - out["reserve"]
    )
    out["complete_cost_per_accepted"] = np.divide(
        out["A_total"] + out["bad_debt"], out["accepted"], out=np.full(n, np.nan), where=out["accepted"] > 0
    )
    out["price"] = np.full(n, price)
    out["human_reference"] = np.full(n, href)
    if not np.allclose(cash - m["opening_financing"], out["operating_profit"], rtol=1e-10, atol=1e-7):
        raise AssertionError("Cash and earned profit reconciliation failed")
    if np.any(out["collections"] > out["revenue"] + 1e-7):
        raise AssertionError("Collections exceed earned service revenue after all refunds")
    if np.any(out["attempts"] > m["months"] * m["capacity_attempts_per_month"]):
        raise AssertionError("Capacity exceeded")
    if np.any(minimum_cash < -1e-7):
        raise AssertionError("Unfunded operation")
    return out


def summary(out: dict[str, np.ndarray]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, values in out.items():
        finite = values[np.isfinite(values)]
        result[name] = {
            "mean": float(finite.mean()) if len(finite) else None,
            "p05": float(np.quantile(finite, 0.05)) if len(finite) else None,
            "p50": float(np.quantile(finite, 0.5)) if len(finite) else None,
            "p95": float(np.quantile(finite, 0.95)) if len(finite) else None,
            "undefined_worlds": int(len(values) - len(finite)),
        }
    if "operating_profit" in out:
        result["positive_profit_fraction"] = float(np.mean(out["operating_profit"] > 0))
    return result


def select(config: dict[str, Any], output: Path) -> dict[str, Any]:
    c = config["confirmation"]
    draws = worlds(config, c["selection_worlds"], c["selection_seed"])
    results = []
    for arrangement in config["policy_family"]["arrangements"]:
        for ratio in config["policy_family"]["price_ratios"]:
            policy = {"price_ratio": ratio, "arrangement": arrangement}
            result = summary(simulate(config, policy, draws))
            results.append({"policy": policy, "result": result})
    best = max(results, key=lambda r: r["result"]["operating_profit"]["mean"])
    freeze = {
        "config_sha256": hashlib.sha256(canonical(config)).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "selection_seed": c["selection_seed"],
        "selection_worlds": c["selection_worlds"],
        "selected_policy": best["policy"],
        "criterion": "highest mean 12-month operating profit in tested family",
        "fresh_seed": c["fresh_seed"],
        "fresh_worlds": c["fresh_worlds"],
        "statement": "Policy selected before confirmation execution; no real buyer optimization or global optimum claim.",
    }
    save(output / "exploratory_policy_results.json", results)
    save(output / "policy_freeze.json", freeze)
    return freeze


def confirm(config: dict[str, Any], output: Path) -> None:
    freeze = json.loads((output / "policy_freeze.json").read_text())
    if freeze["config_sha256"] != hashlib.sha256(canonical(config)).hexdigest():
        raise ValueError("Commercial inputs changed after freeze")
    if freeze["runner_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("Simulator changed after freeze; create a new prospective edition")
    c = config["confirmation"]
    policy = freeze["selected_policy"]
    fresh = worlds(config, c["fresh_worlds"], c["fresh_seed"])
    out = simulate(config, policy, fresh)
    save(
        output / "confirmation.json",
        {
            "freeze": freeze,
            "summary": summary(out),
            "human_reference": human_reference(config),
            "delivery_cost_reference": cost_reference(config),
            "actual_collected_service_revenue": 0,
            "actual_complete_study_cost": None,
        },
    )
    save(
        output / "annual_worlds.json",
        {k: [float(v) if math.isfinite(v) else None for v in vals] for k, vals in out.items()},
    )
    pdraw = worlds(config, c["parameter_worlds"], c["parameter_seed"], uncertain=True)
    save(
        output / "parameter_uncertainty.json",
        {
            "summary": summary(simulate(config, policy, pdraw)),
            "interpretation": "Distribution under explicit triangular priors, not calibrated real-world frequencies.",
            "parameters": {
                k: summary({k: pdraw[k]})[k]
                for k in ["quality", "perceived", "leads", "cost_scale", "cac_scale", "overhead_scale"]
            },
        },
    )
    comparison = []
    for arrangement in config["policy_family"]["arrangements"]:
        for ratio in config["policy_family"]["price_ratios"]:
            other_policy = {"price_ratio": ratio, "arrangement": arrangement}
            comparison.append(
                {
                    "policy": other_policy,
                    "fresh_conditional": summary(simulate(config, other_policy, fresh)),
                    "uncertain_parameters": summary(simulate(config, other_policy, pdraw)),
                }
            )
    save(
        output / "policy_robustness.json",
        {
            "selected_policy_unchanged": policy,
            "comparisons": comparison,
            "interpretation": "Prospective diagnostics; no confirmation-based reselection.",
        },
    )
    stresses: list[dict[str, Any]] = []
    specs = [
        ("central", {}),
        ("low_demand_4", {"qualified_invitations_per_month": 4}),
        ("low_demand_8", {"qualified_invitations_per_month": 8}),
        ("quality_075", {"quality": 0.75, "perceived_quality": 0.75}),
        ("quality_060", {"quality": 0.60, "perceived_quality": 0.60}),
        ("weak_trust_075", {"perceived_quality": 0.75}),
        ("half_capacity", {"capacity_attempts_per_month": 4}),
        ("strong_inhouse_competition", {"inhouse_fraction": 0.80}),
        ("common_failures_020", {"common_outage_probability": 0.20}),
        ("buyer_values_halved", {"value_reference_multipliers": [0.35, 1.05, 2.25]}),
    ]
    for name, overrides in specs:
        altered = copy.deepcopy(config)
        altered["market"].update(overrides)
        ds = worlds(altered, c["sensitivity_worlds"], c["sensitivity_seed"])
        stresses.append({"name": name, "result": summary(simulate(altered, policy, ds))})
    warranty = copy.deepcopy(config)
    warranty["A"]["latent_defect_probability"] = 0.20
    warranty["A"]["warranty_cost"] = 500
    ds = worlds(warranty, c["sensitivity_worlds"], c["sensitivity_seed"])
    stresses.append({"name": "warranty_20pct_at_500", "result": summary(simulate(warranty, policy, ds))})
    for hours in [4, 8, 12, 24, 32]:
        ref = float(human_reference(config, hours)[1]["service_reference"])
        ds = worlds(config, c["sensitivity_worlds"], c["sensitivity_seed"])
        stresses.append(
            {
                "name": f"matched_human_hours_{hours}",
                "human_reference": ref,
                "result": summary(simulate(config, policy, ds, ref)),
            }
        )
    for name, path, multiplier in [
        ("all_delivery_costs_3x", "delivery", 3),
        ("all_delivery_costs_10x", "delivery", 10),
        ("acquisition_costs_3x", "acquisition", 3),
        ("overhead_3x", "overhead", 3),
    ]:
        ds = worlds(config, c["sensitivity_worlds"], c["sensitivity_seed"])
        ds[{"delivery": "cost_scale", "acquisition": "cac_scale", "overhead": "overhead_scale"}[path]] *= multiplier
        stresses.append({"name": name, "result": summary(simulate(config, policy, ds))})
    for inference_multiplier in [0.5, 2.0, 10.0]:
        alt = copy.deepcopy(config)
        for component in alt["inference"]["components"]:
            component["input_usd_per_million"] *= inference_multiplier
            component["output_usd_per_million"] *= inference_multiplier
        ds = worlds(alt, c["sensitivity_worlds"], c["sensitivity_seed"])
        stresses.append({"name": f"model_price_{inference_multiplier}x", "result": summary(simulate(alt, policy, ds))})
    save(output / "sensitivity.json", stresses)
    pairs = []
    dso = worlds(config, c["sensitivity_worlds"], c["operational_seed"])
    baseline = simulate(config, policy, dso)
    for label, dq, costfactor in [
        ("no_operational_advantage", 0, 1),
        ("ordinary_use_4pp_lower", -0.04, 1.20),
        ("ordinary_use_4pp_higher", 0.04, 0.80),
    ]:
        ds = {k: v.copy() for k, v in dso.items()}
        ds["quality"] = np.clip(ds["quality"] + dq, 0, 1)
        ds["cost_scale"] *= costfactor
        ordinary = simulate(config, policy, ds)
        delta = baseline["operating_profit"] - ordinary["operating_profit"]
        pairs.append(
            {
                "scenario": label,
                "E_minus_U_profit": summary({"difference": delta})["difference"],
                "attribution": "assumed counterfactual quality/cost effect; no measured U/E trial",
            }
        )
    b = config["B"]
    uses = out["attempts"]
    setup = b["extraction_and_compatibility"] + b["sharing"]
    fixed = setup + config["market"]["months"] * b["monthly_maintenance"]
    retention = []
    for saving in b["saving_per_use_candidates"]:
        delta = uses * (saving - b["invocation_per_use"]) - fixed
        retention.append(
            {
                "assumed_saving_per_use": saving,
                "incremental_profit_excluding_sunk_assessment": summary({"delta": delta})["delta"],
                "break_even_uses": math.ceil(fixed / (saving - b["invocation_per_use"]))
                if saving > b["invocation_per_use"]
                else None,
            }
        )
    save(
        output / "alpha_separation.json",
        {
            "operational_alpha_scenarios": pairs,
            "retention_scenarios": retention,
            "decision": "HOLD optional network retention investment: no measured marginal saving; origin code remains reusable.",
            "assessment_cost_charged": b["assessment"],
            "gym_decision": "Optional; no automatic allocation.",
            "technical_control": "Identical-information ordinary library can reproduce instrument; provenance is not exclusive economic advantage.",
        },
    )
    perjob = (
        cost_reference(config)["first_attempt_delivery"]
        + config["A"]["first_retry_probability"] * config["A"]["retry_cost"]
    )
    price = out["price"][0]
    q = config["market"]["quality"] * (1 - config["market"]["common_outage_probability"])
    perjob += q * config["A"]["latent_defect_probability"] * config["A"]["warranty_cost"]
    default = config["market"]["nonpayment_probability"]
    deposit_fraction = config["market"]["deposit_fraction"] if policy["arrangement"] == "conditional_deposit" else 0
    net_collect = q * price * (1 - default * (1 - deposit_fraction))
    paid_gross = price * deposit_fraction + q * (1 - default) * price * (1 - deposit_fraction)
    transaction_count = int(deposit_fraction > 0) + q * (1 - default)
    contribution = net_collect - config["A"]["payment_fraction"] * paid_gross
    contribution -= config["A"]["payment_fixed"] * transaction_count + perjob
    annual_fixed = config["market"]["months"] * (
        config["A"]["monthly_business_overhead"]
        + config["market"]["qualified_invitations_per_month"] * config["A"]["cost_per_qualified_invitation"]
    )
    annual_fixed += config["A"]["launch_configuration"]
    save(
        output / "thresholds.json",
        {
            "approximate_annual_attempts_break_even": annual_fixed / contribution,
            "approximate_contribution_per_attempt": contribution,
            "approximation": "Selected-arrangement analytic central expectation; stochastic simulation governs liquidity and outcomes.",
            "fixed_annual_cost_including_launch_and_all_invitations": annual_fixed,
        },
    )
    save(
        output / "example_world.json",
        {
            "world_index": 0,
            "seed": c["fresh_seed"],
            "values": {k: float(v[0]) if math.isfinite(v[0]) else None for k, v in out.items()},
            "scope": "First frozen simulated world, not selected retrospectively and not actual trade.",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["select", "confirm", "all"])
    parser.add_argument("--output", type=Path, default=ROOT / "economics" / "results")
    args = parser.parse_args()
    config = json.loads((ROOT / "configs" / "economics.json").read_text())
    if args.phase in {"select", "all"}:
        if (args.output / "policy_freeze.json").exists():
            raise SystemExit("Refusing to overwrite a frozen experiment; choose a fresh output directory.")
        freeze = select(config, args.output)
        print(json.dumps(freeze))
    if args.phase in {"confirm", "all"}:
        confirm(config, args.output)
        print((args.output / "confirmation.json").read_text())


if __name__ == "__main__":
    main()
