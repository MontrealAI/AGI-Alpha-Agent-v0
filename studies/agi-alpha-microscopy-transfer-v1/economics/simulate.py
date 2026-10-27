from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ARMS = ("E", "E+", "ordinary_library")
ROUTES = {
    "established": (False, False),
    "technical_only": (True, False),
    "coordination_only": (False, True),
    "combined": (True, True),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cents(amount: float) -> int:
    return round(amount * 100)


@dataclass(frozen=True)
class Policy:
    route: str
    price: float
    deposit_fraction: float
    minimum_participants: int
    operate: bool = True


class Ledger:
    def __init__(self, seed: float, reserve: float) -> None:
        self.seed = cents(seed)
        self.cash = self.seed
        self.reserve = cents(reserve)
        self.liabilities = 0
        self.committed = 0
        self.earned = 0
        self.collections = 0
        self.refunds = 0
        self.expenses = {"A": 0, "B": 0, "C": 0}
        self.opportunity = 0
        self.events: list[dict[str, Any]] = []
        self.pending: list[tuple[int, str, int]] = []
        self.day = 0
        self.minimum_available = self.available
        self.counter = 0

    @property
    def available(self) -> int:
        return self.cash - self.liabilities - self.committed - self.reserve

    def record(self, kind: str, amount: int, purpose: str, category: str | None = None) -> None:
        self.counter += 1
        self.minimum_available = min(self.minimum_available, self.available)
        self.events.append(
            {
                "event_id": self.counter,
                "day": self.day,
                "kind": kind,
                "amount_cents": amount,
                "purpose": purpose,
                "category": category,
                "cash_cents": self.cash,
                "unearned_deposits_cents": self.liabilities,
                "committed_cents": self.committed,
                "available_cents": self.available,
                "evidence_type": "simulated",
            }
        )

    def spend(self, amount: float, category: str, purpose: str) -> bool:
        value = cents(amount)
        if value > self.available:
            self.record("liquidity_stop", value, purpose, category)
            return False
        self.cash -= value
        self.expenses[category] += value
        self.record("expense", value, purpose, category)
        return True

    def deposit(self, amount: float, purpose: str) -> None:
        value = cents(amount)
        self.cash += value
        self.collections += value
        self.liabilities += value
        self.record("refundable_deposit", value, purpose)

    def settle(self, deposit: float, earned: float, default: bool, delay: int, purpose: str) -> None:
        prepay, earned_cents = cents(deposit), cents(earned)
        self.liabilities -= prepay
        self.earned += earned_cents
        refund = max(0, prepay - earned_cents)
        self.cash -= refund
        self.refunds += refund
        self.record("milestone_and_refund", refund, purpose)
        due = max(0, earned_cents - prepay)
        if default:
            self.record("bad_debt", due, purpose)
        elif due:
            self.pending.append((self.day + delay, purpose, due))
            self.record("receivable", due, purpose)

    def advance(self, day: int) -> None:
        due = sorted(item for item in self.pending if item[0] <= day)
        self.pending = [item for item in self.pending if item[0] > day]
        for event_day, purpose, amount in due:
            self.day = event_day
            self.cash += amount
            self.collections += amount
            self.record("collection", amount, purpose)
        self.day = day

    def output(self) -> dict[str, Any]:
        total = sum(self.expenses.values())
        net_collections = self.collections - self.refunds
        assert self.cash == self.seed + net_collections - total
        assert self.liabilities == 0 and self.committed == 0
        assert all(value >= 0 for value in self.expenses.values())
        assert not self.pending
        return {
            "seed_capital": self.seed / 100,
            "gross_collections": self.collections / 100,
            "refunds": self.refunds / 100,
            "net_collections": net_collections / 100,
            "earned_revenue": self.earned / 100,
            "bad_debt": (self.earned - net_collections) / 100,
            "A_cash": self.expenses["A"] / 100,
            "B_cash": self.expenses["B"] / 100,
            "C_cash": self.expenses["C"] / 100,
            "opportunity_cost": self.opportunity / 100,
            "settled_cash_contribution": (net_collections - total) / 100,
            "economic_surplus": (net_collections - total - self.opportunity) / 100,
            "ending_cash": self.cash / 100,
            "reserve": self.reserve / 100,
            "available_funds": self.available / 100,
            "minimum_available_funds": self.minimum_available / 100,
            "outstanding_obligations": 0,
            "outstanding_receivables": 0,
            "cash_balance_verified": True,
        }


def world(seed: int, a: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(seed)
    buyers = []
    for index in range(a["potential_buyers"]):
        hours = rng.choice(config["human_reference"]["hours_choices"])
        buyers.append(
            {
                "id": f"buyer-{index}",
                "human_hours": hours,
                "value_ratio": rng.uniform(0.9, 1.5),
                "active": rng.random(),
                "withdraw": rng.random(),
                "fail": rng.random(),
                "default": rng.random(),
                "support": rng.random(),
                "partial": rng.random(),
            }
        )
    return {"buyers": buyers, "common_failure": rng.random()}


def choose_retention(arm: str, a: dict[str, Any], ledger: Ledger) -> tuple[bool, bool]:
    if arm == "E":
        return False, False
    if not ledger.spend(a["assessment_cash"], "B", "one structural admission screen"):
        return False, False
    forecast = a["expected_reuse_count"] * a["forecast_retained_saving_hours"] * a["internal_labor_cash_per_hour"]
    required = a["retention_cash"] + a["upkeep_cash"]
    if forecast <= required:
        return False, False
    if not ledger.spend(required, "B", "additional retention plus horizon upkeep"):
        return False, False
    gym_gain = a["expected_reuse_count"] * a["gym_saving_hours"] * a["internal_labor_cash_per_hour"]
    gym = gym_gain > a["gym_cash"] and ledger.spend(a["gym_cash"], "C", "optional extra practice")
    return True, gym


def simulate(
    config: dict[str, Any], overrides: dict[str, Any], policy: Policy, seed: int, arm: str, keep_events: bool = False
) -> dict[str, Any]:
    a = config["assumptions"] | overrides
    ledger = Ledger(a["seed_capital"], a["reserve"])
    w = world(seed, a, config)
    ledger.record("seed_capital", ledger.seed, "financing, excluded from revenue")
    origin_cost = a["origin_construction_cash"] + a["origin_delivery_cash"]
    origin = ledger.spend(origin_cost, "A", "originating delivery, including necessary construction")
    if origin:
        ledger.opportunity += cents(a["origin_owner_hours"] * a["owner_opportunity_cost_per_hour"])
        ledger.settle(0, a["origin_price"], False, 1, "fictional accepted origin")
        ledger.advance(1)
    if not origin:
        return ledger.output() | {
            "seed": seed,
            "arm": arm,
            "origin_accepted": False,
            "origin_economic_surplus": 0,
            "fresh_economic_surplus": 0,
            "retained": False,
            "gym": False,
            "full_deliveries": 0,
            "partial_deliveries": 0,
            "participants": 0,
            "withdrawals": 0,
            "declined": a["potential_buyers"],
            "liquidity_stops": 1,
            "labor_hours": 0,
            "events": ledger.events if keep_events else [],
        }
    retained, gym = choose_retention(arm, a, ledger)
    ledger.spend(a["routine_overhead"], "A", "operating-period overhead")
    technical, coordination = ROUTES[policy.route]
    constructed = not technical
    stops, full, partial, withdrawals, labor = 0, 0, 0, 0, 0.0
    participants = []
    if policy.operate:
        if technical and not coordination:
            constructed = ledger.spend(a["new_adapter_construction_cash"], "A", "self-funded common adapter")
            stops += int(not constructed)
        for b in w["buyers"]:
            human_price = b["human_hours"] * config["human_reference"]["formatted_business_per_hour"]
            value = human_price * b["value_ratio"]
            outside_utility = max(0.0, value - human_price)
            expected_acceptance = (1 - a["common_failure_probability"]) * (1 - a["final_failure_probability"])
            own_effort = a["customer_effort_hours"] * a["customer_effort_per_hour"]
            expected_utility = expected_acceptance * value - policy.price - own_effort
            expected_utility -= policy.deposit_fraction * policy.price * a["withdrawal_probability"] * 0.1
            if b["active"] < a["active_probability"] and expected_utility >= outside_utility:
                participants.append(b)
        if coordination:
            if len(participants) < policy.minimum_participants:
                participants = []
            elif ledger.spend(a["coordination_cash"], "A", "contingent cohort coordination"):
                if technical:
                    constructed = ledger.spend(a["new_adapter_construction_cash"], "A", "committed common adapter")
                    stops += int(not constructed)
            else:
                participants = []
                stops += 1
        if not constructed:
            participants = []
    for b in participants:
        job = b["id"]
        deposit = policy.price * policy.deposit_fraction
        ledger.deposit(deposit, job)
        ledger.advance(ledger.day + 1)
        if b["withdraw"] < a["withdrawal_probability"]:
            withdrawals += 1
            ledger.settle(deposit, 0, False, 0, job + " withdrawal before adaptation")
            continue
        saving = a["technical_saving_hours"] if technical else 0.0
        saving += a["actual_retained_saving_hours"] if retained else 0.0
        saving += a["gym_saving_hours"] if gym else 0.0
        base_hours = max(0.05, a["baseline_delivery_labor_hours"] - saving)
        model_usd = (
            a["input_tokens_per_attempt"] * config["model_reference"]["input_usd_per_million"]
            + a["output_tokens_per_attempt"] * config["model_reference"]["output_usd_per_million"]
        ) / 1e6
        attempt_cash = model_usd * a["cad_per_usd"] + a["tool_hosting_cash_per_attempt_cad"]
        maximum_hours = base_hours + a["correction_hours"] + a["support_hours"]
        maximum_cash = maximum_hours * a["internal_labor_cash_per_hour"] + 2 * attempt_cash
        if (
            cents(maximum_cash) > ledger.available
            or labor + maximum_hours > a["production_capacity_hours"]
            or ledger.day > a["operating_horizon_days"]
        ):
            stops += 1
            ledger.record("resource_stop", cents(maximum_cash), job)
            ledger.settle(deposit, 0, False, 0, job + " unstarted refund")
            continue
        ledger.committed += cents(maximum_cash)
        ledger.record("reserve_job", cents(maximum_cash), job)
        correction = b["fail"] < a["initial_failure_probability"]
        support = b["support"] < a["support_probability"]
        job_hours = base_hours + int(correction) * a["correction_hours"] + int(support) * a["support_hours"]
        actual_cash = job_hours * a["internal_labor_cash_per_hour"] + (1 + int(correction)) * attempt_cash
        ledger.committed -= cents(maximum_cash)
        assert ledger.spend(actual_cash, "A", job + " full delivery, correction and support")
        labor += job_hours
        ledger.opportunity += cents(a["owner_hours_per_job"] * a["owner_opportunity_cost_per_hour"])
        common_fail = w["common_failure"] < a["common_failure_probability"]
        accepted = not common_fail and b["fail"] >= a["final_failure_probability"]
        partial_accepted = not accepted and not common_fail and b["partial"] < a["partial_contract_probability"]
        full += int(accepted)
        partial += int(partial_accepted)
        earned = policy.price if accepted else policy.price * a["partial_fraction"] if partial_accepted else 0.0
        ledger.settle(deposit, earned, b["default"] < a["default_probability"], a["collection_delay_days"], job)
    ledger.advance(a["settlement_horizon_days"])
    financial = ledger.output()
    origin_surplus = a["origin_price"] - origin_cost - a["origin_owner_hours"] * a["owner_opportunity_cost_per_hour"]
    return financial | {
        "seed": seed,
        "arm": arm,
        "origin_accepted": origin,
        "origin_economic_surplus": origin_surplus,
        "fresh_economic_surplus": financial["economic_surplus"] - origin_surplus,
        "retained": retained,
        "gym": gym,
        "full_deliveries": full,
        "partial_deliveries": partial,
        "participants": len(participants),
        "withdrawals": withdrawals,
        "declined": a["potential_buyers"] - len(participants),
        "liquidity_stops": stops,
        "labor_hours": labor,
        "events": ledger.events if keep_events else [],
    }


def policies(a: dict[str, Any], route: str) -> list[Policy]:
    minimums = a["coordination_minimum_grid"] if ROUTES[route][1] else [1]
    stop = Policy(route, a["price_grid"][0], 0.0, 1, False)
    return [stop] + [
        Policy(route, p, d, m) for p, d, m in itertools.product(a["price_grid"], a["deposit_grid"], minimums)
    ]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        "net_collections",
        "economic_surplus",
        "fresh_economic_surplus",
        "A_cash",
        "B_cash",
        "C_cash",
        "opportunity_cost",
        "full_deliveries",
        "partial_deliveries",
        "participants",
        "withdrawals",
        "bad_debt",
        "refunds",
        "available_funds",
        "minimum_available_funds",
        "labor_hours",
        "settled_cash_contribution",
    )
    answer = {f"mean_{f}": statistics.mean(row[f] for row in rows) for f in fields}
    values = [row["economic_surplus"] for row in rows]
    answer |= {
        "worlds": len(rows),
        "economic_surplus_min": min(values),
        "economic_surplus_max": max(values),
        "positive_worlds": sum(x > 0 for x in values),
        "any_liquidity_stop_worlds": sum(row["liquidity_stops"] > 0 for row in rows),
        "retained_worlds": sum(row["retained"] for row in rows),
        "monte_carlo_mean_interval": [
            statistics.mean(values) - 1.96 * statistics.stdev(values) / math.sqrt(len(values)),
            statistics.mean(values) + 1.96 * statistics.stdev(values) / math.sqrt(len(values)),
        ],
    }
    return answer


def develop(config: dict[str, Any], output: Path) -> None:
    a, seeds = config["assumptions"], config["development_seeds"]
    results = []
    selected = {}
    for route in ROUTES:
        candidates = []
        for policy in policies(a, route):
            rows = [
                simulate(config, {}, policy, seed, "E")
                for seed in range(seeds["start"], seeds["start"] + seeds["count"])
            ]
            score = statistics.mean(row["economic_surplus"] for row in rows)
            candidates.append((score, policy))
            results.append({"policy": asdict(policy), "mean_economic_surplus": score})
        score, chosen = max(
            candidates, key=lambda x: (x[0], -x[1].price, -x[1].deposit_fraction, -x[1].minimum_participants)
        )
        selected[route] = asdict(chosen)
    best_route = max(
        selected, key=lambda name: max(r["mean_economic_surplus"] for r in results if r["policy"]["route"] == name)
    )
    freeze = {
        "protocol": "develop on 24 worlds; freeze before 96 fresh worlds; no confirmation-based policy changes",
        "code_sha256": digest(Path(__file__)),
        "config_sha256": digest(ROOT / "config.json"),
        "selected_by_route": selected,
        "competent_baseline_route": best_route,
        "all_development_scores": results,
        "development_seeds": seeds,
        "confirmation_seed_commitment": config["confirmation_seeds"],
    }
    output.mkdir(exist_ok=True, parents=True)
    (output / "policy_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")


def confirm(config: dict[str, Any], output: Path) -> None:
    freeze = json.loads((output / "policy_freeze.json").read_text())
    assert freeze["code_sha256"] == digest(Path(__file__))
    assert freeze["config_sha256"] == digest(ROOT / "config.json")
    scenarios = {
        "primary_zero_gain": {},
        "conditional_half_hour_reuse": {"forecast_retained_saving_hours": 0.5, "actual_retained_saving_hours": 0.5},
        "conditional_one_hour_reuse": {"forecast_retained_saving_hours": 1.0, "actual_retained_saving_hours": 1.0},
        "false_admission_negative_transfer": {
            "forecast_retained_saving_hours": 0.5,
            "actual_retained_saving_hours": -0.5,
        },
        "thin_demand": {"active_probability": 0.2},
        "common_failure": {"common_failure_probability": 0.3},
        "low_liquidity": {"seed_capital": 350.0},
        "greater_customer_effort": {"customer_effort_hours": 0.5},
        "high_labor_cost": {"internal_labor_cash_per_hour": 129.75},
        "zero_owner_obligation": {"owner_hours_per_job": 0.0},
        "greater_owner_obligation": {"owner_hours_per_job": 1.0},
        "conditional_technical_half_hour": {"technical_saving_hours": 0.5},
    }
    first = config["confirmation_seeds"]["start"]
    n = config["confirmation_seeds"]["count"]
    all_rows, summaries, parity = [], {}, True
    for scenario, overrides in scenarios.items():
        summaries[scenario] = {}
        for route, raw_policy in freeze["selected_by_route"].items():
            policy = Policy(**raw_policy)
            arm_rows = {}
            for arm in ARMS:
                rows = [simulate(config, overrides, policy, seed, arm) for seed in range(first, first + n)]
                arm_rows[arm] = rows
                summaries[scenario][route + "/" + arm] = summarize(rows)
                for row in rows:
                    all_rows.append(
                        {"scenario": scenario, "route": route, **{k: v for k, v in row.items() if k != "events"}}
                    )
            parity &= all(
                {k: v for k, v in left.items() if k != "arm"} == {k: v for k, v in right.items() if k != "arm"}
                for left, right in zip(arm_rows["E+"], arm_rows["ordinary_library"])
            )
            delta = [p["economic_surplus"] - b["economic_surplus"] for p, b in zip(arm_rows["E+"], arm_rows["E"])]
            summaries[scenario][route + "/paired_increment"] = {
                "mean": statistics.mean(delta),
                "min": min(delta),
                "max": max(delta),
            }
    with (output / "confirmation.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    primary_policy = Policy(**freeze["selected_by_route"][freeze["competent_baseline_route"]])
    receipt = simulate(config, {}, primary_policy, first, "E+", keep_events=True)
    (output / "example_ledger.json").write_text(json.dumps(receipt, indent=2) + "\n")
    a = config["assumptions"]
    thresholds = []
    for uses in [0, 1, 2, 4, 8, 16]:
        cost = a["assessment_cash"] + a["retention_cash"] + a["upkeep_cash"]
        thresholds.append(
            {
                "realized_reuses": uses,
                "additional_B_cost": cost,
                "minimum_cash_labor_hours_saved_per_use": cost / (uses * a["internal_labor_cash_per_hour"])
                if uses
                else None,
                "status": "conditional threshold, not measured time saving",
            }
        )
    result = {
        "evidence_type": "simulated conditional scenarios",
        "currency": config["currency"],
        "source_sha256": freeze["code_sha256"],
        "policy_freeze_sha256": digest(output / "policy_freeze.json"),
        "world_rows": len(all_rows),
        "ordinary_library_exact_parity": parity,
        "all_cash_balances_verified": all(row["cash_balance_verified"] for row in all_rows),
        "actual_execution": config["actual_execution"],
        "competent_baseline_route": freeze["competent_baseline_route"],
        "thresholds": thresholds,
        "scenarios": summaries,
    }
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "rows": len(all_rows),
                "parity": parity,
                "best_route": freeze["competent_baseline_route"],
                "primary": summaries["primary_zero_gain"][freeze["competent_baseline_route"] + "/E"],
                "increment": summaries["primary_zero_gain"][freeze["competent_baseline_route"] + "/paired_increment"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["develop", "confirm"])
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    settings = json.loads((ROOT / "config.json").read_text())
    (develop if args.phase == "develop" else confirm)(settings, args.output)
