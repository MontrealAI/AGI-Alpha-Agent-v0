# SPDX-License-Identifier: Apache-2.0
"""Finite family evidence implications with explicit, unproved identity guards."""

from __future__ import annotations

from itertools import permutations
from math import factorial
from typing import Any

from .qif_reader import EvidenceError, QIF, decimal

GUARDS = (
    "feature_set_identity",
    "specimen_scope",
    "requirement_requalification",
    "measurement_adequacy",
    "current_authority",
)


def prove_family(
    source: QIF, incoming: QIF, source_ids: list[str], target_id: str, guards: dict[str, str], policy: dict[str, Any]
) -> dict[str, Any]:
    """Prove a numerical implication, never an unauthenticated physical substitution."""
    if len(source_ids) != len(set(source_ids)) or not source_ids:
        raise EvidenceError("Family source identifiers must be nonempty and unique")
    try:
        candidates = [source.characteristics[x] for x in source_ids]
        target = incoming.characteristics[target_id]
    except KeyError as error:
        raise EvidenceError(f"Requested characteristic is absent: {error}") from error
    basis = "researcher_counterfactual" if source.override else "formal_source_interpretation"
    result: dict[str, Any] = {
        "basis": basis,
        "source_ids": source_ids,
        "incoming_id": target_id,
        "source_asset_sha256": source.sha256,
        "incoming_asset_sha256": incoming.sha256,
        "counterfactual_primary_unit": source.override,
        "physical_reuse_admitted": False,
        "guard_status": {key: guards.get(key, "unverified") for key in GUARDS},
        "guard_evidence_authenticated": False,
        "refs": [r for c in candidates + [target] for r in c["refs"]],
        "scope": "numeric family evidence under explicit correspondence, coverage and acceptance assumptions",
    }
    if any(not c["supported_predicate"] or c["kind"] != "Diameter" for c in candidates + [target]):
        return result | {"status": "unsupported_predicate", "reason": "Only Diameter intervals support family proof"}
    dest_low, dest_high = decimal(target["interval"]["low_si"]), decimal(target["interval"]["high_si"])
    intervals = [
        {"source_id": c["id"], "low_si": c["interval"]["low_si"], "high_si": c["interval"]["high_si"]}
        for c in candidates
    ]
    inclusive = all(dest_low <= decimal(c["low_si"]) <= decimal(c["high_si"]) <= dest_high for c in intervals)
    nominals = all(
        c["target"] is not None
        and target["target"] is not None
        and decimal(c["target"]["si"]) == decimal(target["target"]["si"])
        for c in candidates
    )
    values = [
        {
            "source_id": c["id"],
            "actual_id": a["id"],
            "result_id": a["result_id"],
            "value_si": a["value"]["si"],
            "raw": a["value"]["raw"],
            "ref": a["ref"],
        }
        for c in candidates
        for a in c["actuals"]
        if a["value"] is not None
    ]
    missing_values = any(not c["actuals"] or any(a["value"] is None for a in c["actuals"]) for c in candidates)
    all_observed = (
        bool(values)
        and not missing_values
        and all(dest_low <= decimal(value["value_si"]) <= dest_high for value in values)
    )
    target_features = set(target["features"])
    for actual in target["actuals"]:
        for identifier in actual["feature_actual_ids"]:
            target_features.add(incoming.feature_actuals[identifier]["item_id"])
    target_feature_ids = sorted(target_features, key=int)
    size_ok = len(source_ids) == len(target_feature_ids) and bool(target_feature_ids)
    permutation_count = factorial(len(source_ids)) if size_ok else 0
    enumerated = []
    if 0 < permutation_count <= policy["max_permutations_enumerated"]:
        enumerated = [list(p) for p in permutations(source_ids)]
    numeric_witness = None
    for item in intervals:
        low, high = decimal(item["low_si"]), decimal(item["high_si"])
        if low < dest_low or high > dest_high:
            value = low if low < dest_low else high
            numeric_witness = {
                "source_id": item["source_id"],
                "constructed_value_si": str(value),
                "source_numeric_pass": low <= value <= high,
                "destination_numeric_pass": dest_low <= value <= dest_high,
                "observed_measurement": False,
            }
            break
    observed_counterexample = next((v for v in values if not dest_low <= decimal(v["value_si"]) <= dest_high), None)
    ambiguity = None
    if size_ok and len(source_ids) > 1:
        swapped = source_ids.copy()
        swapped[0], swapped[1] = swapped[1], swapped[0]
        ambiguity = {
            "basis": "conditional_correspondence_model",
            "mapping_A": dict(zip(target_feature_ids, source_ids)),
            "mapping_B": dict(zip(target_feature_ids, swapped)),
            "distinguished_target_feature": target_feature_ids[0],
            "assumption": "All bijections of a subsequently verified family are admissible; individual links not supplied",
            "conclusion": "Individual feature provenance differs although a universal common-interval conclusion is invariant",
        }
    status = "proved_numeric_implication" if inclusive else "refuted_numeric_implication"
    result.update(
        {
            "status": status,
            "source_intervals": intervals,
            "destination_interval": {"low_si": str(dest_low), "high_si": str(dest_high), "unit": "meter"},
            "equal_nominal_under_this_interpretation": nominals,
            "all_source_intervals_subset": inclusive,
            "observed_values": values,
            "all_observed_values_satisfy_destination": all_observed,
            "missing_actual_values": missing_values,
            "target_feature_ids": target_feature_ids,
            "family_cardinality_consistent": size_ok,
            "permutation_count": permutation_count,
            "enumerated_source_permutations": enumerated,
            "permutation_invariance_proved": size_ok,
            "family_all_recorded_values_pass": bool(size_ok and all_observed),
            "proof_rule": "A conjunction of the same interval predicate over every member is invariant under bijections; inclusion proves the implication for every allowed source value",
            "interval_counterexample": numeric_witness,
            "observed_numeric_counterexample": observed_counterexample,
            "assignment_counterexample": ambiguity,
            "not_proved": [
                "feature-set identity and completeness",
                "specimen identity and coverage",
                "equivalent measurement method and uncertainty",
                "standard/revision requalification",
                "current authority",
            ],
        }
    )
    if source.override:
        result["not_proved"].insert(
            0, "authorized source-unit correction; supplied override is a researcher hypothesis"
        )
    return result


def candidate_families(source: QIF, incoming: QIF) -> list[tuple[list[str], str]]:
    """Generate numerical candidate families; numerical similarity never proves identity."""
    candidates = []
    for destination in incoming.characteristics.values():
        if not destination["supported_predicate"] or destination["target"] is None:
            continue
        ids = [
            c["id"]
            for c in source.characteristics.values()
            if c["supported_predicate"]
            and c["kind"] == destination["kind"]
            and c["target"] is not None
            and decimal(c["target"]["si"]) == decimal(destination["target"]["si"])
        ]
        if ids:
            candidates.append((ids, destination["id"]))
    return candidates
