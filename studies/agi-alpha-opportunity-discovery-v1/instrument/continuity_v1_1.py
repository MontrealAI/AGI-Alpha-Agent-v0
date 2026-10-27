# SPDX-License-Identifier: Apache-2.0
"""Strict independent-snapshot event assay; no event detection or cumulative state."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def finite(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numerical observation")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite observation")
    return result


def load_packet(raw: bytes, mapping: dict[str, Any]) -> list[dict[str, Any]]:
    if hashlib.sha256(raw).hexdigest() != mapping["source_sha256"]:
        raise ValueError("Source identity changed; qualify a new packet")
    reader = csv.DictReader(
        io.StringIO(raw.decode("utf-8-sig")), delimiter=mapping.get("delimiter", "\t")
    )
    rows = []
    for index, item in enumerate(reader, 1):
        identifier = (
            str(item[mapping["id_column"]]) if mapping.get("id_column") else str(index)
        )
        if mapping["derivation"] == "supplied_yi_vi":
            y, v = (
                finite(item[mapping["yi_column"]]),
                finite(item[mapping["vi_column"]]),
            )
        elif mapping["derivation"] == "bangert_secondary_equal_arms":
            n = finite(item["ni"])
            if n <= 2.25:
                raise ValueError(
                    "Insufficient sample for declared secondary correction"
                )
            y = round((1 - 3 / (4 * n - 9)) * finite(item["di"]), 2)
            v = round((8 + y * y) / (2 * n), 3)
        else:
            raise ValueError("Unsupported derivation requires fresh qualification")
        if v <= 0:
            raise ValueError("Sampling variance must be positive")
        rows.append(
            {
                "id": identifier,
                "yi": y,
                "vi": v,
                "source_row": index + 1,
                "active": True,
            }
        )
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Ambiguous row identity")
    if len(rows) != mapping["expected_rows"]:
        raise ValueError("Row count differs from qualified source")
    return rows


def reml(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [r for r in rows if r["active"]]
    if len(selected) < 3:
        raise ValueError("Contract requires at least three active effect rows")
    y = np.array([finite(r["yi"]) for r in selected])
    v = np.array([finite(r["vi"]) for r in selected])
    if np.any(v <= 0):
        raise ValueError("Sampling variance must be positive")

    def objective(tau2: float) -> float:
        w = 1.0 / (v + tau2)
        mean = np.dot(w, y) / w.sum()
        return float(
            0.5
            * (np.log(v + tau2).sum() + math.log(w.sum()) + np.dot(w, (y - mean) ** 2))
        )

    upper = max(1.0, float(np.var(y)) * 8.0, float(v.max()) * 8.0)
    for _ in range(16):
        if objective(upper) >= objective(upper / 2):
            break
        upper *= 2
    else:
        raise ValueError("Variance profile failed to bracket")
    grid = np.concatenate(([0.0], np.geomspace(1e-12, upper, 160)))
    vals = [objective(float(t)) for t in grid]
    best = int(np.argmin(vals))
    candidates = [(vals[best], float(grid[best])), (objective(0), 0.0)]
    left, right = (
        float(grid[max(best - 1, 0)]),
        float(grid[min(best + 1, len(grid) - 1)]),
    )
    if right > left:
        fit = minimize_scalar(
            objective, bounds=(left, right), method="bounded", options={"xatol": 1e-13}
        )
        if not fit.success:
            raise ValueError("REML optimization failed")
        candidates.append((float(fit.fun), float(fit.x)))
    tau2 = min(candidates)[1]
    w = 1.0 / (v + tau2)
    mu, se = float(np.dot(w, y) / w.sum()), math.sqrt(1.0 / w.sum())
    return {
        "k": len(selected),
        "estimate": mu,
        "se": se,
        "ci_lower": mu - 1.959963984540054 * se,
        "ci_upper": mu + 1.959963984540054 * se,
        "tau2": tau2,
        "method": "intercept-only REML; normal interval",
        "interpretation": "Conditional quantitative reproduction; no causal, editorial or practice verdict",
    }


def qualify(contract: dict[str, Any], mission: dict[str, Any]) -> tuple[bool, str]:
    if digest(mission.get("purpose")) != contract["purpose_digest"]:
        return False, "PURPOSE_REQUALIFICATION_REQUIRED"
    if mission.get("execute_authorized") is not True:
        return False, "FRESH_EXECUTION_AUTHORITY_REQUIRED"
    if mission.get("rights_current") is not True:
        return False, "CURRENT_RIGHTS_REQUIRED"
    if mission.get("model_version") != contract["qualified_model_version"]:
        return False, "METHOD_REQUALIFICATION_REQUIRED"
    if mission.get("schema_version") != contract["schema_version"]:
        return False, "SCHEMA_REQUALIFICATION_REQUIRED"
    return True, "qualified-for-declared-local-research-fixture"


_EVENT_COMMON = frozenset({"id", "kind", "purpose_digest"})
_EVENT_FIELDS = {
    "no_change": _EVENT_COMMON | {"source_id"},
    "background_notice": _EVENT_COMMON | {"source_id"},
    "withdrawal": _EVENT_COMMON | {"row_ids", "scope_confirmed"},
    "reinstatement": _EVENT_COMMON | {"row_ids", "scope_confirmed"},
    "corrected_estimate": _EVENT_COMMON | {"row_ids", "scope_confirmed", "replacement"},
    "overlap_disclosed": _EVENT_COMMON,
    "unknown_source": _EVENT_COMMON,
    "ambiguous_duplicate": _EVENT_COMMON,
    "scale_changed": _EVENT_COMMON,
    "rights_withdrawn": _EVENT_COMMON,
    "source_unavailable": _EVENT_COMMON,
    "editorial_retraction_request": _EVENT_COMMON,
    "uncertain_correction": _EVENT_COMMON,
}


def qualify_event(event: Any, contract: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """Reject unsupported event semantics instead of silently ignoring fields."""
    if not isinstance(event, dict) or any(not isinstance(key, str) for key in event):
        return False, "EVENT_OBJECT_REQUIRED", []
    kind = event.get("kind")
    if not isinstance(kind, str) or kind not in _EVENT_FIELDS:
        return False, "SUPPORTED_EVENT_KIND_REQUIRED", []
    unexpected = sorted(set(event) - _EVENT_FIELDS[kind])
    if unexpected:
        return False, "UNSUPPORTED_EVENT_FIELDS", unexpected
    if "id" in event and (not isinstance(event["id"], str) or not event["id"]):
        return False, "EVENT_ID_TYPE_REQUIRED", []
    if "purpose_digest" in event and not isinstance(event["purpose_digest"], str):
        return False, "EVENT_PURPOSE_DIGEST_TYPE_REQUIRED", []
    if "source_id" in event:
        source = event["source_id"]
        if not isinstance(source, str) or source not in contract["background_sources"]:
            return False, "DECLARED_BACKGROUND_SOURCE_REQUIRED", []
    try:
        digest(event)
    except (TypeError, ValueError):
        return False, "FINITE_JSON_EVENT_REQUIRED", []
    return True, "qualified-independent-snapshot-event", []


def process(
    packet: dict[str, Any], mission: dict[str, Any], event: Any
) -> dict[str, Any]:
    contract = packet["contract"]
    event_ok, event_reason, unexpected = qualify_event(event, contract)
    try:
        event_hash = digest(event)
    except (TypeError, ValueError):
        event_hash = None
    common = {
        "event_id": event.get("id")
        if isinstance(event, dict) and isinstance(event.get("id"), str)
        else None,
        "packet_digest": digest(packet),
        "purpose_digest": contract["purpose_digest"],
        "event_digest": event_hash,
        "evidence": "OBSERVED_EXECUTION_ON_SOURCED_DATA_WITH_INJECTED_EVENT",
        "instrument_version": "1.1-candidate",
        "event_schema_version": "independent-snapshot-event/v1.1",
        "event_semantics": "ONE_EVENT_AGAINST_SUPPLIED_ORIGINAL_SNAPSHOT",
        "cumulative_history": False,
        "authority_evidence": "SIMULATED_MISSION_AUTHORITY; native controls are separate",
        "production_admission": False,
        "commercial_acceptance": False,
        "scientific_conclusion": "No automatic editorial or scientific verdict",
    }
    if mission.get("packet_digest") != digest(packet):
        return {
            **common,
            "status": "hold",
            "reason": "CURRENT_PACKET_IDENTITY_REQUIRED",
            "numeric_result": None,
            "recomputed": False,
        }
    valid, reason = qualify(contract, mission)
    if not valid:
        return {
            **common,
            "status": "hold",
            "reason": reason,
            "numeric_result": None,
            "recomputed": False,
        }
    if not event_ok:
        return {
            **common,
            "status": "hold",
            "reason": event_reason,
            "unsupported_fields": unexpected,
            "numeric_result": None,
            "recomputed": False,
        }
    if (
        event.get("purpose_digest", contract["purpose_digest"])
        != contract["purpose_digest"]
    ):
        return {
            **common,
            "status": "hold",
            "reason": "EVENT_PURPOSE_MISMATCH",
            "numeric_result": None,
            "recomputed": False,
        }
    kind = event.get("kind")
    holds = {
        "overlap_disclosed": "DEPENDENCE_MODEL_REQUIRED",
        "unknown_source": "SOURCE_RECONCILIATION_REQUIRED",
        "ambiguous_duplicate": "COHORT_IDENTITY_REQUIRED",
        "scale_changed": "EFFECT_SCALE_REQUALIFICATION_REQUIRED",
        "rights_withdrawn": "CURRENT_RIGHTS_REQUIRED",
        "source_unavailable": "SOURCE_EVIDENCE_REQUIRED",
        "editorial_retraction_request": "EDITORIAL_ADJUDICATION_REQUIRED",
        "uncertain_correction": "CORRECTION_SCOPE_REQUIRED",
    }
    if kind in holds:
        return {
            **common,
            "status": "hold",
            "reason": holds[kind],
            "numeric_result": None,
            "recomputed": False,
            "needed_evidence": holds[kind],
        }
    if kind == "background_notice":
        if event.get("source_id") not in contract["background_sources"]:
            return {
                **common,
                "status": "hold",
                "reason": "BACKGROUND_ROLE_UNPROVEN",
                "numeric_result": None,
                "recomputed": False,
            }
        return {
            **common,
            "status": "unchanged",
            "reason": "NO_QUANTITATIVE_DEPENDENCY_WITHIN_DECLARED_SCOPE",
            "numeric_result": packet["baseline"],
            "recomputed": False,
            "remaining_review": "Background interpretation may still need editorial review",
        }
    rows = deepcopy(packet["rows"])
    lookup = {r["id"]: r for r in rows}
    if kind == "no_change":
        return {
            **common,
            "status": "unchanged",
            "reason": "EXPLICIT_NO_DATA_CHANGE",
            "numeric_result": packet["baseline"],
            "recomputed": False,
        }
    ids = event.get("row_ids", [])
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(i, (str, int)) or isinstance(i, bool) for i in ids)
        or len({str(i) for i in ids}) != len(ids)
        or any(str(i) not in lookup for i in ids)
    ):
        return {
            **common,
            "status": "hold",
            "reason": "ROW_IDENTITY_REQUIRED",
            "numeric_result": None,
            "recomputed": False,
        }
    if event.get("scope_confirmed") is not True:
        return {
            **common,
            "status": "hold",
            "reason": "CORRECTION_SCOPE_REQUIRED",
            "numeric_result": None,
            "recomputed": False,
        }
    try:
        if kind == "withdrawal":
            for identity in ids:
                lookup[str(identity)]["active"] = False
        elif kind == "corrected_estimate":
            if len(ids) != 1 or set(event.get("replacement", {})) != {"yi", "vi"}:
                raise ValueError(
                    "Correction must supply complete paired estimate and variance"
                )
            y, v = (finite(event["replacement"][k]) for k in ("yi", "vi"))
            if v <= 0:
                raise ValueError("Positive variance required")
            lookup[str(ids[0])].update(yi=y, vi=v)
        elif kind == "reinstatement":
            for identity in ids:
                if lookup[str(identity)]["active"]:
                    raise ValueError("Reinstatement requires an existing withdrawn row")
                lookup[str(identity)]["active"] = True
        else:
            return {
                **common,
                "status": "hold",
                "reason": "UNSUPPORTED_EVENT",
                "numeric_result": None,
                "recomputed": False,
            }
        answer = reml(rows)
    except (TypeError, ValueError, KeyError) as exc:
        return {
            **common,
            "status": "reject",
            "reason": str(exc),
            "numeric_result": None,
            "recomputed": False,
        }
    return {
        **common,
        "status": "recomputed",
        "reason": "QUANTITATIVE_UPDATE_REPRODUCED",
        "numeric_result": answer,
        "recomputed": True,
        "updated_rows": rows,
        "changed_rows": ids,
        "remaining_review": "Inclusion, dependence, certainty, generalization and publication decisions remain scoped obligations",
    }


def process_snapshot_batch(
    packet: dict[str, Any],
    mission: dict[str, Any],
    events: Any,
    mode: str = "independent-snapshots",
) -> dict[str, Any]:
    """Run independent cases against one original snapshot; refuse sequence intent."""
    common = {
        "schema": "independent-snapshot-assay/v1.1",
        "mode": mode,
        "packet_digest": digest(packet),
        "cumulative_history": False,
        "production_admission": False,
        "commercial_acceptance": False,
        "interpretation": "Every event uses the same original packet; outputs are not a chronological ledger",
    }
    if mode != "independent-snapshots":
        return {
            **common,
            "status": "hold",
            "reason": "SEQUENTIAL_OR_OTHER_MODE_REQUIRES_SEPARATE_INSTRUMENT",
            "results": [],
        }
    if not isinstance(events, list):
        return {
            **common,
            "status": "hold",
            "reason": "INDEPENDENT_EVENT_LIST_REQUIRED",
            "results": [],
        }
    return {
        **common,
        "status": "evaluated",
        "results": [process(packet, mission, event) for event in events],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Independent snapshot event assay. No event detection, chronology or cumulative mutation."
    )
    parser.add_argument(
        "--packet", type=Path, required=True, help="One qualified original snapshot"
    )
    parser.add_argument(
        "--mission",
        type=Path,
        required=True,
        help="Fresh local purpose and authority fixture",
    )
    parser.add_argument(
        "--events",
        type=Path,
        required=True,
        help="JSON list: each event is applied independently to the same original snapshot",
    )
    parser.add_argument(
        "--mode",
        default="independent-snapshots",
        help="Only independent-snapshots is supported; sequential or other intent is held",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    packet, mission, events = (
        json.loads(p.read_text()) for p in (args.packet, args.mission, args.events)
    )
    result = process_snapshot_batch(packet, mission, events, args.mode)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
