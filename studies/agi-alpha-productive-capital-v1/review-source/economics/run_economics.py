from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCALE = 1_000_000
FAMILIES = ("release_assurance", "rollout_planning", "bilingual_dossier")


def money(x):
    return int((Decimal(str(x)) * SCALE).to_integral_value(rounding=ROUND_HALF_UP))


def portion(x, r):
    return int((Decimal(x) * Decimal(str(r))).to_integral_value(rounding=ROUND_HALF_UP))


def dollars(x):
    return round(x / SCALE, 6)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def probability(seed, *parts):
    return int(hashlib.sha256(("|".join([seed, *map(str, parts)])).encode()).hexdigest()[:13], 16) / (16**13)


def load_bridge(path):
    b = json.loads(Path(path).read_text())
    rows = b.get("joint_rows", b.get("joint_metrics", []))
    if not rows:
        raise ValueError("Observed bridge requires joint_rows; shared timings must not be summed over families")
    by = {}
    for row in rows:
        n = row.get("projects", row.get("joint_runs"))
        cpu = row.get("total_cpu_ms")
        wall = row.get("total_wall_ms")
        if not isinstance(n, (int, float)) or n <= 0 or cpu is None or wall is None:
            raise ValueError("Missing observed joint project count or CPU/wall measurement")
        by[(int(row["cycle"]), row["arm"])] = {
            "projects": n,
            "cpu_ms": float(cpu) / n,
            "wall_ms": float(wall) / n,
            "accepted_joint": row.get("accepted_joint", row.get("accepted")),
            "work_units": row.get("work_units"),
        }
    for c in (0, 1, 2, 3):
        for arm in ("conventional_cache", "flywheel"):
            if (c, arm) not in by:
                raise ValueError(f"Missing paired bridge row {c}/{arm}")
    changed = [c for c in (2, 3)]
    savings = sum(by[(c, "conventional_cache")]["cpu_ms"] - by[(c, "flywheel")]["cpu_ms"] for c in changed) / len(
        changed
    )
    return b, by, savings


def project_cost(cfg, key):
    p = cfg["projects"][key]
    r = cfg["rates"]
    return money(
        p.get("construction_cash_usd", 0)
        + p.get("construction_engineer_hours", 0) * r["software_engineer_usd_per_hour"]
        + p.get("construction_verification_hours", 0) * r["reviewer_usd_per_hour"]
        + p.get("construction_model_tool_usd", 0)
    )


def maintenance_cost(cfg, key):
    p = cfg["projects"][key]
    return money(
        p.get("maintenance_cash_usd_per_cycle", 0)
        + p.get("maintenance_engineer_hours_per_cycle", 0) * cfg["rates"]["software_engineer_usd_per_hour"]
    )


class Model:
    def __init__(self, cfg, scenario, policy, bridge, metrics, saving):
        self.c = cfg
        self.s = scenario
        self.policy = policy
        self.bridge = bridge
        self.metrics = metrics
        self.cpu_saving_ms = saving
        self.route = dict(cfg["routes"][scenario.get("route", cfg["base_route"])])
        for k in ("gas_usd_per_order", "conversion_spread_fraction", "volatility_haircut_fraction"):
            if k in scenario:
                self.route[k] = scenario[k]
        self.fail = scenario.get("failure_probability", cfg["operational_attempt_failure_probability"])
        self.attention = scenario.get("attention_multiplier", 1)
        self.prices = {f: cfg["families"][f]["price_usd"] * scenario.get("price_multiplier", 1) for f in FAMILIES}
        self.demand = scenario.get("demand_sets", cfg["demand_sets"])
        self.weights = scenario.get("collection_weights", cfg["business"]["receivable_collection_weights"])
        self.cash = self.ar = self.collateral = self.ap = self.asset = 0
        self.operating_paid = self.operating_accrued = self.net_external = self.invested = 0
        self.reserved_profit = 0
        self.events = []
        self.ledger = []
        self.class_rows = []
        self.pending = []
        self.bonds = []
        self.assets = {}
        self.ever = set()
        self.prefix = {"scenario": scenario["id"], "policy_fraction": policy, "evidence_class": "SIMULATED"}
        self.event(
            0,
            "external_initial_capital",
            cash=money(cfg["initial_external_capital_usd"]),
            amount=money(cfg["initial_external_capital_usd"]),
        )

    def event(self, cycle, kind, cash=0, ar=0, collateral=0, asset=0, ap=0, amount=0, **extra):
        self.cash += cash
        self.ar += ar
        self.collateral += collateral
        self.asset += asset
        self.ap += ap
        if min(self.cash, self.ar, self.collateral, self.asset, self.ap) < 0:
            raise AssertionError((kind, self.cash, self.ar, self.collateral, self.asset, self.ap))
        self.events.append(
            dict(
                self.prefix,
                cycle=cycle,
                event=kind,
                amount_usd=dollars(amount),
                cash_delta_usd=dollars(cash),
                receivable_delta_usd=dollars(ar),
                collateral_delta_usd=dollars(collateral),
                capital_asset_delta_usd=dollars(asset),
                payable_delta_usd=dollars(ap),
                cash_balance_usd=dollars(self.cash),
                **extra,
            )
        )

    def pay_operating(self, cycle, amount, kind, family=None):
        paid = min(amount, max(0, self.cash - self.reserved_profit))
        self.operating_accrued += amount
        self.operating_paid += paid
        self.event(cycle, kind, cash=-paid, ap=amount - paid, amount=amount, family=family)
        return paid

    def unit(self, f, cycle, child=False):
        x = self.c["families"][f]
        r = self.c["rates"]
        biz = self.c["business"]
        a = self.attention
        setup = x["setup_minutes_per_order"] * a
        att = (x["supervision_minutes_per_attempt"] + x["verification_minutes_per_attempt"]) * a
        retry = x["retry_correction_minutes"] * a
        support = x["support_minutes_per_accepted"] * a
        arm = "flywheel" if child else "conventional_cache"
        cpu = self.metrics[(min(cycle - 1, 3), arm)]["cpu_ms"] / 3
        native_cost = cpu / 3_600_000 * biz["kernel_compute_usd_per_cpu_hour"]
        attempt = (
            (
                x["supervision_minutes_per_attempt"] * a * r["operator_usd_per_hour"]
                + x["verification_minutes_per_attempt"] * a * r["reviewer_usd_per_hour"]
            )
            / 60
            + x["model_tool_usd_per_attempt"]
            + biz["storage_usd_per_attempt"]
            + native_cost
        )
        order = (
            setup * r["operator_usd_per_hour"] / 60 + biz["acquisition_usd_per_order"] + self.route["gas_usd_per_order"]
        )
        accepted = (
            support * r["operator_usd_per_hour"] / 60
            + biz["delivery_usd_per_accepted"]
            + biz["processing_fee_usd_per_accepted"]
            + self.prices[f] * biz["processing_fee_fraction"]
        )
        return {
            "attempt": money(attempt),
            "order": money(order),
            "accepted": money(accepted),
            "retry": money(retry * r["software_engineer_usd_per_hour"] / 60),
            "setup_min": setup,
            "attempt_min": att,
            "retry_min": retry,
            "support_min": support,
            "native_cpu_ms_per_family_share": cpu,
            "native_compute_usd_unrounded": native_cost,
        }

    def receive(self, cycle, include_current=False):
        got = refunds = defaults = fees = 0
        for q in self.pending:
            if q["due"] != cycle or q.get("done"):
                continue
            if not include_current and q["issued"] == cycle:
                continue
            q["done"] = True
            amount = q["amount"]
            if q["kind"] == "default":
                defaults += amount
                self.event(cycle, "receivable_default_writeoff", ar=-amount, amount=amount, family=q["family"])
                continue
            self.event(cycle, "external_worker_collection", cash=amount, ar=-amount, amount=amount, family=q["family"])
            got += amount
            conversion = portion(amount, self.route["volatility_haircut_fraction"])
            spread = portion(amount - conversion, self.route["conversion_spread_fraction"])
            if conversion + spread:
                self.pay_operating(cycle, conversion + spread, "conversion_and_volatility_cost", q["family"])
                fees += conversion + spread
            refund = portion(amount, self.c["business"]["refund_fraction_of_collections"])
            self.event(cycle, "customer_refund", cash=-refund, amount=refund, family=q["family"])
            refunds += refund
            self.net_external += amount - refund
        return got, refunds, defaults, fees

    def invoice(self, cycle, f):
        price = money(self.prices[f])
        entitlement = portion(price, self.route["worker_entitlement_fraction"])
        self.event(
            cycle,
            "invoice_worker_entitlement",
            ar=entitlement,
            amount=entitlement,
            family=f,
            customer_gross_invoice_usd=dollars(price),
            other_participant_allocation_usd=dollars(price - entitlement),
        )
        default = portion(entitlement, self.c["business"]["default_fraction"])
        collectible = entitlement - default
        allocated = 0
        for lag, w in enumerate(self.weights):
            amount = collectible - allocated if lag == len(self.weights) - 1 else portion(collectible, w)
            allocated += amount
            if amount:
                self.pending.append(
                    {"issued": cycle, "due": cycle + lag, "kind": "collection", "amount": amount, "family": f}
                )
        if default:
            self.pending.append(
                {
                    "issued": cycle,
                    "due": cycle + len(self.weights) - 1,
                    "kind": "default",
                    "amount": default,
                    "family": f,
                }
            )
        return price, entitlement

    def next_plan(self, target_sets=None):
        c = self.c
        plan = c["next_cycle_plan"]
        n = plan["accepted_sets"] if target_sets is None else target_sets
        operating = money(c["business"]["fixed_operating_usd_per_cycle"]) + money(
            c["business"]["fixed_administration_minutes_per_cycle"] * c["rates"]["operator_usd_per_hour"] / 60
        )
        collateral = 0
        minutes = c["business"]["fixed_administration_minutes_per_cycle"]
        attempts = 0
        current_provider_cap = self.s.get("provider_attempt_limit", c["provider_attempt_limit"])
        existing_capacity_maintenance = 0
        for key, state in self.assets.items():
            if state["remaining_life"] <= 0:
                continue
            if key == "extra-execution-block":
                current_provider_cap += c["projects"][key]["extra_provider_attempts_per_cycle"]
            if key != plan["new_capability"]:
                extra_maintenance = maintenance_cost(c, key)
                operating += extra_maintenance
                existing_capacity_maintenance += extra_maintenance
                minutes += 60 * c["projects"][key].get("maintenance_engineer_hours_per_cycle", 0)
        by = {}
        for f in FAMILIES:
            u = self.unit(f, min(c["cycles"], max(1, len(self.ledger) + 1)), False)
            v = n * (u["order"] + 2 * u["attempt"] + u["retry"] + u["accepted"])
            by[f] = v
            operating += v
            collateral += n * money(self.prices[f] * self.route["collateral_fraction"])
            minutes += n * (u["setup_min"] + 2 * u["attempt_min"] + u["retry_min"] + u["support_min"])
            attempts += 2 * n
        cap = project_cost(c, plan["new_capability"])
        maint = maintenance_cost(c, plan["new_capability"])
        project = c["projects"][plan["new_capability"]]
        construction_minutes = 60 * (
            project.get("construction_engineer_hours", 0) + project.get("construction_verification_hours", 0)
        )
        maintenance_minutes = 60 * project.get("maintenance_engineer_hours_per_cycle", 0)
        minutes += construction_minutes + maintenance_minutes
        elapsed = (
            attempts * c["business"]["elapsed_hours_per_attempt"]
            + (c["business"]["fixed_administration_minutes_per_cycle"] + construction_minutes + maintenance_minutes)
            / 60
        )
        tests = {
            "service_cash_budget": operating + maint <= money(c["per_cycle_cash_spend_budget_usd"]),
            "human_minutes": minutes <= c["human_attention_budget_minutes"],
            "elapsed_hours": elapsed <= c["elapsed_budget_hours"],
            "provider_attempts": attempts <= current_provider_cap,
        }
        return {
            "construction": cap,
            "operating": operating,
            "collateral": collateral,
            "maintenance": maint,
            "total": cap + operating + collateral + maint,
            "family_working_capital": by,
            "target_orders_per_family": n,
            "acceptance_guaranteed": False,
            "attempt_budget": attempts,
            "human_minutes": minutes,
            "elapsed_hours": elapsed,
            "budget_feasible": all(tests.values()),
            "budget_checks": tests,
            "next_provider_cap": current_provider_cap,
            "existing_capacity_maintenance": existing_capacity_maintenance,
            "coverage_is_execution_authority": False,
            "construction_scope": "Stipulated fresh child commissioning; no claim that a currently owned child must be bought again",
        }

    def offers(self, cycle, available):
        c = self.c
        left = c["cycles"] - cycle
        life = min(left, c["projects"]["dependency-repair-v1"]["life_cycles"])
        uses = min(
            self.s.get("child_reuse_limit", c["projects"]["dependency-repair-v1"]["finite_reuses"]),
            sum(self.demand[cycle : cycle + life]),
        )
        saving_usd = self.cpu_saving_ms / 3_600_000 * c["business"]["kernel_compute_usd_per_cpu_hour"] * uses
        child_cost = project_cost(c, "dependency-repair-v1")
        child_maint = maintenance_cost(c, "dependency-repair-v1") * life
        child_npv = saving_usd - dollars(child_cost + child_maint)
        child_admit = left > 0 and child_npv >= 0
        if self.s.get("force_research") and left > 0:
            child_admit = True
        child = {
            "id": "dependency-repair-v1",
            "kind": "capability",
            "cost": child_cost,
            "npv_usd": round(child_npv, 6),
            "benefit_usd": round(saving_usd, 9),
            "future_reuses": uses,
            "admissible": child_admit,
            "reason": (
                "Explicit compelled research, not positive economic return"
                if self.s.get("force_research")
                else (
                    "Measured compute savings cover modeled construction and maintenance"
                    if child_admit
                    else "HOLD: strongest conventional reuse ties scope and measured CPU does not repay construction/maintenance"
                )
            ),
            "evidence_class": "measured CPU effect; estimated costs; assumed future reuse",
        }
        units = [self.unit(f, min(cycle + 1, c["cycles"]), False) for f in FAMILIES]
        mean_cost = (
            sum(
                u["order"]
                + u["attempt"]
                + portion(u["attempt"] + u["retry"], self.fail)
                + portion(u["accepted"], 1 - self.fail**2)
                for u in units
            )
            / 3
            / (1 + self.fail)
            / SCALE
        )
        mean_min = (
            sum(
                u["setup_min"]
                + u["attempt_min"]
                + self.fail * (u["attempt_min"] + u["retry_min"])
                + (1 - self.fail**2) * u["support_min"]
                for u in units
            )
            / 3
            / (1 + self.fail)
        )
        fixed = (
            c["business"]["fixed_operating_usd_per_cycle"]
            + c["business"]["fixed_administration_minutes_per_cycle"] * c["rates"]["operator_usd_per_hour"] / 60
        )
        cap_other = min(
            max(0, c["per_cycle_cash_spend_budget_usd"] - fixed) / mean_cost,
            max(0, c["human_attention_budget_minutes"] - c["business"]["fixed_administration_minutes_per_cycle"])
            / mean_min,
            c["elapsed_budget_hours"] / c["business"]["elapsed_hours_per_attempt"],
        )
        base_cap = self.s.get("provider_attempt_limit", c["provider_attempt_limit"])
        extra = c["projects"]["extra-execution-block"]["extra_provider_attempts_per_cycle"]
        life2 = min(left, c["projects"]["extra-execution-block"]["life_cycles"])
        added = sum(
            max(
                0,
                min(base_cap + extra, cap_other, self.demand[j] * 3 * (1 + self.fail))
                - min(base_cap, cap_other, self.demand[j] * 3 * (1 + self.fail)),
            )
            for j in range(cycle, cycle + life2)
        )
        expected_receipt = (
            sum(self.prices.values())
            / 3
            * self.route["worker_entitlement_fraction"]
            * (1 - c["business"]["default_fraction"])
            * (1 - c["business"]["refund_fraction_of_collections"])
            * (1 - self.route["conversion_spread_fraction"])
            * (1 - self.route["volatility_haircut_fraction"])
            * (1 - self.fail**2)
            / (1 + self.fail)
        )
        capacity_cost = project_cost(c, "extra-execution-block")
        capacity_npv = added * (expected_receipt - mean_cost) - dollars(
            capacity_cost + maintenance_cost(c, "extra-execution-block") * life2
        )
        capacity = {
            "id": "extra-execution-block",
            "kind": "execution_capacity",
            "cost": capacity_cost,
            "npv_usd": round(capacity_npv, 6),
            "added_attempts_expected": round(added, 4),
            "admissible": left > 0 and added > 0 and capacity_npv >= 0,
            "reason": (
                "Modeled provider bottleneck can be relieved within unchanged other budgets"
                if left > 0 and added > 0 and capacity_npv >= 0
                else "HOLD: no supported profitable relief of the binding constraint"
            ),
            "evidence_class": "assumed vendor offer and expected-resource model; not observed capacity acquisition",
        }
        discovery = {
            "id": "discovery-process-pilot",
            "kind": "discovery",
            "cost": project_cost(c, "discovery-process-pilot"),
            "npv_usd": None,
            "admissible": False,
            "reason": "HOLD: productive effect is unmeasured",
            "evidence_class": "estimated cost; unknown benefit",
        }
        return [child, capacity, discovery]

    def run(self):
        c = self.c
        biz = c["business"]
        all_accepted = {f: 0 for f in FAMILIES}
        total_costs = {f: 0 for f in FAMILIES}
        all_attempts = {f: 0 for f in FAMILIES}
        for cycle in range(1, c["cycles"] + 1):
            opening = (self.cash, self.ar, self.collateral, self.ap, self.asset)
            op_paid_open = self.operating_paid
            op_accrued_open = self.operating_accrued
            invest_open = self.invested
            _external_open = self.net_external
            got, refunds, defaults, conversion = self.receive(cycle)
            returned = 0
            for b in self.bonds:
                if b["due"] == cycle:
                    self.event(
                        cycle,
                        "collateral_principal_return",
                        cash=b["amount"],
                        collateral=-b["amount"],
                        amount=b["amount"],
                    )
                    returned += b["amount"]
            if self.ap:
                payment = min(max(0, self.cash - self.reserved_profit), self.ap)
                self.event(cycle, "prior_operating_payable_payment", cash=-payment, ap=-payment, amount=payment)
                self.operating_paid += payment
            fixed = money(biz["fixed_operating_usd_per_cycle"]) + money(
                biz["fixed_administration_minutes_per_cycle"] * c["rates"]["operator_usd_per_hour"] / 60
            )
            nonproduction_minutes = float(biz["fixed_administration_minutes_per_cycle"])
            if cycle == 1:
                fixed += money(
                    (biz["initial_integration_engineer_hours"] + biz["unsuccessful_build_engineer_hours"])
                    * c["rates"]["software_engineer_usd_per_hour"]
                    + biz["initial_verification_hours"] * c["rates"]["reviewer_usd_per_hour"]
                    + biz["initial_model_tool_cost_usd"]
                )
                nonproduction_minutes += 60 * (
                    biz["initial_integration_engineer_hours"]
                    + biz["unsuccessful_build_engineer_hours"]
                    + biz["initial_verification_hours"]
                )
            depreciation = 0
            extra_capacity = 0
            child = False
            active = []
            for key, state in self.assets.items():
                if state["remaining_life"] <= 0:
                    continue
                if key == "dependency-repair-v1" and state["remaining_uses"] <= 0:
                    depreciation += state["book_value"]
                    self.event(
                        cycle,
                        "expired_capability_writeoff",
                        asset=-state["book_value"],
                        amount=state["book_value"],
                        project=key,
                    )
                    state["book_value"] = 0
                    state["remaining_life"] = 0
                    continue
                active.append(key)
                fixed += maintenance_cost(c, key)
                nonproduction_minutes += 60 * c["projects"][key].get("maintenance_engineer_hours_per_cycle", 0)
                d = (
                    state["book_value"]
                    if state["remaining_life"] == 1
                    else state["original_cost"] // c["projects"][key]["life_cycles"]
                )
                depreciation += d
                state["book_value"] -= d
                state["remaining_life"] -= 1
                self.event(cycle, "capital_depreciation_non_cash", asset=-d, amount=d, project=key)
                if key == "extra-execution-block":
                    extra_capacity += c["projects"][key]["extra_provider_attempts_per_cycle"]
                if key == "dependency-repair-v1":
                    child = True
            self.pay_operating(cycle, fixed, "fixed_business_setup_and_maintenance")
            spent = fixed
            attention = nonproduction_minutes
            elapsed = nonproduction_minutes / 60
            attempts_total = 0
            collateral_out = 0
            invoiced = 0
            entitled = 0
            new_investment = 0
            class_data = {
                f: {
                    "orders": 0,
                    "attempts": 0,
                    "accepted": 0,
                    "failed_orders": 0,
                    "failed_attempts": 0,
                    "cost": 0,
                    "attention": 0.0,
                    "cpu": 0.0,
                    "native_compute_unrounded": 0.0,
                    "invoice": 0,
                    "entitlement": 0,
                    "finance_expected": 0,
                }
                for f in FAMILIES
            }
            reasons = set()
            projects_used = set()
            for order in range(self.demand[cycle - 1]):
                for f in FAMILIES:
                    child_applied = child and order < self.assets["dependency-repair-v1"]["remaining_uses"]
                    u = self.unit(f, cycle, child_applied)
                    bond = money(self.prices[f] * self.route["collateral_fraction"])
                    reserved = u["order"] + 2 * u["attempt"] + u["retry"] + u["accepted"]
                    reserve_min = u["setup_min"] + 2 * u["attempt_min"] + u["retry_min"] + u["support_min"]
                    if self.ap:
                        reasons.add("unpaid_obligations")
                        continue
                    if self.cash - self.reserved_profit - money(biz["contingency_cash_floor_usd"]) < reserved + bond:
                        reasons.add("cash_liquidity")
                        continue
                    if spent + reserved > money(c["per_cycle_cash_spend_budget_usd"]):
                        reasons.add("cash_spend_budget")
                        continue
                    if attention + reserve_min > c["human_attention_budget_minutes"]:
                        reasons.add("human_attention_budget")
                        continue
                    if (
                        attempts_total + 2
                        > self.s.get("provider_attempt_limit", c["provider_attempt_limit"]) + extra_capacity
                    ):
                        reasons.add("provider_attempt_limit")
                        continue
                    if elapsed + 2 * biz["elapsed_hours_per_attempt"] > c["elapsed_budget_hours"]:
                        reasons.add("elapsed_budget")
                        continue
                    z = class_data[f]
                    z["orders"] += 1
                    if child_applied:
                        projects_used.add(order)
                    if bond:
                        self.event(
                            cycle, "worker_collateral_locked", cash=-bond, collateral=bond, amount=bond, family=f
                        )
                        self.bonds.append({"due": cycle + max(1, self.route["collateral_lock_cycles"]), "amount": bond})
                        collateral_out += bond
                    cost = u["order"]
                    minutes = u["setup_min"]
                    accepted = False
                    n_attempts = 0
                    n_fails = 0
                    for a in range(2):
                        n_attempts += 1
                        cost += u["attempt"]
                        minutes += u["attempt_min"]
                        if a:
                            cost += u["retry"]
                            minutes += u["retry_min"]
                        if probability(c["sample_seed"], cycle, f, order, a) >= self.fail:
                            accepted = True
                            break
                        n_fails += 1
                    if accepted:
                        cost += u["accepted"]
                        minutes += u["support_min"]
                        z["accepted"] += 1
                    else:
                        z["failed_orders"] += 1
                    self.pay_operating(cycle, cost, "delivery_business_cost", f)
                    spent += cost
                    attention += minutes
                    elapsed += n_attempts * biz["elapsed_hours_per_attempt"]
                    attempts_total += n_attempts
                    z["attempts"] += n_attempts
                    z["failed_attempts"] += n_fails
                    z["cost"] += cost
                    z["attention"] += minutes
                    z["cpu"] += u["native_cpu_ms_per_family_share"] * n_attempts
                    z["native_compute_unrounded"] += u["native_compute_usd_unrounded"] * n_attempts
                    if accepted:
                        price, entitlement = self.invoice(cycle, f)
                        invoiced += price
                        entitled += entitlement
                        z["invoice"] += price
                        z["entitlement"] += entitlement
                        z["finance_expected"] += portion(
                            entitlement,
                            (1 - biz["default_fraction"])
                            * (
                                self.route["volatility_haircut_fraction"]
                                + (1 - self.route["volatility_haircut_fraction"])
                                * self.route["conversion_spread_fraction"]
                            ),
                        )
            if child:
                self.assets["dependency-repair-v1"]["remaining_uses"] -= len(projects_used)
            got2, refunds2, defaults2, conversion2 = self.receive(cycle, True)
            got += got2
            refunds += refunds2
            defaults += defaults2
            conversion += conversion2
            earned_before = self.net_external - self.operating_paid - self.invested - self.ap
            obligation_reserve = portion(
                max(0, self.net_external - self.operating_paid - self.ap),
                biz["cash_profit_obligation_reserve_fraction"],
            )
            self.reserved_profit = obligation_reserve
            contingency = money(biz["contingency_cash_floor_usd"])
            available = max(
                0, min(earned_before - obligation_reserve, self.cash - self.ap - obligation_reserve - contingency)
            )
            policy_budget = portion(available, self.policy)
            offers = self.offers(cycle, available)
            purchased = []
            ordering = (
                offers
                if self.s.get("force_research")
                else sorted(
                    offers, key=lambda q: q.get("npv_usd") if q.get("npv_usd") is not None else -math.inf, reverse=True
                )
            )
            for offer in ordering:
                key = offer["id"]
                cost = offer["cost"]
                construction_minutes = 60 * (
                    c["projects"][key].get("construction_engineer_hours", 0)
                    + c["projects"][key].get("construction_verification_hours", 0)
                )
                resource_ok = (
                    attention + construction_minutes <= c["human_attention_budget_minutes"]
                    and elapsed + construction_minutes / 60 <= c["elapsed_budget_hours"]
                )
                eligible = (
                    key not in self.ever
                    and offer["admissible"]
                    and resource_ok
                    and cost <= policy_budget - new_investment
                    and cost <= self.cash - self.ap - obligation_reserve - contingency
                )
                offer["policy_funding_eligible"] = cost <= policy_budget and key not in self.ever
                offer["already_purchased"] = key in self.ever
                offer["resource_admission_eligible"] = resource_ok
                offer["construction_human_minutes_estimated"] = construction_minutes
                offer["purchased"] = eligible
                if not eligible:
                    continue
                self.event(cycle, "bounded_productive_investment", cash=-cost, asset=cost, amount=cost, project=key)
                self.invested += cost
                new_investment += cost
                self.ever.add(key)
                purchased.append(key)
                attention += construction_minutes
                elapsed += construction_minutes / 60
                self.assets[key] = {
                    "original_cost": cost,
                    "book_value": cost,
                    "remaining_life": c["projects"][key]["life_cycles"],
                    "remaining_uses": self.s.get("child_reuse_limit", c["projects"][key].get("finite_reuses", 10**9)),
                }
            plan = self.next_plan()
            smaller = [self.next_plan(n) for n in range(plan["target_orders_per_family"] + 1)]
            feasible = [p for p in smaller if p["budget_feasible"]]
            smaller_plan = feasible[-1] if feasible else None
            _total_acc = sum(z["accepted"] for z in class_data.values())
            total_orders = sum(z["orders"] for z in class_data.values())
            fixed_share = fixed + depreciation
            cost_allocated = 0
            for i, f in enumerate(FAMILIES):
                z = class_data[f]
                share = (
                    fixed_share - cost_allocated
                    if i == len(FAMILIES) - 1
                    else fixed_share * z["orders"] // total_orders if total_orders else fixed_share // 3
                )
                cost_allocated += share
                full = z["cost"] + share + z["finance_expected"]
                total_costs[f] += full
                all_accepted[f] += z["accepted"]
                all_attempts[f] += z["attempts"]
                rate = c["rates"][c["families"][f]["traditional_rate_key"]]
                cp = dollars(full) / z["accepted"] if z["accepted"] else None
                customer_review = c["families"][f]["customer_review_minutes_per_accepted"] * self.attention
                buy = self.prices[f] + customer_review * c["rates"]["operator_usd_per_hour"] / 60
                _future_finance = 0
                self.class_rows.append(
                    dict(
                        self.prefix,
                        cycle=cycle,
                        family=f,
                        offered_orders=self.demand[cycle - 1],
                        started_orders=z["orders"],
                        attempts=z["attempts"],
                        accepted=z["accepted"],
                        failed_orders=z["failed_orders"],
                        failed_attempts=z["failed_attempts"],
                        estimated_human_minutes=round(z["attention"], 4),
                        allocated_business_cost_usd=dollars(full),
                        cost_per_accepted_usd=round(cp, 6) if cp is not None else None,
                        modeled_full_cost_including_expected_conversion_per_accepted_usd=(
                            round(cp, 6) if cp is not None else None
                        ),
                        cost_scope="all modeled delivery/business cost, setup, failed construction, failed attempts, allocated fixed costs, capital depreciation, expected current-invoice conversion; realized collection cash separate",
                        price_usd=round(self.prices[f], 6),
                        customer_all_in_usd=round(buy, 6),
                        worker_entitlement_invoiced_usd=dollars(z["entitlement"]),
                        traditional_hourly_rate_usd=rate,
                        internal_human_break_even_minutes=round(60 * cp / rate, 6) if cp is not None else None,
                        customer_human_break_even_minutes=round(60 * buy / rate, 6),
                        customer_human_time_sensitivity=[
                            {
                                "traditional_minutes": t,
                                "traditional_cost_usd": round(t * rate / 60, 6),
                                "customer_saving_usd": round(t * rate / 60 - buy, 6),
                                "evidence_class": "ASSUMED duration; sourced rate scenario",
                            }
                            for t in c["sensitivity"]["human_minutes"]
                        ],
                        allocated_native_cpu_ms=round(z["cpu"], 6),
                        native_compute_cost_usd_unrounded=z["native_compute_unrounded"],
                        live_agent_cost_usd=None,
                    )
                )
            operating_cash = self.operating_paid - op_paid_open
            investment_cash = self.invested - invest_open
            cash_error = self.cash - (
                opening[0] + got + returned - refunds - operating_cash - investment_cash - collateral_out
            )
            ar_error = self.ar - (opening[1] + entitled - got - defaults)
            if cash_error or ar_error:
                raise AssertionError(("conservation", cash_error, ar_error))
            self.ledger.append(
                dict(
                    self.prefix,
                    cycle=cycle,
                    opening_cash_usd=dollars(opening[0]),
                    customer_gross_invoiced_usd=dollars(invoiced),
                    worker_entitlement_invoiced_usd=dollars(entitled),
                    gross_worker_collections_usd=dollars(got),
                    refunds_usd=dollars(refunds),
                    default_writeoffs_usd=dollars(defaults),
                    paid_operating_cost_usd=dollars(operating_cash),
                    incurred_operating_cost_usd=dollars(self.operating_accrued - op_accrued_open),
                    noncash_depreciation_usd=dollars(depreciation),
                    productive_investment_usd=dollars(investment_cash),
                    collateral_deposit_usd=dollars(collateral_out),
                    collateral_return_usd=dollars(returned),
                    closing_cash_usd=dollars(self.cash),
                    closing_receivables_usd=dollars(self.ar),
                    closing_collateral_usd=dollars(self.collateral),
                    closing_payables_usd=dollars(self.ap),
                    productive_asset_book_value_usd=dollars(self.asset),
                    cumulative_net_external_collections_usd=dollars(self.net_external),
                    cumulative_operating_cash_paid_usd=dollars(self.operating_paid),
                    cumulative_productive_investment_usd=dollars(self.invested),
                    cumulative_earned_cash_before_reserves_usd=dollars(earned_before),
                    obligation_cash_reserve_usd=dollars(obligation_reserve),
                    contingency_cash_floor_usd=dollars(contingency),
                    available_preallocation_operating_surplus_usd=dollars(available),
                    policy_budget_usd=dollars(policy_budget),
                    unspent_policy_budget_usd=dollars(policy_budget - new_investment),
                    next_plan_cash_need_usd=dollars(plan["total"]),
                    next_plan_construction_usd=dollars(plan["construction"]),
                    next_plan_operating_working_capital_usd=dollars(plan["operating"]),
                    next_plan_new_collateral_usd=dollars(plan["collateral"]),
                    next_plan_one_cycle_maintenance_usd=dollars(plan["maintenance"]),
                    full_surplus_next_plan_coverage=round(available / plan["total"], 6),
                    policy_next_plan_coverage=round(policy_budget / plan["total"], 6),
                    construction_only_coverage=round(available / plan["construction"], 6),
                    accepted_by_family={f: z["accepted"] for f, z in class_data.items()},
                    attempts_by_family={f: z["attempts"] for f, z in class_data.items()},
                    failures_by_family={f: z["failed_orders"] for f, z in class_data.items()},
                    estimated_human_minutes=round(attention, 4),
                    estimated_elapsed_hours=round(elapsed, 4),
                    provider_attempts=attempts_total,
                    binding_constraints=sorted(reasons),
                    active_capabilities=active,
                    purchased_projects=purchased,
                    offers=[dict(o, cost_usd=dollars(o["cost"])) for o in offers],
                    cash_conservation_error_usd=dollars(cash_error),
                    receivable_conservation_error_usd=dollars(ar_error),
                    capital_opportunity_cost_usd=round(
                        dollars(self.collateral)
                        * biz["capital_opportunity_cost_annual_fraction"]
                        * c["cycle_days"]
                        / 365,
                        6,
                    ),
                    capital_opportunity_cost_is_cash=False,
                    live_agent_cost_usd=None,
                )
            )
            self.ledger[-1].update(
                next_plan_budget_feasible=plan["budget_feasible"],
                next_plan_budget_checks=plan["budget_checks"],
                next_plan_target_orders_per_family=plan["target_orders_per_family"],
                next_plan_acceptance_guaranteed=False,
                next_plan_estimated_human_minutes=round(plan["human_minutes"], 4),
                next_plan_estimated_elapsed_hours=round(plan["elapsed_hours"], 4),
                next_plan_provider_attempts=plan["attempt_budget"],
                next_plan_available_provider_attempts=plan["next_provider_cap"],
                next_plan_existing_capacity_maintenance_usd=dollars(plan["existing_capacity_maintenance"]),
                next_plan_construction_scope=plan["construction_scope"],
                next_plan_cash_coverage_is_executable_plan=(
                    False if not plan["budget_feasible"] else available >= plan["total"]
                ),
                maximum_budget_feasible_target_orders_per_family=(
                    smaller_plan["target_orders_per_family"] if smaller_plan else None
                ),
                budget_feasible_smaller_plan_cash_need_usd=dollars(smaller_plan["total"]) if smaller_plan else None,
                budget_feasible_smaller_plan_surplus_coverage=(
                    round(available / smaller_plan["total"], 6) if smaller_plan else None
                ),
                smaller_plan_status="Post-result feasibility diagnostic; no permission or budget change; output acceptance remains uncertain",
            )
        last = self.ledger[-1]
        self.summary = dict(
            self.prefix,
            route=self.s.get("route", "direct"),
            accepted_by_family=all_accepted,
            attempts_by_family=all_attempts,
            full_cost_per_accepted_by_family={
                f: round(dollars(total_costs[f]) / all_accepted[f], 6) if all_accepted[f] else None for f in FAMILIES
            },
            initial_external_capital_usd=c["initial_external_capital_usd"],
            closing_cash_usd=dollars(self.cash),
            closing_receivables_usd=dollars(self.ar),
            closing_collateral_usd=dollars(self.collateral),
            closing_payables_usd=dollars(self.ap),
            closing_capital_asset_usd=dollars(self.asset),
            cumulative_net_external_collections_usd=dollars(self.net_external),
            cumulative_operating_cash_paid_usd=dollars(self.operating_paid),
            cumulative_investment_usd=dollars(self.invested),
            available_operating_surplus_usd=last["available_preallocation_operating_surplus_usd"],
            full_surplus_next_plan_coverage=last["full_surplus_next_plan_coverage"],
            policy_next_plan_coverage=last["policy_next_plan_coverage"],
            purchased_projects=sorted(self.ever),
            self_financing_demonstrated=False,
            self_acceleration_demonstrated=False,
            live_agent_cost_usd=None,
        )
        self.summary.update(
            next_plan_budget_feasible=last["next_plan_budget_feasible"],
            next_plan_budget_checks=last["next_plan_budget_checks"],
            next_plan_target_orders_per_family=last["next_plan_target_orders_per_family"],
            next_plan_acceptance_guaranteed=False,
            next_plan_cash_need_usd=last["next_plan_cash_need_usd"],
            maximum_budget_feasible_target_orders_per_family=last["maximum_budget_feasible_target_orders_per_family"],
            budget_feasible_smaller_plan_cash_need_usd=last["budget_feasible_smaller_plan_cash_need_usd"],
            budget_feasible_smaller_plan_surplus_coverage=last["budget_feasible_smaller_plan_surplus_coverage"],
        )
        return self


def write_csv(path, rows):
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "protocol/economics_config.json"))
    parser.add_argument("--bridge", default=str(ROOT / "outputs/economics_bridge.json"))
    parser.add_argument("--output", default=str(ROOT / "economics/outputs"))
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    freeze = json.loads((ROOT / "protocol/economics_freeze.json").read_text())
    expected = freeze["files"]["protocol/economics_config.json"]
    if sha(args.config) != expected:
        raise ValueError("Economic assumptions changed after freeze; explicit version/amendment required")
    bridge, metrics, saving = load_bridge(args.bridge)
    if bridge.get("source_summary_sha256") != sha(ROOT / "outputs/summary.json"):
        raise ValueError("Observed source summary changed; rebind bridge explicitly")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    provenance = {
        "config_sha256": sha(args.config),
        "bridge_sha256": sha(args.bridge),
        "engine_sha256": sha(__file__),
        "config_frozen_at_utc": freeze["frozen_at_utc"],
        "correction_records": ["protocol/economics_amendment_1.json", "protocol/economics_amendment_2.json"],
        "business_outputs": "SIMULATED",
        "observed_source": "local deterministic research measurements only",
        "live_browser_executor": "NOT RUN",
        "live_paid_transactions": "NOT RUN",
        "complete_live_agent_cost_usd": None,
        "independence": "author implementation; separate reviewer may check arithmetic, same-session shared tooling",
    }
    sims = [
        Model(cfg, s, p, bridge, metrics, saving).run() for s in cfg["scenarios"] for p in cfg["reinvestment_policies"]
    ]
    ledger = [r for m in sims for r in m.ledger]
    family = [r for m in sims for r in m.class_rows]
    events = [r for m in sims for r in m.events]
    base = next(m for m in sims if m.s["id"] == "base" and m.policy == 0)
    summary = {
        "schema_version": "1.0",
        "study_id": cfg["study_id"],
        "provenance": provenance,
        "counts": {
            "scenarios": len(cfg["scenarios"]),
            "policies": len(cfg["reinvestment_policies"]),
            "scenario_policy_runs": len(sims),
            "cycles_per_run": cfg["cycles"],
            "ledger_rows": len(ledger),
            "class_rows": len(family),
            "events": len(events),
        },
        "measured_bridge": {
            "changed_cycle_cpu_saving_ms_per_joint_project_vs_conventional_cache": saving,
            "value_per_joint_reuse_usd": saving / 3_600_000 * cfg["business"]["kernel_compute_usd_per_cpu_hour"],
            "quality_or_attention_saving_assumed": False,
            "directly_measured_revenue": False,
        },
        "base": base.summary,
        "scenario_results": [m.summary for m in sims],
        "claim_status": {
            "service_delivery": "observed separately within bounded controlled local domain; operational wrapper modeled",
            "immediate_economic_advantage": "conditional modeled comparison against sourced wages and explicit human-time assumptions",
            "operating_surplus": "modeled, after cost, obligations and reserve accounting",
            "capability_admission": "HOLD against strong conventional reuse when measured CPU cannot repay construction/maintenance",
            "capacity_scaling": "modeled only where provider constraint binds",
            "self_financing": "not empirically demonstrated: no external paid collections",
            "self_acceleration": "not demonstrated",
        },
    }
    for name, data in [
        ("summary.json", summary),
        ("ledger.json", {"provenance": provenance, "rows": ledger}),
        (
            "scenarios.json",
            {"provenance": provenance, "scenarios": cfg["scenarios"], "results": [m.summary for m in sims]},
        ),
        ("family_results.json", {"provenance": provenance, "rows": family}),
    ]:
        (out / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    (out / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n" for e in events))
    write_csv(out / "ledger.csv", ledger)
    write_csv(out / "family_results.csv", family)
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "provenance": provenance,
                "files": {
                    name: sha(out / name)
                    for name in [
                        "summary.json",
                        "ledger.json",
                        "scenarios.json",
                        "family_results.json",
                        "events.jsonl",
                        "ledger.csv",
                        "family_results.csv",
                    ]
                },
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"counts": summary["counts"], "base": base.summary, "bridge_cpu_saving_ms": saving}, indent=2))


if __name__ == "__main__":
    main()
