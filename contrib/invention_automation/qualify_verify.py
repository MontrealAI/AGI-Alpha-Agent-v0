# SPDX-License-Identifier: Apache-2.0
"""Independent static checker for bounded specification-screening construction.

This module never imports or evaluates the candidate interpreter. Its proof is
syntactic control-flow dominance over all branches. It authenticates no web
publisher, proves no transformer suitability, and qualifies no business cohort.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

UNIT_DIMENSIONS = {
    "V": "voltage",
    "kV": "voltage",
    "VA": "apparent_power",
    "kVA": "apparent_power",
    "MVA": "apparent_power",
    "Hz": "frequency",
}
DIMENSIONS = set(UNIT_DIMENSIONS.values())
REQUEST_SCHEMA = "agialpha/specification-synthesis-request/v1"
LOSS_DRIVER = "incompatible dimension could pass specification screen"
UNCERTAINTY = "source typo or intended value unknown; no silent correction"
MAX_BYTES = 1_048_576


def sha(value: Any) -> str:
    """Hash canonical inert JSON independently of candidate helpers."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    """Reject with an explicit check, including under Python optimization."""
    if not condition:
        raise ValueError(message)


def keys(value: Any, wanted: set[str], optional: set[str] | None = None) -> None:
    """Require one exact object shape."""
    require(
        type(value) is dict and wanted <= set(value) and not set(value) - wanted - (optional or set()), "record keys"
    )


def bounded(value: Any) -> None:
    """Reject non-inert, deep, excessive, floating, or nonfinite records."""
    count = 0

    def visit(node: Any, depth: int) -> None:
        nonlocal count
        count += 1
        require(count <= 20_000 and depth <= 32, "JSON structural bound")
        if node is None or type(node) in {bool, str}:
            if type(node) is str:
                require(len(node) <= MAX_BYTES, "JSON string bound")
        elif type(node) is int:
            require(abs(node) <= 10**18, "JSON integer bound")
        elif type(node) is list:
            for child in node:
                visit(child, depth + 1)
        elif type(node) is dict and all(type(k) is str for k in node):
            for key, child in node.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ValueError("inert exact JSON required")

    visit(value, 0)
    require(len(json.dumps(value).encode()) <= MAX_BYTES, "JSON byte bound")


def text(value: Any, *, limit: int = 10_000) -> None:
    """Require bounded nonempty human-readable text."""
    require(type(value) is str and bool(value.strip()) and len(value) <= limit, "bounded text required")


def ident(value: Any) -> None:
    """Require a bounded unambiguous identifier."""
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", value) is not None, "identifier")


def rational(value: Any) -> Fraction:
    """Require an exact nonnegative finite quantity; suitability ranges are out of scope."""
    require(
        type(value) is str and re.fullmatch(r"[0-9]{1,16}(?:/[1-9][0-9]{0,15})?", value) is not None,
        "nonnegative rational string required",
    )
    result = Fraction(value)
    require(0 <= result <= 10**15, "nonnegative quantity bound")
    return result


@dataclass(frozen=True)
class State:
    """One abstract branch; no record values or candidate effects are evaluated."""

    observed: frozenset[str]
    dimensions: frozenset[tuple[str, str]]
    tested: frozenset[str] = frozenset()
    terminal: str | None = None


def prove_program(
    program: dict[str, Any], requirements: dict[str, str], budget: dict[str, int], *, dominance: bool
) -> dict[str, Any]:
    """Check every syntactic branch for typed use and terminal dominance.

    This deliberately accepts only the inert grammar. It is a proof of guard
    presence, not execution, parser correctness, source truth, or useful yield.
    """
    bounded(program)
    count = 0
    deepest = 0
    unsafe: set[str] = set()

    def walk(node: Any, states: list[State], depth: int) -> list[State]:
        nonlocal count, deepest
        count += 1
        deepest = max(deepest, depth)
        require(count <= budget["max_nodes"] and depth <= budget["max_depth"], "program budget exceeded")
        require(type(node) is dict, "AST object required")
        require(all(s.terminal is None for s in states), "nonterminal tail after emission")
        op = node.get("op")
        if op == "sequence":
            keys(node, {"op", "steps"})
            require(type(node["steps"]) is list and 1 <= len(node["steps"]) <= 16, "bounded sequence")
            out = states
            for child in node["steps"]:
                out = walk(child, out, depth + 1)
            return out
        if op == "observe":
            keys(node, {"op", "field"})
            require(node["field"] in requirements, "unregistered observed field")
            field = node["field"]
            return [State(s.observed | {field}, s.dimensions, s.tested) for s in states]
        if op == "if":
            keys(node, {"op", "test", "then", "else"})
            test = node["test"]
            keys(test, {"op", "field", "dimension"})
            require(test["op"] == "dimension-is", "uninstalled predicate")
            field, dimension = test["field"], test["dimension"]
            require(field in requirements and dimension == requirements[field], "unregistered predicate type")
            count += 1  # Predicates are resource-bearing AST nodes.
            require(count <= budget["max_nodes"], "program budget exceeded")
            require(all(field in s.observed for s in states), "observation must dominate predicate")
            require(
                all(field not in s.tested for s in states), "repeated dimensional test makes reachability ambiguous"
            )
            yes = [State(s.observed, s.dimensions | {(field, dimension)}, s.tested | {field}) for s in states]
            no = [State(s.observed, s.dimensions, s.tested | {field}) for s in states]
            return walk(node["then"], yes, depth + 1) + walk(node["else"], no, depth + 1)
        if op == "emit":
            keys(node, {"op", "status"})
            require(node["status"] in {"CONSISTENT", "ABSTAIN"}, "uninstalled conclusion")
            for state in states:
                if node["status"] == "CONSISTENT":
                    missing = {
                        field
                        for field, dimension in requirements.items()
                        if field not in state.observed or (field, dimension) not in state.dimensions
                    }
                    unsafe.update(missing)
                    if dominance:
                        require(not missing, "CONSISTENT lacks required dimensional dominance")
            return [State(s.observed, s.dimensions, s.tested, node["status"]) for s in states]
        raise ValueError("uninstalled AST operator; no generated host execution")

    final = walk(program, [State(frozenset(), frozenset())], 1)
    require(all(s.terminal in {"CONSISTENT", "ABSTAIN"} for s in final), "every branch requires one terminal")
    if dominance:
        require(any(s.terminal == "CONSISTENT" for s in final), "nonvacuous positive terminal required")
    return {
        "nodes": count,
        "depth": deepest,
        "terminal_paths": len(final),
        "consistent_paths": sum(state.terminal == "CONSISTENT" for state in final),
        "statuses": sorted({str(s.terminal) for s in final}),
        "unsafe_fields": sorted(unsafe),
        "proof": "syntactic dimensional dominance over all branches; no candidate evaluation",
    }


def verify_request(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate immutable cohort, exact quantities, sources, and type contract."""
    bounded(request)
    keys(
        request, {"schema", "problem", "records", "sources", "requirements", "baseline", "proposal", "author", "budget"}
    )
    require(request["schema"] == REQUEST_SCHEMA, "request schema")
    keys(request["problem"], {"id", "activity", "scope"})
    ident(request["problem"]["id"])
    text(request["problem"]["activity"])
    require(request["problem"]["scope"] == "specification-consistency-only", "no physical or procurement scope")
    requirements = request["requirements"]
    require(type(requirements) is dict and 1 <= len(requirements) <= 6, "bounded requirements")
    for field, dimension in requirements.items():
        ident(field)
        require(dimension in DIMENSIONS, "grounded dimension required")
    budget = request["budget"]
    keys(budget, {"max_nodes", "max_depth", "max_candidates"})
    for name, maximum in [("max_nodes", 128), ("max_depth", 20), ("max_candidates", 32)]:
        require(type(budget[name]) is int and 1 <= budget[name] <= maximum, "bounded integer program budget")
    author = request["author"]
    keys(author, {"kind", "model", "prompt", "usage"})
    require(author["kind"] == "host-model" and author["usage"] == "UNKNOWN", "explicit author and unknown usage")
    text(author["model"])
    text(author["prompt"], limit=40_000)
    require(type(request["sources"]) is list and 1 <= len(request["sources"]) <= 16, "bounded source list")
    sources: dict[str, Any] = {}
    for source in request["sources"]:
        keys(source, {"id", "url", "sha256", "excerpt"})
        ident(source["id"])
        require(source["id"] not in sources, "duplicate source identity")
        text(source["url"])
        require(
            source["url"].startswith("https://") or source["url"] == "fixture:development-only",
            "public HTTPS or explicit development fixture provenance required",
        )
        text(source["excerpt"])
        require(hashlib.sha256(source["excerpt"].encode()).hexdigest() == source["sha256"], "source excerpt hash")
        sources[source["id"]] = source
    require(type(request["records"]) is list and 1 <= len(request["records"]) <= 64, "bounded all-cohort records")
    records: dict[str, Any] = {}
    for record in request["records"]:
        keys(record, {"id", "source_id", "fields"})
        ident(record["id"])
        require(record["id"] not in records and record["source_id"] in sources, "record/source identity")
        require(
            type(record["fields"]) is dict and set(record["fields"]) <= set(requirements),
            "record fields outside specification",
        )
        for quantity in record["fields"].values():
            keys(quantity, {"value", "unit"})
            rational(quantity["value"])
            text(quantity["unit"], limit=20)
        records[record["id"]] = record
    return records, sources


def verify_criticism(request: dict[str, Any], witness: dict[str, Any]) -> dict[str, Any]:
    """Validate literal/static criticism before any corrective construction.

    It checks no candidate execution and does not infer an intended correction.
    A missing dimensional guard is a static defect, not an executed failure.
    """
    records, sources = verify_request(request)
    bounded(witness)
    old = prove_program(request["baseline"], request["requirements"], request["budget"], dominance=False)
    keys(
        witness,
        {
            "record_id",
            "field",
            "observed_unit",
            "required_dimension",
            "source_id",
            "source_hash",
            "loss_driver",
            "uncertainty",
        },
    )
    require(witness["record_id"] in records, "critic record retained")
    record = records[witness["record_id"]]
    field = witness["field"]
    require(field in request["requirements"] and field in old["unsafe_fields"], "baseline defect not established")
    require(witness["source_id"] == record["source_id"], "critic source link")
    source = sources[record["source_id"]]
    require(witness["source_hash"] == source["sha256"], "critic source hash")
    require(witness["observed_unit"] == record["fields"][field]["unit"], "literal observed unit binding")
    require(witness["required_dimension"] == request["requirements"][field], "critic required dimension")
    require(
        UNIT_DIMENSIONS.get(witness["observed_unit"]) != witness["required_dimension"],
        "irrelevant dimensional criticism",
    )
    require(
        witness["loss_driver"] == LOSS_DRIVER and witness["uncertainty"] == UNCERTAINTY, "critic scope and uncertainty"
    )
    literals = re.findall(
        r"(?<![A-Za-z0-9.])([0-9]+(?:\.[0-9]+)?)\s*(MVA|kVA|VA|kV|V|Hz)(?![A-Za-z])", source["excerpt"]
    )
    require(
        any(
            Fraction(value) == rational(record["fields"][field]["value"]) and unit == witness["observed_unit"]
            for value, unit in literals
        ),
        "witness quantity/unit absent from literal source excerpt",
    )
    return {
        "schema": "agialpha/specification-criticism-verification/v1",
        "request_hash": sha(request),
        "witness_hash": sha(witness),
        "record_hash": sha(record),
        "baseline_hash": sha(request["baseline"]),
        "baseline_static": old,
        "critic_validated": True,
        "scope": "source literal and static missing dominance only",
        "intended_source_correction": "UNKNOWN",
        "candidate_executed": False,
        "confirmation": False,
    }


def conventional_reference(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Run a fixed independent dimension table over all records, never the AST."""
    outcomes = []
    for record in request["records"]:
        failures = []
        for field, expected in request["requirements"].items():
            reading = record["fields"].get(field)
            if reading is None:
                failures.append({"field": field, "reason": "missing observation"})
            elif UNIT_DIMENSIONS.get(reading["unit"]) != expected:
                failures.append({"field": field, "reason": "unknown or incompatible dimension"})
        outcomes.append({"id": record["id"], "status": "ABSTAIN" if failures else "CONSISTENT", "failures": failures})
    return outcomes


def verify_construction(request: dict[str, Any], bundle: dict[str, Any]) -> None:
    """Independently check retained attempted structures and bounded selection."""
    construction = bundle["construction"]
    keys(
        construction,
        {"program", "origin", "attempts", "candidate_count", "constraint_used", "static", "runtime_status"},
    )
    attempts = construction["attempts"]
    require(
        type(attempts) is list and 1 <= len(attempts) <= request["budget"]["max_candidates"],
        "matched construction candidate budget",
    )
    require(
        type(construction["candidate_count"]) is int and construction["candidate_count"] == len(attempts),
        "attempt-count accounting mismatch",
    )
    require(construction["constraint_used"] == sha(bundle["constraint"]), "construction must bind validated constraint")
    accepted = []
    for attempt in attempts:
        keys(attempt, {"program", "origin", "hash", "status"}, {"proof", "failure"})
        require(
            attempt["origin"] in {"host-model", "deterministic-constraint-compiler"},
            "actual construction origin required",
        )
        require(attempt["hash"] == sha(attempt["program"]), "attempt program hash mismatch")
        try:
            proof = prove_program(attempt["program"], request["requirements"], request["budget"], dominance=True)
        except ValueError:
            require(
                attempt["status"] == "REJECTED" and "failure" in attempt and "proof" not in attempt,
                "failed adaptation must remain rejected",
            )
            text(attempt["failure"])
        else:
            require(
                attempt["status"] == "STATIC_VALID" and "proof" in attempt and "failure" not in attempt,
                "attempt static disposition mismatch",
            )
            declared = attempt["proof"]
            keys(declared, {"valid", "scope", "nodes", "depth", "consistent_paths"})
            require(
                declared["valid"] is True and declared["scope"] == "static dominance proof only", "attempt proof scope"
            )
            require(
                all(
                    type(declared[metric]) is int and declared[metric] == proof[metric]
                    for metric in ["nodes", "depth", "consistent_paths"]
                ),
                "attempt proof resource mismatch",
            )
            accepted.append(attempt)
    require(bool(accepted), "no accepted static candidate")
    chosen = accepted[0]
    require(
        construction["program"] == chosen["program"] == bundle["program"]
        and construction["origin"] == chosen["origin"],
        "bounded selection identity",
    )
    require(
        construction["static"] == bundle["static"] and construction["runtime_status"] == "NOT_EXECUTED",
        "construction execution/promotion status",
    )


def verify_bundle(request: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Independently verify one inert construction receipt, without executing it."""
    records, _ = verify_request(request)
    bounded(bundle)
    keys(
        bundle,
        {
            "schema",
            "request_hash",
            "baseline_hash",
            "proposal_hash",
            "criticism",
            "constraint",
            "program",
            "static",
            "sandbox",
            "economics",
            "confirmation",
        },
        {"construction", "conventional_reference", "source_hashes", "resources", "independent_criticism"},
    )
    require(bundle["schema"] == "agialpha/specification-synthesis-bundle/v1", "bundle schema")
    require(bundle["request_hash"] == sha(request), "immutable request binding")
    require(bundle["baseline_hash"] == sha(request["baseline"]), "baseline binding")
    require(bundle["proposal_hash"] == sha(request["proposal"]), "proposal binding")
    require(bundle["program"] == request["proposal"], "program identity")
    require(sha(request["baseline"]) != sha(request["proposal"]), "corrective structure must change")
    old = prove_program(request["baseline"], request["requirements"], request["budget"], dominance=False)
    new = prove_program(request["proposal"], request["requirements"], request["budget"], dominance=True)
    witness = bundle["criticism"]
    critic_receipt = verify_criticism(request, witness)
    old = critic_receipt["baseline_static"]
    record = records[witness["record_id"]]
    field = witness["field"]
    constraint = bundle["constraint"]
    keys(
        constraint,
        {
            "kind",
            "field",
            "dimension",
            "record_id",
            "source_id",
            "record_hash",
            "baseline_hash",
            "witness_hash",
            "validated",
        },
    )
    wanted = {
        "kind": "require-dimension",
        "field": field,
        "dimension": witness["required_dimension"],
        "record_id": witness["record_id"],
        "source_id": witness["source_id"],
        "record_hash": sha(record),
        "baseline_hash": bundle["baseline_hash"],
        "witness_hash": sha(witness),
        "validated": True,
    }
    require(constraint == wanted, "typed corrective constraint not independently reproduced")
    keys(bundle["static"], {"valid", "scope"}, {"nodes", "depth", "consistent_paths"})
    require(
        bundle["static"]["valid"] is True and bundle["static"]["scope"] == "static dominance proof only",
        "static proof scope",
    )
    for metric in ["nodes", "depth", "consistent_paths"]:
        if metric in bundle["static"]:
            require(
                type(bundle["static"][metric]) is int and bundle["static"][metric] == new[metric],
                "static resource accounting mismatch",
            )
    keys(bundle["sandbox"], {"status", "reason", "executed"})
    require(
        bundle["sandbox"]["status"] == "BLOCKED" and bundle["sandbox"]["executed"] is False,
        "generated execution must remain blocked",
    )
    text(bundle["sandbox"]["reason"])
    keys(bundle["economics"], {"status", "operating_cohort_admitted", "earned_surplus", "actual_external_cash_paid"})
    require(
        bundle["economics"]
        == {
            "status": "UNKNOWN",
            "operating_cohort_admitted": False,
            "earned_surplus": "0",
            "actual_external_cash_paid": "0",
        },
        "no commercial or funding promotion from static proof",
    )
    require(bundle["confirmation"] is False, "no confirmation allocation")
    if "conventional_reference" in bundle:
        require(
            bundle["conventional_reference"] == conventional_reference(request),
            "all-cohort conventional reference mismatch",
        )
    if "construction" in bundle:
        verify_construction(request, bundle)
    if "resources" in bundle:
        resources = bundle["resources"]
        required = {
            "self_cpu_ns",
            "wall_ns",
            "child_cpu_seconds",
            "model_tokens",
            "prior_campaign_consumption",
            "deterministic_candidate_count",
        }
        require(type(resources) is dict and required <= set(resources), "resource meter fields")
        for metric in ["self_cpu_ns", "wall_ns", "deterministic_candidate_count"]:
            require(type(resources[metric]) is int and resources[metric] >= 0, "nonnegative exact resource meter")
        require(
            type(resources["child_cpu_seconds"]) is str
            and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", resources["child_cpu_seconds"]) is not None,
            "child CPU meter quantity",
        )
        require(
            resources["model_tokens"] == "UNKNOWN" and resources["prior_campaign_consumption"] == "UNKNOWN; not zero",
            "unknown usage cannot become zero",
        )
        if "construction" in bundle:
            actual = sum(
                attempt["origin"] == "deterministic-constraint-compiler"
                for attempt in bundle["construction"]["attempts"]
            )
            require(resources["deterministic_candidate_count"] == actual, "candidate-count accounting mismatch")
    if "independent_criticism" in bundle:
        saved = bundle["independent_criticism"]
        require(
            type(saved) is dict and all(saved.get(key) == critic_receipt[key] for key in critic_receipt),
            "preconstruction critic receipt mismatch",
        )
    return {
        "schema": "agialpha/specification-static-verification/v1",
        "accepted_static": True,
        "request_hash": sha(request),
        "program_hash": sha(request["proposal"]),
        "all_cohort_ids": list(records),
        "baseline_static": old,
        "proposal_static": new,
        "critic_validated": True,
        "intended_source_correction": "UNKNOWN",
        "source_authentication": "local excerpt integrity only; primary publisher provenance audited separately",
        "author_identity": "declared host-model identity, exact snapshot/usage not authenticated",
        "candidate_executed": False,
        "technical_activity_accepted": False,
        "business_accepted": False,
        "confirmation": False,
        "independence": "separate verifier implementation/process; shared host/libraries/mission context",
    }


def read_json(path: Path) -> Any:
    """Load bounded regular files with duplicate-key rejection."""
    require(not path.is_symlink() and path.is_file(), "regular JSON input required")
    require(path.stat().st_size <= MAX_BYTES, "input byte bound")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    result = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    bounded(result)
    return result


def verify_source_freeze(root: Path, pins: dict[str, str]) -> None:
    """Check externally frozen source bytes, never a candidate-supplied checker."""
    require(type(pins) is dict and 1 <= len(pins) <= 128, "bounded source freeze")
    own = "contrib/invention_automation/qualify_verify.py"
    require(own in pins, "verifier source must be frozen")
    for relative, wanted in pins.items():
        path = root / relative
        resolved = path.resolve(strict=True)
        require(resolved.is_relative_to(root.resolve()), "source escapes repository")
        require(not any(p.is_symlink() for p in [path, *path.parents]), "symlink source refused")
        require(
            path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == wanted,
            "source freeze mismatch: " + relative,
        )


def main() -> None:
    """Run checker under the inherited read-only kernel filter."""
    from contrib.invention_automation.readonly import enforce

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--bundle", type=Path)
    mode.add_argument("--criticism-only", action="store_true")
    parser.add_argument("--witness", type=Path)
    args = parser.parse_args()
    if args.criticism_only and args.witness is None:
        parser.error("--criticism-only requires --witness")
    if args.bundle is not None and args.witness is not None:
        parser.error("--witness is only for criticism-only verification")
    restriction = enforce()
    pins = read_json(args.freeze)
    verify_source_freeze(args.root, pins)
    own = args.root / "contrib/invention_automation/qualify_verify.py"
    write_denied = False
    try:
        with own.open("ab"):
            pass
    except PermissionError:
        write_denied = True
    require(write_denied, "verifier candidate-write restriction did not take effect")
    socket_denied = False
    try:
        with socket.socket():
            pass
    except PermissionError:
        socket_denied = True
    require(socket_denied, "verifier socket restriction did not take effect")
    request = read_json(args.request)
    if args.criticism_only:
        receipt = verify_criticism(request, read_json(args.witness))
    else:
        bundle = read_json(args.bundle)
        for name, expected in bundle.get("source_hashes", {}).items():
            require(pins.get(name) == expected, "candidate source must match externally frozen source")
        receipt = verify_bundle(request, bundle)
    print(
        json.dumps(
            {
                **receipt,
                "restriction": restriction,
                "candidate_write_denied_by_os": write_denied,
                "new_socket_denied_by_os": socket_denied,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
