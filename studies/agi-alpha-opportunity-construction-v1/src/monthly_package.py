# SPDX-License-Identifier: Apache-2.0
"""Construct the exact 20-day package priced in the commercial simulation.

Repeat only the declared daily purpose, offers and constraints. Each day has a
separate evidence hash and authority requirement. This is not physical care,
legal approval, electronic signature or a live escrow implementation.
"""

from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from e1_instrument_v2 import solve  # noqa: E402
from e1_verify_v2 import verify_offer  # noqa: E402


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def fair_allocation(case, offer):
    """A specified feasible allocation, not a fairness optimality claim.

    Parents each contribute CAD40 to primary care. Employers split common
    remaining costs and the fee; each pays its own worker compensation.
    """
    entries = []
    parents = [p for p in case["payers"] if p["kind"] == "parent"]
    employers = [p for p in case["payers"] if p["kind"] == "employer"]
    totals = {p["id"]: 0 for p in case["payers"]}

    def add(item, payer, amount):
        if amount:
            entries.append({"item_id": item["id"], "payer_id": payer["id"], "amount_cents": amount})
            totals[payer["id"]] += amount

    for item in offer["cost_items"]:
        amount = item["amount_cents"]
        if item["category"] == "primary_care":
            for parent in parents:
                share = parent["payment_ceiling_cents"]
                if not set(parent["beneficiary_worker_ids"]) & set(item["beneficiary_worker_ids"]):
                    raise ValueError("Declared package requires the same one-cohort primary opening")
                add(item, parent, share)
                amount -= share
            if amount < 0:
                raise ValueError("Parents cannot be charged more than primary cost")
        if item["category"] == "worker_compensation":
            candidates = [
                p for p in employers if set(item["beneficiary_worker_ids"]) <= set(p["beneficiary_worker_ids"])
            ]
            if len(candidates) != 1:
                raise ValueError("Worker compensation payer is ambiguous")
            add(item, candidates[0], amount)
        else:
            if amount % 2:
                raise ValueError("Equal employer allocation requires integral cents")
            for emp in employers:
                add(item, emp, amount // 2)
    if any(totals[p["id"]] > p["payment_ceiling_cents"] for p in case["payers"]):
        raise ValueError("Individual payer ceiling exceeded")
    offer["payer_allocation"] = {
        **offer["payer_allocation"],
        "entries": entries,
        "payer_totals_cents": totals,
        "rule": "Parents pay primary care; each employer pays its workers; employers split common residual costs and fee equally. This is one stated feasible arrangement, not a fairness optimum.",
    }
    return offer


def required_actors(case):
    return sorted(
        [f"employer:{x['id']}" for x in case["employers"]]
        + [f"worker:{x['id']}" for x in case["workers"]]
        + [f"parent:{x['id']}" for x in case["children"]]
        + [f"provider:{x['id']}" for x in case["providers"]]
    )


def fixture_activation_check(day, grants, funds_cents, now_minute, observed_case_sha256):
    """Test explicit simulated consent/funding state. Never authorizes real action."""
    expected = set(day["required_authority_actors"])
    errors = []
    if set(grants) != expected:
        errors.append("Missing or extra independent authority role")
    if any(g.get("case_sha256") != day["case_sha256"] for g in grants.values()):
        errors.append("Grant belongs to another mission")
    if any(g.get("expires_minute", -1) < now_minute for g in grants.values()):
        errors.append("Expired grant")
    if any(g.get("fixture") is not True for g in grants.values()):
        errors.append("Fixture adapter cannot validate live authority")
    if observed_case_sha256 != day["case_sha256"]:
        errors.append("Mission changed; recheck and regrant required")
    if funds_cents < day["pass_prefunding_cents"]:
        errors.append("Complete finite obligation is not prefunded")
    if now_minute > day["commitment_deadline_minute"]:
        errors.append("Notice/commitment deadline passed")
    return {"fixture_eligible": not errors, "errors": errors, "live_authorization": False}


def main():
    origin = json.loads((ROOT / "technical/origin_case.json").read_text())
    c = json.loads((ROOT / "config/economic_config_v1.json").read_text())
    freeze = json.loads((ROOT / "economics_v2/POLICY_FREEZE.json").read_text())
    total_fee = int(freeze["selected_policy"]["price_cad"] * 100)
    days = c["operating_days"]
    if total_fee % days:
        raise ValueError("Fee must allocate exactly across days")
    out = ROOT / "technical/monthly_package"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    all_cases = []
    for i in range(1, days + 1):
        case = copy.deepcopy(origin)
        case["case_id"] = f"commercial-day-{i:02d}"
        case["coordinator_fee_cents"] = total_fee // days
        result = solve(case, "combined")
        if result["status"] != "offered":
            raise ValueError(f"Day {i} refused: priced deliverable is not feasible")
        offer = fair_allocation(case, result["offer"])
        check = verify_offer(case, offer)
        if not check["valid"]:
            raise ValueError(check)
        day = {
            "day": i,
            "case_sha256": digest(case),
            "offer_sha256": digest(offer),
            "maximum_funding_cents": offer["maximum_funded_package_cents"],
            "pass_prefunding_cents": offer["pass_through_obligations_cents"],
            "required_authority_actors": required_actors(case),
            "commitment_deadline_minute": 300,
            "first_care_start_minute": 330,
            "verification": check,
            "case": case,
            "offer": offer,
        }
        all_cases.append(day)
        records.append(
            {
                "day": i,
                "case_sha256": day["case_sha256"],
                "offer_sha256": day["offer_sha256"],
                "checks": check["checks_performed"],
                "funding_cents": day["maximum_funding_cents"],
                "payer_totals_cents": offer["payer_allocation"]["payer_totals_cents"],
            }
        )
    day = all_cases[0]
    grants = {
        a: {"case_sha256": day["case_sha256"], "expires_minute": 300, "fixture": True}
        for a in day["required_authority_actors"]
    }
    base = (grants, day["pass_prefunding_cents"], 299, day["case_sha256"])
    guard = []

    def test(name, args, expected):
        r = fixture_activation_check(day, *args)
        guard.append(
            {
                "name": name,
                "expected_fixture_eligible": expected,
                "result": r,
                "passed": r["fixture_eligible"] == expected,
            }
        )

    test("All simulated roles and funds", base, True)
    missing = copy.deepcopy(grants)
    missing.pop(next(iter(missing)))
    test("Missing distinct worker or employer grant", (missing, *base[1:]), False)
    stale = copy.deepcopy(grants)
    next(iter(stale.values()))["case_sha256"] = "different-mission"
    test("Reused prior-mission grant", (stale, *base[1:]), False)
    test("One cent underfunded", (grants, day["pass_prefunding_cents"] - 1, 299, day["case_sha256"]), False)
    test("Changed mission inputs", (grants, day["pass_prefunding_cents"], 299, "changed"), False)
    test("Late commitment", (grants, day["pass_prefunding_cents"], 301, day["case_sha256"]), False)
    external = copy.deepcopy(grants)
    next(iter(external.values()))["fixture"] = False
    test("Unverified live authorization", (external, *base[1:]), False)
    test(
        "Fresh day cannot inherit grants",
        (grants, day["pass_prefunding_cents"], 299, all_cases[1]["case_sha256"]),
        False,
    )
    assert all(g["passed"] for g in guard)
    contract = {
        "schema": "agi-alpha.monthly-care-package.v2",
        "synthetic": True,
        "currency": "CAD",
        "price_policy": freeze["selected_policy"],
        "days": days,
        "sold_output": "A verified finite 20-day repeating cohort plan, cost/funding and authority packet; automatic recheck on changed inputs is costed, physical childcare is not delivered by this program.",
        "state": "DRAFT_RESEARCH_ONLY",
        "actual_signed_contracts": 0,
        "actual_funds": 0,
        "physical_care_delivered": False,
        "scope": "Twenty day-specific repetitions of the same declared origin constraints, not twenty independent generalization trials.",
        "termination": "Before commitment, any missing consent or funding prevents activation. After commitment, stated provider primary/standby costs are nonrefundable; unused activation reserve is returned to its employer funders. Any changed mission requires a new verified plan and separate grants. No arbitrary permission inheritance.",
        "fallback": "Only the enumerated pre-start single-provider-outage worlds are covered, with CAD170/day fully reserved. Provider ordinary safeguarding/emergency obligations remain external and must be verified before live contracting; no mid-session transfer or simultaneous-provider survival is promised.",
        "service_payment_terms": "Half after accepted package, half 30 days later; failed package acceptance incurs no service fee. Participant/provider funds are segregated outside company operating cash.",
        "initial_service_payment_cad": total_fee / 200,
        "deferred_service_receivable_cad": total_fee / 200,
        "funding_distinction": "Complete customer liability includes the service fee. Only provider/worker/backup pass obligations are prefunded for care activation; half the service fee is collected separately before package release, half is credit due at 30 days. The company bears default on that receivable.",
        "total_service_fee_cad": total_fee / 100,
        "total_pass_through_funding_cad": days * c["daily_pass_maximum_cad"],
        "total_maximum_customer_funding_cad": sum(d["maximum_funding_cents"] for d in all_cases) / 100,
        "normal_world_pass_consumption_cad": days * c["daily_pass_consumption_cad"],
        "refundable_backup_reserve_cad": days * c["daily_backup_reserve_cad"],
        "individual_ceiling_cad_per_day": {"each_parent": 40, "each_employer": 145},
        "actual_allocation_cad_per_day": {
            k: v / 100 for k, v in all_cases[0]["offer"]["payer_allocation"]["payer_totals_cents"].items()
        },
        "days_index": records,
        "activation_guards": guard,
        "source_policy_sha256": hashlib.sha256((ROOT / "economics_v2/POLICY_FREEZE.json").read_bytes()).hexdigest(),
    }
    (out / "CONTRACT.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    (out / "DAY_WITNESSES.json").write_text(json.dumps(all_cases, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                k: contract[k]
                for k in [
                    "days",
                    "total_service_fee_cad",
                    "total_pass_through_funding_cad",
                    "total_maximum_customer_funding_cad",
                    "normal_world_pass_consumption_cad",
                    "refundable_backup_reserve_cad",
                    "actual_allocation_cad_per_day",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
