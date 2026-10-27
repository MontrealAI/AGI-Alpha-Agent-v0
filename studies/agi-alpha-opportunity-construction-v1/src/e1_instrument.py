# SPDX-License-Identifier: Apache-2.0
"""Construct bounded, synthetic joint-roster and funded-care commitment packages.

The enumeration is conventional. The experimental object is the complete
finite commitment package. This program neither provides childcare nor
establishes licensing, actual consent, customer demand, or commercial novelty.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

Json = dict[str, Any]
CATEGORIES = {
    "primary_care",
    "backup_standby",
    "backup_activation_reserve",
    "worker_compensation",
    "coordination_fee",
}
HARD_LIMITS = {"workers": 12, "children": 8, "offers": 8, "scenarios": 6}
MODES = (
    "fixed_roster_pooled_care",
    "flexible_without_opening_commitment",
    "combined",
    "ordinary_exact_same_formulation",
)


class SearchLimit(RuntimeError):
    """The finite search budget was reached; no infeasibility claim follows."""


def digest(value: Any) -> str:
    """Hash canonical JSON content."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def indexed(case: Json, key: str) -> dict[str, Json]:
    """Index a uniquely identified collection."""
    return {item["id"]: item for item in case[key]}


def integer(value: Any, name: str, minimum: int = 0) -> None:
    """Require a nonnegative integer rather than an implicit float or boolean."""
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def validate_input(case: Json) -> None:
    """Validate the bounded input contract and references; no legal rules are inferred."""
    if case.get("schema") != "agi-alpha.e1-case.v1" or case.get("synthetic") is not True:
        raise ValueError("Only explicitly synthetic agi-alpha.e1-case.v1 inputs are accepted")
    if case.get("currency") != "CAD":
        raise ValueError("This version requires integer CAD cents")
    horizon = case["horizon"]
    if horizon["operating_days"] != 1 or horizon["maximum_backup_event_worlds_realized"] != 1:
        raise ValueError("This version covers one day and one mutually exclusive realized world")
    if not case["children"]:
        raise ValueError("At least one child is required")
    for key, hard in HARD_LIMITS.items():
        cap = case["limits"].get(f"maximum_{key}", hard)
        integer(cap, f"maximum_{key}", 1)
        if cap > hard or len(case[key]) > cap:
            raise ValueError(f"{key} exceeds the declared or hard bounded limit")
    integer(case["limits"]["maximum_search_states"], "maximum_search_states", 1)
    if case["limits"]["maximum_search_states"] > 1_000_000:
        raise ValueError("maximum_search_states exceeds the hard limit")
    if not 1 <= len(case["shifts"]) <= 4:
        raise ValueError("One to four shifts are supported")
    collections = [
        "shifts",
        "employers",
        "workers",
        "children",
        "providers",
        "locations",
        "staff",
        "offers",
        "scenarios",
        "payers",
    ]
    for key in collections:
        ids = [x["id"] for x in case[key]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {key} identifiers")
    ix = {key: indexed(case, key) for key in collections}
    for shift in case["shifts"]:
        integer(shift["start_minute"], "shift start")
        integer(shift["end_minute"], "shift end")
        if not shift["start_minute"] < shift["end_minute"] <= 1440:
            raise ValueError("Invalid shift interval")
    for employer in case["employers"]:
        if set(employer["staffing_quotas"]) != set(ix["shifts"]):
            raise ValueError("Every employer must declare every shift quota")
        for value in employer["staffing_quotas"].values():
            integer(value, "staffing quota")
    for worker in case["workers"]:
        if worker["employer_id"] not in ix["employers"]:
            raise ValueError("Unknown worker employer")
        if worker["current_shift_id"] not in ix["shifts"]:
            raise ValueError("Unknown current shift")
        if len(worker["permitted_shift_ids"]) != len(set(worker["permitted_shift_ids"])):
            raise ValueError("Duplicate permitted shifts")
        for shift_id in worker["permitted_shift_ids"]:
            if shift_id not in ix["shifts"] or shift_id not in worker["change_compensation_cents"]:
                raise ValueError("Every permitted shift needs explicit compensation")
            integer(worker["change_compensation_cents"][shift_id], "worker compensation")
    for child in case["children"]:
        if child["parent_worker_id"] not in ix["workers"]:
            raise ValueError("Unknown parent worker")
        for location_id in child["acceptable_location_ids"]:
            if location_id not in ix["locations"]:
                raise ValueError("Unknown acceptable location")
            commute = child["commute_minutes_by_location"].get(location_id)
            if commute is None:
                raise ValueError("Every acceptable location requires explicit before/after commute")
            integer(commute["before"], "commute before")
            integer(commute["after"], "commute after")
    for location in case["locations"]:
        integer(location["declared_concurrent_child_capacity"], "location capacity")
        _validate_windows(location["opening_windows"])
    for staff in case["staff"]:
        _validate_windows(staff["available_windows"])
        integer(staff["max_active_minutes"], "max active minutes")
        integer(staff["max_reserved_minutes"], "max reserved minutes")
    for offer in case["offers"]:
        if offer["provider_id"] not in ix["providers"] or offer["location_id"] not in ix["locations"]:
            raise ValueError("Unknown offer provider/location")
        if offer["role"] not in ("primary", "backup"):
            raise ValueError("Offers must explicitly be primary or backup")
        if type(offer["commitment_required"]) is not bool:
            raise ValueError("commitment_required must be boolean")
        _validate_windows([offer["window"]])
        integer(offer["declared_child_capacity"], "offer capacity")
        integer(offer["minimum_qualified_staff"], "minimum qualified staff", 1)
        for name in ("fixed_opening_cost_cents", "per_child_cost_cents", "standby_retainer_cents"):
            integer(offer[name], name)
        if len(offer["staff_ids"]) != len(set(offer["staff_ids"])):
            raise ValueError("A staff member cannot be counted twice within one offer")
        if any(s not in ix["staff"] for s in offer["staff_ids"]):
            raise ValueError("Unknown offer staff")
        if "cost_breakdown" in offer:
            for value in offer["cost_breakdown"].values():
                integer(value, "opening cost component")
            if sum(offer["cost_breakdown"].values()) != offer["fixed_opening_cost_cents"]:
                raise ValueError("Opening cost components must reconcile")
    for provider in case["providers"]:
        if type(provider["declared_offer_acceptance"]) is not bool:
            raise ValueError("Provider acceptance must be explicitly boolean")
    for scenario in case["scenarios"]:
        integer(scenario["announced_minute"], "announcement minute")
        for field, target in (
            ("failed_provider_ids", "providers"),
            ("failed_staff_ids", "staff"),
            ("closed_location_ids", "locations"),
        ):
            if any(x not in ix[target] for x in scenario[field]):
                raise ValueError(f"Unknown entity in {field}")
    normal = [s for s in case["scenarios"] if s["id"] == "normal"]
    if len(normal) != 1 or any(
        normal[0][k] for k in ("failed_provider_ids", "failed_staff_ids", "closed_location_ids")
    ):
        raise ValueError("Exactly one outage-free normal world is required")
    for payer in case["payers"]:
        integer(payer["payment_ceiling_cents"], "payer ceiling")
        if not set(payer["allowed_cost_categories"]) <= CATEGORIES:
            raise ValueError("Unknown payer cost category")
        if any(x not in ix["workers"] for x in payer["beneficiary_worker_ids"]):
            raise ValueError("Unknown payer beneficiary")
    integer(case["coordinator_fee_cents"], "coordinator fee")


def _validate_windows(windows: list[list[int]]) -> None:
    for start, end in windows:
        integer(start, "window start")
        integer(end, "window end")
        if not start < end <= 1440:
            raise ValueError("Invalid opening/availability window")


def contained(interval: tuple[int, int] | list[int], windows: list[list[int]]) -> bool:
    """Test whole-interval containment in a declared window."""
    return any(a <= interval[0] and interval[1] <= b for a, b in windows)


def overlaps(a: tuple[int, int] | list[int], b: tuple[int, int] | list[int]) -> bool:
    """Use half-open intervals so touching shifts do not overlap."""
    return max(a[0], b[0]) < min(a[1], b[1])


def union_minutes(intervals: Sequence[tuple[int, int] | list[int]]) -> int:
    """Count the union of time intervals."""
    total, right = 0, -1
    for start, end in sorted(intervals):
        total += max(0, end - max(start, right))
        right = max(right, end)
    return total


def child_interval(case: Json, child: Json, roster: dict[str, str], location_id: str) -> tuple[int, int]:
    """Recompute complete care including both explicitly supplied commute margins."""
    shift = indexed(case, "shifts")[roster[child["parent_worker_id"]]]
    commute = child["commute_minutes_by_location"][location_id]
    return shift["start_minute"] - commute["before"], shift["end_minute"] + commute["after"]


def offer_available(case: Json, offer: Json, scenario: Json, committed: bool) -> str | None:
    """Return an explicit reason if a declared offer cannot be used in this world."""
    if offer["commitment_required"] and not committed:
        return "opening_commitment_missing"
    if not indexed(case, "providers")[offer["provider_id"]]["declared_offer_acceptance"]:
        return "provider_withdrawn"
    if offer["provider_id"] in scenario["failed_provider_ids"]:
        return "provider_absent"
    if offer["location_id"] in scenario["closed_location_ids"]:
        return "location_closed"
    if set(offer["staff_ids"]) & set(scenario["failed_staff_ids"]):
        return "declared_staff_absent"
    location = indexed(case, "locations")[offer["location_id"]]
    if not contained(offer["window"], location["opening_windows"]):
        return "provider_opening_window"
    staff_ix = indexed(case, "staff")
    qualified = 0
    for staff_id in offer["staff_ids"]:
        staff = staff_ix[staff_id]
        if not contained(offer["window"], staff["available_windows"]):
            return "staff_availability"
        if set(offer["required_qualification_tags"]) <= set(staff["qualification_tags"]):
            qualified += 1
    if qualified < offer["minimum_qualified_staff"]:
        return "insufficient_qualified_staff"
    return None


def care_feasible(
    case: Json, roster: dict[str, str], assignment: dict[str, str], scenario: Json, committed: bool
) -> tuple[bool, str]:
    """Check complete child intervals and all concurrently consumed care resources."""
    offers = indexed(case, "offers")
    locations = indexed(case, "locations")
    if set(assignment) != {c["id"] for c in case["children"]}:
        return False, "not_every_child_assigned"
    intervals_by_offer: dict[str, list[tuple[int, int]]] = defaultdict(list)
    intervals_by_location: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for child in case["children"]:
        offer = offers[assignment[child["id"]]]
        if offer["location_id"] not in child["acceptable_location_ids"]:
            return False, "no_acceptable_location"
        reason = offer_available(case, offer, scenario, committed)
        if reason:
            return False, reason
        need = child_interval(case, child, roster, offer["location_id"])
        if need[0] < 0 or need[1] > 1440 or not contained(need, [offer["window"]]):
            return False, "full_care_interval_uncovered"
        if scenario["id"] != "normal" and scenario["announced_minute"] > need[0]:
            return False, "outage_notice_after_care_start"
        intervals_by_offer[offer["id"]].append(need)
        intervals_by_location[offer["location_id"]].append(need)
    for offer_id, intervals in intervals_by_offer.items():
        if peak_count(intervals) > offers[offer_id]["declared_child_capacity"]:
            return False, "insufficient_offer_capacity"
    for location_id, intervals in intervals_by_location.items():
        if peak_count(intervals) > locations[location_id]["declared_concurrent_child_capacity"]:
            return False, "insufficient_location_capacity"
    staff_windows: dict[str, list[list[int]]] = defaultdict(list)
    for offer_id in intervals_by_offer:
        for staff_id in offers[offer_id]["staff_ids"]:
            staff_windows[staff_id].append(offers[offer_id]["window"])
    staff_ix = indexed(case, "staff")
    for staff_id, windows in staff_windows.items():
        if any(overlaps(a, b) for a, b in itertools.combinations(windows, 2)):
            return False, "staff_double_booked"
        if sum(b - a for a, b in windows) > staff_ix[staff_id]["max_active_minutes"]:
            return False, "staff_active_minutes_exceeded"
    return True, "ok"


def peak_count(intervals: list[tuple[int, int]]) -> int:
    """Count concurrent children at event boundaries exactly."""
    events = [(start, 1) for start, _ in intervals] + [(end, -1) for _, end in intervals]
    count = peak = 0
    for _, delta in sorted(events):
        count += delta
        peak = max(peak, count)
    return peak


def roster_quota_ok(case: Json, roster: dict[str, str]) -> bool:
    """Check exact employer output quotas."""
    counts: Counter[tuple[str, str]] = Counter()
    for worker in case["workers"]:
        shift_id = roster.get(worker["id"])
        if shift_id is None or shift_id not in worker["permitted_shift_ids"]:
            return False
        counts[(worker["employer_id"], shift_id)] += 1
    return all(
        counts[(employer["id"], shift_id)] == quota
        for employer in case["employers"]
        for shift_id, quota in employer["staffing_quotas"].items()
    )


def rosters(
    case: Json, fixed: bool, ordinary: bool, stats: Counter[str], tick: Callable[[], None]
) -> Iterator[dict[str, str]]:
    """Enumerate roster choices with either a quota-pruned DFS or ordinary Cartesian enumeration."""
    workers = case["workers"]
    if fixed:
        tick()
        roster = {w["id"]: w["current_shift_id"] for w in workers}
        stats["roster_assignments_examined"] += 1
        if roster_quota_ok(case, roster):
            yield roster
        else:
            stats["roster_quota_or_permission_failure"] += 1
        return
    choices = [w["permitted_shift_ids"] for w in workers]
    if ordinary:
        for shifts in itertools.product(*choices):
            tick()
            stats["roster_assignments_examined"] += 1
            roster = dict(zip([w["id"] for w in workers], shifts))
            if roster_quota_ok(case, roster):
                yield roster
        return
    employers = indexed(case, "employers")
    counts: Counter[tuple[str, str]] = Counter()
    current: dict[str, str] = {}

    def visit(index: int) -> Iterator[dict[str, str]]:
        tick()
        stats["roster_partial_nodes"] += 1
        if index == len(workers):
            stats["roster_assignments_examined"] += 1
            if roster_quota_ok(case, current):
                yield dict(current)
            return
        worker = workers[index]
        for shift_id in worker["permitted_shift_ids"]:
            key = (worker["employer_id"], shift_id)
            if counts[key] >= employers[worker["employer_id"]]["staffing_quotas"][shift_id]:
                continue
            counts[key] += 1
            current[worker["id"]] = shift_id
            yield from visit(index + 1)
            counts[key] -= 1
            del current[worker["id"]]

    yield from visit(0)


def assignment_options(
    case: Json,
    roster: dict[str, str],
    role: str,
    scenario: Json,
    committed: bool,
    fixed_assignments: dict[str, str] | None = None,
) -> tuple[list[list[str]], list[str]]:
    """Find whole-interval choices without relaxing a child's location preferences."""
    options, blockers = [], []
    for child in case["children"]:
        if fixed_assignments and child["id"] in fixed_assignments:
            options.append([fixed_assignments[child["id"]]])
            continue
        viable = []
        local_reasons = set()
        for offer in case["offers"]:
            if offer["role"] != role:
                continue
            reason = offer_available(case, offer, scenario, committed)
            if reason:
                local_reasons.add(reason)
                continue
            location = offer["location_id"]
            if location not in child["acceptable_location_ids"]:
                local_reasons.add("no_acceptable_location")
                continue
            interval = child_interval(case, child, roster, location)
            if contained(interval, [offer["window"]]) and interval[0] >= 0 and interval[1] <= 1440:
                if scenario["id"] == "normal" or scenario["announced_minute"] <= interval[0]:
                    viable.append(offer["id"])
                else:
                    local_reasons.add("outage_notice_after_care_start")
            else:
                local_reasons.add("full_care_interval_uncovered")
        options.append(viable)
        if not viable:
            blockers.extend(sorted(local_reasons or {"no_declared_offer"}))
    return options, blockers


def cost_item(item_id: str, category: str, amount: int, beneficiaries: list[str], detail: Json) -> Json:
    """Create an integer-cent obligation with explicit eligible beneficiaries."""
    return {
        "id": item_id,
        "category": category,
        "amount_cents": amount,
        "beneficiary_worker_ids": sorted(set(beneficiaries)),
        "detail": detail,
    }


def build_ledger(case: Json, roster: dict[str, str], plans: dict[str, dict[str, str]]) -> tuple[list[Json], Json]:
    """Build pass-through costs, worker compensation, fee and a maximum-world activation reserve."""
    offers = indexed(case, "offers")
    children = indexed(case, "children")
    normal = plans["normal"]
    items = []
    primary_groups: dict[str, list[str]] = defaultdict(list)
    for child_id, offer_id in normal.items():
        primary_groups[offer_id].append(child_id)
    for offer_id, child_ids in sorted(primary_groups.items()):
        offer = offers[offer_id]
        amount = offer["fixed_opening_cost_cents"] + offer["per_child_cost_cents"] * len(child_ids)
        items.append(
            cost_item(
                f"primary:{offer_id}",
                "primary_care",
                amount,
                [children[c]["parent_worker_id"] for c in child_ids],
                {
                    "offer_id": offer_id,
                    "child_ids": sorted(child_ids),
                    "fixed_opening_cost_cents": offer["fixed_opening_cost_cents"],
                    "per_child_cost_cents": offer["per_child_cost_cents"],
                    "opening_cost_breakdown": offer.get("cost_breakdown", {}),
                    "primary_cost_is_nonrefundable_if_provider_absent": True,
                },
            )
        )
    backup_groups: dict[str, set[str]] = defaultdict(set)
    activation_costs = {}
    for scenario_id, assignment in plans.items():
        active_backup: dict[str, list[str]] = defaultdict(list)
        for child_id, offer_id in assignment.items():
            if offers[offer_id]["role"] == "backup":
                active_backup[offer_id].append(child_id)
                backup_groups[offer_id].add(child_id)
        activation_costs[scenario_id] = sum(
            offers[o]["fixed_opening_cost_cents"] + offers[o]["per_child_cost_cents"] * len(cs)
            for o, cs in active_backup.items()
        )
    reserve_staff_windows: dict[str, list[list[int]]] = defaultdict(list)
    for offer_id, protected_child_ids in sorted(backup_groups.items()):
        offer = offers[offer_id]
        for staff_id in offer["staff_ids"]:
            reserve_staff_windows[staff_id].append(offer["window"])
        items.append(
            cost_item(
                f"standby:{offer_id}",
                "backup_standby",
                offer["standby_retainer_cents"],
                [children[c]["parent_worker_id"] for c in protected_child_ids],
                {"offer_id": offer_id, "covered_child_ids": sorted(protected_child_ids)},
            )
        )
    staff = indexed(case, "staff")
    for staff_id, windows in reserve_staff_windows.items():
        if union_minutes(windows) > staff[staff_id]["max_reserved_minutes"]:
            raise ValueError("staff_reserved_minutes_exceeded")
    reserve = max(activation_costs.values(), default=0)
    protected = sorted({c for cs in backup_groups.values() for c in cs})
    if reserve:
        items.append(
            cost_item(
                "backup_activation_reserve",
                "backup_activation_reserve",
                reserve,
                [children[c]["parent_worker_id"] for c in protected],
                {
                    "mutually_exclusive_world_costs_cents": activation_costs,
                    "maximum_realized_worlds": 1,
                    "refundable_unused_amount": True,
                    "coordinator_revenue": False,
                },
            )
        )
    for worker in case["workers"]:
        shift_id = roster[worker["id"]]
        amount = worker["change_compensation_cents"][shift_id]
        if amount:
            items.append(
                cost_item(
                    f"worker:{worker['id']}",
                    "worker_compensation",
                    amount,
                    [worker["id"]],
                    {"worker_id": worker["id"], "from_shift": worker["current_shift_id"], "to_shift": shift_id},
                )
            )
    parent_workers = sorted({c["parent_worker_id"] for c in case["children"]})
    items.append(
        cost_item(
            "coordination_fee",
            "coordination_fee",
            case["coordinator_fee_cents"],
            parent_workers,
            {"sold_output": "one-day verified commitment/schedule package", "childcare_delivery_claim": False},
        )
    )
    reserve_summary = {
        "maximum_activation_reserve_cents": reserve,
        "activation_cost_by_scenario_cents": activation_costs,
        "backup_offer_ids": sorted(backup_groups),
        "reserve_staff_minutes": {s: union_minutes(ws) for s, ws in sorted(reserve_staff_windows.items())},
    }
    return items, reserve_summary


def allocate(case: Json, items: list[Json]) -> Json:
    """Find an exact eligible payer allocation with a conventional integral maximum flow."""
    payers = case["payers"]
    n_items, n_payers = len(items), len(payers)
    source, sink = 0, 1 + n_items + n_payers
    graph: list[list[list[int]]] = [[] for _ in range(sink + 1)]

    def add(a: int, b: int, capacity: int) -> int:
        index = len(graph[a])
        graph[a].append([b, len(graph[b]), capacity])
        graph[b].append([a, index, 0])
        return index

    edge_refs = []
    demand = sum(i["amount_cents"] for i in items)
    for j, item in enumerate(items):
        node = 1 + j
        add(source, node, item["amount_cents"])
        for k, payer in enumerate(payers):
            if item["category"] in payer["allowed_cost_categories"] and set(item["beneficiary_worker_ids"]) & set(
                payer["beneficiary_worker_ids"]
            ):
                forward_index = add(node, 1 + n_items + k, demand)
                edge_refs.append((j, k, node, forward_index, demand))
    for k, payer in enumerate(payers):
        add(1 + n_items + k, sink, payer["payment_ceiling_cents"])
    flow = 0
    while True:
        parent: list[tuple[int, int] | None] = [None] * len(graph)
        parent[source] = (-1, -1)
        queue = deque([source])
        while queue and parent[sink] is None:
            node = queue.popleft()
            for index, edge in enumerate(graph[node]):
                if edge[2] > 0 and parent[edge[0]] is None:
                    parent[edge[0]] = (node, index)
                    queue.append(edge[0])
        if parent[sink] is None:
            break
        amount, node = demand - flow, sink
        while node != source:
            previous, edge_index = parent[node]  # type: ignore[misc]
            amount = min(amount, graph[previous][edge_index][2])
            node = previous
        node = sink
        while node != source:
            previous, edge_index = parent[node]  # type: ignore[misc]
            edge = graph[previous][edge_index]
            edge[2] -= amount
            graph[node][edge[1]][2] += amount
            node = previous
        flow += amount
    entries = []
    payer_totals = {p["id"]: 0 for p in payers}
    for j, k, node, edge_index, initial in edge_refs:
        value = initial - graph[node][edge_index][2]
        if value:
            entries.append({"item_id": items[j]["id"], "payer_id": payers[k]["id"], "amount_cents": value})
            payer_totals[payers[k]["id"]] += value
    return {
        "feasible": flow == demand,
        "required_cents": demand,
        "funded_cents": flow,
        "shortfall_cents": demand - flow,
        "entries": entries,
        "payer_totals_cents": payer_totals,
        "payer_ceilings_cents": {p["id"]: p["payment_ceiling_cents"] for p in payers},
        "rule": "Deterministic exact eligible maximum flow, not a fairness optimum.",
    }


def maximum_fee(case: Json, items: list[Json]) -> int | None:
    """Find the greatest coordinator fee compatible with this physical plan and every payer limit."""
    trial = copy.deepcopy(items)
    fee = next(i for i in trial if i["category"] == "coordination_fee")
    fee["amount_cents"] = 0
    if not allocate(case, trial)["feasible"]:
        return None
    low, high = 0, sum(p["payment_ceiling_cents"] for p in case["payers"])
    while low < high:
        middle = (low + high + 1) // 2
        fee["amount_cents"] = middle
        if allocate(case, trial)["feasible"]:
            low = middle
        else:
            high = middle - 1
    return low


def materialize(
    case: Json,
    roster: dict[str, str],
    plans: dict[str, dict[str, str]],
    items: list[Json],
    reserve: Json,
    allocation: Json,
    max_fee: int | None,
) -> Json:
    """Emit the complete inspectable schedule, care, backup, cost and transformation witness."""
    shifts, offers = indexed(case, "shifts"), indexed(case, "offers")
    schedule = []
    for worker in case["workers"]:
        shift_id = roster[worker["id"]]
        schedule.append(
            {
                "worker_id": worker["id"],
                "employer_id": worker["employer_id"],
                "original_shift_id": worker["current_shift_id"],
                "selected_shift_id": shift_id,
                "permitted_shift_ids": worker["permitted_shift_ids"],
                "work_interval": [shifts[shift_id]["start_minute"], shifts[shift_id]["end_minute"]],
                "required_compensation_cents": worker["change_compensation_cents"][shift_id],
            }
        )
    worlds = []
    for scenario in case["scenarios"]:
        assignment = plans[scenario["id"]]
        child_care = []
        for child in case["children"]:
            offer = offers[assignment[child["id"]]]
            need = child_interval(case, child, roster, offer["location_id"])
            child_care.append(
                {
                    "child_id": child["id"],
                    "parent_worker_id": child["parent_worker_id"],
                    "offer_id": offer["id"],
                    "location_id": offer["location_id"],
                    "required_care_interval": list(need),
                    "provided_care_interval": list(need),
                    "opening_window": offer["window"],
                    "staff_ids": offer["staff_ids"],
                    "role": offer["role"],
                    "commute": child["commute_minutes_by_location"][offer["location_id"]],
                }
            )
        active = sorted(set(assignment.values()))
        worlds.append(
            {
                "scenario_id": scenario["id"],
                "declared_outages": scenario,
                "child_care": child_care,
                "active_offer_ids": active,
                "opening_plan": [
                    {**offers[o], "assigned_child_ids": sorted(c for c, x in assignment.items() if x == o)}
                    for o in active
                ],
                "activation_cost_cents": reserve["activation_cost_by_scenario_cents"][scenario["id"]],
                "unused_refundable_reserve_cents": reserve["maximum_activation_reserve_cents"]
                - reserve["activation_cost_by_scenario_cents"][scenario["id"]],
            }
        )
    totals: Counter[str] = Counter()
    for item in items:
        totals[item["category"]] += item["amount_cents"]
    employer_output = []
    for employer in case["employers"]:
        actual = {
            s["id"]: sum(w["employer_id"] == employer["id"] and roster[w["id"]] == s["id"] for w in case["workers"])
            for s in case["shifts"]
        }
        employer_output.append(
            {
                "employer_id": employer["id"],
                "required_quotas": employer["staffing_quotas"],
                "actual_quotas": actual,
                "required_worker_minutes": sum(
                    employer["staffing_quotas"][s["id"]] * (s["end_minute"] - s["start_minute"]) for s in case["shifts"]
                ),
                "actual_worker_minutes": sum(
                    actual[s["id"]] * (s["end_minute"] - s["start_minute"]) for s in case["shifts"]
                ),
            }
        )
    return {
        "worker_roster": roster,
        "worker_schedule": schedule,
        "scenario_assignments": plans,
        "worlds": worlds,
        "cost_items": items,
        "cost_totals_cents": dict(totals),
        "maximum_funded_package_cents": sum(i["amount_cents"] for i in items),
        "coordinator_revenue_cents": case["coordinator_fee_cents"],
        "pass_through_obligations_cents": sum(i["amount_cents"] for i in items) - case["coordinator_fee_cents"],
        "repeatable_eligible_workload": {
            "verified_operating_days": 1,
            "workers": len(case["workers"]),
            "children": len(case["children"]),
            "employers": len(case["employers"]),
            "required_worlds_per_day": len(case["scenarios"]),
            "future_days_require_identical_or_freshly_verified_inputs": True,
        },
        "maximum_admissible_coordinator_fee_cents": max_fee,
        "payer_allocation": allocation,
        "backup_obligation": reserve,
        "employer_output_checks": employer_output,
        "useful_outcome": {
            "children_required": len(case["children"]),
            "children_completely_covered_per_world": {w["scenario_id"]: len(w["child_care"]) for w in worlds},
            "care_minutes_per_world": {
                w["scenario_id"]: sum(
                    x["provided_care_interval"][1] - x["provided_care_interval"][0] for x in w["child_care"]
                )
                for w in worlds
            },
            "all_employer_quotas_preserved": all(e["required_quotas"] == e["actual_quotas"] for e in employer_output),
            "actual_childcare_delivered": False,
        },
        "transformation_witness": {
            "case_sha256": digest(case),
            "preserved_obligations": [
                "every employer shift quota",
                "every worker permitted shift and compensation",
                "every child's full commute-inclusive interval and acceptable location",
                "declared provider capacity, staffing, qualifications and windows",
                "every enumerated contingency",
                "every eligible payer ceiling",
            ],
            "changed_worker_ids": [w["id"] for w in case["workers"] if roster[w["id"]] != w["current_shift_id"]],
            "primary_opened_offer_ids": sorted(set(plans["normal"].values())),
            "new_commitment_offer_ids": sorted(
                {o for assignment in plans.values() for o in assignment.values() if offers[o]["commitment_required"]}
            ),
            "financial_instrument": "Prepaid primary and standby offers, fully reserved finite backup, paid worker changes.",
            "no_external_acceptance_inferred": True,
        },
    }


def solve(case: Json, mode: str) -> Json:
    """Construct an exact bounded package or a refusal with preserved physical/economic evidence."""
    validate_input(case)
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode}")
    started = time.perf_counter()
    fixed = mode == "fixed_roster_pooled_care"
    committed = mode != "flexible_without_opening_commitment"
    ordinary = mode == "ordinary_exact_same_formulation"
    stats: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    normal = next(s for s in case["scenarios"] if s["id"] == "normal")
    offers = indexed(case, "offers")
    child_ids = [c["id"] for c in case["children"]]
    best = None
    least_physical = None
    largest_fee = None
    min_shortfall = None
    state_count = 0
    complete = True

    def tick() -> None:
        nonlocal state_count
        state_count += 1
        if state_count > case["limits"]["maximum_search_states"]:
            raise SearchLimit()

    try:
        for roster in rosters(case, fixed, ordinary, stats, tick):
            stats["quota_valid_rosters"] += 1
            options, blockers = assignment_options(case, roster, "primary", normal, committed)
            if blockers:
                failures.update(blockers)
                continue
            for selection in itertools.product(*options):
                tick()
                primary = dict(zip(child_ids, selection))
                ok, reason = care_feasible(case, roster, primary, normal, committed)
                if not ok:
                    failures[reason] += 1
                    continue
                world_options: list[list[dict[str, str]]] = []
                impossible = False
                for scenario in case["scenarios"]:
                    if scenario["id"] == "normal":
                        world_options.append([primary])
                        continue
                    fixed_children = {
                        c: o
                        for c, o in primary.items()
                        if offer_available(case, offers[o], scenario, committed) is None
                    }
                    choices, reasons = assignment_options(case, roster, "backup", scenario, committed, fixed_children)
                    if reasons:
                        failures.update(reasons)
                        impossible = True
                        break
                    feasible_worlds = []
                    for backup_selection in itertools.product(*choices):
                        tick()
                        assignment = dict(zip(child_ids, backup_selection))
                        ok, reason = care_feasible(case, roster, assignment, scenario, committed)
                        if ok:
                            feasible_worlds.append(assignment)
                        else:
                            failures[reason] += 1
                    if not feasible_worlds:
                        impossible = True
                        break
                    world_options.append(feasible_worlds)
                if impossible:
                    continue
                for world_selection in itertools.product(*world_options):
                    tick()
                    plans = dict(zip([s["id"] for s in case["scenarios"]], world_selection))
                    try:
                        items, reserve = build_ledger(case, roster, plans)
                    except ValueError as exc:
                        failures[str(exc)] += 1
                        continue
                    stats["complete_physical_plans"] += 1
                    allocation = allocate(case, items)
                    max_fee = maximum_fee(case, items)
                    if max_fee is not None:
                        largest_fee = max(max_fee, largest_fee if largest_fee is not None else -1)
                    price = sum(i["amount_cents"] for i in items)
                    key = (
                        price,
                        tuple(roster[w["id"]] for w in case["workers"]),
                        tuple(plans[s["id"]][c] for s in case["scenarios"] for c in child_ids),
                    )
                    if least_physical is None or key < least_physical[0]:
                        least_physical = (key, materialize(case, roster, plans, items, reserve, allocation, max_fee))
                    if not allocation["feasible"]:
                        failures["payment_ceiling_or_eligibility_shortfall"] += 1
                        min_shortfall = min(
                            allocation["shortfall_cents"],
                            min_shortfall if min_shortfall is not None else allocation["shortfall_cents"],
                        )
                        continue
                    stats["fully_funded_plans"] += 1
                    if best is None or key < best[0]:
                        best = (key, materialize(case, roster, plans, items, reserve, allocation, max_fee))
    except SearchLimit:
        complete = False
    result: Json = {
        "mode": mode,
        "status": "offered"
        if best and complete
        else ("search_limit_not_a_refusal_proof" if not complete else "refused"),
        "exhaustive_within_declared_bounds": complete,
        "search_states": state_count,
        "statistics": dict(stats),
        "rejection_reasons": dict(sorted(failures.items())),
        "minimum_funding_shortfall_cents": 0 if best else min_shortfall,
        "minimum_shortfall_among_rejected_physical_plans_cents": min_shortfall,
        "global_maximum_admissible_coordination_fee_cents": largest_fee,
        "elapsed_seconds": time.perf_counter() - started,
        "offer": best[1] if best and complete else None,
        "least_cost_complete_physical_plan": least_physical[1] if least_physical else None,
        "claim": "Synthetic finite schedule/commitment package; no childcare delivery or human acceptance.",
    }
    if best and complete:
        from e1_verify import verify_offer

        result["acceptance_check"] = verify_offer(case, result["offer"], commitment_allowed=committed)
        if not result["acceptance_check"]["valid"]:
            result["status"] = "checker_rejected"
    return result


def compare(case: Json) -> Json:
    """Run all four specified controls on the identical case."""
    results = {mode: solve(case, mode) for mode in MODES}
    combined, ordinary = results["combined"], results["ordinary_exact_same_formulation"]

    def signature(result: Json) -> Any:
        if not result["offer"]:
            return result["status"], None
        offer = result["offer"]
        return (
            result["status"],
            offer["maximum_funded_package_cents"],
            offer["worker_roster"],
            offer["scenario_assignments"],
        )

    parity = signature(combined) == signature(ordinary)
    return {
        "schema": "agi-alpha.e1-comparison.v1",
        "case_id": case["case_id"],
        "case_sha256": digest(case),
        "synthetic": True,
        "results": results,
        "same_formulation_exact_control": {
            "identical_selected_result": parity,
            "superiority_claim": False,
            "interpretation": "The same formulation permits an ordinary exact coordinator to tie.",
        },
        "complete_transformation_witness": {
            "input_snapshot": case,
            "all_four_controls_retained": True,
            "control_outcomes": {m: r["status"] for m, r in results.items()},
            "complete_origin_and_target_schedules_in_results": True,
        },
    }


def main() -> None:
    """Run the instrument on an explicit case and save a reviewable JSON result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["compare", "solve"])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=MODES, default="combined")
    args = parser.parse_args()
    case = json.loads(args.input.read_text())
    try:
        result = compare(case) if args.command == "compare" else solve(case, args.mode)
    except (KeyError, ValueError, TypeError) as exc:
        result = {
            "schema": "agi-alpha.e1-input-refusal.v1",
            "status": "invalid_input",
            "reason": str(exc),
            "actual_childcare_delivered": False,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.command == "compare" and "results" in result:
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "statuses": {k: v["status"] for k, v in result["results"].items()},
                    "ordinary_control_ties": result["same_formulation_exact_control"]["identical_selected_result"],
                }
            )
        )
    else:
        print(json.dumps({"status": result["status"]}))


if __name__ == "__main__":
    main()
