# SPDX-License-Identifier: Apache-2.0
"""Replay the frozen scientific assay, fixture transfer, and native accounting.

No registry is implemented here. Admission, rights, provenance and revocation use
the exact upstream research lifecycle through lifecycle_bridge. Scientific
execution remains local because the live protected capsule scope is unsupported.
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import time
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from typing import Any

from lifecycle_bridge import replay_native_costs, run_lifecycle

HERE = Path(__file__).resolve().parent
CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]
T95_DF11 = Decimal("1.795884819")


def load(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text())
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dec(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Nonfinite observed amount")
    return result


def mean(values: list[Decimal]) -> Decimal:
    if not values:
        raise ValueError("Empty prespecified cluster")
    return sum(values, Decimal(0)) / len(values)


def money(seconds: Decimal, rate: Decimal) -> Decimal:
    return seconds * rate / Decimal(3600)


def units(value: Decimal, scale: int, *, upward: bool) -> int:
    return int((value * scale).to_integral_value(rounding=ROUND_CEILING if upward else ROUND_FLOOR))


def observed_assay(
    records: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    baseline: str,
    version: str,
    *,
    rate: Decimal = Decimal("3.52"),
    forecast_uses: int = 100,
    compute_increment_usd: Decimal = Decimal(0),
    stipulated_increment_usd: Decimal = Decimal(0),
) -> dict[str, Any]:
    """Use all cases; twelve cluster means are the only inferential units."""
    ids = [case["case_id"] for case in cases if case["family"] == "transfer"]
    if len(ids) < 12 or len(set(ids)) != len(ids):
        raise ValueError("At least twelve unique transfer cases are required")
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in records:
        if row["family"] != "transfer" or row["method"] not in {baseline, version}:
            continue
        key = (row["case_id"], row["method"])
        if key in lookup:
            raise ValueError("Duplicate observed comparison arm")
        lookup[key] = row
    if set(case for case, _ in lookup) != set(ids):
        raise ValueError("Observed transfer population differs from the protected case manifest")
    grouped: list[list[tuple[Decimal, Decimal]]] = [[] for _ in range(12)]
    assignments = []
    accepted = True
    for index, case_id in enumerate(ids):
        try:
            base_row, candidate_row = lookup[case_id, baseline], lookup[case_id, version]
        except KeyError as error:
            raise ValueError(f"Missing paired arm: {case_id}") from error
        a_s, b_s = dec(base_row["complete_s"]), dec(candidate_row["complete_s"])
        if min(a_s, b_s) < 0:
            raise ValueError("Negative runtime")
        accepted = accepted and base_row["accepted"] is True and candidate_row["accepted"] is True
        grouped[index % 12].append((money(a_s, rate), money(b_s, rate)))
        assignments.append(
            {
                "case_id": case_id,
                "index": index,
                "cluster": index % 12,
                "baseline_complete_s": str(a_s),
                "candidate_complete_s": str(b_s),
                "baseline_accepted": base_row["accepted"],
                "candidate_accepted": candidate_row["accepted"],
            }
        )
    clusters, pairs, deltas = [], [], []
    for index, values in enumerate(grouped):
        a, b = mean([v[0] for v in values]), mean([v[1] for v in values])
        delta = a - b
        deltas.append(delta)
        clusters.append(
            {
                "cluster": index,
                "count": len(values),
                "baseline_mean_cost_usd": str(a),
                "candidate_mean_cost_usd": str(b),
                "mean_advantage_usd": str(delta),
            }
        )
        # Conservative integer compatibility projection. Negating a lower
        # baseline cost and an upper candidate cost can only reduce advantage.
        pairs.append(
            {
                "probeId": f"transfer-cluster-{index}",
                "clusterId": f"transfer-cluster-{index}",
                "fresh": True,
                "baseline": {"netMissionValueCents": -units(a, 100, upward=False)},
                "candidate": {"netMissionValueCents": -units(b, 100, upward=True)},
            }
        )
    average = mean(deltas)
    variance = sum((x - average) ** 2 for x in deltas) / Decimal(11)
    se = (variance / Decimal(12)).sqrt()
    lower = average - T95_DF11 * se
    compute_net = lower * forecast_uses - compute_increment_usd
    conditional_net = compute_net - stipulated_increment_usd
    return {
        "schema": "observed-runtime-proxy-assay/v1",
        "candidate": version,
        "baseline": baseline,
        "cases_included": len(ids),
        "independent_clusters": 12,
        "all_equivalent_outcomes_accepted": accepted,
        "case_assignment": assignments,
        "clusters": clusters,
        "mean_advantage_usd_per_mission": str(average),
        "standard_error_usd": str(se),
        "lower_95_usd_per_mission": str(lower),
        "forecast_uses": forecast_uses,
        "compute_increment_usd": str(compute_increment_usd),
        "stipulated_extra_increment_usd": str(stipulated_increment_usd),
        "compute_only_lower_lifetime_net_usd": str(compute_net),
        "conditional_lower_lifetime_net_usd": str(conditional_net),
        "conditional_gate": "eligible" if accepted and lower > 0 and conditional_net > 0 else "reject",
        "actual_complete_economic_gate": "UNKNOWN_REAL_RESEARCH_COSTS_NOT_ADMISSIBLE",
        "integer_cent_projection_pairs": pairs,
        "precision": "Decimal proxy diagnostic is authoritative; integer compatibility projection conservatively loses sub-cent information",
        "independence_limit": "Modulo clusters summarize independently generated parameter cases; timing shares one machine and run. The t bound does not cover shared timing bias or real-world representativeness.",
    }


def measurement_inventory(
    selection: dict[str, Any], development: dict[str, Any], confirmation: dict[str, Any]
) -> dict[str, Any]:
    """Account measured activities once; explicitly retain unmeasured remainder."""
    founder = dec(selection["paid_founder_snapshot_s"])
    gym = dec(selection["extra_gym_s"])
    development_assessment = dec(development["development_total_s"]) - founder - gym
    if development_assessment < 0:
        raise ValueError("Development duration smaller than its disjoint founder and Gym activities")
    rows = confirmation["records"] + confirmation["ood_records"] + confirmation["composition"]["solver_records"]
    reference: dict[str, Decimal] = {}
    for row in rows:
        key = row["case_id"]
        value = dec(row["assessment_reference_s"])
        if key in reference and reference[key] != value:
            raise ValueError("Reference measurement disagrees within a paired case")
        reference[key] = value
    solver_s = sum((dec(row["complete_s"]) for row in rows), Decimal(0))
    # Forward solves are shared between counterfactual policy rows, but the
    # source executes each sensor-design and inverse routine separately.
    design_s = Decimal(0)
    inverse_s = Decimal(0)
    for row in confirmation["composition"]["mission_records"]:
        design_s += dec(row["design_s"])
        inverse_s += dec(row["inverse_s"])
    confirm_assessment = (
        solver_s
        + sum(reference.values(), Decimal(0))
        + design_s
        + inverse_s
        + dec(confirmation["domain_build_s"])
        + dec(confirmation["warmup_s"])
        + dec(confirmation["artifact_build_s"])
    )
    cpu_rows = [r for r in rows if "complete_cpu_s" in r]
    return {
        "elapsed_s": {"A": str(founder), "B": str(development_assessment + confirm_assessment), "C": str(gym)},
        "development_complete_elapsed_s": str(dec(development["development_total_s"])),
        "confirmation_measured_elapsed_subtotal_s": str(confirm_assessment),
        "true_process_cpu_s": {
            "A_founder_excluding_artifact_write": selection.get("paid_founder_cpu_s"),
            "C_gym": selection.get("extra_gym_cpu_s"),
            "B_confirmation_solver_subtotal": str(sum((dec(r["complete_cpu_s"]) for r in cpu_rows), Decimal(0))),
        },
        "cpu_measurement_count": len(cpu_rows),
        "solver_measurement_count": len(rows),
        "unknown_compute": "Confirmation orchestration, serialization and other unmetered research work remain unknown; solver CPU subtotal omits reference solves and design routines.",
        "billing_basis": "Elapsed machine occupancy times a stipulated equipment-rate proxy. CPU counters are observation metadata, not an additional expense.",
        "disjointness": "Founder generation A is excluded from B and C; whole development residual is B; each confirmation solver/ref/design invocation is counted once; counterfactual method totals are not added again.",
    }


def actual_research_ledger(inventory: dict[str, Any], rate: Decimal) -> dict[str, Any]:
    charges = []
    for bucket in ["A", "B", "C"]:
        for category in CATEGORIES:
            known = category == "compute"
            charges.append(
                {
                    "activity_id": f"research-{bucket}-{category}",
                    "mission_id": "scientific-research",
                    "bucket": bucket,
                    "category": category,
                    "accrued_micro_usd": units(money(dec(inventory["elapsed_s"][bucket]), rate), 1_000_000, upward=True)
                    if known
                    else None,
                    "paid_micro_usd": 0,
                    "basis": "attested" if known else "unknown",
                    "note": "Observed elapsed subtotal at assumed USD3.52/hour; microUSD rounded up; not invoice or paid expense"
                    if known
                    else "Actual authoring/model/labor/resource expense unknown; no free-cost assumption",
                }
            )
    charges.append(
        {
            "activity_id": "research-unmetered-compute",
            "mission_id": "scientific-research",
            "bucket": "B",
            "category": "compute",
            "accrued_micro_usd": None,
            "paid_micro_usd": 0,
            "basis": "unknown",
            "note": inventory["unknown_compute"],
        }
    )
    result = replay_native_costs(charges)
    result["input_basis"] = "OBSERVED_LOCAL_TIMING_WITH_ASSUMED_RATE_AND_EXPLICIT_UNKNOWN_REAL_EXPENSES"
    result["measurement_inventory"] = inventory
    return result


def positive_control(path: Path, expected_sha: str, protected: list[str]) -> dict[str, Any]:
    """Artificial monetary outcomes exercise the reused lifecycle, never Alpha."""
    candidate = {
        "id": "synthetic-positive-control",
        "version": 2,
        "artifact_path": str(path),
        "expected_artifact_sha256": expected_sha,
        "shared": True,
        "paired_trials": [
            {
                "probeId": f"synthetic-conformance-{i}",
                "clusterId": f"synthetic-conformance-{i}",
                "fresh": True,
                "baseline": {"netMissionValueCents": 0},
                "candidate": {"netMissionValueCents": 500},
            }
            for i in range(12)
        ],
        "lifecycle_cost_cents": 100,
        "evaluation_cost_cents": 50,
        "forecast_uses": 10,
        "correctness_passed": True,
        "replay_available": True,
        "boundary_passed": True,
    }
    key = "synthetic-positive-control@2"
    shared = run_lifecycle(
        [candidate],
        protected_material=protected,
        operations=[
            {"action": "retrieve", "key": key, "member": "lyra.agent.agi.eth", "week": 1},
            {"action": "export", "key": key, "member": "lyra.agent.agi.eth", "week": 1},
            {"action": "revoke", "key": key, "week": 2},
            {"action": "retrieve", "key": key, "member": "lyra.agent.agi.eth", "week": 3},
        ],
    )
    private = run_lifecycle(
        [{**candidate, "shared": False}],
        protected_material=protected,
        operations=[
            {"action": "retrieve", "key": key, "member": "lyra.agent.agi.eth", "week": 1},
            {"action": "retrieve", "key": key, "member": "atlas.agent.agi.eth", "week": 1},
        ],
    )
    expected = [
        ("shared-peer", shared["operations"][0], True),
        ("export-denied", shared["operations"][1], False),
        ("revoked-peer", shared["operations"][3], False),
        ("private-peer", private["operations"][0], False),
        ("private-owner", private["operations"][1], True),
    ]
    equality = []
    for label, actual, allowed in expected:
        returned = actual["result"].get("transferredArtifact")
        equality.append(
            {
                "case": label,
                "ordinary_library_allowed": allowed,
                "research_lifecycle_allowed": actual["result"]["ok"],
                "permissions_equal": actual["result"]["ok"] is allowed,
                "contents_equal": (returned["sha256"] == expected_sha) if returned else None,
            }
        )
    if not all(row["permissions_equal"] and row["contents_equal"] is not False for row in equality):
        raise ValueError("Ordinary-library same-permission equality control failed")
    return {
        "evidence": "SYNTHETIC_POSITIVE_CONFORMANCE_ONLY_NOT_EMPIRICAL_ALPHA",
        "shared": shared,
        "private": private,
        "ordinary_library_equality": equality,
        "library_scope": "Direct local byte retrieval with an equivalent static access decision. This tests content/permission equality only, not graph search efficiency or network scaling.",
        "revocation_limit": "Revocation blocks future mediated retrieval; it cannot erase a recipient's earlier plaintext copy.",
    }


def replay_received_artifact(
    control: dict[str, Any], confirmation_path: Path, cases: list[dict[str, Any]], out: Path
) -> dict[str, Any]:
    """Actually solve with bytes returned by the fixture network, then archive."""
    import numpy as np
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]
    import technical

    transfer = control["shared"]["operations"][0]["result"]["transferredArtifact"]
    data = (
        base64.b64decode(transfer["content"])
        if transfer["contentEncoding"] == "base64"
        else transfer["content"].encode()
    )
    if hashlib.sha256(data).hexdigest() != transfer["sha256"]:
        raise ValueError("Transferred byte digest mismatch")
    received = out / "B_received_v2.npy"
    received.write_bytes(data)
    spec = next(case for case in cases if case["family"] == "transfer")
    tick = time.perf_counter()
    cpu_tick = time.process_time()
    with threadpool_limits(limits=1):
        domain = technical.Diffusion()
        reduced = technical.Reduced(domain, np.load(received, allow_pickle=False))
        reference, ref_s = technical.reference_solve(domain, spec)
        row, solution = technical.execute(domain, spec, "v2", reduced, reference, ref_s)
    elapsed, cpu = time.perf_counter() - tick, time.process_time() - cpu_tick
    with np.load(confirmation_path / "solutions.npz", allow_pickle=False) as saved:
        archived = saved[spec["case_id"] + "__v2"]
    max_difference = float(np.max(np.abs(solution - archived)))
    identical = bool(np.array_equal(solution, archived))
    equivalent = bool(np.allclose(solution, archived, rtol=1e-12, atol=1e-14))
    if not row["accepted"] or not equivalent:
        raise ValueError("Retrieved artifact failed its archived numerical replay")
    return {
        "schema": "received-artifact-execution/v1",
        "artifact": received.name,
        "artifact_sha256": sha(received),
        "case_id": spec["case_id"],
        "execution": row,
        "whole_replay_elapsed_s": elapsed,
        "whole_replay_cpu_s": cpu,
        "archived_solution_bitwise_equal": identical,
        "archived_solution_numerically_equivalent": equivalent,
        "maximum_absolute_difference": max_difference,
        "fresh_independent_trial": False,
        "meaning": "Local B execution consumed actual research-fixture retrieved bytes. This is a post-confirmation conformance replay; the empirical candidate was not economically admitted.",
    }


def enterprise_exemplar(directory: Path) -> dict[str, Any]:
    """Replay one nano-USD simulation history through the micro-USD native API."""
    with (directory / "worlds.csv").open() as stream:
        matches = [
            row
            for row in csv.DictReader(stream)
            if row["profile"] == "reference" and row["world"] == "900000" and row["policy"] == "shared_gym_composition"
        ]
    if len(matches) != 1:
        raise ValueError("The single prespecified enterprise exemplar is missing or duplicated")
    row = matches[0]
    with gzip.open(directory / "example_histories.json.gz", "rt") as stream:
        histories = json.load(stream)
    history = next(
        value
        for value in histories
        if value["profile"] == "reference" and value["world"] == 900000 and value["policy"] == "shared_gym_composition"
    )
    events = history["events"]
    trace_costs = {
        bucket: sum(
            event["amount_nano_usd"] for event in events if event["event"] == "cost" and event["bucket"] == bucket
        )
        for bucket in ["A", "B", "C"]
    }
    totals = {
        name: sum(event["amount_nano_usd"] for event in events if event["event"] == name)
        for name in ["seed_capital", "collection", "refund"]
    }
    closing = [event for event in events if event["event"] == "closing_balance"]
    if len(closing) != 1:
        raise ValueError("Exact native exemplar requires one recorded closing balance")
    close = closing[0]
    reserve_nano = sum(
        close[key] for key in ["base_reserve_nano_usd", "collection_fee_reserve_nano_usd", "refund_exposure_nano_usd"]
    )
    exact_profit = totals["collection"] - totals["refund"] - sum(trace_costs.values())
    exact_cash = totals["seed_capital"] + exact_profit
    if exact_cash != close["cash_nano_usd"] or dec(row["obligations"]) != 0:
        raise ValueError("Exemplar cash mismatch or unsupported credit obligation")
    source_amounts = {
        **trace_costs,
        "collections": totals["collection"],
        "refunds": totals["refund"],
        "profit": exact_profit,
        "cash": exact_cash,
        "reserve": reserve_nano,
    }
    for key, amount in source_amounts.items():
        if abs(dec(row[key]) * 1_000_000_000 - amount) > Decimal(1):
            raise ValueError(f"Exemplar trace disagrees with saved summary: {key}")
    conversions: dict[str, dict[str, int]] = {}

    def native_amount(label: str, amount_nano: int) -> int:
        if amount_nano < 0:
            raise ValueError("Native monetary inputs must be nonnegative")
        # Round once per exported aggregate, never once per tiny transaction.
        rounded = (amount_nano + 500) // 1000
        conversions[label] = {
            "source_nano_usd": amount_nano,
            "native_micro_usd": rounded,
            "rounding_delta_nano_usd": rounded * 1000 - amount_nano,
        }
        return rounded

    charges = []
    for bucket in ["A", "B", "C"]:
        amount = native_amount(bucket, trace_costs[bucket])
        for category in CATEGORIES:
            included = amount if category == "overhead" else 0
            charges.append(
                {
                    "activity_id": f"exemplar-{bucket}-{category}",
                    "mission_id": "simulated-world-900000",
                    "bucket": bucket,
                    "category": category,
                    "accrued_micro_usd": included,
                    "paid_micro_usd": included,
                    "note": "FULLY SIMULATED. Undissected cost bundles placed in overhead; other categories included in bundle, not inferred free.",
                }
            )
    refunds = native_amount("refunds", totals["refund"])
    charges.append(
        {
            "activity_id": "exemplar-refunds",
            "mission_id": "simulated-world-900000",
            "bucket": "A",
            "category": "correction",
            "accrued_micro_usd": refunds,
            "paid_micro_usd": refunds,
            "note": "FULLY SIMULATED. Native ledger has no refund action; refunds are explicit A correction expense, not negative revenue.",
        }
    )
    collections = [
        {
            "record_id": "exemplar-collections",
            "mission_id": "simulated-world-900000",
            "amount_micro_usd": native_amount("collections", totals["collection"]),
        }
    ]
    replay = replay_native_costs(
        charges,
        collections=collections,
        capital_micro_usd=native_amount("seed_capital", totals["seed_capital"]),
        reserve_micro_usd=native_amount("reserve", reserve_nano),
    )
    report = replay["report"]
    exact = {
        "complete_cost_profit": exact_profit,
        "cash": exact_cash,
        "available_funds": max(0, exact_cash - reserve_nano),
    }
    differences = {
        key: (max(0, report[key]) if key == "available_funds" else report[key]) * 1000 - expected
        for key, expected in exact.items()
    }
    checks = {key: abs(delta) <= 1000 for key, delta in differences.items()}
    if not all(checks.values()):
        raise ValueError("Native exemplar reconciliation exceeds one micro-USD rounding tolerance")
    return {
        "schema": "single-native-enterprise-exemplar/v2",
        "evidence": "FULLY_SIMULATED_INPUTS_EXECUTED_NATIVE_ACCOUNTING",
        "worlds_replayed": 1,
        "population_native_replay": False,
        "source_row": row,
        "trace_cost_nano_usd": trace_costs,
        "conversions": conversions,
        "reconciliation": checks,
        "reconciliation_delta_nano_usd": differences,
        "maximum_allowed_reconciliation_delta_nano_usd": 1000,
        "native": replay,
        "mapping": "Every saved transaction includes setup. Nano-USD source aggregates round once to nearest native micro-USD; each input differs by at most half a micro-USD and reported profit/cash/funds by at most one micro-USD. Gross collections retained; refunds map to A correction. Seed capital excluded from earnings. Outstanding receipts are not revenue; warranty and processing exposure remain reserves. Exactly one modeled history is replayed.",
        "source_sha256": {
            name: sha(directory / name) for name in ["worlds.csv", "example_histories.json.gz", "results.json"]
        },
    }


def run(development_path: Path, confirmation_path: Path, out: Path, enterprise: Path | None = None) -> dict[str, Any]:
    protocol = load(HERE / "lifecycle_protocol.json")
    cfg = load(HERE / "economic_protocol.json")
    selection = load(development_path / "selection.json")
    development = load(development_path / "results.json")
    confirmation = load(confirmation_path / "results.json")
    cases = load(confirmation_path / "case_manifest.json")["cases"]
    training = load(development_path / "training.json")
    protected = [case["case_id"] for case in cases]
    experience = [case["case_id"] for case in training["founder_cases"] + training["gym_pool"]]
    experience += [row["case_id"] for row in development["records"]]
    if set(protected) & set(experience):
        raise ValueError("Protected confirmation cases overlap training or development")
    if confirmation["phase"] != "confirmation" or confirmation["selection"] != selection:
        raise ValueError("Confirmation is not bound to the supplied frozen selection")
    if confirmation["source_sha256"] != sha(HERE / "technical.py"):
        raise ValueError("Numerical replay source changed after confirmation")
    inventory = measurement_inventory(selection, development, confirmation)
    rate = dec(protocol["compute_usd_per_hour"])
    observed, native_assays = {}, {}
    for version in protocol["scientific_comparisons"]:
        path = development_path / f"artifacts/{version}.npy"
        if sha(path) != selection[f"{version}_sha256"]:
            raise ValueError("Frozen artifact identity changed")
        assessment_compute = money(dec(inventory["elapsed_s"]["B"]), rate)
        gym_compute = money(dec(inventory["elapsed_s"]["C"]), rate) if version == "v2" else Decimal(0)
        stipulated_b = sum(
            (dec(cfg[key]) for key in ["retention_assessment_usd", "retention_packaging_usd", "sharing_admission_usd"]),
            Decimal(0),
        )
        stipulated_c = dec(cfg["gym_development_usd"]) if version == "v2" else Decimal(0)
        assay = observed_assay(
            confirmation["records"],
            cases,
            selection["baseline"],
            version,
            rate=rate,
            forecast_uses=protocol["forecast_eligible_uses"],
            compute_increment_usd=assessment_compute + gym_compute,
            stipulated_increment_usd=stipulated_b + stipulated_c,
        )
        observed[version] = assay
        candidate = {
            "id": "scientific-basis",
            "version": int(version[1:]),
            "artifact_path": str(path),
            "expected_artifact_sha256": selection[f"{version}_sha256"],
            "shared": True,
            "paired_trials": assay["integer_cent_projection_pairs"],
            "lifecycle_cost_cents": units(gym_compute + stipulated_c, 100, upward=True),
            "evaluation_cost_cents": units(assessment_compute + stipulated_b, 100, upward=True),
            "forecast_uses": protocol["forecast_eligible_uses"],
            "correctness_passed": assay["all_equivalent_outcomes_accepted"],
            "replay_available": True,
            "boundary_passed": True,
        }
        native_assays[version] = run_lifecycle(
            [candidate], protected_material=protected, beta_version=f"technical-{selection['baseline']}-frozen"
        )
    tick = time.perf_counter()
    control = positive_control(development_path / "artifacts/v2.npy", selection["v2_sha256"], protected)
    replay = replay_received_artifact(control, confirmation_path, cases, out)
    control_elapsed = time.perf_counter() - tick
    inventory["elapsed_s"]["B"] = str(dec(inventory["elapsed_s"]["B"]) + dec(control_elapsed))
    inventory["conformance_control_elapsed_s"] = control_elapsed
    ledger = actual_research_ledger(inventory, rate)
    result = {
        "schema": "scientific-lifecycle-study/v1",
        "protocol": protocol,
        "scientific_assays": observed,
        "upstream_scientific_assays": native_assays,
        "counterfactual_note": "v1 and v2 were frozen together and evaluated on identical untouched cases. Each alternative assessment uses its own research state; these are not repeated adaptations or two sequential fresh admissions.",
        "holdout_check": {
            "training_development_id_overlap": False,
            "protected_ids": len(protected),
            "limit": "Disjoint generated case identities and frozen artifacts; this does not constitute independent institutional validation.",
        },
        "synthetic_positive_control": control,
        "received_artifact_replay": replay,
        "native_research_costs": ledger,
        "live_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
        "source_sha256": {
            "lifecycle_protocol.json": sha(HERE / "lifecycle_protocol.json"),
            "run_research_lifecycle.py": sha(Path(__file__)),
            "lifecycle_bridge.py": sha(HERE / "lifecycle_bridge.py"),
            "development_selection": sha(development_path / "selection.json"),
            "confirmation_results": sha(confirmation_path / "results.json"),
        },
    }
    if enterprise is not None:
        result["native_enterprise_exemplar"] = enterprise_exemplar(enterprise)
    else:
        result["native_enterprise_exemplar"] = {"status": "NOT_RUN", "population_native_replay": False}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enterprise", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve lifecycle history; use a fresh output directory")
    args.output.mkdir(parents=True)
    try:
        result = run(args.development, args.confirmation, args.output, args.enterprise)
    except Exception as error:
        (args.output / "failure.json").write_text(
            json.dumps({"error": str(error), "type": type(error).__name__}, indent=2) + "\n"
        )
        raise
    (args.output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "scientific_verdicts": {
                    key: value["conditional_gate"] for key, value in result["scientific_assays"].items()
                },
                "actual_complete_profit": result["native_research_costs"]["report"]["complete_cost_profit"],
                "live_admission": result["live_admission"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
