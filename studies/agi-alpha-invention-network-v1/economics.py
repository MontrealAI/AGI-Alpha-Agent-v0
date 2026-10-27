# SPDX-License-Identifier: Apache-2.0
"""Conditional enterprise replay with disjoint costs and an auditable cash ledger.

Only development observations and declared priors enter policy decisions. Fresh
numerical measurements calibrate realised technical work; customer/model behaviour
is simulated. This module neither calls a frontier model nor earns revenue.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
MONEY_SCALE = 1_000_000_000
ORDINARY = {"direct", "ilu_gmres", "spectral_pcg"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def keyed(world: int, *parts: Any) -> np.random.Generator:
    seed = int.from_bytes(hashlib.sha256(canonical([world, *parts])).digest()[:8], "big")
    return np.random.default_rng(seed)


def money(value: float) -> int:
    """Preserve subcent measured compute and invocation costs in integer units."""
    if not math.isfinite(value):
        raise ValueError("Nonfinite money")
    return round(MONEY_SCALE * value)


def usd(value: int) -> float:
    return value / MONEY_SCALE


def model_bundle_cost(offer: dict[str, Any], cfg: dict[str, Any]) -> float:
    """Calculate an assumed token bundle at documented, explicitly frozen tariffs."""
    total = 0.0
    for bundle in offer["model_token_bundle"]:
        tariff = cfg["model_tariffs"]["models"][bundle["model"]]
        cached = bundle.get("cached_input_tokens", 0)
        uncached = bundle["input_tokens"] - cached
        if min(cached, uncached, bundle["output_tokens"]) < 0 or bundle["calls"] <= 0:
            raise ValueError("Invalid token bundle")
        # Counts are evenly budgeted over calls, not an assertion of actual use.
        if bundle["input_tokens"] / bundle["calls"] > 272000:
            raise ValueError("A short-context tariff cannot price this bundle")
        if bundle["output_tokens"] / bundle["calls"] > 128000:
            raise ValueError("Per-call output exceeds the documented limit")
        total += (
            uncached * tariff["input"] + cached * tariff["cached_input"] + bundle["output_tokens"] * tariff["output"]
        ) / 1_000_000
    if not math.isclose(total, offer["base_model_cost"], abs_tol=1e-9):
        raise ValueError("Model bundle does not reconcile to the declared cost")
    return total


def measurement_rows(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text())
    rows = list(obj.get("records", obj.get("rows", [])))
    rows.extend(obj.get("ood_records", []))
    # Inverse missions include every forward solve, sensor design and inversion.
    rows.extend(obj.get("composition", {}).get("mission_records", []))
    return rows


def sample_table(path: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    acc: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in measurement_rows(path):
        family = row.get("family")
        if family not in {"thermal", "transfer", "composition", "ood"}:
            continue
        method = row.get("method", row.get("solver"))
        elapsed = row.get("complete_s", row.get("total_s"))
        if method and elapsed is not None and math.isfinite(elapsed) and elapsed >= 0:
            acc[family][method].append(
                {"case_id": row.get("case_id"), "seconds": float(elapsed), "accepted": bool(row.get("accepted", True))}
            )
    result = {family: dict(methods) for family, methods in acc.items()}
    if not {"thermal", "transfer", "composition"}.issubset(result):
        raise ValueError("Complete observed thermal, transfer and composition missions are required")
    return result


def timing_table(path: Path) -> dict[str, dict[str, float]]:
    return {
        family: {method: float(np.mean([row["seconds"] for row in rows])) for method, rows in methods.items()}
        for family, methods in sample_table(path).items()
    }


def acceptance_table(samples: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, dict[str, float]]:
    return {
        family: {method: float(np.mean([row["accepted"] for row in rows])) for method, rows in methods.items()}
        for family, methods in samples.items()
    }


def technical_choices(dev: dict[str, dict[str, float]]) -> dict[str, str]:
    """Choose ordinary numerical solvers on development; use the inverse baseline intact."""
    out = {
        family: min((m for m in methods if m in ORDINARY), key=methods.__getitem__)
        for family, methods in dev.items()
        if any(m in methods for m in ORDINARY)
    }
    if "composition" in dev:
        generalist = "competent_generalist" if "competent_generalist" in dev["composition"] else "generalist"
        if generalist not in dev["composition"]:
            raise ValueError("Composition needs an equally scoped generalist baseline")
        out["composition"] = generalist
    return out


def campaign_costs(path: Path) -> dict[str, Any]:
    """Split actual local founder, extraction and search work without double charging."""
    obj = json.loads(path.read_text())
    selection = obj.get("selection", {})
    training_path = path.parent / "training.json"
    if not training_path.exists():
        raise ValueError("Development training.json is required for complete campaign accounting")
    training = json.loads(training_path.read_text())
    founder = [r for r in training["records"] if r["stage"] == "paid_founder"]
    founder_s = sum(r["solve_s"] for r in founder)
    extraction_s = sum(r.get("update_and_verify_s", r.get("update_s", 0)) for r in founder)
    artifact_write_s = training.get("founder_artifact_write_s", 0)
    founder_total_s = founder_s + extraction_s + artifact_write_s
    if not math.isclose(founder_total_s, training["paid_founder_snapshot_s"], abs_tol=1e-7):
        raise ValueError("Founder solve/extraction costs do not reconcile")
    assessment = {}
    dev_rows = obj.get("records", [])
    ood_rows = obj.get("ood_records", [])
    for method in ["v1", "v2"]:
        # The all-method run shares one reference per case; ordinary assessment pays it once.
        assessment[method] = sum(r["complete_s"] for r in dev_rows + ood_rows if r["method"] == method)
    ordinary_s = selection.get("baseline_selection_assessment_s", 0)
    if ordinary_s:
        ordinary_s -= sum(r["complete_s"] for r in dev_rows if r["method"] in {"v1", "v2"})
    else:
        refs = {r["case_id"]: r.get("assessment_reference_s", 0) for r in dev_rows}
        ordinary_s = sum(refs.values()) + sum(r["complete_s"] for r in dev_rows if r["method"] in ORDINARY)
    ood_refs = {r["case_id"]: r.get("assessment_reference_s", 0) for r in ood_rows}
    ordinary_s += sum(ood_refs.values()) + sum(r["complete_s"] for r in ood_rows if r["method"] in ORDINARY)
    ordinary_s += selection.get("domain_build_s", 0) + selection.get("warmup_s", 0)
    comp = obj.get("composition", {})
    comp_solver_rows = comp.get("solver_records", [])
    comp_refs = {r["case_id"]: r.get("assessment_reference_s", 0) for r in comp_solver_rows}
    composition_s = sum(r["complete_s"] for r in comp_solver_rows) + sum(comp_refs.values())
    composition_s += sum(r["design_s"] + r["inverse_s"] for r in comp.get("mission_records", []))
    return {
        "founder_delivery_s": founder_total_s,
        "founder_solution_s": founder_s,
        "founder_basis_construction_s": extraction_s,
        "founder_artifact_write_s": artifact_write_s,
        "gym_enrichment_s": training["extra_gym_s"],
        "all_rank_search_assessment_s": selection["all_candidate_assessment_s"],
        "baseline_selection_assessment_s": ordinary_s,
        "retention_assessment_s": assessment,
        "composition_assessment_s": composition_s,
        "candidate_ranks_paid_for": selection["candidate_ranks"],
        "evidence": "Observed local runtime; conversion uses a sourced equipment-rate proxy. Human work is estimated.",
    }


def zero_campaign() -> dict[str, Any]:
    """Explicit zero observations for small accounting tests, never the study CLI."""
    return {
        "founder_delivery_s": 0,
        "founder_solution_s": 0,
        "founder_basis_construction_s": 0,
        "gym_enrichment_s": 0,
        "all_rank_search_assessment_s": 0,
        "baseline_selection_assessment_s": 0,
        "retention_assessment_s": {"v1": 0, "v2": 0},
        "composition_assessment_s": 0,
        "candidate_ranks_paid_for": [],
    }


def candidate_routes(
    method: str, compose: bool, dev: dict[str, dict[str, float]], *, force: bool = False
) -> dict[str, str]:
    """Routing depends on development, never on held-out speed or acceptance."""
    baseline = technical_choices(dev)
    possibilities = {"thermal": method, "transfer": method, "ood": method}
    if compose:
        possibilities["composition"] = "combination" if method == "v2" else "v1_combination"
    elif method == "v2":
        # Ordinary recipients keep their existing sensor-design tools when using a solver skill.
        possibilities["composition"] = (
            "combination" if "competent_generalist" in dev.get("composition", {}) else "solver_only"
        )
    return {
        family: route
        for family, route in possibilities.items()
        if family in baseline and route in dev[family] and (force or dev[family][route] < dev[family][baseline[family]])
    }


def candidate_options(
    policy: str,
    cfg: dict[str, Any],
    dev: dict[str, dict[str, float]],
    campaign: dict[str, Any],
    week: int,
    *,
    force: bool = False,
    training_multiplier: float = 1.0,
    serving_multiplier: float = 1.0,
) -> list[dict[str, Any]]:
    prior = cfg["decision_prior"]
    remaining = min(cfg["horizon_weeks"] - week - 1, prior["forecast_lifetime_weeks"])
    remaining = max(0, remaining)
    shared = policy.startswith("shared")
    uses = remaining * prior["weekly_opportunities"] * prior["trust"] * prior["applicability_fraction"]
    uses /= 1 if shared else prior["actor_count"]
    cpu = cfg["compute_usd_per_hour"] / 3600
    baseline = technical_choices(dev)
    options = [("v1", False)]
    if "gym" in policy:
        options.append(("v2", False))
    if policy == "shared_gym_composition":
        options.extend([("v1", True), ("v2", True)])
    out = []
    for method, compose in options:
        routes = candidate_routes(method, compose, dev, force=force)
        gross = serving = 0.0
        for family, weight in prior["family_probabilities"].items():
            if family not in routes:
                continue
            delta_s = dev[family][baseline[family]] - dev[family][routes[family]]
            gross += uses * weight * delta_s * cpu
            serving += (
                uses
                * weight
                * (
                    cfg["specialist_invocation_usd"]
                    + (cfg["composition_invocation_usd"] if compose and family == "composition" else 0)
                )
            )
        serving *= serving_multiplier
        b = cfg["retention_assessment_usd"] + cfg["retention_packaging_usd"]
        b += campaign["retention_assessment_s"][method] * cpu
        b += cfg["artifact_initialization_allowance_s"] * cpu
        b += cfg["sharing_admission_usd"] if shared else 0
        if compose:
            b += cfg["composition_assessment_usd"] + cfg["composition_packaging_usd"]
            b += campaign["composition_assessment_s"] * cpu
        c = 0.0
        if method == "v2":
            c = cfg["gym_development_usd"] * training_multiplier
            c += campaign["gym_enrichment_s"] * cpu
            b += campaign["all_rank_search_assessment_s"] * cpu
        forecast = gross - b - c - remaining * cfg["maintenance_usd_per_week"] - serving
        out.append(
            {
                "method": method,
                "compose": compose,
                "shared": shared,
                "routes": routes,
                "B_upfront_usd": b,
                "C_upfront_usd": c,
                "forecast_gross_usd": gross,
                "forecast_serving_usd": serving,
                "forecast_uses": uses,
                "forecast_weeks": remaining,
                "forecast_net_usd": forecast,
            }
        )
    return out


def screening_upper_bound(
    policy: str, cfg: dict[str, Any], dev: dict[str, dict[str, float]], week: int
) -> dict[str, float]:
    """Bound compute-only value before seeing any trained candidate's performance.

    Grant free, perfect elimination of every numerical subproblem and omit Gym,
    serving and maintenance expense. A negative result rejects the opportunity
    without pretending that an unperformed training campaign has a known outcome.
    """
    prior = cfg["decision_prior"]
    weeks = max(0, min(cfg["horizon_weeks"] - week - 1, prior["forecast_lifetime_weeks"]))
    uses = weeks * prior["weekly_opportunities"] * prior["trust"] * prior["applicability_fraction"]
    uses /= 1 if policy.startswith("shared") else prior["actor_count"]
    baselines = technical_choices(dev)
    seconds = sum(weight * dev[family][baselines[family]] for family, weight in prior["family_probabilities"].items())
    gross = uses * seconds * cfg["compute_usd_per_hour"] / 3600
    minimum_cost = cfg["retention_assessment_usd"] + cfg["retention_packaging_usd"]
    minimum_cost += cfg["sharing_admission_usd"] if policy.startswith("shared") else 0
    return {
        "forecast_uses": uses,
        "forecast_weeks": weeks,
        "gross_upper_bound_usd": gross,
        "minimum_incremental_cost_usd": minimum_cost,
        "net_upper_bound_usd": gross - minimum_cost,
    }


def run_world(
    world: int,
    policy: str,
    profile: dict[str, Any],
    cfg: dict[str, Any],
    prices: dict[str, float],
    dev: dict[str, dict[str, float]],
    measured: dict[str, dict[str, float]],
    *,
    expansion: bool = False,
    force_candidate: bool = False,
    trace: bool = False,
    samples: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
    campaign: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    campaign = campaign if campaign is not None else zero_campaign()
    cash = money(cfg["initial_cash"])
    costs = {"A": 0, "B": 0, "C": 0}
    collected = refunds = defaults = invoiced = 0
    events: list[dict[str, Any]] = []
    invoices: list[dict[str, Any]] = []
    warranties: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    screened = founder_started = closed = False
    trained = retained = shared = composed = 0
    useful = bad_accepted = rejected = orders = capacity_rejected = money_rejected = 0
    duration_sum = 0.0
    quoted_sum = 0
    base_reserve = money(cfg["reserve_weeks"] * cfg["weekly_overhead"])
    cpu_rate = cfg["compute_usd_per_hour"] / 3600
    chosen_beta = technical_choices(dev)
    technical_uses = candidate_failed = expansion_count = 0
    negative_transfer_uses = numerical_failures = 0
    negative_transfer_cost = 0
    resources = cfg["weekly_capacity_hours"]
    lost_capacity: list[dict[str, Any]] = []
    model_costs = {family: model_bundle_cost(offer, cfg) for family, offer in cfg["offerings"].items()}
    serving_multiplier = profile.get("serving_cost_multiplier", 1.0)
    training_multiplier = profile.get("training_cost_multiplier", 1.0)

    def log(week: int, event: str, **fields: Any) -> None:
        if trace:
            events.append({"week": week, "event": event, **fields})

    def charge(week: int, bucket: str, amount: int, kind: str, job: str, **fields: Any) -> None:
        nonlocal cash
        if amount < 0 or amount > cash:
            raise ValueError("An expense must be nonnegative and funded; no unreported credit")
        cash -= amount
        costs[bucket] += amount
        log(week, "cost", bucket=bucket, amount_nano_usd=amount, amount_usd=usd(amount), kind=kind, job=job, **fields)

    def reserves() -> tuple[int, int]:
        return sum(x["fee"] for x in invoices), sum(x["amount"] for x in warranties)

    def spendable() -> int:
        fees, warranty = reserves()
        return cash - base_reserve - fees - warranty

    def numerical(family: str, method: str, week: int, index: int) -> tuple[float, bool, Any]:
        if samples is None:
            return measured[family][method], True, None
        rows = samples[family][method]
        # Same case index for every route preserves paired technical difficulty.
        selected = int(keyed(world, "numerical-case", week, index, family).integers(0, len(rows)))
        row = rows[selected]
        return row["seconds"], row["accepted"], row["case_id"]

    log(-1, "seed_capital", amount_nano_usd=cash, amount_usd=usd(cash), earned_revenue=False)
    charge(-1, "A", money(cfg["setup_hours"] * cfg["setup_rate"]), "enterprise_setup", "enterprise")
    charge(
        -1,
        "A",
        money(campaign["baseline_selection_assessment_s"] * cpu_rate),
        "ordinary_solver_assessment_compute",
        "enterprise",
    )
    horizon = cfg["horizon_weeks"]
    for week in range(horizon + cfg["runoff_weeks"]):
        for invoice in [item for item in invoices if item["due"] == week]:
            invoices.remove(invoice)
            if keyed(world, "collection", invoice["job"]).random() < profile["collection_default"]:
                defaults += invoice["amount"]
                log(week, "collection_default", job=invoice["job"], amount_nano_usd=invoice["amount"])
                continue
            collected += invoice["amount"]
            cash += invoice["amount"]
            log(
                week,
                "collection",
                job=invoice["job"],
                amount_nano_usd=invoice["amount"],
                amount_usd=usd(invoice["amount"]),
            )
            charge(week, "A", invoice["fee"], "payment_processing", invoice["job"])
            warranties.append(
                {
                    "due": week + cfg["refund_window_weeks"],
                    "amount": invoice["amount"],
                    "job": invoice["job"],
                    "useful": invoice["useful"],
                }
            )
        for warranty in [item for item in warranties if item["due"] == week]:
            warranties.remove(warranty)
            discovered = keyed(world, "refund-discovery", warranty["job"]).random()
            if not warranty["useful"] and discovered < cfg["refund_discovery_probability"]:
                if warranty["amount"] > cash:
                    raise AssertionError("Reserved refund is not funded")
                cash -= warranty["amount"]
                refunds += warranty["amount"]
                log(
                    week,
                    "refund",
                    job=warranty["job"],
                    amount_nano_usd=warranty["amount"],
                    amount_usd=usd(warranty["amount"]),
                )
            else:
                log(week, "warranty_release", job=warranty["job"], amount_nano_usd=warranty["amount"])
        if week >= horizon or closed:
            continue
        if week == profile["obsolescence_week"]:
            log(week, "observed_frontier_upgrade", assumption="model bundle -25%, quality +0.03")
            if active is not None:
                active = None
                log(week, "retire_at_successor", reason="No extrapolated Alpha beyond measured baseline")
        if spendable() < money(cfg["weekly_overhead"]):
            closed = True
            active = None
            log(week, "operations_close", reason="Insufficient unreserved cash; no new overhead commitment")
            continue
        charge(week, "A", money(cfg["weekly_overhead"]), "base_delivery_overhead", "enterprise")
        if active is not None:
            if spendable() < money(cfg["maintenance_usd_per_week"]):
                active = None
                log(week, "retire_unfunded_upkeep")
            else:
                charge(week, "B", money(cfg["maintenance_usd_per_week"]), "capability_maintenance", "capability")
        expansion_cfg = cfg["expansion"]
        if expansion and expansion_count < expansion_cfg["maximum_expansions"]:
            lookback = expansion_cfg["lookback_weeks"]
            observed = [r for r in lost_capacity if week - lookback <= r["week"] < week]
            if week >= expansion_cfg["minimum_history_weeks"] and observed:
                average_hours = float(np.mean([r["hours"] for r in observed]))
                extra_jobs = min(len(observed) / lookback, expansion_cfg["extra_hours_per_week"] / average_hours)
                expected_margin = float(np.mean([r["forecast_margin"] for r in observed]))
                future_weeks = min(horizon - week, expansion_cfg["forecast_weeks"])
                expected_benefit = extra_jobs * expected_margin * future_weeks
                investment = money(expansion_cfg["cash_cost_usd"])
                if (
                    spendable() - money(cfg["initial_cash"]) >= investment
                    and expected_benefit > expansion_cfg["cash_cost_usd"]
                ):
                    charge(
                        week,
                        "C",
                        investment,
                        "capacity_expansion",
                        "enterprise",
                        forecast_benefit_usd=expected_benefit,
                        past_capacity_rejected=len(observed),
                    )
                    resources += expansion_cfg["extra_hours_per_week"]
                    expansion_count += 1
        hours_left = resources
        monthly_bad = keyed(world, "quality_month", week // 4).random() < profile.get("correlated_error", 0.08)
        opportunities = int(keyed(world, "arrivals", week).poisson(profile["weekly_opportunities"]))
        for index in range(opportunities):
            rng = keyed(world, "opportunity", week, index)
            family = str(rng.choice(["thermal", "transfer", "composition"], p=[0.4, 0.35, 0.25]))
            actor = int(rng.integers(0, cfg["decision_prior"]["actor_count"]))
            offer = cfg["offerings"][family]
            human = offer["human_hours"] * offer["human_rate"]
            price = money(prices[family] * human)
            willingness = profile["value_multiplier"] * math.exp(rng.normal(-0.1, 0.35))
            buy = rng.random() < profile["trust"] and usd(price) <= human * willingness
            job = f"{week}-{index}"
            if not buy:
                log(week, "opportunity_declined_price_or_trust", job=job, family=family, price_usd=usd(price))
                continue
            orders += 1
            quoted_sum += price
            successor = week >= profile["obsolescence_week"]
            quality = max(0, min(0.999, profile["quality"] + (0.03 if successor else 0) - (0.2 if monthly_bad else 0)))
            model_cost = model_costs[family] * profile["model_cost_multiplier"] * (0.75 if successor else 1)
            elapsed = offer["base_agent_hours"]
            numerical_family = family
            if family == "transfer" and "ood" in measured:
                if keyed(world, "out-of-scope", job).random() < profile.get("out_of_scope_fraction", 0):
                    numerical_family = "ood"
            base = chosen_beta[numerical_family]
            candidate = active if active and (active["shared"] or actor == active["owner"]) else None
            method = base
            serving_cost = 0.0
            if candidate and numerical_family in candidate["routes"]:
                route = candidate["routes"][numerical_family]
                call_cost = cfg["specialist_invocation_usd"]
                if candidate["compose"] and family == "composition":
                    call_cost += cfg["composition_invocation_usd"]
                call_cost *= serving_multiplier
                expected_saving = (dev[numerical_family][base] - dev[numerical_family][route]) * cpu_rate
                if force_candidate or expected_saving > call_cost:
                    method, serving_cost = route, call_cost
            founder = family == "thermal" and not founder_started
            numerical_budget = cfg["per_job_numerical_budget_seconds"][numerical_family]
            estimated_s = campaign["founder_delivery_s"] if founder else dev[numerical_family][method]
            estimated_cost = model_cost + offer["integration_tools_cost"] + offer["acceptance_cost"]
            estimated_cost += estimated_s * cpu_rate
            funded_cost = model_cost + offer["integration_tools_cost"] + offer["acceptance_cost"]
            funded_cost += max(numerical_budget, campaign["founder_delivery_s"] if founder else 0) * cpu_rate
            correction_budget = 0.6 * (model_cost + offer["integration_tools_cost"]) + numerical_budget * cpu_rate
            fee = money(usd(price) * cfg["collection_fee_fraction"] + cfg["collection_fee_fixed_usd"])
            if elapsed > hours_left:
                capacity_rejected += 1
                prior = cfg["decision_prior"]
                expected_receipt = usd(price) * prior["quality"] * (1 - prior["collection_default"])
                lost_capacity.append(
                    {"week": week, "hours": elapsed, "forecast_margin": expected_receipt - estimated_cost - usd(fee)}
                )
                log(week, "order_declined_capacity", job=job, family=family, agent_hours=elapsed)
                continue
            if spendable() < money(funded_cost + serving_cost + correction_budget) + fee:
                money_rejected += 1
                log(week, "order_declined_cash", job=job, family=family)
                continue
            hours_left -= elapsed
            duration_sum += elapsed
            founder_started = founder_started or founder
            # Held-out outcomes are revealed only after admission and route selection.
            base_seconds, base_accepted, case_id = numerical(numerical_family, base, week, index)
            solve_seconds, technical_ok, _ = numerical(numerical_family, method, week, index)
            if max(base_seconds, solve_seconds) > numerical_budget:
                raise ValueError("Fresh measured runtime exceeds the registered numerical job budget")
            if founder and campaign["founder_delivery_s"] > 0:
                solve_seconds = campaign["founder_delivery_s"]
            full_cost = model_cost + offer["integration_tools_cost"] + offer["acceptance_cost"]
            full_cost += solve_seconds * cpu_rate
            if method != base:
                technical_uses += 1
                charge(
                    week,
                    "B",
                    money(serving_cost),
                    "specialist_serving",
                    job,
                    method=method,
                    includes_composition=bool(candidate["compose"] and family == "composition"),
                )
                if solve_seconds > base_seconds or (base_accepted and not technical_ok):
                    negative_transfer_uses += 1
                    negative_transfer_cost += money(max(0, solve_seconds - base_seconds) * cpu_rate + serving_cost)
            charge(
                week,
                "A",
                money(full_cost),
                "complete_delivery",
                job,
                model_usd=model_cost,
                integration_usd=offer["integration_tools_cost"],
                acceptance_usd=offer["acceptance_cost"],
                numerical_usd=solve_seconds * cpu_rate,
                founder_solution_generation=founder,
            )
            numerical_failures += int(not technical_ok)
            model_good = keyed(world, "initial-quality", job).random() < quality
            good = bool(model_good and technical_ok)
            validator_detects = keyed(world, "validator", job).random() < (0.55 if monthly_bad else 0.94)
            detected = not technical_ok or (not model_good and validator_detects)
            if detected and hours_left >= 0.5 * elapsed and spendable() >= money(correction_budget) + fee:
                correction_cost = 0.6 * (model_cost + offer["integration_tools_cost"]) + base_seconds * cpu_rate
                charge(week, "A", money(correction_cost), "correction", job, ordinary_solver=base)
                hours_left -= 0.5 * elapsed
                duration_sum += 0.5 * elapsed
                good = bool(
                    keyed(world, "correction-quality", job).random() < max(0.1, quality - 0.08) and base_accepted
                )
                detected = not good
            if detected:
                rejected += 1
                log(
                    week,
                    "delivery_rejected",
                    job=job,
                    family=family,
                    method=method,
                    technical_accepted=technical_ok,
                    numerical_s=solve_seconds,
                )
                continue
            useful += int(good)
            bad_accepted += int(not good)
            delay = profile.get("collection_delay", cfg["collection_delay_weeks"])
            # The controller sees an invoice, not the eventual random default or latent correctness.
            invoices.append({"due": week + max(1, delay), "amount": price, "fee": fee, "job": job, "useful": good})
            invoiced += price
            log(
                week,
                "delivery",
                job=job,
                family=family,
                actor=actor,
                simulated_useful=good,
                observed_acceptance=True,
                invoice_nano_usd=price,
                fee_reserved_nano_usd=fee,
                price_usd=usd(price),
                method=method,
                numerical_s=solve_seconds,
                numerical_family=numerical_family,
                numerical_case=case_id,
                technical_accepted=technical_ok,
                successor=successor,
            )
            # Use observable acceptance, not the simulator's hidden ground-truth 'good'.
            if policy == "beta" or screened or family != "thermal":
                continue
            screened = True
            if spendable() < money(cfg["candidate_screen_usd"]):
                candidate_failed += 1
                log(week, "decline_candidate", reason="Screen not fundable")
                continue
            charge(week, "B", money(cfg["candidate_screen_usd"]), "candidate_screen", "candidate")
            if successor:
                candidate_failed += 1
                log(week, "decline_candidate", reason="No qualified artifact evidence against the observed upgrade")
                continue
            bound = screening_upper_bound(policy, cfg, dev, week)
            if bound["net_upper_bound_usd"] <= 0 and not force_candidate:
                candidate_failed += 1
                log(
                    week,
                    "candidate_decision",
                    options=[],
                    selected=None,
                    forced=False,
                    screening_upper_bound=bound,
                    candidate_outcomes_consulted=False,
                )
                log(
                    week,
                    "decline_candidate",
                    forecast_net_upper_bound_usd=bound["net_upper_bound_usd"],
                    reason="Even eliminating all numerical compute cannot cover minimum retention cost",
                )
                continue
            options = candidate_options(
                policy,
                cfg,
                dev,
                campaign,
                week,
                force=force_candidate,
                training_multiplier=training_multiplier,
                serving_multiplier=serving_multiplier,
            )
            chosen = max(options, key=lambda option: option["forecast_net_usd"])
            if force_candidate:
                desired = "v2" if "gym" in policy else "v1"
                desired_compose = policy == "shared_gym_composition"
                chosen = next(o for o in options if o["method"] == desired and o["compose"] == desired_compose)
            log(
                week,
                "candidate_decision",
                options=options,
                selected=chosen["method"],
                selected_composition=chosen["compose"],
                forced=force_candidate,
            )
            if chosen["forecast_net_usd"] <= 0 and not force_candidate:
                candidate_failed += 1
                log(
                    week,
                    "decline_candidate",
                    forecast_net_usd=chosen["forecast_net_usd"],
                    reason="Complete incremental cost exceeds development-based forecast benefit",
                )
                continue
            if spendable() < money(chosen["B_upfront_usd"] + chosen["C_upfront_usd"]):
                candidate_failed += 1
                log(week, "decline_candidate", reason="Selected investment not fundable")
                continue
            b_components = {
                "retention_human_assessment": cfg["retention_assessment_usd"],
                "retention_packaging": cfg["retention_packaging_usd"],
                "artifact_initialization_allowance": cfg["artifact_initialization_allowance_s"] * cpu_rate,
                "retention_assessment_compute": campaign["retention_assessment_s"][chosen["method"]] * cpu_rate,
                "sharing_admission": cfg["sharing_admission_usd"] if chosen["shared"] else 0,
            }
            if chosen["compose"]:
                b_components.update(
                    {
                        "composition_human_assessment": cfg["composition_assessment_usd"],
                        "composition_packaging": cfg["composition_packaging_usd"],
                        "composition_assessment_compute": campaign["composition_assessment_s"] * cpu_rate,
                    }
                )
            for kind, amount in b_components.items():
                if amount:
                    charge(week, "B", money(amount), kind, "candidate")
            if chosen["method"] == "v2":
                charge(
                    week,
                    "C",
                    money(cfg["gym_development_usd"] * training_multiplier),
                    "optional_gym_human_development",
                    "candidate",
                )
                charge(week, "C", money(campaign["gym_enrichment_s"] * cpu_rate), "optional_gym_compute", "candidate")
                charge(
                    week,
                    "B",
                    money(campaign["all_rank_search_assessment_s"] * cpu_rate),
                    "all_rank_search_assessment_compute",
                    "candidate",
                    ranks=campaign["candidate_ranks_paid_for"],
                )
                trained += 1
            active = {**chosen, "owner": actor}
            retained += 1
            shared += int(chosen["shared"])
            composed += int(chosen["compose"])
    fee_reserve, refund_exposure = reserves()
    receivables = sum(invoice["amount"] for invoice in invoices)
    reserve = base_reserve + fee_reserve + refund_exposure
    net = collected - refunds - sum(costs.values())
    if cash != money(cfg["initial_cash"]) + net or cash < 0:
        raise AssertionError("Cash ledger does not reconcile")
    row = {
        "world": world,
        "policy": policy,
        "collections": usd(collected),
        "refunds": usd(refunds),
        "A": usd(costs["A"]),
        "B": usd(costs["B"]),
        "C": usd(costs["C"]),
        "complete_cost": usd(sum(costs.values())),
        "profit": usd(net),
        "cash": usd(cash),
        "obligations": 0.0,
        "receivables": usd(receivables),
        "reserve": usd(reserve),
        "base_reserve": usd(base_reserve),
        "collection_fee_reserve": usd(fee_reserve),
        "refund_exposure": usd(refund_exposure),
        "invoices": usd(invoiced),
        "collection_defaults": usd(defaults),
        "available_funds": usd(max(0, cash - reserve)),
        "available_earned_funds": usd(max(0, cash - money(cfg["initial_cash"]) - reserve)),
        "useful": useful,
        "bad_accepted": bad_accepted,
        "rejected": rejected,
        "orders": orders,
        "capacity_rejected": capacity_rejected,
        "cash_rejected": money_rejected,
        "retained": retained,
        "trained": trained,
        "shared": shared,
        "composed": composed,
        "technical_uses": technical_uses,
        "negative_transfer_uses": negative_transfer_uses,
        "negative_transfer_incremental_cost": usd(negative_transfer_cost),
        "numerical_failures": numerical_failures,
        "declined_candidates": candidate_failed,
        "expansions": expansion_count,
        "closed": int(closed),
        "agent_hours": duration_sum,
        "quoted_order_prices": usd(quoted_sum),
        "cost_per_useful": usd(sum(costs.values())) / useful if useful else None,
    }
    log(
        horizon + cfg["runoff_weeks"],
        "closing_balance",
        cash_nano_usd=cash,
        receivables_nano_usd=receivables,
        refund_exposure_nano_usd=refund_exposure,
        collection_fee_reserve_nano_usd=fee_reserve,
        base_reserve_nano_usd=base_reserve,
    )
    return row, events


def audit_history(row: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Independently reconstruct every cash movement from exported transactions."""
    balance = seed = collections = refunds = 0
    costs = {"A": 0, "B": 0, "C": 0}
    minimum = math.inf
    for event in events:
        amount = event.get("amount_nano_usd", 0)
        if event["event"] == "seed_capital":
            seed += amount
            balance += amount
        elif event["event"] == "collection":
            collections += amount
            balance += amount
        elif event["event"] == "refund":
            refunds += amount
            balance -= amount
        elif event["event"] == "cost":
            costs[event["bucket"]] += amount
            balance -= amount
        minimum = min(minimum, balance)
    if minimum < 0 or abs(usd(balance) - row["cash"]) > 1e-8:
        raise AssertionError("History has negative cash or disagrees with summary")
    for key, expected in {"collections": collections, "refunds": refunds, **costs}.items():
        if abs(usd(expected) - row[key]) > 1e-8:
            raise AssertionError(f"History does not reconcile: {key}")
    if abs(usd(balance - seed) - row["profit"]) > 1e-8:
        raise AssertionError("Seed capital was included in earnings")
    delivered = {e["job"] for e in events if e["event"] in {"delivery", "delivery_rejected"}}
    serving = {e["job"] for e in events if e["event"] == "cost" and e["kind"] == "specialist_serving"}
    if not serving.issubset(delivered):
        raise AssertionError("Serving charged to an order that never started")
    return {"verified": True, "transactions": len(events), "minimum_cash_usd": usd(int(minimum))}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    beta = {row["world"]: row for row in rows if row["policy"] == "beta"}
    for policy in sorted({row["policy"] for row in rows}):
        selected = [row for row in rows if row["policy"] == policy]
        delta = [row["profit"] - beta[row["world"]]["profit"] for row in selected]
        means = {}
        for key in selected[0]:
            values = [r[key] for r in selected if isinstance(r[key], (int, float)) and key != "world"]
            if values:
                means[key] = float(np.mean(values))
        profits = [row["profit"] for row in selected]
        useful = sum(row["useful"] for row in selected)
        accepted = useful + sum(row["bad_accepted"] for row in selected)
        means.update(
            {
                "positive_profit_share": float(np.mean(np.array(profits) > 0)),
                "profit_q05": float(np.quantile(profits, 0.05)),
                "profit_q95": float(np.quantile(profits, 0.95)),
                "incremental_profit": float(np.mean(delta)),
                "incremental_mcse": float(np.std(delta, ddof=1) / math.sqrt(len(delta))) if len(delta) > 1 else 0,
                "cost_per_useful_pooled": sum(r["complete_cost"] for r in selected) / useful if useful else None,
                "false_pass_share": sum(r["bad_accepted"] for r in selected) / accepted if accepted else None,
            }
        )
        out[policy] = means
    return out


def select_prices(cfg: dict[str, Any]) -> dict[str, Any]:
    """A declared development-only price-grid objective, not a real-market optimum."""
    trials = []
    profile = cfg["profiles"]["reference"]
    prior = cfg["decision_prior"]
    for fraction in cfg["price_fractions"]:
        expected = 0.0
        for world in cfg["development_world_ids"]:
            willingness = profile["value_multiplier"] * np.exp(
                keyed(world, "price-development").normal(-0.1, 0.35, 3000)
            )
            purchase = float(np.mean(willingness >= fraction)) * prior["trust"]
            q = prior["quality"]
            # Initial acceptable delivery plus one detected-failure correction.
            detection = 0.94
            corrected = (1 - q) * detection * max(0.1, q - 0.08)
            missed = (1 - q) * (1 - detection)
            accepted = q + corrected + missed
            collectible = q + corrected + missed * (1 - cfg["refund_discovery_probability"])
            collectible *= 1 - prior["collection_default"]
            for family, offer in cfg["offerings"].items():
                human = offer["human_hours"] * offer["human_rate"]
                model_cost = model_bundle_cost(offer, cfg)
                direct = model_cost + offer["integration_tools_cost"] + offer["acceptance_cost"]
                correction = (1 - q) * detection * 0.6 * (model_cost + offer["integration_tools_cost"])
                fee = fraction * human * cfg["collection_fee_fraction"] + cfg["collection_fee_fixed_usd"]
                expected_fee = accepted * (1 - prior["collection_default"]) * fee
                margin = fraction * human * collectible - direct - correction - expected_fee
                expected += (
                    prior["family_probabilities"][family] * purchase * margin / len(cfg["development_world_ids"])
                )
        trials.append({"fraction": fraction, "development_objective_usd_per_opportunity": expected})
    selected = max(trials, key=lambda trial: trial["development_objective_usd_per_opportunity"])["fraction"]
    return {
        "prices": {family: selected for family in cfg["offerings"]},
        "development_trials": trials,
        "limits": "Finite common price grid, declared reference belief and one-opportunity contribution objective. "
        "Includes estimated correction/default/refund/processing costs; excludes fixed overhead, "
        "capacity competition and learning. Not a global optimum or observed customer price.",
    }


def source_manifest(development: Path) -> dict[str, str]:
    paths = {
        "protocol": HERE / "economic_protocol.json",
        "economics": Path(__file__),
        "development": development,
        "training": development.parent / "training.json",
    }
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--worlds", type=int)
    args = parser.parse_args()
    cfg = json.loads((HERE / "economic_protocol.json").read_text())
    dev = timing_table(args.development)
    campaign = campaign_costs(args.development)
    args.output.mkdir(parents=True, exist_ok=True)
    lock = args.output / "policy_freeze.json"
    if args.freeze:
        if lock.exists():
            raise FileExistsError("Policy freeze already exists")
        data = {
            **select_prices(cfg),
            "development_timing": dev,
            "numerical_baselines": technical_choices(dev),
            "development_acceptance": acceptance_table(sample_table(args.development)),
            "campaign_costs": campaign,
            "source_sha256": source_manifest(args.development),
            "protocol_sha256": source_manifest(args.development)["protocol"],
            "economics_sha256": source_manifest(args.development)["economics"],
            "development_sha256": source_manifest(args.development)["development"],
        }
        lock.write_text(json.dumps(data, indent=2) + "\n")
        print(json.dumps(data, indent=2))
        return
    if not args.confirmation or not lock.exists():
        raise ValueError("Freeze policy first; supply confirmation measurements")
    frozen = json.loads(lock.read_text())
    if source_manifest(args.development) != frozen["source_sha256"]:
        raise ValueError("Source drift after policy freeze")
    obs = timing_table(args.confirmation)
    samples = sample_table(args.confirmation)
    worlds = args.worlds if args.worlds is not None else cfg["confirmation_worlds_per_profile"]
    if worlds < 1:
        raise ValueError("At least one world is required")
    summaries, diagnostics, all_rows, examples = {}, {}, [], []
    transaction_count = history_count = 0
    stress = {
        "forced_retention": {},
        "congestion": {"weekly_opportunities": 12},
        "correlated_errors": {"correlated_error": 0.4},
        "late_collections": {"collection_delay": 16},
        "early_successor": {"obsolescence_week": 13},
        "low_value": {"value_multiplier": 0.5},
        "no_demand": {"weekly_opportunities": 0},
        "surplus_funded_expansion": {"weekly_opportunities": 12},
        "forced_high_training_cost": {"training_cost_multiplier": 10},
        "forced_high_serving_cost": {"serving_cost_multiplier": 1000},
        "forced_negative_transfer": {"out_of_scope_fraction": 1.0},
    }
    groups = [(label, profile, worlds, 900000, False) for label, profile in cfg["profiles"].items()]
    groups.extend(
        (label, {**cfg["profiles"]["reference"], **changes}, min(worlds, 100), 910000, True)
        for label, changes in stress.items()
    )
    # Every world, including stresses and failures, has a complete, independently checked ledger.
    with (args.output / "all_histories.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8") as stream:
                for label, profile, count, first, diagnostic in groups:
                    rows = []
                    for world in range(first, first + count):
                        for policy in cfg["policies"]:
                            row, events = run_world(
                                world,
                                policy,
                                profile,
                                cfg,
                                frozen["prices"],
                                dev,
                                obs,
                                force_candidate=label.startswith("forced_") and policy != "beta",
                                expansion=label == "surplus_funded_expansion",
                                trace=True,
                                samples=samples,
                                campaign=campaign,
                            )
                            row["profile"] = label
                            audit = audit_history(row, events)
                            transaction_count += audit["transactions"]
                            history_count += 1
                            history = {
                                "profile": label,
                                "world": world,
                                "policy": policy,
                                "summary": row,
                                "audit": audit,
                                "events": events,
                            }
                            stream.write(json.dumps(history, separators=(",", ":"), allow_nan=False) + "\n")
                            if world == first:
                                examples.append(history)
                            rows.append(row)
                    (diagnostics if diagnostic else summaries)[label] = summarize(rows)
                    all_rows.extend(rows)
    report = {
        "schema": "invention-network-economics/v1",
        "evidence": cfg["evidence"],
        "evidence_labels": cfg["evidence_labels"],
        "worlds_per_profile": worlds,
        "policy_freeze": frozen,
        "profiles": summaries,
        "diagnostics": diagnostics,
        "confirmation_timing": obs,
        "confirmation_acceptance": acceptance_table(samples),
        "rows": len(all_rows),
        "statistical_limits": "Monte Carlo variability is conditional on declared profiles and empirical numerical replay. "
        "More seeds do not validate demand, quality, price, labour, or access assumptions.",
        "accounting_audit": {
            "histories": history_count,
            "transactions": transaction_count,
            "cash_identity_failures": 0,
            "minimum_cash_test": "all histories nonnegative",
            "complete_histories": "all_histories.jsonl.gz",
            "actual_customer_revenue_usd": 0,
            "actual_research_cost": "unknown; no zero-cost claim",
        },
    }
    (args.output / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    with (args.output / "worlds.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    with gzip.open(args.output / "example_histories.json.gz", "wt") as stream:
        json.dump(examples, stream, allow_nan=False)
    print(json.dumps({"output": str(args.output), "rows": len(all_rows), "profiles": summaries}, indent=2))


if __name__ == "__main__":
    main()
