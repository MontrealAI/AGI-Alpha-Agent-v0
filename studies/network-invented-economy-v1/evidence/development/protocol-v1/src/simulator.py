# SPDX-License-Identifier: Apache-2.0
"""Finite-cash, heterogeneous-agent research simulation; no live service calls."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from .alpha_assessment import AlphaAssessment, AlphaCosts, evaluate_alpha


MODEL_VERSION = "network-economy/1.0"
DOMAINS = ("procurement", "allocation", "coordination")
KINDS = ("representation", "falsifier", "composition")
HUMAN_RATES = (334.18, 213.72, 264.95, 200.09)
ROLE_HOURS = ((24, 40, 24, 12), (48, 80, 48, 20), (96, 160, 96, 32))
HUMAN_REFERENCES = tuple(round(sum(a * b for a, b in zip(h, HUMAN_RATES)), 2) for h in ROLE_HOURS)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def uniform(seed: int, *keys: Any) -> float:
    digest = hashlib.blake2b(canonical([seed, *keys]), digest_size=8, person=b"network-v1").digest()
    return (int.from_bytes(digest, "big") + 0.5) / 2**64


def cents(amount: float) -> int:
    return round(amount * 100)


@dataclass(frozen=True)
class Scenario:
    name: str = "central"
    weeks: int = 104
    runoff: int = 16
    agents: int = 6
    validator_slots: int = 2
    seed_capital: float = 60000
    setup_cost: float = 9500
    leads_per_week: float = 4.0
    demand_dispersion: float = 0.35
    human_price_factor: float = 1.0
    initial_trust: float = 0.78
    demand_value: float = 1.45
    integration_fraction: float = 0.13
    choice_temperature: float = 0.14
    collection_delay: int = 4
    default_probability: float = 0.04
    common_fault_probability: float = 0.055
    spec_error: float = 0.045
    implementation_error: float = 0.10
    false_rejection: float = 0.035
    semantic_detection: float = 0.78
    executable_detection: float = 0.97
    correction_success: float = 0.78
    invention_probability: float = 0.48
    construction_success: float = 0.72
    asset_defect_probability: float = 0.06
    admission_false_pass: float = 0.08
    admission_false_rejection: float = 0.045
    transfer_success: float = 0.80
    harmful_transfer: float = 0.035
    initial_overlap: float = 0.25
    specialization: float = 0.45
    useful_lifetime: int = 40
    obsolete_hazard: float = 0.006
    external_improvement: float = 0.18
    reuse_savings_factor: float = 1.0
    token_cost_factor: float = 1.0
    tool_cost_factor: float = 1.0
    construction_cost_factor: float = 1.0
    quota_input_m: float = 200.0
    quota_output_m: float = 40.0
    max_queue: int = 24
    diversity: int = 3
    depth_weights: tuple[float, float, float] = (0.45, 0.35, 0.20)
    quality_decay_load: float = 0.025
    distribution_fixed: float = 70.0
    member_overhead: float = 4.0
    maintenance_per_skill: float = 22.0
    revalidation_period: int = 12
    revalidation_failure: float = 0.08
    revalidation_false_negative: float = 0.05
    membership_count: int = 24
    warranty_weeks: int = 6
    refund_probability: float = 0.90
    repeat_probability: float = 0.18
    sharing_bounty: float = 125.0
    ticks_per_week: int = 5
    transfer_validation_factor: float = 1.0
    beta_epoch_weeks: int = 26
    ordinary_learning_rate: float = 0.12
    copying_hazard: float = 0.006
    cache_enabled: bool = True


SCENARIOS = {
    "central": Scenario(),
    "conservative": Scenario(
        name="conservative", leads_per_week=1.8, initial_trust=0.61, demand_value=1.25,
        integration_fraction=0.22, default_probability=0.09, collection_delay=7,
        common_fault_probability=0.11, spec_error=0.10, implementation_error=0.18,
        semantic_detection=0.63, correction_success=0.60, invention_probability=0.28,
        construction_success=0.50, transfer_success=0.60, harmful_transfer=0.07,
        initial_overlap=0.55, useful_lifetime=22, obsolete_hazard=0.02,
        token_cost_factor=2.0, tool_cost_factor=1.5, construction_cost_factor=1.5,
        external_improvement=0.40, quota_input_m=110, quota_output_m=22,
    ),
    "favorable": Scenario(
        name="favorable", leads_per_week=7.0, initial_trust=0.87, demand_value=1.60,
        integration_fraction=0.08, default_probability=0.02, collection_delay=2,
        common_fault_probability=0.025, spec_error=0.025, implementation_error=0.065,
        correction_success=0.87, invention_probability=0.65, construction_success=0.84,
        transfer_success=0.92, harmful_transfer=0.015, initial_overlap=0.10,
        useful_lifetime=64, obsolete_hazard=0.003, external_improvement=0.10,
        quota_input_m=290, quota_output_m=58,
    ),
}


@dataclass(frozen=True)
class Policy:
    name: str = "adaptive"
    pricing: str = "adaptive"
    price_ratio: float = 0.75
    price_offset: float = 0.0
    invest: bool = True
    hurdle: float = 1.35
    reserve_weeks: int = 6
    forecast_weight: float = 0.65
    allow_bundles: bool = True
    max_investment_share: float = 0.60
    abandon_after_idle_weeks: int = 16


@dataclass
class Ledger:
    seed: float
    cash: int = 0
    committed: dict[str, int] = field(default_factory=dict)
    warranty: dict[str, tuple[int, int]] = field(default_factory=dict)
    unpaid: int = 0
    records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = cents(self.seed)
        self.records.append({"week": 0, "kind": "seed", "amount_cents": self.cash, "cash_cents": self.cash})

    @property
    def reserved(self) -> int:
        return sum(self.committed.values()) + sum(v[0] for v in self.warranty.values())

    def available(self, floor: float = 0) -> float:
        return max(0, self.cash - self.reserved - self.unpaid - cents(floor)) / 100

    def reserve(self, key: str, amount: float, week: int) -> bool:
        n = cents(amount)
        if key in self.committed or n < 0 or self.cash - self.reserved - self.unpaid < n:
            return False
        self.committed[key] = n
        self.records.append({"week": week, "kind": "reserve", "key": key, "amount_cents": n,
                             "cash_cents": self.cash, "reserved_cents": self.reserved})
        return True

    def release(self, key: str, week: int) -> None:
        n = self.committed.pop(key, 0)
        self.records.append({"week": week, "kind": "release", "key": key, "amount_cents": n,
                             "cash_cents": self.cash, "reserved_cents": self.reserved})

    def spend(self, amount: float, week: int, category: str, key: str = "", **metadata: Any) -> bool:
        n = cents(amount)
        if n < 0:
            raise ValueError("negative expense")
        if key in self.committed:
            if n > self.committed[key]:
                raise ValueError(f"spend exceeds pre-funded commitment: {key}")
            self.committed[key] -= n
        unprotected = self.cash - self.reserved
        paid = min(n, max(0, unprotected))
        self.cash -= paid
        self.unpaid += n - paid
        self.records.append({"week": week, "kind": "expense", "category": category, "key": key,
                             "amount_cents": n, "paid_cents": paid, "cash_cents": self.cash,
                             "reserved_cents": self.reserved, **metadata})
        return paid == n

    def receive(self, amount: float, week: int, key: str, warranty_weeks: int = 0) -> None:
        n = cents(amount)
        self.cash += n
        if warranty_weeks:
            self.warranty[key] = (round(n * 0.15), week + warranty_weeks)
        self.records.append({"week": week, "kind": "collection", "key": key, "amount_cents": n,
                             "cash_cents": self.cash, "reserved_cents": self.reserved})

    def age(self, week: int) -> None:
        for key, (_, expiry) in list(self.warranty.items()):
            if week >= expiry:
                del self.warranty[key]


@dataclass(frozen=True)
class Work:
    astra_input: float = 0.0
    astra_cache: float = 0.0
    astra_output: float = 0.0
    terra_input: float = 0.0
    terra_cache: float = 0.0
    terra_output: float = 0.0
    tools: float = 0.0
    latency: float = 0.0

    def cost(self, s: Scenario) -> float:
        # With caching, conservatively bill every fresh input token as a 30-minute
        # cache write (12.50/1.25), then bill the separately counted read tokens.
        # Work volumes are assumed aggregate underlying Pro work, including reasoning.
        if s.cache_enabled:
            inputs = self.astra_input * 12.5 + self.astra_cache + self.terra_input * 1.25 + self.terra_cache * 0.05
        else:
            inputs = (self.astra_input + self.astra_cache) * 10 + self.terra_input + self.terra_cache
        tokens = inputs + self.astra_output * 50 + self.terra_output * 5
        return tokens * s.token_cost_factor + self.tools * s.tool_cost_factor

    @property
    def input_m(self) -> float:
        return self.astra_input + self.astra_cache + self.terra_input + self.terra_cache

    @property
    def output_m(self) -> float:
        return self.astra_output + self.terra_output

    def scale(self, v: float) -> Work:
        return Work(**{k: x * v for k, x in asdict(self).items()})

    def __add__(self, other: Work) -> Work:
        return Work(**{k: v + getattr(other, k) for k, v in asdict(self).items()})


PRODUCTION = (
    Work(4, 2, 0.8, 4, 1, 0.7, 100, 0.7),
    Work(8, 4, 1.6, 8, 2, 1.4, 230, 1.0),
    Work(16, 8, 3.2, 16, 4, 2.8, 470, 1.5),
)
RECONSTRUCTION = (
    Work(16, 5, 3.2, 6, 2, 1.2, 160, 0.7),
    Work(14, 5, 2.8, 6, 2, 1.2, 200, 0.7),
    Work(24, 8, 4.8, 8, 3, 1.6, 310, 1.0),
)
INTEGRATION = Work(1.2, 0.6, 0.24, 1.5, 0.5, 0.3, 22, 0.12)
VALIDATION = (
    Work(5, 2, 1.0, 2, 0.5, 0.3, 80, 0.45),
    Work(10, 4, 2.0, 4, 1, 0.6, 170, 0.65),
    Work(18, 6, 3.6, 8, 2, 1.2, 340, 0.9),
)
CORRECTION = Work(6, 2, 1.2, 3, 1, 0.5, 90, 0.45)
PACKAGING = Work(0.4, 0.2, 0.08, 2, 0.5, 0.4, 25, 0.1)
INTAKE = Work(0.16, 0.06, 0.035, 0.2, 0.05, 0.04, 2.0, 0)
EVALUATION = Work(1.8, 0.5, 0.35, 0.4, 0.1, 0.06, 10, 0.15)
CONSTRUCTION = (
    Work(75, 20, 15, 20, 5, 4, 1700, 2.0),
    Work(60, 20, 12, 20, 5, 4, 1900, 2.0),
    Work(105, 30, 21, 25, 7, 5, 2400, 2.5),
)
REVALIDATE = Work(2, 0.6, 0.4, 0.5, 0.2, 0.1, 45, 0.12)


@dataclass
class Skill:
    key: tuple[int, int]
    owner: int
    born: int
    expiry: int
    next_check: int
    valid: bool
    active: bool = True
    uses: int = 0
    recipients: set[int] = field(default_factory=set)
    adaptations: dict[int, bool] = field(default_factory=dict)
    harmful_adaptations: set[int] = field(default_factory=set)
    useful_recipients: set[int] = field(default_factory=set)
    source_job: int = -1
    version: int = 1
    beta_version: str = "beta-2026-10-26-epoch-0"
    alpha_net_lower: float = 0.0
    alpha_assessment: dict[str, Any] = field(default_factory=dict)
    bundle_id: str = ""
    bundle_keys: tuple[tuple[int, int], ...] = ()


@dataclass
class Candidate:
    key: tuple[int, int]
    owner: int
    source_job: int
    week: int
    campaign_id: str
    task_valid: bool = True


@dataclass
class Job:
    id: int
    domain: int
    depth: int
    born: int
    price: float
    human_reference: float
    owner: int
    deadline: int
    production: Work
    validation: Work
    missing: list[int]
    selected: list[Skill]
    wrong_components: int
    stage: str = "production"
    remaining_input: float = 0.0
    remaining_output: float = 0.0
    remaining_latency: float = 0.0
    stage_charged: bool = False
    stage_paid_cents: int = 0
    true_correct: bool | None = None
    common_blind: bool = False
    corrections: int = 0
    transferred: int = 0
    duration: int = 0

    def start(self, stage: str, work: Work) -> None:
        self.stage = stage
        self.remaining_input = work.input_m
        self.remaining_output = work.output_m
        self.remaining_latency = work.latency
        self.stage_charged = False
        self.stage_paid_cents = 0


def poisson(rng: random.Random, lam: float) -> int:
    product, count = 1.0, 0
    limit = math.exp(-lam)
    while product > limit:
        product *= rng.random()
        count += 1
    return count - 1


class Enterprise:
    def __init__(self, scenario: Scenario, policy: Policy, seed: int, arm: str = "network", retain: bool = False):
        if arm not in {"network", "isolated", "beta", "no_retention", "remove_representation", "remove_falsifier",
                       "remove_composition", "duplicate", "network_no_invest"}:
            raise ValueError(arm)
        self.s, self.p, self.seed, self.arm, self.retain = scenario, policy, seed, arm, retain
        self.ledger = Ledger(scenario.seed_capital)
        self.ledger.spend(scenario.setup_cost, 0, "setup")
        self.jobs: list[Job] = []
        self.skills: list[Skill] = []
        self.candidates: dict[tuple[int, int, int], Candidate] = {}
        self.investments: list[dict[str, Any]] = []
        self.pending_investments: list[dict[str, Any]] = []
        self.receipts: list[dict[str, Any]] = []
        self.repeat_leads: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
        self.stats: Counter[str] = Counter()
        self.costs: Counter[str] = Counter()
        self.events: list[dict[str, Any]] = []
        self.weekly: list[dict[str, Any]] = []
        self.trust = scenario.initial_trust
        self.conversion = 0.25
        self.observed_leads = scenario.leads_per_week
        self.new_work = True
        self.input_budget = 0.0
        self.output_budget = 0.0
        self.validator_overhead_remaining = 0.0
        self.producer_overhead_remaining = 0.0
        self.max_input = 0.0
        self.max_output = 0.0
        self.sample_prices: list[float] = []
        self.last_order_week = 0
        self.outcomes: list[dict[str, Any]] = []
        self.known = [[uniform(seed, "known", a, d) < scenario.initial_overlap for d in range(scenario.diversity)]
                      for a in range(scenario.agents)]
        rng = random.Random(seed)
        self.world_demand = math.exp(rng.gauss(-scenario.demand_dispersion**2 / 2, scenario.demand_dispersion))
        self.arrivals: list[list[dict[str, Any]]] = []
        jid = 0
        for week in range(1, scenario.weeks + 1):
            rows = []
            for _ in range(poisson(rng, scenario.leads_per_week * self.world_demand)):
                jid += 1
                depth = rng.choices((1, 2, 3), scenario.depth_weights)[0]
                rows.append({"id": jid, "domain": rng.randrange(scenario.diversity), "depth": depth,
                             "value": math.exp(rng.gauss(math.log(scenario.demand_value), 0.24)),
                             "urgency": rng.uniform(0.02, 0.06), "human_quality": rng.uniform(0.90, 0.98)})
            self.arrivals.append(rows)

    def log(self, week: int, kind: str, **data: Any) -> None:
        self.events.append({"week": week, "kind": kind, **data})

    def fixed_cost(self) -> float:
        network = self.arm not in {"isolated", "no_retention", "beta"}
        return 165 + 40 * self.s.agents + (self.s.distribution_fixed + self.s.membership_count * self.s.member_overhead
                                         if network else 35)

    def eligible(self, skill: Skill, owner: int, domain: int, kind: int, week: int) -> bool:
        if not skill.active or skill.expiry <= week or skill.next_check <= week:
            return False
        if skill.beta_version != self.beta_version(week):
            return False
        if skill.bundle_keys and any(not any(x.bundle_id == skill.bundle_id and x.key == k and x.active
                                             and x.expiry > week and x.next_check > week
                                             and x.beta_version == self.beta_version(week) for x in self.skills)
                                     for k in skill.bundle_keys):
            return False
        if skill.key != (domain, kind):
            return False
        if self.arm == "isolated" and skill.owner != owner:
            return False
        if self.arm in {"no_retention", "beta"}:
            return False
        removed = {"remove_representation": 0, "remove_falsifier": 1, "remove_composition": 2}
        return removed.get(self.arm) != kind

    def missing_work(self, owner: int, domain: int, kind: int, week: int) -> Work:
        familiarity = 0.60 if self.known[owner][domain] else 1.0
        if owner % self.s.diversity == domain:
            familiarity *= 1 - self.s.specialization
        diffusion = max(0.15, 1 - self.s.external_improvement * week / 52)
        return RECONSTRUCTION[kind].scale(familiarity * diffusion)

    def plan(self, lead: dict[str, Any], week: int) -> tuple[int, Work, Work, list[int], list[Skill]]:
        domain, depth = lead["domain"], lead["depth"]
        occupied = Counter(j.owner for j in self.jobs)
        plans = []
        for owner in range(self.s.agents):
            work, missing, selected = PRODUCTION[depth - 1], [], []
            for kind in range(depth):
                available = [x for x in self.skills if self.eligible(x, owner, domain, kind, week)]
                available = [x for x in available if x.adaptations.get(owner, True)]
                skill = min(available, key=lambda x: (x.owner != owner, -x.born)) if available else None
                reconstruction = self.missing_work(owner, domain, kind, week)
                if skill is not None:
                    if self.arm == "duplicate":
                        addon = reconstruction + INTEGRATION.scale(self.s.transfer_validation_factor)
                    elif owner == skill.owner:
                        addon = reconstruction.scale(max(0, 1 - 0.90 * self.s.reuse_savings_factor))
                    elif self.known[owner][domain]:
                        addon = reconstruction + INTEGRATION.scale(self.s.transfer_validation_factor)
                    else:
                        addon = reconstruction.scale(max(0, 1 - 0.78 * self.s.reuse_savings_factor)) + INTEGRATION.scale(self.s.transfer_validation_factor)
                    if addon.cost(self.s) < reconstruction.cost(self.s):
                        work += addon
                        selected.append(skill)
                    else:
                        work += reconstruction
                        missing.append(kind)
                else:
                    work += reconstruction
                    missing.append(kind)
            val = VALIDATION[depth - 1]
            if any(x.key[1] == 1 for x in selected) and self.arm != "duplicate":
                val = val.scale(max(0.35, 1 - 0.35 * self.s.reuse_savings_factor))
            score = work.cost(self.s) + val.cost(self.s) + occupied[owner] * 1800
            plans.append((score, owner, work, val, missing, selected))
        _, owner, work, val, missing, selected = min(plans, key=lambda x: x[0])
        return owner, work, val, missing, selected

    def perceived_success(self, depth: int, missing: list[int], load: float) -> float:
        first = (1 - self.s.spec_error) * (1 - self.s.implementation_error - 0.025 * (depth - 1))
        first *= (1 - 0.055) ** len(missing)
        after_correction = first + (1 - first) * self.s.correction_success * 0.85
        return max(0.30, min(0.97, after_correction - self.s.quality_decay_load * load))

    def utilities(self, price_ratio: float, lead: dict[str, Any], q: float, wait: float,
                  trust: float | None = None) -> list[float]:
        t = self.trust if trust is None else trust
        v, urgency = lead["value"], lead["urgency"]
        ours = v * q * t - price_ratio - self.s.integration_fraction - urgency * wait
        human = v * lead["human_quality"] - 1 - 0.05 - urgency * (4 + 2 * lead["depth"])
        postpone = 0.12 * max(0, v - 1) - urgency * 5
        return [ours, human, postpone, 0.0]

    def purchase_probability(self, ratio: float, lead: dict[str, Any], q: float, wait: float) -> float:
        u = self.utilities(ratio, lead, q, wait)
        m = max(u)
        exp = [math.exp((x - m) / self.s.choice_temperature) for x in u]
        return exp[0] / sum(exp)

    def choose_price(self, lead: dict[str, Any], q: float, wait: float, expected_cost: float) -> float:
        if self.p.pricing == "fixed":
            return self.p.price_ratio
        h = HUMAN_REFERENCES[lead["depth"] - 1] * self.s.human_price_factor
        grid = (0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 1.0, 1.15, 1.30)
        expected_collect = q * (1 - self.s.default_probability)
        costs = expected_cost + (1 - q) * h * 0.02
        observed = {**lead, "value": self.s.demand_value, "human_quality": 0.95}
        best = max(grid, key=lambda r: self.purchase_probability(r, observed, q, wait)
                   * (r * h * expected_collect - costs))
        return max(0.15, min(1.40, best + self.p.price_offset))

    def pay_work(self, work: Work, week: int, category: str, key: str = "", cost_override: float | None = None) -> bool:
        ok = self.ledger.spend(work.cost(self.s) if cost_override is None else cost_override, week, category, key,
                               input_m=round(work.input_m, 8), output_m=round(work.output_m, 8),
                               work=asdict(work))
        if not ok:
            self.stats["cash_shortfall"] = 1
            self.new_work = False
        return ok

    def consume(self, work: Work, fraction: float = 1) -> bool:
        if work.input_m * fraction > self.input_budget + 1e-9 or work.output_m * fraction > self.output_budget + 1e-9:
            return False
        self.input_budget -= work.input_m * fraction
        self.output_budget -= work.output_m * fraction
        return True

    def sell(self, lead: dict[str, Any], week: int) -> None:
        self.stats["prospects"] += 1
        if not self.new_work or self.ledger.available() < INTAKE.cost(self.s) or not self.consume(INTAKE):
            self.stats["intake_refused"] += 1
            return
        self.pay_work(INTAKE, week, "automated_intake")
        owner, production, validation, missing, selected = self.plan(lead, week)
        load = len(self.jobs) / self.s.agents
        wait = production.latency + validation.latency + load * 1.4 + 1
        q = self.perceived_success(lead["depth"], missing, load)
        h = HUMAN_REFERENCES[lead["depth"] - 1] * self.s.human_price_factor
        expected_cost = (production + validation + PACKAGING).cost(self.s) + 0.3 * (CORRECTION + validation).cost(self.s)
        ratio = self.choose_price(lead, q, wait, expected_cost)
        price = round(ratio * h, 2)
        if price * q * (1 - self.s.default_probability) <= expected_cost + (1 - q) * h * 0.02:
            self.stats["commercial_abstentions"] += 1
            return
        u = self.utilities(ratio, lead, q, wait)
        noisy = [x - self.s.choice_temperature * math.log(-math.log(uniform(self.seed, "choice", lead["id"], i)))
                 for i, x in enumerate(u)]
        choice = max(range(4), key=lambda i: noisy[i])
        self.stats[("buyer_ours", "buyer_human", "buyer_postpone", "buyer_none")[choice]] += 1
        if choice != 0:
            return
        if len(self.jobs) >= self.s.max_queue or q < 0.60 or wait > 12:
            self.stats["capacity_refused"] += 1
            return
        extra = Work()
        wrong = 0
        transferred = 0
        new_adaptations = []
        effective_selected = []
        for skill in selected:
            failed = False
            if skill.owner != owner and owner not in skill.adaptations:
                success = uniform(self.seed, "adapt", skill.source_job, owner, skill.key) < self.s.transfer_success
                new_adaptations.append((skill, success))
                if not success:
                    extra += self.missing_work(owner, lead["domain"], skill.key[1], week)
                    failed = True
                    missing.append(skill.key[1])
                if uniform(self.seed, "harmful", skill.source_job, owner, skill.key) < self.s.harmful_transfer:
                    wrong += 1
            elif skill.owner != owner and not skill.adaptations[owner]:
                extra += self.missing_work(owner, lead["domain"], skill.key[1], week)
                failed = True
                missing.append(skill.key[1])
            if owner in skill.harmful_adaptations:
                wrong += 1
            if skill.owner != owner:
                transferred += 1
            if not skill.valid:
                wrong += 1
            if not failed:
                effective_selected.append(skill)
        selected = effective_selected
        transferred = sum(skill.owner != owner for skill in selected)
        if not any(x.key[1] == 1 for x in selected):
            validation = VALIDATION[lead["depth"] - 1]
        production += extra
        max_cost = (production + validation + CORRECTION + validation + PACKAGING).cost(self.s) + price * 0.025
        key = f"job-{lead['id']}"
        floor = self.fixed_cost() * self.p.reserve_weeks
        if self.ledger.available(floor) < max_cost or not self.ledger.reserve(key, max_cost, week):
            self.stats["cash_refused"] += 1
            return
        for skill, success in new_adaptations:
            skill.adaptations[owner] = success
            self.stats["successful_transfer" if success else "failed_transfer"] += 1
            if uniform(self.seed, "harmful", skill.source_job, owner, skill.key) < self.s.harmful_transfer:
                self.stats["harmful_transfer"] += 1
                skill.harmful_adaptations.add(owner)
        job = Job(lead["id"], lead["domain"], lead["depth"], week, price, h, owner,
                  week + max(5, math.ceil(wait) + 3), production, validation, missing, selected, wrong,
                  transferred=transferred)
        job.start("production", production)
        self.jobs.append(job)
        self.last_order_week = week
        self.stats["orders"] += 1
        self.sample_prices.append(ratio)
        for skill in selected:
            skill.uses += 1
            skill.recipients.add(owner)
        self.log(week, "order", job=job.id, domain=DOMAINS[job.domain], depth=job.depth, price=price,
                 human_reference=h, owner=owner, missing=missing,
                 skills=[list(x.key) for x in selected], max_funded_cost=round(max_cost, 2))

    def stage_work(self, job: Job) -> Work:
        if job.stage == "production":
            return job.production
        if job.stage == "correction":
            return CORRECTION
        if job.stage == "packaging":
            return PACKAGING
        return job.validation

    def correctness(self, job: Job, week: int) -> bool:
        load = len(self.jobs) / self.s.agents
        spec_good = uniform(self.seed, "spec", job.id) >= self.s.spec_error
        impl_error = min(0.80, self.s.implementation_error + 0.025 * (job.depth - 1)
                         + self.s.quality_decay_load * max(0, load - 1))
        impl_good = uniform(self.seed, "implementation", job.id) >= impl_error
        component_good = all(uniform(self.seed, "component", job.id, k) >
                             (0.025 if self.known[job.owner][job.domain] else 0.065) for k in job.missing)
        common = uniform(self.seed, "common", week) < self.s.common_fault_probability
        job.common_blind = common and uniform(self.seed, "common_affects", job.id) < 0.65
        common_good = not job.common_blind
        return spec_good and impl_good and component_good and common_good and job.wrong_components == 0

    def validator_pass(self, job: Job, week: int) -> bool:
        if job.true_correct:
            passed = uniform(self.seed, "false_reject", job.id, job.corrections) >= self.s.false_rejection
            if not passed:
                self.stats["false_rejections"] += 1
            return passed
        executable = uniform(self.seed, "error_type", job.id) < 0.65
        common = job.common_blind or uniform(self.seed, "common", week) < self.s.common_fault_probability
        detection = self.s.executable_detection if executable else self.s.semantic_detection
        if common and not executable:
            detection *= 0.35
        return uniform(self.seed, "detect", job.id, job.corrections) > detection

    def complete(self, job: Job, week: int, passed: bool) -> None:
        late = week > job.deadline
        delivered = passed and not late
        useful = delivered and bool(job.true_correct)
        self.stats["completed"] += 1
        self.stats["late"] += int(late)
        self.stats["accepted_useful"] += int(useful)
        self.stats["false_passes"] += int(delivered and not job.true_correct)
        self.stats["abstentions"] += int(not delivered)
        self.stats["recipient_useful"] += int(useful and job.transferred > 0)
        self.stats[f"useful_depth_{job.depth}"] += int(useful)
        if useful:
            self.stats["customer_savings_cents"] += cents(max(0, job.human_reference - job.price))
            for skill in job.selected:
                skill.useful_recipients.add(job.owner)
        outcome = {"job": job.id, "week": week, "domain": job.domain, "depth": job.depth,
                   "owner": job.owner, "true_correct": job.true_correct, "delivered": delivered,
                   "useful": useful, "late": late, "price": job.price,
                   "transferred": job.transferred, "duration": week - job.born + 1}
        self.outcomes.append(outcome)
        self.log(week, "outcome", **{k: v for k, v in outcome.items() if k != "week"})
        if delivered:
            default = uniform(self.seed, "default", job.id) < self.s.default_probability
            collect_week = week + self.s.collection_delay
            self.receipts.append({"week": collect_week, "job": job.id, "amount": job.price,
                                  "default": default, "wrong": not job.true_correct})
            if useful and uniform(self.seed, "repeat", job.id) < self.s.repeat_probability:
                self.repeat_leads[week + 8].append((job.domain, job.depth, job.id))
        elif not job.true_correct:
            self.ledger.spend(job.price * 0.025, week, "failed_job_recovery", f"job-{job.id}")
        self.ledger.release(f"job-{job.id}", week)
        self.jobs.remove(job)
        self.trust = min(0.95, max(0.35, self.trust * 0.985 + (0.95 if delivered else 0.40) * 0.015))
        if delivered:
            self.generate_candidates(job, week)
            if self.arm != "no_retention" and uniform(self.seed, "ordinary_learning", job.id) < self.s.ordinary_learning_rate:
                self.known[job.owner][job.domain] = True

    def generate_candidates(self, job: Job, week: int) -> None:
        if self.arm in {"no_retention", "network_no_invest", "beta"}:
            return
        for kind in job.missing:
            if uniform(self.seed, "invention", job.id, kind) >= self.s.invention_probability:
                self.stats["invention_search_failed"] += 1
                continue
            key = (job.domain, kind, job.owner)
            self.candidates.setdefault(key, Candidate((job.domain, kind), job.owner, job.id, week,
                                                     f"campaign-{job.id}-{kind}", bool(job.true_correct)))
            self.stats["candidate_events"] += 1
            self.log(week, "candidate", job=job.id, owner=job.owner, key=list(key),
                     campaign=f"campaign-{job.id}-{kind}")

    def work_jobs(self, week: int, tick: float = 1.0) -> None:
        producers = {c.owner for item in self.pending_investments for c in item["candidates"]}
        validators = min(self.s.validator_slots, len(self.pending_investments))
        producer_admin = min(self.s.agents, math.ceil(max(0, self.producer_overhead_remaining - 1e-9) / tick))
        validator_admin = min(max(0, self.s.validator_slots - validators),
                              math.ceil(max(0, self.validator_overhead_remaining - 1e-9) / tick))
        producers.update(range(producer_admin))
        validators += validator_admin
        self.producer_overhead_remaining = max(0, self.producer_overhead_remaining - producer_admin * tick)
        self.validator_overhead_remaining = max(0, self.validator_overhead_remaining - validator_admin * tick)
        for job in list(self.jobs):
            if any(not self.eligible(skill, job.owner, job.domain, skill.key[1], week) for skill in job.selected):
                self.stats["current_skill_refusals"] += 1
                self.complete(job, week, False)
                continue
            if job.stage in {"validation", "revalidation"}:
                if validators >= self.s.validator_slots:
                    self.stats["validator_wait_weeks"] += tick
                    continue
                validators += 1
            else:
                if job.owner in producers:
                    self.stats["producer_wait_weeks"] += tick
                    continue
                producers.add(job.owner)
            work = self.stage_work(job)
            time_fraction = min(1.0, tick / job.remaining_latency if job.remaining_latency > 1e-9 else 1.0)
            fraction = min(time_fraction,
                           self.input_budget / job.remaining_input if job.remaining_input > 1e-9 else 1.0,
                           self.output_budget / job.remaining_output if job.remaining_output > 1e-9 else 1.0)
            portion = job.remaining_input / work.input_m * fraction if work.input_m else 0
            if portion > 1e-10:
                n = min(cents(work.cost(self.s) * portion), cents(work.cost(self.s)) - job.stage_paid_cents)
                if fraction >= 1 - 1e-9:
                    n = cents(work.cost(self.s)) - job.stage_paid_cents
                if not self.pay_work(work.scale(portion), week, job.stage, f"job-{job.id}", n / 100):
                    continue
                job.stage_paid_cents += n
            self.input_budget -= job.remaining_input * fraction
            self.output_budget -= job.remaining_output * fraction
            job.remaining_input *= 1 - fraction
            job.remaining_output *= 1 - fraction
            job.remaining_latency *= 1 - fraction
            if fraction < time_fraction - 1e-9:
                self.stats["quota_wait_weeks"] += tick
            if job.remaining_input > 1e-8 or job.remaining_output > 1e-8 or job.remaining_latency > 1e-8:
                continue
            if job.stage == "production":
                job.true_correct = self.correctness(job, week)
                job.start("validation", job.validation)
            elif job.stage == "correction":
                if uniform(self.seed, "correction", job.id) < self.s.correction_success * (0.50 if job.common_blind else 1):
                    job.true_correct = True
                job.start("revalidation", job.validation)
            elif job.stage in {"validation", "revalidation"}:
                passed = self.validator_pass(job, week)
                if passed:
                    job.start("packaging", PACKAGING)
                elif job.corrections == 0:
                    job.corrections = 1
                    self.stats["corrections"] += 1
                    job.start("correction", CORRECTION)
                else:
                    self.stats["correction_failed"] += 1
                    self.complete(job, week, False)
            else:
                self.complete(job, week, True)

    def settle_receipts(self, week: int) -> None:
        for item in list(self.receipts):
            if item["week"] > week:
                continue
            self.receipts.remove(item)
            if item.get("refund"):
                self.ledger.warranty.pop(str(item["job"]), None)
                if not self.ledger.spend(item["amount"], week, "refund_and_recovery"):
                    self.stats["cash_shortfall"] = 1
                    self.new_work = False
                self.stats["refunded"] += 1
                self.trust = max(0.35, self.trust - 0.06)
            elif item["default"]:
                self.stats["defaulted"] += 1
            else:
                self.ledger.receive(item["amount"], week, str(item["job"]), self.s.warranty_weeks)
                self.stats["collected_jobs"] += 1
                if item["wrong"] and uniform(self.seed, "refund", item["job"]) < self.s.refund_probability:
                    self.receipts.append({"week": week + self.s.warranty_weeks, "job": item["job"],
                                          "amount": item["amount"] * 1.10, "refund": True})

    def beta_version(self, week: int) -> str:
        epoch = week // self.s.beta_epoch_weeks if self.s.external_improvement else 0
        return f"beta-2026-10-26-epoch-{epoch}"

    def alpha_assess(self, candidates: list[Candidate], week: int, construction_cost: float,
                     continuation: bool = False, remaining_life: int | None = None) -> dict[str, Any]:
        """Compare matched modeled recipient/depth missions against competent Beta.

        No private validity or future buyer draw enters this decision. Every probe
        permits the baseline its cheapest current retained method or competent
        reconstruction, with the same ordinary knowledge, tools and job scope.
        Probe values are deterministic cost-model consequences, not experiments.
        """
        if not candidates or len({c.key[0] for c in candidates}) != 1:
            raise ValueError("Alpha assessment requires a nonempty same-domain candidate bundle")
        domain = candidates[0].key[0]
        horizon = max(0, min(self.s.useful_lifetime, self.s.weeks - week))
        if remaining_life is not None:
            horizon = min(horizon, max(0, remaining_life))
        demand = self.p.forecast_weight * self.observed_leads + (1 - self.p.forecast_weight) * self.s.leads_per_week
        reuse = min(demand * self.conversion * horizon / self.s.diversity, horizon * self.s.agents / 6)
        owners = {x.owner for x in candidates}
        recipients = tuple(sorted(owners)) if self.arm == "isolated" else tuple(range(self.s.agents))
        if self.arm == "isolated":
            reuse /= self.s.agents
        reuse *= (1 - self.s.obsolete_hazard) ** (horizon / 2)
        identities = {(c.key, c.owner, c.source_job) for c in candidates}
        reassessed = {
            (s.key, s.owner, s.source_job): s for s in self.skills
            if continuation and (s.key, s.owner, s.source_job) in identities
        }
        excluded = {id(s) for s in reassessed.values()}
        integration_unit = INTEGRATION.cost(self.s) * self.s.transfer_validation_factor

        def option(asset: Skill | Candidate, recipient: int, kind: int, depth: int,
                   *, proposed: bool = False) -> dict[str, Any] | None:
            if self.arm == "isolated" and asset.owner != recipient:
                return None
            ordinary = self.missing_work(recipient, domain, kind, week).cost(self.s)
            known_asset = reassessed.get((asset.key, asset.owner, asset.source_job)) if proposed else asset
            adaptations = known_asset.adaptations if isinstance(known_asset, Skill) else {}
            if asset.owner != recipient and (self.known[recipient][domain] or adaptations.get(recipient) is False):
                return None
            if self.arm == "duplicate":
                residual = 1.0
            else:
                fraction = 0.90 if asset.owner == recipient else 0.78
                residual = max(0.0, 1 - fraction * self.s.reuse_savings_factor)
            transfer = asset.owner != recipient
            success = 1.0 if not transfer or adaptations.get(recipient) is True else self.s.transfer_success
            recovery = (1 - success) * ordinary
            risk = self.s.harmful_transfer * (CORRECTION + VALIDATION[depth - 1]).cost(self.s) if transfer else 0.0
            return {"method": "proposed-bundle" if proposed else "current-retained-capability",
                    "identity": [list(asset.key), asset.owner, asset.source_job],
                    "reconstruction": ordinary * residual,
                    "integration": integration_unit if transfer or self.arm == "duplicate" else 0.0,
                    "operating": recovery, "risk": risk}

        def total(method: dict[str, Any]) -> float:
            return sum(method[k] for k in ("reconstruction", "integration", "operating", "risk"))

        probes = []
        for recipient in recipients:
            for depth in (1, 2, 3):
                baseline_parts, proposed_parts = [], []
                for kind in range(depth):
                    baseline = {"method": "competent-reconstruction", "identity": None,
                                "reconstruction": self.missing_work(recipient, domain, kind, week).cost(self.s),
                                "integration": 0.0, "operating": 0.0, "risk": 0.0}
                    for skill in self.skills:
                        if id(skill) in excluded or not self.eligible(skill, recipient, domain, kind, week):
                            continue
                        alternative = option(skill, recipient, kind, depth)
                        if alternative is not None and total(alternative) < total(baseline):
                            baseline = alternative
                    proposed = baseline
                    for candidate in candidates:
                        if candidate.key != (domain, kind):
                            continue
                        alternative = option(candidate, recipient, kind, depth, proposed=True)
                        if alternative is not None and total(alternative) < total(proposed):
                            proposed = alternative
                    baseline_parts.append(baseline)
                    proposed_parts.append(proposed)
                base = {k: sum(m[k] for m in baseline_parts)
                        for k in ("reconstruction", "integration", "operating", "risk")}
                added = {k: sum(m[k] for m in proposed_parts) for k in base}
                # Preserve exact net pair arithmetic with nonnegative cost lines:
                # reductions in existing integration/recovery/risk are gross gains;
                # increases are charged once in the corresponding cost category.
                increments = {k: added[k] - base[k] for k in ("integration", "operating", "risk")}
                gross = base["reconstruction"] - added["reconstruction"]
                gross += sum(max(0.0, -value) for value in increments.values())
                common = (PRODUCTION[depth - 1] + VALIDATION[depth - 1] + PACKAGING).cost(self.s)
                probes.append({"recipient": recipient, "depth": depth,
                               "weight": self.s.depth_weights[depth - 1] / len(recipients),
                               "baseline_methods": baseline_parts, "proposed_methods": proposed_parts,
                               "baseline_delivery_cost": common + sum(base.values()),
                               "proposed_delivery_cost": common + sum(added.values()),
                               "gross_gain_before_incremental_costs": gross,
                               "incremental_integration": max(0.0, increments["integration"]),
                               "incremental_operating": max(0.0, increments["operating"]),
                               "incremental_risk": max(0.0, increments["risk"])})
        mass = sum(p["weight"] for p in probes)

        def average(field: str) -> float:
            return sum(p["weight"] * p[field] for p in probes) / mass

        gross = average("gross_gain_before_incremental_costs")
        active_count = sum(s.active and id(s) not in excluded for s in self.skills)
        costs = AlphaCosts(
            construction=construction_cost * 0.70,
            validation=construction_cost * 0.20,
            migration=construction_cost * 0.10,
            acquisition=0 if continuation else len(candidates) * self.s.sharing_bounty,
            integration=average("incremental_integration") * reuse,
            operating=average("incremental_operating") * reuse,
            risk=average("incremental_risk") * reuse,
            maintenance=len(candidates) * horizon * (self.s.maintenance_per_skill
                        + REVALIDATE.cost(self.s) / self.s.revalidation_period),
            distribution=(self.s.distribution_fixed + self.s.membership_count * self.s.member_overhead)
                         * horizon * len(candidates) / max(1, active_count + len(candidates))
                         if self.arm != "isolated" else 0,
        )
        capabilities = [
            {"key": list(s.key), "owner": s.owner, "source_job": s.source_job,
             "version": s.version, "beta_version": s.beta_version,
             "adaptations": sorted(s.adaptations.items()), "bundle_id": s.bundle_id}
            for s in self.skills if id(s) not in excluded
            and any(self.eligible(s, a, s.key[0], s.key[1], week) for a in recipients)
        ]
        assessment = AlphaAssessment(
            beta_id=self.beta_version(week), comparator_capability_set_hash=hashlib.sha256(canonical(
                {"beta_id": self.beta_version(week), "known": self.known, "available": capabilities,
                 "recipients": recipients, "week": week})).hexdigest(),
            scope=(DOMAINS[domain], "bounded-protocol-design", "joint-bundle" if len(candidates) > 1 else "single-component"),
            paired_gains=tuple(p["gross_gain_before_incremental_costs"] for p in probes),
            paired_weights=tuple(p["weight"] for p in probes), planned_reuse=reuse, costs=costs,
            uncertainty_margin_per_use=0.20 * max(0.0, gross),
            source_kind="simulation", protocol_id="matched-recipient-depth-cost-probes-v2",
            evidence_hash=hashlib.sha256(canonical(probes)).hexdigest(),
            dependency_hashes=tuple(hashlib.sha256(canonical(
                [list(c.key), c.owner, c.source_job, c.campaign_id])).hexdigest() for c in candidates),
            redundant=self.arm == "duplicate" or gross <= 0,
        )
        decision = evaluate_alpha(assessment)
        return {"assessment": asdict(assessment), "decision": asdict(decision), "continuation": continuation,
                "remaining_life": remaining_life, "horizon": horizon, "paired_probes": probes,
                "assumptions": {
                    "recipient_weights": "uniform over authorized modeled recipients; stated task-depth probabilities",
                    "unknown_adaptation": "conservative fresh-attempt recovery charge on each modeled use",
                    "risk": "incremental harmful-transfer probability times correction plus frontier revalidation cost",
                    "quality_and_capacity_upside": "excluded from this direct cost probe",
                    "uncertainty_margin": "declared 20% of mean gross benefit, not statistical confidence",
                    "continuation": "exclude exactly reassessed identities, preserve their observed adaptation state",
                },
                "limitation": "Deterministic matched cost-model counterfactuals and forecast reuse; no empirical mission validation."}

    def age_skills(self, week: int) -> None:
        assessed_bundles: set[str] = set()
        for skill in self.skills:
            if not skill.active:
                continue
            if week >= skill.expiry or uniform(self.seed, "obsolete", skill.source_job, skill.key, week) < self.s.obsolete_hazard:
                skill.active = False
                self.stats["retired_skills"] += 1
                self.log(week, "retire", key=list(skill.key), source_job=skill.source_job)
                continue
            if skill.beta_version != self.beta_version(week):
                bundle = [x for x in self.skills if x.active and (x.bundle_id == skill.bundle_id if skill.bundle_id else x is skill)]
                token = skill.bundle_id or str(skill.source_job) + str(skill.key)
                if token not in assessed_bundles:
                    assessed_bundles.add(token)
                    work = REVALIDATE.scale(len(bundle))
                    if self.ledger.available() < work.cost(self.s) or not self.consume(work):
                        self.stats["stale_beta_assessment"] += 1
                        continue
                    self.pay_work(work, week, "moving_beta_alpha_reassessment")
                    self.validator_overhead_remaining += work.latency
                    candidates = [Candidate(x.key, x.owner, x.source_job, x.born, "continuation", x.valid) for x in bundle]
                    alpha = self.alpha_assess(candidates, week, 0, True,
                                              remaining_life=min(x.expiry - week for x in bundle))
                    for x in bundle:
                        if alpha["decision"]["accepted"]:
                            x.beta_version = self.beta_version(week)
                            x.alpha_assessment = alpha
                            x.alpha_net_lower = alpha["decision"]["lower_net"]
                        else:
                            x.active = False
                            self.stats["retired_into_beta"] += 1
                    self.log(week, "beta_reassessment", keys=[list(x.key) for x in bundle], alpha=alpha)
                if not skill.active or skill.beta_version != self.beta_version(week):
                    continue
            if week >= skill.next_check:
                if self.ledger.available() < REVALIDATE.cost(self.s) or not self.consume(REVALIDATE):
                    self.stats["stale_skill_weeks"] += 1
                    continue
                self.pay_work(REVALIDATE, week, "skill_revalidation")
                self.validator_overhead_remaining += REVALIDATE.latency
                detected_defect = not skill.valid and uniform(self.seed, "revalidation_detect", skill.source_job, week) >= self.s.revalidation_false_negative
                failure = detected_defect or uniform(self.seed, "revalidate", skill.source_job, week) < self.s.revalidation_failure
                if failure:
                    skill.active = False
                    self.stats["revoked_skills"] += 1
                    self.log(week, "revoke", key=list(skill.key), source_job=skill.source_job)
                else:
                    skill.next_check = week + self.s.revalidation_period
            if skill.active:
                if not self.ledger.spend(self.s.maintenance_per_skill, week, "skill_maintenance"):
                    self.stats["cash_shortfall"] = 1
                    self.new_work = False

    def investment_cost(self, candidates: list[Candidate]) -> float:
        return sum(CONSTRUCTION[x.key[1]].cost(self.s) for x in candidates) * self.s.construction_cost_factor
        
    def evaluate_investment(self, week: int) -> None:
        if not self.p.invest or self.arm in {"no_retention", "network_no_invest", "beta"} or not self.new_work:
            return
        if self.pending_investments or week % 4 or week >= self.s.weeks - 12 or not self.candidates:
            return
        if self.ledger.available() < EVALUATION.cost(self.s) or not self.consume(EVALUATION):
            return
        self.pay_work(EVALUATION, week, "investment_evaluation")
        self.producer_overhead_remaining += EVALUATION.latency
        options: list[list[Candidate]] = []
        for d in range(self.s.diversity):
            domain_candidates = []
            for kind in range(3):
                candidates = [x for x in self.candidates.values() if x.key == (d, kind)
                              and not any(self.eligible(s, x.owner, d, kind, week) for s in self.skills)]
                if candidates:
                    domain_candidates.append(min(candidates, key=lambda x: x.week))
            options.extend([[x] for x in domain_candidates])
            if self.p.allow_bundles and len(domain_candidates) > 1:
                options.append(domain_candidates)
        if not options:
            return
        scored = []
        paid = sum(x["paid_cents"] for x in self.ledger.records if x["kind"] == "expense")
        collected = sum(x["amount_cents"] for x in self.ledger.records if x["kind"] == "collection")
        observed_weekly_margin = max(0, (collected - paid) / 100 / max(1, week))
        spare_capacity = max(0, 1 - len(self.jobs) / self.s.agents)
        for option in options:
            cost = self.investment_cost(option)
            appraisal = self.alpha_assess(option, week, cost)["decision"]
            # Technical success is uncertain. Build costs are paid even when it fails;
            # benefits and upkeep conditional on admission must not be credited for free.
            admission_probability = (self.s.construction_success * (1 - self.s.asset_defect_probability)
                                     * (1 - self.s.admission_false_rejection)) ** len(option)
            expected = (appraisal["expected_net"] + cost) * admission_probability - cost
            duration = sum(CONSTRUCTION[x.key[1]].latency for x in option) * self.s.construction_cost_factor
            foregone_margin = observed_weekly_margin * duration * (1 - spare_capacity) / self.s.agents
            score = min(expected, appraisal["lower_net"]) - (self.p.hurdle - 1) * cost - foregone_margin
            scored.append((score, option))
        advantage, chosen = max(scored, key=lambda x: x[0])
        cost = self.investment_cost(chosen)
        floor = self.fixed_cost() * self.p.reserve_weeks
        available = self.ledger.available(floor)
        earned = (sum(x["amount_cents"] for x in self.ledger.records if x["kind"] == "collection")
                  - sum(x["paid_cents"] for x in self.ledger.records if x["kind"] == "expense")) / 100
        if advantage <= 0 or cost > available * self.p.max_investment_share:
            self.stats["investment_waits"] += 1
            self.log(week, "wait", expected_increment=round(advantage, 2), cost=round(cost, 2),
                     available=round(available, 2))
            return
        key = f"investment-{len(self.investments)}"
        bounty = len(chosen) * self.s.sharing_bounty
        if not self.ledger.reserve(key, cost + bounty, week):
            self.stats["investment_waits"] += 1
            return
        item = {"id": key, "week": week, "candidates": chosen, "cost": cost, "bounty": bounty,
                "remaining_input": sum(CONSTRUCTION[c.key[1]].input_m for c in chosen) * self.s.construction_cost_factor,
                "remaining_output": sum(CONSTRUCTION[c.key[1]].output_m for c in chosen) * self.s.construction_cost_factor,
                "total_input": sum(CONSTRUCTION[c.key[1]].input_m for c in chosen) * self.s.construction_cost_factor,
                "remaining_latency": sum(CONSTRUCTION[c.key[1]].latency for c in chosen) * self.s.construction_cost_factor,
                "forecast_net": advantage, "paid_cents": 0}
        self.pending_investments.append(item)
        self.investments.append({"id": key, "week": week, "cost": round(cost + bounty, 2),
                                 "forecast_net": round(advantage, 2), "available_before": round(available, 2),
                                 "earned_cash_before": round(earned, 2),
                                 "funding_basis": "operating-surplus" if earned >= cost + bounty else "seed-or-mixed",
                                 "skills": [list(x.key) for x in chosen], "source_jobs": [x.source_job for x in chosen]})
        self.log(week, "investment", **{k: v for k, v in self.investments[-1].items() if k != "week"})
        for c in chosen:
            self.candidates.pop((*c.key, c.owner), None)

    def build_skills(self, week: int, tick: float = 1.0) -> None:
        for item in list(self.pending_investments):
            fraction = min(1.0, tick / item["remaining_latency"] if item["remaining_latency"] > 1e-9 else 1.0,
                           self.input_budget / item["remaining_input"] if item["remaining_input"] else 1.0,
                           self.output_budget / item["remaining_output"] if item["remaining_output"] else 1.0)
            portion = item["remaining_input"] / item["total_input"] * fraction
            if portion > 1e-10:
                n = min(cents(item["cost"] * portion), cents(item["cost"]) - item["paid_cents"])
                if fraction >= 1 - 1e-9:
                    n = cents(item["cost"]) - item["paid_cents"]
                item["paid_cents"] += n
                self.ledger.spend(n / 100, week, "capability_search_build_confirm_migrate", item["id"],
                                  input_m=item["remaining_input"] * fraction,
                                  output_m=item["remaining_output"] * fraction)
            self.input_budget -= item["remaining_input"] * fraction
            self.output_budget -= item["remaining_output"] * fraction
            item["remaining_input"] *= 1 - fraction
            item["remaining_output"] *= 1 - fraction
            item["remaining_latency"] *= 1 - fraction
            self.stats["invention_capacity_weeks"] += tick
            if item["remaining_input"] > 1e-8 or item["remaining_output"] > 1e-8 or item["remaining_latency"] > 1e-8:
                continue
            assessments = []
            for c in item["candidates"]:
                constructed = uniform(self.seed, "construct", c.source_job, c.key) < self.s.construction_success
                valid = constructed and c.task_valid and uniform(self.seed, "asset_defect", c.source_job, c.key) >= self.s.asset_defect_probability
                technical_pass = (valid and uniform(self.seed, "asset_reject", c.source_job, c.key) > self.s.admission_false_rejection)
                technical_pass |= (not valid and uniform(self.seed, "asset_falsepass", c.source_job, c.key) < self.s.admission_false_pass)
                assessments.append((c, constructed, valid, technical_pass))
            alpha = self.alpha_assess(item["candidates"], week, item["cost"])
            admitted = all(x[3] for x in assessments) and alpha["decision"]["accepted"]
            self.log(week, "alpha_assessment", campaign=item["id"], alpha=alpha,
                     technical_pass=all(x[3] for x in assessments), admitted=admitted)
            for c, constructed, valid, _ in assessments:
                if admitted:
                    skill = Skill(c.key, c.owner, week, week + self.s.useful_lifetime,
                                  week + self.s.revalidation_period, valid, source_job=c.source_job,
                                  beta_version=self.beta_version(week), alpha_net_lower=alpha["decision"]["lower_net"],
                                  alpha_assessment=alpha, bundle_id=item["id"],
                                  bundle_keys=tuple(x.key for x in item["candidates"]))
                    self.skills.append(skill)
                    self.stats["admitted_skills"] += 1
                    self.stats["invalid_admissions"] += int(not valid)
                    self.ledger.spend(self.s.sharing_bounty, week, "creator_bounty", item["id"])
                    self.log(week, "admit", key=list(c.key), owner=c.owner, source_job=c.source_job,
                             latent_valid=valid, available_to="all_authenticated_direct_agent_members" if self.arm != "isolated" else "owner_counterfactual")
                else:
                    self.stats["rejected_constructions"] += 1
                    self.stats["alpha_assessment_rejections"] += int(not alpha["decision"]["accepted"])
                    self.log(week, "reject", key=list(c.key), source_job=c.source_job, constructed=constructed)
            self.ledger.release(item["id"], week)
            self.pending_investments.remove(item)

    def run(self) -> dict[str, Any]:
        for week in range(1, self.s.weeks + self.s.runoff + 1):
            self.input_budget, self.output_budget = self.s.quota_input_m, self.s.quota_output_m
            # Exogenous ordinary-method diffusion, including copying, is shared by
            # every counterfactual arm. Network authentication is not a copying barrier.
            for owner in range(self.s.agents):
                for domain in range(self.s.diversity):
                    if uniform(self.seed, "copying", owner, domain, week) < self.s.copying_hazard:
                        self.known[owner][domain] = True
            self.ledger.age(week)
            self.settle_receipts(week)
            operating = bool(self.jobs or self.pending_investments or (week <= self.s.weeks and self.new_work))
            winding_down = bool(self.receipts or self.ledger.warranty)
            if operating or winding_down:
                overhead = self.fixed_cost() if operating else 60.0
                if not self.ledger.spend(overhead, week, "infrastructure_access_storage"):
                    self.stats["cash_shortfall"] = 1
                    self.new_work = False
                if week <= self.s.weeks and self.new_work:
                    self.age_skills(week)
            for _ in range(self.s.ticks_per_week):
                self.work_jobs(week, 1 / self.s.ticks_per_week)
                self.build_skills(week, 1 / self.s.ticks_per_week)
            if week <= self.s.weeks:
                before = self.stats["orders"]
                leads = list(self.arrivals[week - 1])
                for d, depth, parent in self.repeat_leads.get(week, []):
                    leads.append({"id": 1000000 + parent, "domain": d, "depth": depth,
                                  "value": self.s.demand_value, "urgency": 0.035, "human_quality": 0.95})
                for lead in leads:
                    self.sell(lead, week)
                self.observed_leads = 0.90 * self.observed_leads + 0.10 * len(leads)
                if leads:
                    self.conversion = 0.9 * self.conversion + 0.1 * (self.stats["orders"] - before) / len(leads)
                self.evaluate_investment(week)
                if week - self.last_order_week >= self.p.abandon_after_idle_weeks and not self.jobs:
                    self.new_work = False
                    self.stats["abandoned_idle_business"] = 1
            self.max_input = max(self.max_input, self.s.quota_input_m - self.input_budget)
            self.max_output = max(self.max_output, self.s.quota_output_m - self.output_budget)
            self.weekly.append({"week": week, "cash": self.ledger.cash / 100,
                                "available": self.ledger.available(), "committed": self.ledger.reserved / 100,
                                "jobs": len(self.jobs), "skills": sum(self.eligible(x, x.owner, *x.key, week) for x in self.skills),
                                "skills_active_flags": sum(x.active for x in self.skills),
                                "useful": self.stats["accepted_useful"], "trust": round(self.trust, 4),
                                "input_m": round(self.s.quota_input_m - self.input_budget, 5),
                                "output_m": round(self.s.quota_output_m - self.output_budget, 5)})
        expenses = [x for x in self.ledger.records if x["kind"] == "expense"]
        collections = sum(x["amount_cents"] for x in self.ledger.records if x["kind"] == "collection")
        for x in expenses:
            self.costs[x["category"]] += x["amount_cents"] / 100
        total_expense = sum(x["amount_cents"] for x in expenses)
        closing_obligations = self.ledger.unpaid + sum(self.ledger.committed.values())
        # Outstanding receivables are disclosed but never treated as cash or terminal profit.
        future_refunds = cents(sum(x["amount"] for x in self.receipts if x.get("refund")))
        closing_obligations += future_refunds
        profit = (collections - total_expense - sum(self.ledger.committed.values()) - future_refunds) / 100
        assert abs(self.ledger.cash - cents(self.s.seed_capital) - collections
                   + sum(x["paid_cents"] for x in expenses)) == 0
        assert self.ledger.cash >= 0
        assert self.max_input <= self.s.quota_input_m + 1e-6 and self.max_output <= self.s.quota_output_m + 1e-6
        result = {"model": MODEL_VERSION, "scenario": self.s.name, "seed": self.seed, "arm": self.arm,
                  "policy": asdict(self.p), "stats": dict(self.stats), "profit": round(profit, 2),
                  "cash": self.ledger.cash / 100, "seed_capital": self.s.seed_capital,
                  "collections": collections / 100, "costs": {k: round(v, 2) for k, v in self.costs.items()},
                  "expenses": total_expense / 100, "closing_obligations": closing_obligations / 100,
                  "available_cash": self.ledger.available(), "mean_price_ratio":
                      sum(self.sample_prices) / len(self.sample_prices) if self.sample_prices else None,
                  "investment_count": len(self.investments), "investment_cost":
                      round(sum(self.costs[k] for k in ("capability_search_build_confirm_migrate", "creator_bounty", "investment_evaluation")), 2),
                  "investment_budget_committed": round(sum(x["cost"] for x in self.investments), 2),
                  "unique_invention_campaigns": len({s.source_job for s in self.skills}),
                  "recipient_exposed_valid_skills": sum(s.valid and len(s.recipients - {s.owner}) > 0 for s in self.skills),
                  "skills_used_on_useful_recipient_jobs": sum(s.valid and len(s.useful_recipients - {s.owner}) > 0 for s in self.skills),
                  "reused_skills": sum(s.uses > 0 and s.valid for s in self.skills),
                  "min_cash": min(x["cash"] for x in self.weekly),
                  "max_input_m": self.max_input, "max_output_m": self.max_output,
                  "unfinished_jobs": len(self.jobs), "receivables":
                      round(sum(x["amount"] for x in self.receipts if not x.get("refund")), 2),
                  "investments": self.investments,
                  "status": {"actual_sales": 0, "live_model_calls": 0, "live_ens": False,
                             "human_provider_hours": 0, "crypto_enforcement": "simulated"}}
        if self.retain:
            result.update(ledger=self.ledger.records, events=self.events, weekly=self.weekly, outcomes=self.outcomes,
                          skills=[{**asdict(x), "recipients": sorted(x.recipients),
                                   "useful_recipients": sorted(x.useful_recipients),
                                   "harmful_adaptations": sorted(x.harmful_adaptations),
                                   "adaptations": {str(k): v for k, v in x.adaptations.items()}} for x in self.skills])
        return result


def simulate(scenario: Scenario, policy: Policy, seed: int, arm: str = "network", retain: bool = False) -> dict[str, Any]:
    return Enterprise(scenario, policy, seed, arm, retain).run()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="central")
    parser.add_argument("--seed", type=int, default=104729)
    parser.add_argument("--arm", default="network")
    parser.add_argument("--out", type=Path, default=Path("results/single_run.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = simulate(SCENARIOS[args.scenario], Policy(), args.seed, args.arm, True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("scenario", "arm", "profit", "cash", "stats", "investment_count")}))


if __name__ == "__main__":
    main()
