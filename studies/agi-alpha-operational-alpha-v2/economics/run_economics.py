# SPDX-License-Identifier: Apache-2.0
"""Prospective conditional enterprise mechanics with explicit economic assumptions."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, cast

HERE = Path(__file__).resolve().parent
CATEGORIES = ("model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead")
ADMISSION_PATH = HERE.parent / "integration" / "admission.py"
POLICIES = ("ordinary_U", "expert_E", "enhanced_Eplus", "private_retention", "shared_retention", "library_retention")
ARMS = {
    "ordinary_U": "U",
    "expert_E": "E",
    "enhanced_Eplus": "E_plus",
    "private_retention": "E",
    "shared_retention": "E",
    "library_retention": "E",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_pilot(path: Path) -> dict[str, Any]:
    data = cast(dict[str, Any], json.loads(path.read_text()))
    for arm in ("U", "E", "E_plus"):
        item = data["arms"][arm]
        if type(item["accepted"]) is not int or type(item["attempted"]) is not int:
            raise ValueError("pilot counts must be integers")
        if not 0 <= item["accepted"] <= item["attempted"] or item["attempted"] < 1:
            raise ValueError("invalid pilot counts")
    return data


def envelope(maximum: float, uses: float, lifecycle: int, evaluation: int) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("operational_alpha_admission", ADMISSION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing unchanged admission helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(
        dict[str, Any],
        module.research_gate_envelope(
            {
                "maximum_per_use_delta_cents": maximum,
                "forecast_eligible_uses": uses,
                "lifecycle_cost_cents": lifecycle,
                "evaluation_cost_cents": evaluation,
                "maximum_independent_clusters": 6,
            }
        ),
    )


def quality_draw(pilot: dict[str, Any], seed: int) -> dict[str, float]:
    result = {}
    for arm, item in pilot["arms"].items():
        if arm not in ("U", "E", "E_plus"):
            continue
        accepted, n = item["accepted"], item["attempted"]
        rng = random.Random(seed * 1009 + accepted * 31 + n * 7)
        result[arm] = rng.betavariate(accepted + 1, n - accepted + 1)
    return result


def qualities_mean(pilot: dict[str, Any]) -> dict[str, float]:
    return {
        k: (v["accepted"] + 1) / (v["attempted"] + 2) for k, v in pilot["arms"].items() if k in ("U", "E", "E_plus")
    }


def tape(seed: int, config: dict[str, Any], profile: str) -> dict[str, Any]:
    rng = random.Random(seed)
    arrivals = []
    for day in range(config["horizon_days"]):
        count = rng.randrange(7)
        for j in range(count):
            arrivals.append(
                {
                    "id": f"{seed}-{day}-{j}",
                    "day": day,
                    "recipient": j % 2,
                    "bundle": rng.random() < 0.16,
                    "interested": rng.random(),
                    "in_house": rng.random(),
                    "trust": rng.uniform(0.35, 1.05),
                    "value": rng.lognormvariate(-0.05, 0.45),
                    "difficulty": rng.uniform(-0.12, 0.12),
                    "truth": [rng.random(), rng.random()],
                    "validator": [rng.random(), rng.random()],
                    "delay": rng.randint(1, 7),
                    "refund_delay": rng.randint(7, 14),
                }
            )
    return {
        "arrivals": arrivals,
        "assay": [rng.random() for _ in range(12)],
        "assay_error": rng.random(),
        "delivery_error": rng.random(),
        "gym_gain": rng.gauss(config["gym_gain_prior_mean"], config["gym_gain_prior_sd"]),
        "prototype": rng.random(),
        "profile": profile,
    }


def unit_cost(config: dict[str, Any], profile: str) -> dict[str, int]:
    result = cast(dict[str, int], config["per_attempt_categories_cents"].copy())
    minutes = 5 if profile == "residual_5min" else 15 if profile == "residual_15min" else 0
    result["human"] = round(minutes * config["human_reference"]["hourly_rate_usd"] * 100 / 60)
    if profile == "high_shadow_cost":
        result["model"] *= 10
    return result


def simulate(
    pilot: dict[str, Any],
    config: dict[str, Any],
    seed: int,
    profile: str,
    policy: str,
    choice: dict[str, Any],
    record: bool = False,
) -> dict[str, Any]:
    world = tape(seed, config, profile)
    latent = quality_draw(pilot, seed)
    mean = qualities_mean(pilot)
    arm = ARMS[policy]
    cash = config["seed_capital_cents"]
    costs = {group: {category: 0 for category in CATEGORIES} for group in ("A", "B", "C")}
    events = []
    pending: list[dict[str, Any]] = []
    contract_holds: dict[str, tuple[int, int]] = {}
    collections = refunds = invoice = accepted = failures = attempted = quotes = declined = 0
    fixed = config["daily_overhead_cents"]
    reserve = fixed * choice["reserve_days"]
    per_attempt = unit_cost(config, profile)
    basic_cost = sum(per_attempt.values())
    retained = policy == "enhanced_Eplus"
    shared = policy in ("shared_retention", "library_retention")
    candidate_done = gym_done = prototype_done = bundle_ready = False
    stopped = False
    learned_shift = 0.0
    observed_jobs = observed_successes = observed_leads = observed_bundle_leads = 0
    seen_ids: set[str] = set()
    diagnostic = {
        "screens": 0,
        "assessments": 0,
        "admissions": 0,
        "false_admissions": 0,
        "gym_attempts": 0,
        "gym_negative": 0,
        "prototype_attempts": 0,
        "prototype_failures": 0,
        "capacity_rejections": 0,
        "cash_rejections": 0,
        "declined_negative_margin": 0,
        "holds": 0,
        "retained_uses": 0,
        "final_obligations_cents": 0,
    }

    def event(day: int, kind: str, **fields: Any) -> None:
        if record:
            events.append({"day": day, "kind": kind, **fields, "cash_cents": cash})

    def charge(day: int, group: str, category: str, amount: int, activity: str) -> None:
        nonlocal cash
        if amount < 0 or category not in CATEGORIES or group not in costs or activity in seen_ids:
            raise AssertionError("invalid or duplicate cost activity")
        seen_ids.add(activity)
        costs[group][category] += amount
        cash -= amount
        event(day, "cost", group=group, category=category, cents=amount, activity=activity)

    if policy != "ordinary_U":
        charge(-1, "B", "overhead", config["expert_method_setup_cents"], "expert-method-setup")
    if retained:
        charge(-1, "B", "overhead", config["enhancement_package_cents"], "enhancement-package")

    def held(day: int) -> int:
        return sum(amount for amount, expiry in contract_holds.values() if expiry > day)

    for day in range(config["horizon_days"] + config["settlement_days"]):
        for item in pending[:]:
            if item["day"] == day:
                if item["kind"] == "collection":
                    cash += item["amount"]
                    collections += item["amount"]
                    contract_holds[item["job"]] = (item["amount"], item["hold_until"])
                else:
                    cash -= item["amount"]
                    refunds += item["amount"]
                    contract_holds.pop(item["job"], None)
                event(day, item["kind"], cents=item["amount"], job=item["job"])
                pending.remove(item)
        if day >= config["horizon_days"]:
            continue
        recurring = fixed + (config["daily_retained_maintenance_cents"] if retained else 0)
        if stopped or cash - held(day) < recurring:
            stopped = True
            diagnostic["holds"] += 1
            event(day, "stop-production", reason="insufficient-unencumbered-cash-for-recurring-expense")
            continue
        charge(day, "A", "overhead", fixed, f"fixed-{day}")
        if retained:
            charge(day, "B", "storage", config["daily_retained_maintenance_cents"], f"maintenance-{day}")
        capacity = config["daily_capacity_units"]
        remaining = config["horizon_days"] - day
        historical_rate = observed_leads / max(day, 1)
        forecast_uses = min(remaining * historical_rate, remaining * capacity / config["ordinary_job_units"])
        if policy == "private_retention":
            forecast_uses *= 0.5
        expected_p = mean["E_plus" if retained else arm]
        h = (
            (30 if profile == "low_price_human" else config["human_reference"]["hourly_rate_usd"])
            * config["human_reference"]["hours"]
            * 100
        )
        price = round(h * choice["price_ratio"])
        future_expense = (
            config["assessment_cents"]
            + config["retention_cents"]
            + (config["sharing_cents"] if shared else 0)
            + math.ceil(forecast_uses * config["per_retained_use_cents"])
            + remaining * config["daily_retained_maintenance_cents"]
        )
        possible_delta = float(max(price - basic_cost, 0))
        possible_net = forecast_uses * possible_delta - future_expense
        optional = policy in ("private_retention", "shared_retention", "library_retention")
        if optional and not candidate_done and observed_jobs >= 6:
            candidate_done = True
            diagnostic["screens"] += 1
            charge(day, "B", "compute", config["screen_cents"], "retention-screen")
            reachability = envelope(
                possible_delta, forecast_uses, future_expense - config["assessment_cents"], config["assessment_cents"]
            )
            reachable = reachability["reachable"]
            event(
                day,
                "assessment-screen",
                reachable=reachable,
                forecast_uses=forecast_uses,
                max_per_use_cents=possible_delta,
                max_net_cents=possible_net,
                independent_clusters=6,
            )
            if reachable and cash - reserve - held(day) >= future_expense and capacity >= 2:
                charge(day, "B", "acceptance", config["assessment_cents"], "retention-assessment")
                capacity -= 2
                diagnostic["assessments"] += 1
                pairs = []
                common_error = world["assay_error"] < (
                    0.3 if profile == "validator_correlation" else config["validator_common_error_primary"]
                )
                for value in world["assay"][:6]:
                    baseline = value < latent["E"]
                    enhanced = value < latent["E_plus"]
                    if common_error:
                        baseline, enhanced = False, True
                    pairs.append((int(enhanced) - int(baseline)) * max(price - basic_cost, 0))
                lower = statistics.mean(pairs) - 1.645 * statistics.stdev(pairs) / math.sqrt(6)
                net_lower = forecast_uses * lower - future_expense
                admit = lower > 0 and net_lower >= 1
                event(
                    day,
                    "modeled-assessment",
                    pairs_cents=pairs,
                    lower_per_use_cents=lower,
                    net_lower_cents=net_lower,
                    admit=admit,
                    synthetic_future_evidence=True,
                )
                if admit:
                    charge(day, "B", "overhead", config["retention_cents"], "retention-package")
                    if shared:
                        charge(day, "B", "network", config["sharing_cents"], "network-distribution")
                    retained = True
                    diagnostic["admissions"] += 1
                    if latent["E_plus"] <= latent["E"]:
                        diagnostic["false_admissions"] += 1
            else:
                diagnostic["holds"] += 1
        gym_lower = config["gym_gain_prior_mean"] - 1.645 * config["gym_gain_prior_sd"]
        gym_value = forecast_uses * max(price - basic_cost, 0) * gym_lower - config["gym_cents"]
        if optional and candidate_done and not retained and not gym_done and gym_value > 0:
            gym_done = True
            if cash - reserve - held(day) >= config["gym_cents"] and capacity >= 3:
                charge(day, "C", "model", config["gym_cents"], "optional-gym")
                capacity -= 3
                learned_shift = world["gym_gain"]
                diagnostic["gym_attempts"] += 1
                diagnostic["gym_negative"] += int(learned_shift < 0)
                event(day, "gym", gain=learned_shift, update="simulated workflow policy, no model-weight change")
        current_arm = "E_plus" if retained else arm
        eligible_pack = pilot["arms"][current_arm]["accepted"] == pilot["arms"][current_arm]["attempted"]
        prototype_value = observed_bundle_leads / max(day, 1) * remaining * (4 * price * expected_p**4 - 4 * basic_cost)
        if (
            not prototype_done
            and observed_bundle_leads >= 2
            and eligible_pack
            and prototype_value > config["prototype_cents"]
        ):
            if cash - reserve - held(day) >= config["prototype_cents"] and capacity >= 2:
                prototype_done = True
                diagnostic["prototype_attempts"] += 1
                charge(day, "C", "acceptance", config["prototype_cents"], "bundle-prototype")
                capacity -= 2
                bundle_ready = world["prototype"] < latent[current_arm] ** 4
                diagnostic["prototype_failures"] += int(not bundle_ready)
                event(day, "prototype", accepted=bundle_ready, same_offering_menu=True)
        for lead in (item for item in world["arrivals"] if item["day"] == day):
            observed_leads += 1
            observed_bundle_leads += int(lead["bundle"])
            if profile == "thin_demand" and lead["interested"] > 0.22:
                continue
            if lead["interested"] > 0.85 or lead["in_house"] < 0.15:
                declined += 1
                event(day, "buyer-declined", job=lead["id"], choice="defer-or-in-house")
                continue
            units = config["bundle_job_units"] if lead["bundle"] else config["ordinary_job_units"]
            scope = 4 if lead["bundle"] else 1
            receives_method = retained and (policy != "private_retention" or lead["recipient"] == 0)
            current_arm = "E_plus" if receives_method else arm
            expected_p = mean[current_arm]
            if lead["bundle"] and (
                not bundle_ready or pilot["arms"][current_arm]["accepted"] < pilot["arms"][current_arm]["attempted"]
            ):
                continue
            if capacity < units:
                diagnostic["capacity_rejections"] += 1
                continue
            maximum_job_cash = scope * (basic_cost * 2 + 50) + config["quote_cost_cents"]
            maximum_job_cash += config["per_retained_use_cents"] if receives_method else 0
            if cash - reserve - held(day) < maximum_job_cash:
                diagnostic["cash_rejections"] += 1
                continue
            quotes += 1
            charge(day, "A", "model", config["quote_cost_cents"], "quote-" + lead["id"])
            sale = scope * price
            expected_prob = expected_p**scope
            expected_delivery_cost = scope * basic_cost * (2 - expected_prob)
            if expected_prob * sale - expected_delivery_cost <= 0:
                diagnostic["declined_negative_margin"] += 1
                continue
            customer_effort = 4 * 100
            buyer_limit = scope * h * min(lead["trust"], lead["value"])
            if sale + customer_effort > buyer_limit:
                declined += 1
                continue
            capacity -= units
            attempted += 1
            observed_jobs += 1
            job_id = lead["id"]
            p = max(0.02, min(0.995, latent[current_arm] + lead["difficulty"] + learned_shift))
            if profile == "model_upgrade" and day >= 15:
                p = max(0.02, min(0.995, max(latent.values()) + lead["difficulty"]))
            if profile == "transfer_shift" and receives_method and day >= 15:
                p = max(0.02, p - 0.25)
            p = p**scope
            genuinely_accepted = validated = False
            for retry in range(2):
                for category, value in per_attempt.items():
                    charge(day, "A", category, scope * value, f"{job_id}-attempt-{retry}-{category}")
                if retry:
                    charge(day, "A", "correction", 50 * scope, f"{job_id}-correction")
                genuinely_accepted = lead["truth"][retry] < p
                common_delivery_error = world["delivery_error"] < (
                    0.15 if profile == "validator_correlation" else config["validator_common_error_primary"]
                )
                validated = (
                    genuinely_accepted
                    or common_delivery_error
                    or lead["validator"][retry] < config["validator_false_positive_primary"]
                )
                event(
                    day,
                    "delivery",
                    job=job_id,
                    attempt=retry,
                    original_task_id=job_id,
                    scope=scope,
                    validated=validated,
                    true_accepted=genuinely_accepted,
                    configuration=current_arm,
                    recipient=lead["recipient"],
                )
                if validated:
                    break
            observed_successes += int(validated)
            if receives_method:
                diagnostic["retained_uses"] += 1
                charge(day, "B", "network", config["per_retained_use_cents"], f"{job_id}-reuse")
            if validated:
                invoice += sale
                pending.append(
                    {
                        "day": day + lead["delay"],
                        "amount": sale,
                        "kind": "collection",
                        "job": job_id,
                        "hold_until": day + 14,
                    }
                )
                if not genuinely_accepted:
                    pending.append({"day": day + lead["refund_delay"], "amount": sale, "kind": "refund", "job": job_id})
                    failures += 1
                else:
                    accepted += 1
                event(day, "invoice", cents=sale, job=job_id, collection_due=day + lead["delay"])
            else:
                failures += 1
                event(day, "failed-job", job=job_id)
        event(
            day,
            "day-close",
            available_cents=cash - reserve - held(day),
            capacity_unused=capacity,
            observed_jobs=observed_jobs,
            observed_leads=observed_leads,
        )
    total_cost = sum(sum(v.values()) for v in costs.values())
    obligations = sum(p["amount"] for p in pending if p["kind"] == "refund")
    receivable = sum(p["amount"] for p in pending if p["kind"] == "collection")
    net_collections = collections - refunds
    profit = net_collections - total_cost
    if cash != config["seed_capital_cents"] + profit:
        raise AssertionError("cash identity failed")
    if accepted + failures != attempted:
        raise AssertionError("job identity accounting failed")
    if pending:
        raise AssertionError("settlement horizon did not close all invoices/liabilities")
    result = {
        "seed": seed,
        "profile": profile,
        "policy": policy,
        "configuration": arm,
        "choice": choice,
        "collections_cents": collections,
        "refunds_cents": refunds,
        "net_collections_cents": net_collections,
        "invoiced_cents": invoice,
        "costs_cents": costs,
        "total_cost_cents": total_cost,
        "profit_cents": profit,
        "cash_cents": cash,
        "seed_capital_cents": config["seed_capital_cents"],
        "obligations_cents": obligations,
        "receivables_cents": receivable,
        "reserve_cents": reserve,
        "available_cents": cash - reserve - obligations,
        "accepted": accepted,
        "failed": failures,
        "attempted": attempted,
        "quotes": quotes,
        "declined": declined,
        "diagnostics": diagnostic,
        "cost_per_accepted_cents": total_cost / accepted if accepted else None,
        "actual_collections_cents": 0,
        "actual_complete_cost_cents": None,
        "actual_profit_cents": None,
        "events": events if record else [],
    }
    return result


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(q * (len(ordered) - 1))))]


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["profile"] + "/" + row["policy"], []).append(row)
    out = {}
    for key, values in groups.items():
        profits = [r["profit_cents"] / 100 for r in values]
        out[key] = {
            "worlds": len(values),
            "mean_profit_usd": statistics.mean(profits),
            "median_profit_usd": statistics.median(profits),
            "p10_profit_usd": quantile(profits, 0.1),
            "loss_worlds": sum(v < 0 for v in profits),
            "mean_accepted": statistics.mean(r["accepted"] for r in values),
            "mean_complete_cost_usd": statistics.mean(r["total_cost_cents"] / 100 for r in values),
            "mean_collections_usd": statistics.mean(r["net_collections_cents"] / 100 for r in values),
            "mean_cash_usd": statistics.mean(r["cash_cents"] / 100 for r in values),
            "mean_available_usd": statistics.mean(r["available_cents"] / 100 for r in values),
            "mean_B_usd": statistics.mean(sum(r["costs_cents"]["B"].values()) / 100 for r in values),
            "mean_C_usd": statistics.mean(sum(r["costs_cents"]["C"].values()) / 100 for r in values),
            "admissions": sum(r["diagnostics"]["admissions"] for r in values),
            "false_admissions": sum(r["diagnostics"]["false_admissions"] for r in values),
            "gym_attempts": sum(r["diagnostics"]["gym_attempts"] for r in values),
            "prototype_failures": sum(r["diagnostics"]["prototype_failures"] for r in values),
        }
    paired = {}
    for profile in sorted({r["profile"] for r in rows}):
        keyed = {(r["seed"], r["policy"]): r for r in rows if r["profile"] == profile}
        seeds = sorted({key[0] for key in keyed})
        for a, b in (
            ("expert_E", "ordinary_U"),
            ("enhanced_Eplus", "expert_E"),
            ("private_retention", "expert_E"),
            ("shared_retention", "expert_E"),
            ("shared_retention", "library_retention"),
        ):
            differences = [(keyed[s, a]["profit_cents"] - keyed[s, b]["profit_cents"]) / 100 for s in seeds]
            mean = statistics.mean(differences)
            se = statistics.stdev(differences) / math.sqrt(len(differences)) if len(differences) > 1 else 0
            paired[profile + "/" + a + "-" + b] = {
                "mean_usd": mean,
                "monte_carlo_95_interval_usd": [mean - 1.96 * se, mean + 1.96 * se],
                "all_equal": all(x == 0 for x in differences),
                "warning": "conditional simulation uncertainty; not uncertainty in market/model assumptions",
            }
    return {"groups": out, "paired": paired}


def freeze(pilot_path: Path, out: Path) -> None:
    if (out / "FREEZE.json").exists():
        raise ValueError("refusing to overwrite an existing policy freeze")
    config = json.loads((HERE / "protocol.json").read_text())
    pilot = load_pilot(pilot_path)
    selection = {}
    development = []
    for policy in POLICIES:
        candidates = []
        for ratio in config["price_ratios"]:
            for reserve in config["reserve_days_grid"]:
                choice = {"price_ratio": ratio, "reserve_days": reserve}
                rows = [
                    simulate(pilot, config, seed, "reference", policy, choice)
                    for seed in range(config["development_seeds"][0], config["development_seeds"][1] + 1)
                ]
                profits = [float(row["profit_cents"]) for row in rows]
                score = 0.5 * statistics.mean(profits) + 0.5 * quantile(profits, 0.1)
                candidates.append((score, ratio, reserve, choice))
                development.append(
                    {
                        "policy": policy,
                        "choice": choice,
                        "objective_cents": score,
                        "run_summaries": [{k: v for k, v in row.items() if k != "events"} for row in rows],
                    }
                )
        selection[policy] = max(candidates, key=lambda c: (c[0], -c[1], -c[2]))[3]
    if selection["shared_retention"] != selection["library_retention"]:
        raise AssertionError("identical distribution controls must select identically")
    dump(out / "pilot_input.json", pilot)
    dump(out / "development.json", development)
    dump(
        out / "FREEZE.json",
        {
            "schema": config["schema"],
            "source_sha256": sha(Path(__file__)),
            "protocol_sha256": sha(HERE / "protocol.json"),
            "admission_source_sha256": sha(ADMISSION_PATH),
            "pilot_sha256": sha(out / "pilot_input.json"),
            "selection": selection,
            "confirmation_has_run": False,
            "warning": "All money modeled. Four-task posterior extrapolation is assumed, not validated.",
        },
    )
    print(json.dumps({"frozen": str(out / "FREEZE.json"), "selection": selection}, indent=2))


def confirm(out: Path) -> None:
    frozen = json.loads((out / "FREEZE.json").read_text())
    if frozen["source_sha256"] != sha(Path(__file__)) or frozen["protocol_sha256"] != sha(HERE / "protocol.json"):
        raise ValueError("frozen code/protocol changed")
    if frozen["admission_source_sha256"] != sha(ADMISSION_PATH):
        raise ValueError("admission helper changed after freeze")
    if frozen["pilot_sha256"] != sha(out / "pilot_input.json"):
        raise ValueError("pilot input changed")
    if (out / "confirmation.json").exists() or (out / "events.jsonl.gz").exists():
        raise ValueError("refusing to overwrite original confirmation")
    pilot = load_pilot(out / "pilot_input.json")
    config = json.loads((HERE / "protocol.json").read_text())
    rows = []
    event_count = 0
    with (out / "events.jsonl.gz").open("wb") as raw_file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0) as event_file:
            for profile in config["primary_profiles"] + config["stresses"]:
                seeds = (
                    config["confirmation_seeds"] if profile in config["primary_profiles"] else config["stress_seeds"]
                )
                for seed in range(seeds[0], seeds[1] + 1):
                    for policy in POLICIES:
                        row = simulate(pilot, config, seed, profile, policy, frozen["selection"][policy], record=True)
                        for event in row.pop("events"):
                            data = {"seed": seed, "profile": profile, "policy": policy, **event}
                            event_file.write((json.dumps(data, sort_keys=True) + "\n").encode())
                            event_count += 1
                        rows.append(row)
    dump(out / "confirmation.json", rows)
    dump(out / "summary.json", aggregate(rows))
    dump(
        out / "CONFIRMATION_COMPLETE.json",
        {
            "freeze_sha256": sha(out / "FREEZE.json"),
            "histories": len(rows),
            "events": event_count,
            "results_sha256": sha(out / "confirmation.json"),
            "event_stream_sha256": sha(out / "events.jsonl.gz"),
            "actual_customer_collections": 0,
            "actual_research_cost": None,
        },
    )
    print(json.dumps({"histories": len(rows), "events": event_count, "summary": str(out / "summary.json")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "confirm"])
    parser.add_argument("--pilot", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "freeze":
        if args.pilot is None:
            parser.error("freeze needs --pilot")
        freeze(args.pilot, args.out)
    else:
        confirm(args.out)


if __name__ == "__main__":
    main()
