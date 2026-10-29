# SPDX-License-Identifier: Apache-2.0
"""Offline conditional-settlement experiment using existing delivery and accounting helpers.

No payment integration, external authority, live demand, or production escrow is provided.
The custodian is an explicit idealized assumption, not a claimed deployed service.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import io
import json
import random
import statistics
import time
from pathlib import Path
from typing import Any

from .delta_acceptance import verify_delta
from .delta_delivery import build_delta, make_request
from .operate import Recorder, alternative_costs, balances, canonical, digest, money

ROOT = Path(__file__).resolve().parent


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def dump(path: Path, value: Any) -> None:
    path.write_bytes(canonical(value) + b"\n")


class ConditionalExchange:
    """Finite simulated custodian: locked buyer funds never become seller working capital."""

    def __init__(self, request_hash: str, price: int) -> None:
        if not isinstance(request_hash, str) or len(request_hash) != 64:
            raise ValueError("Expected a request digest")
        if type(price) is not int or price <= 0:
            raise ValueError("Price must be positive integer micro-units")
        self.request_hash, self.price = request_hash, price
        self.state = "QUOTED"
        self._packet: bytes | None = None
        self._inputs: tuple[str, str, dict[str, Any]] | None = None

    def lock(self, buyer_funds: int) -> None:
        if self.state != "QUOTED" or type(buyer_funds) is not int or buyer_funds < self.price:
            raise ValueError("Invalid, replayed, or unfunded lock")
        self.state = "LOCKED"

    def prepare(self, before: str, delta: str, request: dict[str, Any], packet: dict[str, Any]) -> None:
        if self.state != "LOCKED":
            raise ValueError("No locked buyer funds")
        snapshot = json.loads(canonical({"before": before, "delta": delta, "request": request, "packet": packet}))
        inputs = {key: snapshot[key] for key in ("before", "delta", "request")}
        if digest(inputs) != self.request_hash:
            raise ValueError("Wrong original request")
        verdict = verify_delta(snapshot["before"], snapshot["delta"], snapshot["packet"], snapshot["request"])
        if verdict["verdict"] != "PASS_IN_SCOPE":
            raise ValueError("Independent output acceptance rejected")
        self._packet = canonical(snapshot["packet"])
        self._inputs = snapshot["before"], snapshot["delta"], snapshot["request"]
        self.state = "PREPARED"

    def abort(self) -> int:
        if self.state not in {"LOCKED", "PREPARED"}:
            raise ValueError("Cannot refund this state")
        self.state, self._packet, self._inputs = "REFUNDED", None, None
        return self.price

    def commit(self) -> dict[str, Any]:
        if self.state != "PREPARED" or self._packet is None or self._inputs is None:
            raise ValueError("No accepted artifact or exchange already consumed")
        packet = json.loads(self._packet)
        before, delta, request = self._inputs
        if verify_delta(before, delta, packet, request)["verdict"] != "PASS_IN_SCOPE":
            raise ValueError("Prepared artifact changed")
        receipt = {"request_hash": self.request_hash, "packet_hash": hashlib.sha256(self._packet).hexdigest(),
                   "output_hash": sha(packet["native_package"]["output_csv"]), "amount": self.price,
                   "basis": "simulated_custodian_atomic_transition", "actual_money": False}
        receipt["id"] = digest(receipt)
        self.state = "COMMITTED"
        return {"receipt": receipt, "output": packet["native_package"]["output_csv"]}


def _csv(headers: list[str], rows: list[list[str]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerows([headers, *rows])
    return stream.getvalue()


def delivery_case(seed: int, buyer: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Synthetic update-only cohort, not the original full-snapshot campaign's cases."""
    rng = random.Random(seed * 1000003 + buyer["request_id"])
    rows = [[f"K{n}", f"Item-{n}-é", f"{rng.randrange(1, 99)}.00", f"local-{n}"] for n in range(rng.randint(8, 30))]
    chosen = rng.sample(rows, rng.randint(1, len(rows) - 1))
    updates = [[row[0], f"{rng.randrange(100, 199)}.25"] for row in chosen]
    if buyer["malformed"]:
        updates.append(updates[0][:])
    request = make_request(["sku"], ["price"], ["price"], {"supplier_code": "sku", "new_price": "price"})
    return _csv(["sku", "name", "price", "note"], rows), _csv(["supplier_code", "new_price"], updates), request


def buyers(seed: int, scenario: str, policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[int]]:
    """Inherited distributions, with all jobs requesting the fixed update-only offering."""
    rng = random.Random(seed)
    settings = policy["scenarios"][scenario]
    result = []
    for period, start in enumerate([0, 60, 120, 240]):
        count = max(1, round(policy["arrivals_per_period"] * settings["demand_factor"] * rng.uniform(.8, 1.2)))
        for n in range(count):
            entry = {"request_id": period * 1000 + n, "period": period, "day": start + rng.randint(1, 55),
                     "buyer_value": rng.uniform(12, 90) * settings["value_factor"],
                     "owner_hour_value": rng.uniform(18, 55), "conventional_hours": rng.uniform(.18, .90),
                     "direct_ai_hours": rng.uniform(.12, .55), "human_hours": rng.uniform(.25, 1.0),
                     "urgency_cost": rng.uniform(0, 6), "switching": rng.uniform(0, 3),
                     "payment_draw": rng.random(), "warranty_draw": rng.random(), "supplier_draw": rng.random(),
                     "malformed": rng.random() < .035, "delay": rng.choice([0, 3, 7, 14, 28, 75]),
                     "lock_draw": rng.random()}
            if scenario == "equal_tool_parity":
                entry.update(conventional_hours=.02, direct_ai_hours=.01, switching=0.0)
            result.append(entry)
    capacity = [max(1, round(policy["capacity_per_period"] * settings["capacity_factor"] * rng.uniform(.85, 1.1)))
                for _ in range(4)]
    return sorted(result, key=lambda item: (item["day"], item["request_id"])), capacity


def simulate(directory: Path, seed: int, scenario: str, contract: str, policy: dict[str, Any],
             *, lock_failure: float = 0.0, friction: int | None = None) -> dict[str, Any]:
    """Execute actual fixed delivery code; project modeled business outcomes, not actual profit."""
    if contract not in {"postpaid", "conditional"} or not 0 <= lock_failure <= 1:
        raise ValueError("Unknown contract or invalid liquidity stress")
    directory.mkdir(parents=True, exist_ok=False)
    artifact_dir = directory / "artifacts"
    artifact_dir.mkdir()
    rec = Recorder(directory, f"settlement-probe/{scenario}/{seed}/{contract}")
    rec.add("opening_capital", 0, money(policy["opening_capital_usd"]))
    rec.add("reserve", 0, money(policy["protected_closeout_usd"]), reserve_kind="closeout")
    rec.resource(0, "inherited-development", 1, policy["base_development_micro_usd"], "allowance", "development")
    rec.resource(0, "incremental-development", 1, policy["incremental_development_micro_usd"], "allowance", "development")
    settings = policy["scenarios"][scenario]
    population, capacities = buyers(seed, scenario, policy)
    dump(directory / "cohort.json", {"buyers": population, "capacity": capacities})
    pending: list[tuple[int, int, str, str, int, bool]] = []
    serial = 0
    accepted = attempted = collected = refused_locks = 0
    seen = orders = 0
    price = policy["price_micro_usd"]
    cost_scale = settings["supplier_price_multiplier"]
    operator_friction = policy["buyer_lock_friction_micro_usd"] if friction is None else friction
    if type(operator_friction) is not int or operator_friction < 0:
        raise ValueError("Friction must be nonnegative integer micro-units")
    costs: dict[str, int] = {}
    request_costs: dict[str, int] = {}

    def charge(day: int, order: str, label: str, amount: int) -> None:
        rec.resource(day, f"{order}/{label}", 1, amount, "modeled-activity", "delivery", order_id=order)
        costs[label] = costs.get(label, 0) + amount
        request_costs[order] = request_costs.get(order, 0) + amount

    def stage(day: int, order: str, label: str) -> None:
        charge(day, order, label, round(policy["activities"][label] * cost_scale))

    def queue(day: int, kind: str, order: str, amount: int, flag: bool = False) -> None:
        nonlocal serial
        serial += 1
        heapq.heappush(pending, (day, serial, kind, order, amount, flag))

    def outstanding(order: str) -> int:
        total = 0
        for event in rec.events:
            if event["order_id"] == order:
                if event["type"] == "earned":
                    total += event["amount_micro_usd"]
                elif event["type"] in {"collect", "writeoff"}:
                    total -= event["amount_micro_usd"]
                elif event["type"] == "revenue_reversal":
                    total -= event["details"]["receivable_reduction_micro_usd"]
        return total

    def settle(until: int) -> None:
        nonlocal collected
        while pending and pending[0][0] <= until:
            day, _, kind, order, amount, flag = heapq.heappop(pending)
            if kind == "collect":
                due = outstanding(order)
                if due:
                    rec.add("writeoff" if flag else "collect", day, due, order_id=order)
                    collected += not flag
            elif kind == "support":
                stage(day, order, "support")
            elif kind == "warranty":
                if flag:
                    reduction = min(amount, outstanding(order))
                    rec.add("revenue_reversal", day, amount, order_id=order, receivable_reduction_micro_usd=reduction)
                    if amount > reduction:
                        rec.add("refund", day, amount - reduction, order_id=order)
                    stage(day, order + "/warranty", "support")
                rec.add("release_reserve", day, amount, order_id=order, reserve_kind="warranty")

    for period in range(4):
        used = 0
        share = orders / max(seen, 1)
        competitor_price = max(settings["competitor_floor"], settings["competitor_initial_price"] -
                               (settings["adoption_response"] * share if period else 0))
        competitor_quality = min(1.0, settings["competitor_quality"] + period * settings["quality_adoption"])
        for buyer in population:
            if buyer["period"] != period:
                continue
            day = buyer["day"]
            settle(day)
            seen += 1
            order = str(buyer["request_id"])
            facts = balances(rec.events)
            available = facts["cash_micro_usd"] - facts["liability_micro_usd"] - facts["reserves_micro_usd"]
            if used >= capacities[period] or available < money(policy["protected_closeout_usd"]):
                rec.add("decline", day, order_id=order, reason="capacity_or_reserve")
                continue
            stage(day, order, "acquisition")
            alternatives = alternative_costs(buyer, competitor_price, competitor_quality)
            # Postpaid keeps the inherited conservative upfront price comparison, even in default worlds.
            # Conditional exchange adds an explicit, nonzero participation/trust/liquidity cost.
            all_in = price / 1e6 + .02 * buyer["buyer_value"] + (operator_friction / 1e6 if contract == "conditional" else 0)
            rec.add("quote", day, order_id=order, alternatives=alternatives, all_in=all_in, price=price)
            if all_in >= min(alternatives.values()):
                rec.add("buyer_decline", day, order_id=order)
                continue
            if contract == "conditional" and buyer["lock_draw"] < lock_failure:
                refused_locks += 1
                rec.add("lock_refused", day, order_id=order, reason="modeled_liquidity_or_trust_failure")
                continue
            before, delta, request = delivery_case(seed, buyer)
            request_hash = digest({"before": before, "delta": delta, "request": request})
            broker = ConditionalExchange(request_hash, price)
            if contract == "conditional":
                broker.lock(price)
                rec.add("external_escrow_locked", day, order_id=order, external_amount=price, request_hash=request_hash)
                fee = policy["broker_fee_fixed_micro_usd"] + price * policy["broker_fee_basis_points"] // 10000
                charge(day, order, "custodian_fee", fee)
            used += 1
            orders += 1
            stage(day, order, "production")
            if buyer["supplier_draw"] < settings["supplier_failure"]:
                rec.add("delivery_failed", day, order_id=order, reason="inherited_supplier_outage")
                if contract == "conditional":
                    rec.add("external_escrow_refunded", day, order_id=order, external_amount=broker.abort())
                continue
            attempted += 1
            started = time.perf_counter_ns()
            packet: dict[str, Any] | None = None
            try:
                packet = build_delta(before, delta, request)
                verdict = verify_delta(before, delta, packet, request)
            except (ValueError, TypeError, KeyError) as error:
                verdict = {"verdict": "REJECTED", "failures": [str(error)]}
            elapsed = time.perf_counter_ns() - started
            artifact = {"before": before, "delta": delta, "request": request, "packet": packet,
                        "acceptance": verdict, "elapsed_ns": elapsed}
            artifact_path = artifact_dir / (order + ".json")
            dump(artifact_path, artifact)
            stage(day, order, "verification")
            byte_days = artifact_path.stat().st_size * max(0, 360 - day)
            charge(day, order, "artifact_retention", (byte_days + 1048575) // 1048576)
            rec.add("artifact", day, order_id=order, path="artifacts/" + order + ".json",
                    artifact_hash=hashlib.sha256(artifact_path.read_bytes()).hexdigest(), accepted=verdict["verdict"] == "PASS_IN_SCOPE")
            if verdict["verdict"] != "PASS_IN_SCOPE" or packet is None:
                stage(day, order, "correction")
                rec.add("acceptance_refused", day, order_id=order)
                if contract == "conditional":
                    rec.add("external_escrow_refunded", day, order_id=order, external_amount=broker.abort())
                continue
            accepted += 1
            if contract == "conditional":
                broker.prepare(before, delta, request, packet)
                commit = broker.commit()
                receipt = commit["receipt"]
                rec.add("settlement_commit", day, order_id=order, receipt=receipt)
                rec.add("earned", day, price, order_id=order, receipt_id=receipt["id"])
                rec.add("collect", day, price, order_id=order, receipt_id=receipt["id"])
                rec.add("delivery", day, order_id=order, receipt_id=receipt["id"], output_hash=sha(commit["output"]))
                collected += 1
            else:
                rec.add("delivery", day, order_id=order, output_hash=sha(packet["native_package"]["output_csv"]))
                rec.add("earned", day, price, order_id=order)
                default = buyer["payment_draw"] < settings["default_rate"]
                queue(day + (max(14, buyer["delay"]) if default else buyer["delay"]), "collect", order, price, default)
            rec.add("reserve", day, price, order_id=order, reserve_kind="warranty")
            queue(day + 2, "support", order, 0)
            queue(day + 7, "warranty", order, price, buyer["warranty_draw"] < settings["warranty_rate"])
        end = [60, 120, 180, 300][period]
        settle(end)
        stage(end, f"period-{period}", "maintenance")
    settle(360)
    journal_bytes = rec.path.stat().st_size
    charge(360, "campaign", "journal_retention", (journal_bytes * 360 + 1048575) // 1048576)
    facts = balances(rec.events)
    cash_free = facts["cash_micro_usd"] - facts["reserves_micro_usd"] - facts["liability_micro_usd"]
    result = {"scenario": scenario, "seed": seed, "contract": contract, "accepted": accepted,
              "artifact_attempts": attempted, "collected_orders": collected, "refused_locks": refused_locks,
              "population": len(population), "modeled_balances": facts, "modeled_free_cash": cash_free,
              "model_profit_usd": facts["profit_micro_usd"] / 1e6, "cost_by_activity": costs,
              "pending": [list(item) for item in pending], "journal_head": rec.events[-1]["hash"],
              "actual_revenue": 0, "actual_complete_cost": None, "full_flywheel": "UNESTABLISHED",
              "autonomous_invention": False, "fresh_successor_benefit": "UNMEASURED",
              "native_accounting_anchor": "not imported into signed production Journal",
              "lock_failure": lock_failure, "buyer_friction_micro_usd": operator_friction}
    dump(directory / "summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--policy", default=str(ROOT / "settlement_probe_policy.json"))
    parser.add_argument("--seed-file", required=True)
    parser.add_argument("--scenario", choices=["all", "reference", "strategic_default", "equal_tool_parity"], default="all")
    parser.add_argument("--lock-failure", type=float, default=0)
    parser.add_argument("--friction-micro-usd", type=int)
    args = parser.parse_args()
    policy = json.loads(Path(args.policy).read_bytes())
    seeds = json.loads(Path(args.seed_file).read_bytes())["seeds"]
    if not seeds or len(seeds) > 128 or len(set(seeds)) != len(seeds) or any(type(seed) is not int for seed in seeds):
        parser.error("Use 1..128 distinct integer seeds")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    dump(output / "policy.json", policy)
    dump(output / "seed-file.json", {"seeds": seeds})
    results = []
    scenarios = list(policy["scenarios"]) if args.scenario == "all" else [args.scenario]
    for scenario in scenarios:
        for seed in seeds:
            for contract in ["postpaid", "conditional"]:
                results.append(simulate(output / f"{scenario}-{seed}-{contract}", seed, scenario, contract, policy,
                                        lock_failure=args.lock_failure, friction=args.friction_micro_usd))
    aggregates = []
    for scenario in scenarios:
        for contract in ["postpaid", "conditional"]:
            selected = [row for row in results if row["scenario"] == scenario and row["contract"] == contract]
            aggregates.append({"scenario": scenario, "contract": contract, "worlds": len(selected),
                               "mean_model_profit_usd": statistics.mean(row["model_profit_usd"] for row in selected),
                               "min_model_profit_usd": min(row["model_profit_usd"] for row in selected),
                               "profitable_worlds": sum(row["model_profit_usd"] > 0 for row in selected),
                               "accepted": sum(row["accepted"] for row in selected),
                               "collected_orders": sum(row["collected_orders"] for row in selected)})
    report = {"scope": "conditional finite economic model; no demand calibration or statistical confirmation",
              "source_freeze_required_for_confirmation": True, "aggregates": aggregates,
              "worlds": results, "actual_commercial_success": False, "full_flywheel": "UNESTABLISHED"}
    dump(output / "REPORT.json", report)
    print(json.dumps({"output": str(output), "aggregates": aggregates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
