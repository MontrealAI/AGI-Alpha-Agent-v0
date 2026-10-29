# SPDX-License-Identifier: Apache-2.0
"""Frozen trusted source-binding regression; no candidate AST interpretation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any

EXCERPT = "high-side voltage 34.5 kV; rated power 500 kVA; frequency 60 Hz."
ORACLE = {
    "field": "high_side_voltage",
    "source_clause": "high-side voltage 34.5 kV",
    "value": "69/2",
    "unit": "kV",
    "scope": "fixed development fixture field association; not general natural-language extraction",
}


def digest(value: Any) -> str:
    """Hash inert JSON without importing candidate helpers."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def require(condition: bool, reason: str) -> None:
    """Preserve checks under optimized Python."""
    if not condition:
        raise ValueError(reason)


def misbound_request(original: dict[str, Any]) -> dict[str, Any]:
    """Create inert misannotated input; leave original control programs unchanged."""
    request = deepcopy(original)
    source = request["sources"][0]
    source.update(excerpt=EXCERPT, url="fixture:development-only")
    source["sha256"] = hashlib.sha256(EXCERPT.encode()).hexdigest()
    request["records"][0]["fields"]["high_side_voltage"] = {"value": "500", "unit": "kVA"}
    return request


def fixed_field_oracle(request: dict[str, Any]) -> dict[str, Any]:
    """Check an independently frozen exact clause, never candidate behavior."""
    require(request["sources"][0]["excerpt"] == EXCERPT, "fixed oracle excerpt mismatch")
    clause = EXCERPT.split(";")[0]
    require(clause == ORACLE["source_clause"], "fixed oracle field clause mismatch")
    match = re.fullmatch(r"high-side voltage ([0-9]+(?:\.[0-9]+)?) (kV)", clause)
    require(match is not None, "fixed oracle clause grammar")
    assert match is not None
    reading = request["records"][0]["fields"][ORACLE["field"]]
    source_value, source_unit = Fraction(match[1]), match[2]
    require(source_value == Fraction(ORACLE["value"]) and source_unit == ORACLE["unit"], "oracle freeze mismatch")
    matches = Fraction(reading["value"]) == source_value and reading["unit"] == source_unit
    return {"field_association_matches": matches, "expected": ORACLE, "supplied_record_reading": reading}


def main() -> int:
    """Emit a JSON receipt from trusted checks under the read-only OS boundary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    freeze_bytes = args.freeze.read_bytes()
    freeze = json.loads(freeze_bytes)
    require(freeze["schema"] == "agialpha/source-grounding-regression-freeze/v1", "freeze schema")
    require(freeze["oracle"] == ORACLE and freeze["excerpt"] == EXCERPT, "frozen oracle changed")
    for relative, expected in freeze["sources"].items():
        path = root / relative
        require(not path.is_symlink(), "source symlink refused")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "frozen source changed: " + relative)
    original = json.loads((root / "contrib/invention_automation/specification-request.json").read_bytes())
    request = misbound_request(original)
    require(digest(request) == freeze["misbound_request_sha256"], "frozen witness changed")
    from alpha_factory_v1.core.runtime.invention_automation import specification as spec
    from contrib.invention_automation import qualify_verify as verifier
    from contrib.invention_automation.readonly import enforce

    # Only fixed trusted validators below; constructed control programs remain inert.
    cpu_start, wall_start = time.process_time_ns(), time.monotonic_ns()
    restriction = enforce()
    tests = []
    cpu, wall = time.process_time_ns(), time.monotonic_ns()
    primary_witness = spec.criticize(original)
    primary_receipt = verifier.verify_criticism(original, primary_witness)
    require(primary_receipt["critic_validated"] is True, "primary source criticism rejected")
    require(primary_witness["observed_unit"] == "kVA", "primary literal unit changed")
    tests.append(
        {
            "id": "primary-doe-source-control",
            "verdict": "CONFIRMED",
            "scope": "literal dimensional mismatch and static missing guard only",
            "witness": primary_witness,
            "receipt": primary_receipt,
            "cpu_ns": time.process_time_ns() - cpu,
            "wall_ns": time.monotonic_ns() - wall,
        }
    )
    cpu, wall = time.process_time_ns(), time.monotonic_ns()
    objection = spec.criticize(request)
    receipt = verifier.verify_criticism(request, objection)
    oracle = fixed_field_oracle(request)
    defect = receipt["critic_validated"] is True and oracle["field_association_matches"] is False
    require(defect, "frozen source-binding defect was not reproduced")
    tests.append(
        {
            "id": "wrong-field-quantity-authentication",
            "verdict": "CONFIRMED",
            "scope": "static evidence-contract failure; no candidate execution or runtime harm established",
            "request": request,
            "request_sha256": digest(request),
            "objection": objection,
            "legacy_verifier": receipt,
            "independent_fixed_oracle": oracle,
            "interpretation": "Legacy checks authenticate the annotation's quantity/unit occurrence, not its source field association.",
            "benign_explanation": "If annotations are trusted, their dimensional inconsistency is real; source-level field attribution remains unverified.",
            "cpu_ns": time.process_time_ns() - cpu,
            "wall_ns": time.monotonic_ns() - wall,
        }
    )
    cpu, wall = time.process_time_ns(), time.monotonic_ns()
    guarded = deepcopy(original)
    guarded["baseline"] = deepcopy(original["proposal"])
    try:
        spec.criticize(guarded)
    except ValueError as error:
        critic_error = str(error)
    else:
        raise ValueError("guarded baseline unexpectedly accused")
    require(critic_error == "baseline already guards specification; no corrective criticism", "known-good result")
    try:
        verifier.verify_criticism(guarded, primary_witness)
    except ValueError as error:
        verifier_error = str(error)
    else:
        raise ValueError("guarded baseline incorrectly confirmed")
    require(verifier_error == "baseline defect not established", "known-good verifier result")
    tests.append(
        {
            "id": "guarded-baseline-known-good",
            "verdict": "NO_DEFECT_ESTABLISHED",
            "scope": "dimensional missing-guard objection refuted for guarded baseline; no whole-artifact guarantee",
            "legacy_critic_exception": critic_error,
            "legacy_verifier_exception": verifier_error,
            "api_gap": "Legacy critic raises instead of returning a typed no-defect record.",
            "cpu_ns": time.process_time_ns() - cpu,
            "wall_ns": time.monotonic_ns() - wall,
        }
    )
    result = {
        "schema": "agialpha/source-grounding-regression-receipt/v1",
        "freeze_sha256": hashlib.sha256(freeze_bytes).hexdigest(),
        "frozen_source_hashes": freeze["sources"],
        "protocol": freeze["protocol"],
        "restriction": restriction,
        "tests": tests,
        "passed_tests": len(tests),
        "candidate_executed": False,
        "generated_test_execution": False,
        "trusted_regression_execution": True,
        "confirmation": False,
        "resources": {
            "self_cpu_ns": time.process_time_ns() - cpu_start,
            "wall_ns": time.monotonic_ns() - wall_start,
            "paid_api_calls": 0,
            "new_external_spend": 0,
            "host_model_tokens": "UNKNOWN",
            "inherited_campaign_consumption": "UNKNOWN; not reset",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
