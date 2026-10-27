# SPDX-License-Identifier: Apache-2.0
"""Recompute the fixed exact certificate and apply its deliberately narrow scope.

This is a local research verifier, not a general theorem prover or production
qualification. It uses only the Python standard library. The expected witness
digest is a reproducibility check, not a signature or an ownership assertion.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parent
WITNESS_SHA256 = "c92bc1977bbb6804af862d52c82507793ff57e2355c501477f609e7a1dd22633"
BOUND = Fraction(1891871140656049, 1929687500000000)
SOURCES = (
    "scout/revised_polynomial.json",
    "scout/certify_bernstein.py",
    "lineage/myerson_independent_bounds.py",
    "lineage/myerson_independent_bivariate.py",
    "study/midpoint_uniform.py",
    "lineage/myerson_independent_uniform.py",
)


class Refusal(ValueError):
    """An input or proof obligation is outside the accepted research certificate."""


def require(condition: bool, reason: str) -> None:
    """Refuse explicitly; acceptance does not depend on Python assertions."""
    if not condition:
        raise Refusal(reason)


def rational(value: Any) -> Fraction:
    """Read a small, exact rational string without accepting floating point."""
    require(isinstance(value, str) and len(value) <= 80, "bound must be an exact rational string")
    require(bool(re.fullmatch(r"[+-]?\d+(?:/\d+|\.\d+)?", value)), "malformed rational")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise Refusal("invalid rational") from error


def assess_scope(request: dict[str, Any]) -> dict[str, Any]:
    """Check requested assumptions; this function alone does not recompute a proof."""
    require(isinstance(request, dict), "request must be a JSON object")
    required = {"dimension", "coverage", "class_type", "minimum_hits", "interval_length", "lower_bound"}
    allowed = required | {"interval_start", "distinct_moduli"}
    require(required <= request.keys() <= allowed, "missing or unknown request fields")
    require(type(request["dimension"]) is int and request["dimension"] == 1, "only dimension one is proved")
    require(request["coverage"] == "exactly_once", "an exact partition is required")
    require(request["class_type"] == "full_residue", "complete restricted residue classes are required")
    require(type(request["minimum_hits"]) is int and request["minimum_hits"] >= 2, "singletons are unsupported")
    n = request["interval_length"]
    require(n == "all" or (type(n) is int and n >= 2), "length must be all or an integer at least two")
    require(type(request.get("interval_start", 1)) is int, "interval start must be an integer")
    require(type(request.get("distinct_moduli", True)) is bool, "distinct_moduli must be Boolean")
    target = rational(request["lower_bound"])
    require(Fraction(0) <= target <= BOUND, "requested bound exceeds the proved certificate or is negative")
    return {
        "status": "SCOPE_ADMISSIBLE; proof recomputation still required",
        "requested_strict_lower_bound": str(target),
        "proved_strict_lower_bound": str(BOUND),
        "distinct_moduli_required_by_proof": False,
        "existence_of_a_cover_asserted": False,
        "translation": "Integer interval translations preserve the residue-class assumptions.",
    }


def validate_witness(raw: bytes) -> dict[str, Any]:
    """Match the frozen candidate, then check exact representation and integral."""
    require(hashlib.sha256(raw).hexdigest() == WITNESS_SHA256, "witness digest differs from the frozen certificate")
    obj = json.loads(raw)
    require(obj.get("basis") == "T_2j(2x-1)", "unexpected polynomial basis")
    require(isinstance(obj.get("coefficients"), list) and len(obj["coefficients"]) == 11, "wrong coefficient count")
    cs = [rational(v) for v in obj["coefficients"]]
    integral = sum((c / (1 - 4 * j * j) for j, c in enumerate(cs)), Fraction(0))
    require(integral == BOUND == rational(obj["integral"]), "integral mismatch")
    return obj


def verify(output: Path, request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recompute every proof obligation in an isolated temporary copy."""
    require(sys.flags.optimize == 0, "run without -O; underlying research checkers use assertions")
    decision = assess_scope(request) if request is not None else None
    validate_witness((ROOT / SOURCES[0]).read_bytes())
    frozen = json.loads((ROOT / "study/confirmation_protocol.json").read_text())
    for relative in SOURCES[1:]:
        require(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == frozen["source_hashes"][relative],
                f"frozen checker changed: {relative}")
    require(not output.exists(), "choose a fresh output directory; preserved evidence is never overwritten")
    output.mkdir(parents=True)
    commands = [
        ["scout/certify_bernstein.py"],
        ["lineage/myerson_independent_bounds.py", "scout/revised_polynomial.json",
         "lineage/myerson_revised_independent_bounds.json"],
        ["lineage/myerson_independent_bivariate.py"],
        ["study/midpoint_uniform.py"],
        ["lineage/myerson_independent_uniform.py"],
    ]
    started = time.monotonic()
    executions = []
    with tempfile.TemporaryDirectory(prefix="exact_certificate_", dir=output) as temporary:
        work = Path(temporary)
        for relative in SOURCES:
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        for index, command in enumerate(commands):
            begin = time.monotonic()
            done = subprocess.run([sys.executable, "-E", "-B", *command], cwd=work,
                                  capture_output=True, text=True, timeout=60, check=False)
            (output / f"step_{index + 1}.log").write_text(done.stdout + done.stderr)
            executions.append({"command": command, "exit_code": done.returncode,
                               "elapsed_seconds": time.monotonic() - begin})
            require(done.returncode == 0, f"proof obligation failed: {command[0]}")
        reports = {}
        for relative in ("scout/bernstein_results.json", "lineage/myerson_revised_independent_bounds.json",
                         "lineage/myerson_independent_bivariate.json", "study/midpoint_uniform_result.json",
                         "lineage/myerson_independent_uniform.json"):
            reports[relative] = json.loads((work / relative).read_text())
            destination = output / Path(relative).name
            shutil.copyfile(work / relative, destination)
        primary = reports["scout/bernstein_results.json"]
        expected = {(k, side) for k in range(2, 41) for side in (0, 1)}
        require(len(primary) == 78 and {(p["k"], p["side"]) for p in primary} == expected
                and all(p["ok"] for p in primary), "primary continuous domain is incomplete")
        independent = reports["lineage/myerson_independent_bivariate.json"]
        require(len(independent["patches"]) == 78 and all(p["passed"] for p in independent["patches"]),
                "independent continuous domain is incomplete")
        tail = reports["lineage/myerson_revised_independent_bounds.json"]
        require(tail["tail_passes_unscaled"] and not tail["finite_n_objective_failures"], "tail or finite-length failure")
        uniform = reports["lineage/myerson_independent_uniform.json"]
        require(Fraction(uniform["integral"]) == BOUND and len(uniform["positive_intervals"]) == 16,
                "uniform objective certificate missing")
    if decision is not None:
        decision["status"] = "ACCEPTED_WITHIN_STATED_ASSUMPTIONS"
    report = {
        "status": "PASS: exact research certificate recomputed",
        "witness_sha256": WITNESS_SHA256,
        "strict_lower_bound": str(BOUND),
        "original_threshold": "49/50",
        "scope": "One-dimensional exact partitions into full residue classes, each hitting at least twice.",
        "executions": executions,
        "elapsed_seconds": time.monotonic() - started,
        "request_decision": decision,
        "external_peer_review": False,
        "proof_assistant_formalization": False,
        "model_performance_comparison": False,
        "revenue_or_demand_established": False,
    }
    (output / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    """CLI entry point with nonzero refusal status and no external activity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text()) if args.request else None
        report = verify(args.output, request)
        print(json.dumps(report, indent=2))
        return 0
    except (Refusal, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "REFUSED", "reason": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
