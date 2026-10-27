# SPDX-License-Identifier: Apache-2.0
"""Check an E1 package against original inputs without importing its constructor.

This separately coded checker is not an independent human or institutional
acceptance. It verifies finite synthetic obligations, not actual care delivery.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

Json = dict[str, Any]


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _contained(start: int, end: int, windows: list[list[int]]) -> bool:
    return any(left <= start < end <= right for left, right in windows)


def _peak(intervals: list[tuple[int, int]]) -> int:
    points = sorted({x for interval in intervals for x in interval})
    return max((sum(start <= t < end for start, end in intervals) for t in points), default=0)


def _union(intervals: list[list[int]]) -> int:
    points = sorted({x for interval in intervals for x in interval})
    return sum(b - a for a, b in zip(points, points[1:]) if any(start <= a and b <= end for start, end in intervals))


def _fundable(case: Json, obligations: dict[str, Json], fee: int) -> bool:
    """Use a separate residual-network implementation to check fee-boundary claims."""
    capacity: dict[tuple[str, str], int] = defaultdict(int)
    neighbors: dict[str, set[str]] = defaultdict(set)
    required = 0

    def edge(a: str, b: str, value: int) -> None:
        capacity[(a, b)] += value
        neighbors[a].add(b)
        neighbors[b].add(a)

    for item_id, item in obligations.items():
        amount = fee if item["category"] == "coordination_fee" else item["amount_cents"]
        required += amount
        edge("SOURCE", f"I:{item_id}", amount)
        for payer in case["payers"]:
            if item["category"] in payer["allowed_cost_categories"] and set(item["beneficiary_worker_ids"]) & set(
                payer["beneficiary_worker_ids"]
            ):
                edge(f"I:{item_id}", f"P:{payer['id']}", amount)
    for payer in case["payers"]:
        edge(f"P:{payer['id']}", "SINK", payer["payment_ceiling_cents"])
    delivered = 0
    while True:
        previous: dict[str, str | None] = {"SOURCE": None}
        queue = deque(["SOURCE"])
        while queue and "SINK" not in previous:
            a = queue.popleft()
            for b in sorted(neighbors[a]):
                if b not in previous and capacity[(a, b)] > 0:
                    previous[b] = a
                    queue.append(b)
        if "SINK" not in previous:
            return delivered == required
        amount = required - delivered
        node = "SINK"
        while previous[node] is not None:
            before = previous[node]
            assert before is not None
            amount = min(amount, capacity[(before, node)])
            node = before
        node = "SINK"
        while previous[node] is not None:
            before = previous[node]
            assert before is not None
            capacity[(before, node)] -= amount
            capacity[(node, before)] += amount
            node = before
        delivered += amount


def _validate_supported_domain(case: Json) -> None:
    """Validate the standalone checker's supported synthetic one-day input contract."""

    def nonnegative_integer(value: Any, label: str) -> None:
        if type(value) is not int or value < 0:
            raise ValueError(f"{label} must be a nonnegative integer")

    def windows(values: list[list[int]]) -> None:
        for start, end in values:
            nonnegative_integer(start, "window start")
            nonnegative_integer(end, "window end")
            if not start < end <= 1440:
                raise ValueError("Window outside supported day")

    if case.get("schema") != "agi-alpha.e1-case.v1" or case.get("synthetic") is not True:
        raise ValueError("Only the declared synthetic input domain is supported")
    if case.get("currency") != "CAD":
        raise ValueError("Only integer CAD-cent contracts are supported")
    horizon = case["horizon"]
    for field in ("operating_days", "maximum_backup_event_worlds_realized"):
        if type(horizon[field]) is not int or horizon[field] != 1:
            raise ValueError("Only one operating day and one mutually exclusive realized world are supported")
    keys = (
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
    )
    indices = {}
    for key in keys:
        ids = [entry["id"] for entry in case[key]]
        if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("Identifiers must be unique nonempty strings")
        indices[key] = {entry["id"]: entry for entry in case[key]}
    for key, hard in (("workers", 12), ("children", 8), ("offers", 8), ("scenarios", 6)):
        cap = case["limits"].get(f"maximum_{key}", hard)
        if type(cap) is not int or not 1 <= cap <= hard or len(case[key]) > cap:
            raise ValueError(f"Unsupported {key} bound")
    states = case["limits"]["maximum_search_states"]
    if type(states) is not int or not 1 <= states <= 1_000_000:
        raise ValueError("Unsupported search-state bound")
    if not case["children"] or not 1 <= len(case["shifts"]) <= 4:
        raise ValueError("Unsupported empty-child or shift domain")
    for shift in case["shifts"]:
        windows([[shift["start_minute"], shift["end_minute"]]])
    for employer in case["employers"]:
        if set(employer["staffing_quotas"]) != set(indices["shifts"]):
            raise ValueError("Every employer must declare every shift quota")
        for quota in employer["staffing_quotas"].values():
            nonnegative_integer(quota, "quota")
    for worker in case["workers"]:
        if worker["employer_id"] not in indices["employers"] or worker["current_shift_id"] not in indices["shifts"]:
            raise ValueError("Unknown employer/current shift")
        if len(worker["permitted_shift_ids"]) != len(set(worker["permitted_shift_ids"])):
            raise ValueError("Duplicated permitted shift")
        for shift_id in worker["permitted_shift_ids"]:
            if shift_id not in indices["shifts"] or shift_id not in worker["change_compensation_cents"]:
                raise ValueError("Permitted shift lacks an explicit compensation term")
            nonnegative_integer(worker["change_compensation_cents"][shift_id], "worker compensation")
    for child in case["children"]:
        if child["parent_worker_id"] not in indices["workers"]:
            raise ValueError("Unknown parent")
        for location in child["acceptable_location_ids"]:
            if location not in indices["locations"]:
                raise ValueError("Unknown acceptable location")
            commute = child["commute_minutes_by_location"][location]
            nonnegative_integer(commute["before"], "commute before")
            nonnegative_integer(commute["after"], "commute after")
    for provider in case["providers"]:
        if type(provider["declared_offer_acceptance"]) is not bool:
            raise ValueError("Provider acceptance must be explicitly boolean")
    for location in case["locations"]:
        windows(location["opening_windows"])
        nonnegative_integer(location["declared_concurrent_child_capacity"], "location capacity")
    for person in case["staff"]:
        windows(person["available_windows"])
        nonnegative_integer(person["max_active_minutes"], "staff active limit")
        nonnegative_integer(person["max_reserved_minutes"], "staff reservation limit")
    for declared in case["offers"]:
        if declared["provider_id"] not in indices["providers"] or declared["location_id"] not in indices["locations"]:
            raise ValueError("Unknown provider or location")
        if declared["role"] not in ("primary", "backup") or type(declared["commitment_required"]) is not bool:
            raise ValueError("Invalid role or opening commitment term")
        windows([declared["window"]])
        nonnegative_integer(declared["declared_child_capacity"], "offer capacity")
        if type(declared["minimum_qualified_staff"]) is not int or declared["minimum_qualified_staff"] < 1:
            raise ValueError("A positive declared staffing requirement is mandatory")
        if len(declared["staff_ids"]) != len(set(declared["staff_ids"])):
            raise ValueError("Repeated staff identifier")
        if any(s not in indices["staff"] for s in declared["staff_ids"]):
            raise ValueError("Unknown staff identifier")
        for field in ("fixed_opening_cost_cents", "per_child_cost_cents", "standby_retainer_cents"):
            nonnegative_integer(declared[field], field)
        if "cost_breakdown" in declared:
            for amount in declared["cost_breakdown"].values():
                nonnegative_integer(amount, "opening cost component")
            if sum(declared["cost_breakdown"].values()) != declared["fixed_opening_cost_cents"]:
                raise ValueError("Opening cost components do not reconcile")
    for scenario in case["scenarios"]:
        nonnegative_integer(scenario["announced_minute"], "notice")
        for field, collection in (
            ("failed_provider_ids", "providers"),
            ("failed_staff_ids", "staff"),
            ("closed_location_ids", "locations"),
        ):
            if any(identifier not in indices[collection] for identifier in scenario[field]):
                raise ValueError("Unknown outage entity")
    normal = [s for s in case["scenarios"] if s["id"] == "normal"]
    if len(normal) != 1 or any(
        normal[0][field] for field in ("failed_provider_ids", "failed_staff_ids", "closed_location_ids")
    ):
        raise ValueError("An outage-free normal world is mandatory")
    allowed = {"primary_care", "backup_standby", "backup_activation_reserve", "worker_compensation", "coordination_fee"}
    for payer in case["payers"]:
        nonnegative_integer(payer["payment_ceiling_cents"], "payer ceiling")
        if not set(payer["allowed_cost_categories"]) <= allowed:
            raise ValueError("Unknown payer cost category")
        if any(worker not in indices["workers"] for worker in payer["beneficiary_worker_ids"]):
            raise ValueError("Unknown payer beneficiary")
    nonnegative_integer(case["coordinator_fee_cents"], "coordination fee")


def verify_offer(case: Json, offer: Json, commitment_allowed: bool = True) -> Json:
    """Reconstruct exact care, staffing, output, finance and finite-reserve obligations."""
    errors: list[str] = []
    counts: Counter[str] = Counter()

    def require(condition: bool, message: str) -> None:
        counts["checks"] += 1
        if not condition:
            errors.append(message)

    try:
        _validate_supported_domain(case)
        workers = {w["id"]: w for w in case["workers"]}
        shifts = {s["id"]: s for s in case["shifts"]}
        children = {c["id"]: c for c in case["children"]}
        offers = {o["id"]: o for o in case["offers"]}
        locations = {p["id"]: p for p in case["locations"]}
        providers = {p["id"]: p for p in case["providers"]}
        staff = {s["id"]: s for s in case["staff"]}
        payers = {p["id"]: p for p in case["payers"]}
        scenarios = {s["id"]: s for s in case["scenarios"]}
        roster = offer["worker_roster"]
        require(set(roster) == set(workers), "Worker roster is not a bijection")
        require(offer["transformation_witness"]["case_sha256"] == _canonical_hash(case), "Input hash mismatch")
        schedule = {w["worker_id"]: w for w in offer["worker_schedule"]}
        require(
            len(schedule) == len(offer["worker_schedule"]) == len(workers), "Worker schedule has duplicates/omissions"
        )
        employer_counts: Counter[tuple[str, str]] = Counter()
        expected: dict[str, Json] = {}

        def item(item_id: str, category: str, amount: int, beneficiaries: list[str]) -> None:
            expected[item_id] = {
                "category": category,
                "amount_cents": amount,
                "beneficiary_worker_ids": sorted(set(beneficiaries)),
            }

        for worker_id, worker in workers.items():
            shift_id = roster[worker_id]
            require(shift_id in worker["permitted_shift_ids"], f"Worker permission violated: {worker_id}")
            shift = shifts[shift_id]
            compensation = worker["change_compensation_cents"][shift_id]
            row = schedule[worker_id]
            require(row["employer_id"] == worker["employer_id"], f"Serialized employer differs: {worker_id}")
            require(
                row["permitted_shift_ids"] == worker["permitted_shift_ids"],
                f"Serialized worker permission differs: {worker_id}",
            )
            require(row["selected_shift_id"] == shift_id, f"Serialized shift differs: {worker_id}")
            require(
                row["work_interval"] == [shift["start_minute"], shift["end_minute"]],
                f"Work interval differs: {worker_id}",
            )
            require(row["required_compensation_cents"] == compensation, f"Worker compensation differs: {worker_id}")
            require(row["original_shift_id"] == worker["current_shift_id"], f"Original shift differs: {worker_id}")
            employer_counts[(worker["employer_id"], shift_id)] += 1
            if compensation:
                item(f"worker:{worker_id}", "worker_compensation", compensation, [worker_id])
        employer_output = {x["employer_id"]: x for x in offer["employer_output_checks"]}
        require(
            len(employer_output) == len(offer["employer_output_checks"]) == len(case["employers"])
            and set(employer_output) == {e["id"] for e in case["employers"]},
            "Employer output rows are not a bijection",
        )
        for employer in case["employers"]:
            actual = {s: employer_counts[(employer["id"], s)] for s in shifts}
            require(actual == employer["staffing_quotas"], f"Employer quota violated: {employer['id']}")
            minutes = sum(actual[s] * (shifts[s]["end_minute"] - shifts[s]["start_minute"]) for s in shifts)
            output = employer_output[employer["id"]]
            require(
                output["actual_quotas"] == actual and output["required_quotas"] == employer["staffing_quotas"],
                f"Reported employer output differs: {employer['id']}",
            )
            require(
                output["actual_worker_minutes"] == minutes == output["required_worker_minutes"],
                f"Employer useful work minutes differ: {employer['id']}",
            )

        plans = offer["scenario_assignments"]
        require(set(plans) == set(scenarios), "Required scenario omitted or added")
        worlds = {w["scenario_id"]: w for w in offer["worlds"]}
        require(len(worlds) == len(offer["worlds"]) == len(scenarios), "World list has duplicates/omissions")
        primary_groups: dict[str, list[str]] = defaultdict(list)
        for child_id, offer_id in plans["normal"].items():
            primary_groups[offer_id].append(child_id)
            require(offers[offer_id]["role"] == "primary", "Normal care must use a primary offer")
        for offer_id, child_ids in primary_groups.items():
            o = offers[offer_id]
            amount = o["fixed_opening_cost_cents"] + len(child_ids) * o["per_child_cost_cents"]
            item(f"primary:{offer_id}", "primary_care", amount, [children[c]["parent_worker_id"] for c in child_ids])

        activation_costs: dict[str, int] = {}
        backup_groups: dict[str, set[str]] = defaultdict(set)
        care_minutes: dict[str, int] = {}
        reserved_windows: dict[str, list[list[int]]] = defaultdict(list)
        for scenario_id, scenario in scenarios.items():
            assignment = plans[scenario_id]
            require(set(assignment) == set(children), f"Children omitted in {scenario_id}")
            world = worlds[scenario_id]
            require(world["declared_outages"] == scenario, f"Outage declaration changed: {scenario_id}")
            rows = {x["child_id"]: x for x in world["child_care"]}
            require(
                len(rows) == len(world["child_care"]) == len(children), f"Care rows duplicated/omitted: {scenario_id}"
            )
            offer_intervals: dict[str, list[tuple[int, int]]] = defaultdict(list)
            location_intervals: dict[str, list[tuple[int, int]]] = defaultdict(list)
            active_backup: dict[str, list[str]] = defaultdict(list)
            minutes = 0
            for child_id, child in children.items():
                selected = offers[assignment[child_id]]
                location = selected["location_id"]
                require(location in child["acceptable_location_ids"], f"Unaccepted location: {scenario_id}/{child_id}")
                commute = child["commute_minutes_by_location"][location]
                shift = shifts[roster[child["parent_worker_id"]]]
                start, end = shift["start_minute"] - commute["before"], shift["end_minute"] + commute["after"]
                require(0 <= start < end <= 1440, f"Care outside declared day: {scenario_id}/{child_id}")
                require(
                    _contained(start, end, [selected["window"]]),
                    f"Full care interval not covered: {scenario_id}/{child_id}",
                )
                if scenario_id != "normal":
                    require(
                        scenario["announced_minute"] <= start, f"Unsupported late contingency notice: {scenario_id}"
                    )
                require(
                    providers[selected["provider_id"]]["declared_offer_acceptance"],
                    f"Provider offer was withdrawn: {selected['id']}",
                )
                require(
                    selected["provider_id"] not in scenario["failed_provider_ids"],
                    f"Absent provider used: {scenario_id}/{selected['id']}",
                )
                require(
                    location not in scenario["closed_location_ids"], f"Closed location used: {scenario_id}/{location}"
                )
                require(
                    not (set(selected["staff_ids"]) & set(scenario["failed_staff_ids"])),
                    f"Absent staff used: {scenario_id}/{selected['id']}",
                )
                require(
                    commitment_allowed or not selected["commitment_required"],
                    f"Unfunded opening commitment used: {selected['id']}",
                )
                primary = offers[plans["normal"][child_id]]
                healthy_primary = (
                    primary["provider_id"] not in scenario["failed_provider_ids"]
                    and primary["location_id"] not in scenario["closed_location_ids"]
                    and not (set(primary["staff_ids"]) & set(scenario["failed_staff_ids"]))
                )
                if healthy_primary:
                    require(
                        selected["id"] == primary["id"], f"Unnecessary/unapproved care switch: {scenario_id}/{child_id}"
                    )
                else:
                    require(selected["role"] == "backup", f"Missing backup role: {scenario_id}/{child_id}")
                row = rows[child_id]
                require(
                    row["parent_worker_id"] == child["parent_worker_id"],
                    f"Serialized parent differs: {scenario_id}/{child_id}",
                )
                require(
                    row["role"] == selected["role"] and row["opening_window"] == selected["window"],
                    f"Serialized role/opening window differs: {scenario_id}/{child_id}",
                )
                require(
                    row["offer_id"] == selected["id"] and row["location_id"] == location,
                    f"Serialized location/offer differs: {scenario_id}/{child_id}",
                )
                require(
                    row["required_care_interval"] == row["provided_care_interval"] == [start, end],
                    f"Serialized care interval differs: {scenario_id}/{child_id}",
                )
                require(
                    row["staff_ids"] == selected["staff_ids"], f"Serialized caregivers differ: {scenario_id}/{child_id}"
                )
                require(row["commute"] == commute, f"Serialized commute differs: {scenario_id}/{child_id}")
                offer_intervals[selected["id"]].append((start, end))
                location_intervals[location].append((start, end))
                minutes += end - start
                if selected["role"] == "backup":
                    active_backup[selected["id"]].append(child_id)
                    backup_groups[selected["id"]].add(child_id)
            care_minutes[scenario_id] = minutes
            active_ids = sorted(offer_intervals)
            require(world["active_offer_ids"] == active_ids, f"Active offer list differs: {scenario_id}")
            opening_rows = {x["id"]: x for x in world["opening_plan"]}
            require(
                len(opening_rows) == len(world["opening_plan"]) == len(active_ids),
                f"Opening plan duplicated/omitted: {scenario_id}",
            )
            staff_windows: dict[str, list[list[int]]] = defaultdict(list)
            for offer_id, intervals in offer_intervals.items():
                selected = offers[offer_id]
                require(
                    _peak(intervals) <= selected["declared_child_capacity"],
                    f"Declared offer capacity exceeded: {scenario_id}/{offer_id}",
                )
                require(
                    _contained(
                        selected["window"][0],
                        selected["window"][1],
                        locations[selected["location_id"]]["opening_windows"],
                    ),
                    f"Opening window not permitted: {offer_id}",
                )
                qualified = 0
                require(len(selected["staff_ids"]) == len(set(selected["staff_ids"])), "Duplicated staff credential")
                for staff_id in selected["staff_ids"]:
                    person = staff[staff_id]
                    require(
                        _contained(selected["window"][0], selected["window"][1], person["available_windows"]),
                        f"Staff unavailable: {scenario_id}/{staff_id}",
                    )
                    qualified += set(selected["required_qualification_tags"]) <= set(person["qualification_tags"])
                    staff_windows[staff_id].append(selected["window"])
                require(
                    qualified >= selected["minimum_qualified_staff"],
                    f"Insufficient qualified staff: {scenario_id}/{offer_id}",
                )
                require(
                    all(opening_rows[offer_id][k] == value for k, value in selected.items()),
                    f"Serialized opening terms differ: {scenario_id}/{offer_id}",
                )
                require(
                    sorted(opening_rows[offer_id]["assigned_child_ids"])
                    == sorted(c for c, assigned in assignment.items() if assigned == offer_id),
                    f"Serialized enrollment differs: {scenario_id}/{offer_id}",
                )
            for location_id, intervals in location_intervals.items():
                require(
                    _peak(intervals) <= locations[location_id]["declared_concurrent_child_capacity"],
                    f"Location capacity exceeded: {scenario_id}/{location_id}",
                )
            for staff_id, windows in staff_windows.items():
                require(
                    all(max(a[0], b[0]) >= min(a[1], b[1]) for a, b in itertools.combinations(windows, 2)),
                    f"Staff double booked: {scenario_id}/{staff_id}",
                )
                require(
                    sum(b - a for a, b in windows) <= staff[staff_id]["max_active_minutes"],
                    f"Staff active-minute limit exceeded: {scenario_id}/{staff_id}",
                )
            activation_costs[scenario_id] = sum(
                offers[o]["fixed_opening_cost_cents"] + offers[o]["per_child_cost_cents"] * len(cs)
                for o, cs in active_backup.items()
            )
            require(
                world["activation_cost_cents"] == activation_costs[scenario_id],
                f"Activation cost differs: {scenario_id}",
            )
        for offer_id, protected_child_ids in backup_groups.items():
            selected = offers[offer_id]
            item(
                f"standby:{offer_id}",
                "backup_standby",
                selected["standby_retainer_cents"],
                [children[c]["parent_worker_id"] for c in protected_child_ids],
            )
            for staff_id in selected["staff_ids"]:
                reserved_windows[staff_id].append(selected["window"])
        reserve = max(activation_costs.values(), default=0)
        if reserve:
            item(
                "backup_activation_reserve",
                "backup_activation_reserve",
                reserve,
                [children[c]["parent_worker_id"] for child_ids in backup_groups.values() for c in child_ids],
            )
        for staff_id, windows in reserved_windows.items():
            require(
                _union(windows) <= staff[staff_id]["max_reserved_minutes"],
                f"Staff standby commitment exceeded: {staff_id}",
            )
        item(
            "coordination_fee",
            "coordination_fee",
            case["coordinator_fee_cents"],
            [c["parent_worker_id"] for c in case["children"]],
        )
        expected_details: dict[str, Json] = {}
        for worker_id, worker in workers.items():
            if worker["change_compensation_cents"][roster[worker_id]]:
                expected_details[f"worker:{worker_id}"] = {
                    "worker_id": worker_id,
                    "from_shift": worker["current_shift_id"],
                    "to_shift": roster[worker_id],
                }
        for offer_id, enrolled in primary_groups.items():
            declared = offers[offer_id]
            expected_details[f"primary:{offer_id}"] = {
                "offer_id": offer_id,
                "child_ids": sorted(enrolled),
                "fixed_opening_cost_cents": declared["fixed_opening_cost_cents"],
                "per_child_cost_cents": declared["per_child_cost_cents"],
                "opening_cost_breakdown": declared.get("cost_breakdown", {}),
                "primary_cost_is_nonrefundable_if_provider_absent": True,
            }
        for offer_id, protected in backup_groups.items():
            expected_details[f"standby:{offer_id}"] = {"offer_id": offer_id, "covered_child_ids": sorted(protected)}
        if reserve:
            expected_details["backup_activation_reserve"] = {
                "mutually_exclusive_world_costs_cents": activation_costs,
                "maximum_realized_worlds": 1,
                "refundable_unused_amount": True,
                "coordinator_revenue": False,
            }
        expected_details["coordination_fee"] = {
            "sold_output": "one-day verified commitment/schedule package",
            "childcare_delivery_claim": False,
        }
        actual_items = {i["id"]: i for i in offer["cost_items"]}
        require(len(actual_items) == len(offer["cost_items"]) == len(expected), "Cost items duplicated/omitted")
        require(set(actual_items) == set(expected), "Unexpected/missing cost obligation")
        for item_id, obligation in expected.items():
            actual = actual_items[item_id]
            require(actual["detail"] == expected_details[item_id], f"Cost obligation detail differs: {item_id}")
            require(all(actual[k] == value for k, value in obligation.items()), f"Cost obligation differs: {item_id}")
        require(offer["backup_obligation"]["maximum_activation_reserve_cents"] == reserve, "Backup reserve understated")
        require(
            offer["backup_obligation"]["activation_cost_by_scenario_cents"] == activation_costs,
            "Backup event accounting differs",
        )
        require(
            offer["backup_obligation"]["backup_offer_ids"] == sorted(backup_groups),
            "Backup reservation offer list differs",
        )
        require(
            offer["backup_obligation"]["reserve_staff_minutes"]
            == {person: _union(intervals) for person, intervals in sorted(reserved_windows.items())},
            "Reserved staff-minute summary differs",
        )
        for scenario_id, world in worlds.items():
            require(
                world["unused_refundable_reserve_cents"] == reserve - activation_costs[scenario_id],
                f"Refundable reserve differs: {scenario_id}",
            )
        allocation = offer["payer_allocation"]
        require(
            set(allocation["payer_totals_cents"]) == set(payers)
            and set(allocation["payer_ceilings_cents"]) == set(payers),
            "Payer summaries are not a bijection",
        )
        paid_items: Counter[str] = Counter()
        paid_payers: Counter[str] = Counter()
        for entry in allocation["entries"]:
            amount = entry["amount_cents"]
            require(type(amount) is int and amount >= 0, "Invalid allocated amount")
            obligation, payer = expected[entry["item_id"]], payers[entry["payer_id"]]
            require(obligation["category"] in payer["allowed_cost_categories"], "Payer category permission violated")
            require(
                bool(set(obligation["beneficiary_worker_ids"]) & set(payer["beneficiary_worker_ids"])),
                "Payer beneficiary permission violated",
            )
            paid_items[entry["item_id"]] += amount
            paid_payers[entry["payer_id"]] += amount
        for item_id, obligation in expected.items():
            require(paid_items[item_id] == obligation["amount_cents"], f"Obligation not fully funded: {item_id}")
        for payer_id, payer in payers.items():
            require(paid_payers[payer_id] <= payer["payment_ceiling_cents"], f"Payer ceiling exceeded: {payer_id}")
            require(
                allocation["payer_totals_cents"][payer_id] == paid_payers[payer_id],
                f"Reported payer amount differs: {payer_id}",
            )
            require(
                allocation["payer_ceilings_cents"][payer_id] == payer["payment_ceiling_cents"],
                f"Payer ceiling changed: {payer_id}",
            )
        total = sum(x["amount_cents"] for x in expected.values())
        totals: Counter[str] = Counter()
        for obligation in expected.values():
            totals[obligation["category"]] += obligation["amount_cents"]
        require(offer["cost_totals_cents"] == dict(totals), "Reported cost category totals differ")
        require(offer["maximum_funded_package_cents"] == total, "Package price differs")
        require(offer["coordinator_revenue_cents"] == case["coordinator_fee_cents"], "Pass-through counted as revenue")
        require(
            offer["pass_through_obligations_cents"] == total - case["coordinator_fee_cents"],
            "Pass-through obligation total differs",
        )
        require(
            allocation["feasible"] is True
            and allocation["funded_cents"] == total
            and allocation["required_cents"] == total
            and allocation["shortfall_cents"] == 0,
            "Allocation accounting does not reconcile",
        )
        fee_ceiling = offer["maximum_admissible_coordinator_fee_cents"]
        require(type(fee_ceiling) is int and fee_ceiling >= case["coordinator_fee_cents"], "Invalid fee ceiling")
        require(_fundable(case, expected, fee_ceiling), "Reported maximum fee is not fundable")
        require(not _fundable(case, expected, fee_ceiling + 1), "Reported maximum fee is not maximal")
        require(
            offer["repeatable_eligible_workload"]
            == {
                "verified_operating_days": 1,
                "workers": len(workers),
                "children": len(children),
                "employers": len(case["employers"]),
                "required_worlds_per_day": len(scenarios),
                "future_days_require_identical_or_freshly_verified_inputs": True,
            },
            "Repeatable-workload summary exceeds or changes the verified scope",
        )
        transformation = offer["transformation_witness"]
        require(
            transformation["changed_worker_ids"]
            == [w["id"] for w in case["workers"] if roster[w["id"]] != w["current_shift_id"]],
            "Transformation changed-worker list differs",
        )
        require(
            transformation["primary_opened_offer_ids"] == sorted(set(plans["normal"].values())),
            "Transformation primary-opening list differs",
        )
        require(
            transformation["new_commitment_offer_ids"]
            == sorted(
                {o for assignment in plans.values() for o in assignment.values() if offers[o]["commitment_required"]}
            ),
            "Transformation commitment list differs",
        )
        require(transformation["no_external_acceptance_inferred"] is True, "External acceptance was inferred")
        require(
            transformation["preserved_obligations"]
            == [
                "every employer shift quota",
                "every worker permitted shift and compensation",
                "every child's full commute-inclusive interval and acceptable location",
                "declared provider capacity, staffing, qualifications and windows",
                "every enumerated contingency",
                "every eligible payer ceiling",
            ],
            "Transformation preservation scope differs",
        )
        require(
            transformation["financial_instrument"]
            == "Prepaid primary and standby offers, fully reserved finite backup, paid worker changes.",
            "Transformation financial terms differ",
        )
        useful = offer["useful_outcome"]
        require(useful["children_required"] == len(children), "Child count changed")
        require(
            useful["children_completely_covered_per_world"] == {s: len(children) for s in scenarios},
            "Useful care-count claim differs",
        )
        require(useful["care_minutes_per_world"] == care_minutes, "Useful care-minute claim differs")
        require(useful["all_employer_quotas_preserved"] is True, "Employer-output flag differs")
        require(useful["actual_childcare_delivered"] is False, "Synthetic package mislabeled as delivered care")
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        errors.append(f"Malformed or inconsistent witness: {type(exc).__name__}: {exc}")
    return {
        "valid": not errors,
        "checks_performed": counts["checks"],
        "errors": errors,
        "scope": "Separately coded finite-input checker v2; no actual delivery or external acceptance.",
        "checker_version": "v2",
    }


def main() -> None:
    """Check an offered plan saved in a comparison or standalone result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--mode", default="combined")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    case = json.loads(args.input.read_text())
    result = json.loads(args.result.read_text())
    selected = result["results"][args.mode] if "results" in result else result
    check = (
        verify_offer(case, selected["offer"], commitment_allowed=args.mode != "flexible_without_opening_commitment")
        if selected.get("offer")
        else {"valid": False, "errors": ["No offer to verify"]}
    )
    if args.output:
        args.output.write_text(json.dumps(check, indent=2, sort_keys=True) + "\n")
    print(json.dumps(check))
    raise SystemExit(0 if check["valid"] else 1)


if __name__ == "__main__":
    main()
