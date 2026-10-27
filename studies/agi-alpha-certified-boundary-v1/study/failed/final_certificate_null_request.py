# SPDX-License-Identifier: Apache-2.0
"""Verify the strongest, conventionally discovered exact research certificate.

The earlier polynomial result remains separately reproducible through
certificate_service.py. No network, identity, payment or model access is used.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from certificate_service import Refusal, rational, require

ROOT = Path(__file__).resolve().parent
BOUND = Fraction(17902560, 18258529)
MAXIMUM = Fraction(18258529, 18240)
INTEGRAL = Fraction(1963, 2)
SOURCES = ("fresh_conventional/verify_weight.py", "lineage/audit_conventional_weight.py")


def assess_scope(request: dict[str, Any]) -> dict[str, Any]:
    """Validate a requested consequence, without claiming to have checked the proof."""
    require(isinstance(request, dict), "request must be a JSON object")
    required = {"dimension", "coverage", "class_type", "minimum_hits", "interval_length", "lower_bound"}
    allowed = required | {"interval_start", "distinct_moduli", "bound_relation"}
    require(required <= request.keys() <= allowed, "missing or unknown request fields")
    require(type(request["dimension"]) is int and request["dimension"] == 1, "only dimension one is proved")
    require(request["coverage"] == "exactly_once", "exact partition required")
    require(request["class_type"] == "full_residue", "complete restricted residue classes required")
    require(type(request["minimum_hits"]) is int and request["minimum_hits"] >= 2, "singleton classes unsupported")
    n = request["interval_length"]
    require(n == "all" or (type(n) is int and n >= 2), "length must be all or an integer at least two")
    require(type(request.get("interval_start", 1)) is int, "interval start must be an integer")
    require(type(request.get("distinct_moduli", True)) is bool, "distinct_moduli must be Boolean")
    relation = request.get("bound_relation", ">=")
    require(relation in (">=", ">"), "unsupported inequality relation")
    target = rational(request["lower_bound"])
    require(Fraction(0) <= target <= BOUND, "bound outside proved range")
    require(relation != ">" or target < BOUND, "strictness at the exact final constant is not certified")
    return {"status": "SCOPE_ADMISSIBLE; proof recomputation still required",
            "requested_lower_bound": str(target), "requested_relation": relation,
            "proved_lower_bound": str(BOUND), "proved_relation": ">=",
            "distinct_moduli_required_by_proof": False, "existence_of_a_cover_asserted": False}


def validate_inputs() -> dict[str, Any]:
    """Match frozen witness and sources; these hashes are reproducibility controls."""
    freeze = json.loads((ROOT / "study/final_confirmation_protocol.json").read_text())
    for relative, digest in freeze["source_hashes"].items():
        require(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest,
                f"frozen input changed: {relative}")
    witness = json.loads((ROOT / "certificate/weight.json").read_text())
    require(witness["dimension"] == 1 and witness["knots_denominator"] == 20, "witness domain mismatch")
    require(len(witness["heights"]) == 21 and witness["heights"] == witness["heights"][::-1],
            "witness symmetry or length mismatch")
    require(all(type(x) is int for x in witness["heights"]), "heights must be exact integers")
    require(Fraction(witness["maximum"]) == MAXIMUM and Fraction(witness["integral"]) == INTEGRAL,
            "witness constants mismatch")
    require(INTEGRAL / MAXIMUM == Fraction(witness["bound"]) == BOUND, "normalization mismatch")
    return witness


def verify(output: Path, request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recompute original and independent exact line-arrangement verifiers."""
    require(sys.flags.optimize == 0, "run without -O; underlying research checkers use assertions")
    decision = assess_scope(request) if request is not None else None
    witness = validate_inputs()
    require(not output.exists(), "choose a fresh output directory; evidence is never overwritten")
    output.mkdir(parents=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="final_exact_", dir=output) as temporary:
        work = Path(temporary)
        for relative in SOURCES:
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        # The independent checker also reruns the original checker in its own
        # temporary directory before reconstructing the entire calculation.
        done = subprocess.run([sys.executable, "-E", "-B", SOURCES[1]], cwd=work,
                              capture_output=True, text=True, timeout=60, check=False)
        (output / "verification.log").write_text(done.stdout + done.stderr)
        require(done.returncode == 0, "exact proof obligation failed")
        result_dir = work / "confirmation/conventional_independent"
        audit = json.loads((result_dir / "INDEPENDENT_WEIGHT_AUDIT.json").read_text())
        original = json.loads((result_dir / "original_checker_certificate.json").read_text())
        require(audit["heights"] == original["weight_values"] == witness["heights"], "weight mismatch")
        require(Fraction(audit["maximum"]) == Fraction(original["maximum"]) == MAXIMUM,
                "exact class maximum mismatch")
        require({c["k"] for c in audit["class_results"]} == set(range(2, 21))
                and len(audit["class_results"]) == 19, "short-class coverage incomplete")
        require(Fraction(audit["tail_k_ge_21"]) == Fraction(7905, 8) < MAXIMUM, "tail is not covered")
        require(Fraction(audit["integral"]) == INTEGRAL and audit["variation"] == 21200,
                "integral or derivative variation mismatch")
        require(Fraction(audit["stronger_normalization_bound"]) == BOUND, "final bound mismatch")
        for item in result_dir.iterdir():
            if item.is_file():
                shutil.copyfile(item, output / item.name)
    if decision is not None:
        decision["status"] = "ACCEPTED_WITHIN_STATED_ASSUMPTIONS"
    receipt = {"status": "PASS: final exact certificate recomputed in two implementations",
               "bound": str(BOUND), "relation": ">=", "bound_decimal": float(BOUND),
               "strictly_above_original_threshold": BOUND > Fraction(49, 50),
               "original_threshold": "49/50", "maximum": str(MAXIMUM), "integral": str(INTEGRAL),
               "elapsed_seconds": time.monotonic() - started, "request_decision": decision,
               "discovered_by": "fresh-context conventional challenge within this study",
               "stronger_normalization_by": "independent audit of the already computed exact maximum",
               "proof_scope": "All finite one-dimensional exact partitions into full residue classes with at least two hits each.",
               "proof_assistant_formalization": False, "external_peer_review": False,
               "exclusive_operational_or_discovery_alpha_established": False,
               "actual_revenue": 0, "actual_complete_profit": None}
    (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    """Command-line entry point; every failed proof input refuses with exit code 2."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text()) if args.request else None
        print(json.dumps(verify(args.output, request), indent=2))
        return 0
    except (Refusal, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "REFUSED", "reason": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
