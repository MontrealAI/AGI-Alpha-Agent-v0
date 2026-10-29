# SPDX-License-Identifier: Apache-2.0
"""Typed criticism and bounded program construction, without host candidate execution.

The static checker proves control-flow dominance, not transformer suitability.
The conventional record inspector is trusted engineering code. Constructed ASTs
remain inert until the repository Docker execution boundary is available.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from copy import deepcopy
from typing import Any

from ..structural_transfer.contracts import bounded, digest, exact_keys, identifier, quantity, text

SCHEMA = "agialpha/specification-synthesis-request/v1"
UNITS = {
    "V": "voltage",
    "kV": "voltage",
    "VA": "apparent_power",
    "kVA": "apparent_power",
    "MVA": "apparent_power",
    "Hz": "frequency",
}
DIMENSIONS = set(UNITS.values())


def validate_request(request: dict[str, Any]) -> None:
    """Validate exact inert inputs; quantities are evidence, never executable code."""
    bounded(request)
    exact_keys(
        request, {"schema", "problem", "sources", "records", "requirements", "baseline", "proposal", "author", "budget"}
    )
    if request["schema"] != SCHEMA:
        raise ValueError("specification request schema")
    exact_keys(request["problem"], {"id", "activity", "scope"})
    identifier(request["problem"]["id"])
    text(request["problem"]["activity"])
    if request["problem"]["scope"] != "specification-consistency-only":
        raise ValueError("physical or procurement authorization unsupported")
    reqs = request["requirements"]
    if not isinstance(reqs, dict) or not 1 <= len(reqs) <= 6:
        raise ValueError("one to six required dimensions")
    for name, dim in reqs.items():
        identifier(name)
        if dim not in DIMENSIONS:
            raise ValueError("uninstalled physical dimension")
    budget = request["budget"]
    exact_keys(budget, {"max_nodes", "max_depth", "max_candidates"})
    for key, cap in [("max_nodes", 128), ("max_depth", 20), ("max_candidates", 32)]:
        if type(budget[key]) is not int or not 1 <= budget[key] <= cap:
            raise ValueError("bounded integer construction budget")
    if not isinstance(request["sources"], list) or not 1 <= len(request["sources"]) <= 16:
        raise ValueError("source count bound")
    sources = {}
    for source in request["sources"]:
        exact_keys(source, {"id", "url", "sha256", "excerpt"})
        identifier(source["id"])
        text(source["url"])
        text(source["excerpt"])
        if source["id"] in sources or hashlib.sha256(source["excerpt"].encode()).hexdigest() != source["sha256"]:
            raise ValueError("duplicate or corrupt literal source")
        sources[source["id"]] = source
    if not isinstance(request["records"], list) or not 1 <= len(request["records"]) <= 64:
        raise ValueError("record count bound")
    seen = set()
    for record in request["records"]:
        exact_keys(record, {"id", "source_id", "fields"})
        identifier(record["id"])
        if record["id"] in seen or record["source_id"] not in sources:
            raise ValueError("record identity or provenance")
        seen.add(record["id"])
        if not isinstance(record["fields"], dict) or set(record["fields"]) - set(reqs):
            raise ValueError("record fields outside specification")
        for reading in record["fields"].values():
            exact_keys(reading, {"value", "unit"})
            quantity(reading["value"])
            text(reading["unit"], 20)
    exact_keys(request["author"], {"kind", "model", "prompt", "usage"})
    if request["author"]["kind"] not in {"host-model", "operator", "deterministic"}:
        raise ValueError("authorship must be explicit")
    for item in ["model", "prompt", "usage"]:
        text(request["author"][item], 12000)
    shape(request["baseline"], reqs, budget)
    shape(request["proposal"], reqs, budget)


def shape(program: dict[str, Any], requirements: dict[str, str], budget: dict[str, int]) -> dict[str, int]:
    """Validate a compositional allowlisted AST. This does not interpret it."""
    bounded(program)
    count = 0
    deepest = 0

    def visit(node: dict[str, Any], depth: int) -> None:
        nonlocal count, deepest
        count += 1
        deepest = max(deepest, depth)
        if count > budget["max_nodes"] or depth > budget["max_depth"]:
            raise ValueError("AST resource bound")
        if not isinstance(node, dict):
            raise ValueError("AST node object required")  # noqa: TRY004 - contract refusal matches other schema errors
        op = node.get("op")
        if op == "sequence":
            exact_keys(node, {"op", "steps"})
            if not isinstance(node["steps"], list) or not 1 <= len(node["steps"]) <= 16:
                raise ValueError("sequence bound")
            for step in node["steps"]:
                visit(step, depth + 1)
        elif op == "observe":
            exact_keys(node, {"op", "field"})
            if node["field"] not in requirements:
                raise ValueError("observation outside task")
        elif op == "emit":
            exact_keys(node, {"op", "status"})
            if node["status"] not in {"CONSISTENT", "ABSTAIN"}:
                raise ValueError("screen status; no suitability claim")
        elif op == "if":
            exact_keys(node, {"op", "test", "then", "else"})
            test = node["test"]
            exact_keys(test, {"op", "field", "dimension"})
            if (
                test["op"] != "dimension-is"
                or test["field"] not in requirements
                or test["dimension"] != requirements[test["field"]]
            ):
                raise ValueError("typed grounded predicate required")
            count += 1  # Predicates consume nodes too.
            if count > budget["max_nodes"]:
                raise ValueError("AST resource bound")
            visit(node["then"], depth + 1)
            visit(node["else"], depth + 1)
        else:
            raise ValueError("uninstalled AST operator; no Python, files, shell, network or payment")

    visit(program, 1)
    return {"nodes": count, "depth": deepest}


def dominance(program: dict[str, Any], requirements: dict[str, str], budget: dict[str, int]) -> dict[str, Any]:
    """Prove all CONSISTENT terminals dominated by every required dimension test.

    Both branches are visited symbolically. No input record or candidate action
    is executed; this proof cannot establish runtime outputs or economic value.
    """
    stats = shape(program, requirements, budget)
    success_paths = 0

    def walk(node: dict[str, Any], observed: set[str], guarded: set[str], tested: set[str]) -> bool:
        nonlocal success_paths
        op = node["op"]
        if op == "observe":
            observed.add(node["field"])
            return False
        if op == "emit":
            if node["status"] == "CONSISTENT":
                if not set(requirements) <= observed & guarded:
                    raise ValueError("unguarded CONSISTENT path")
                success_paths += 1
            return True
        if op == "sequence":
            done = False
            for step in node["steps"]:
                if done:
                    raise ValueError("unreachable tail after terminal")
                done = walk(step, observed, guarded, tested)
            return done
        field = node["test"]["field"]
        if field not in observed:
            raise ValueError("predicate before observation")
        if field in tested:
            raise ValueError("repeated predicate can create infeasible apparent acceptance")
        yes = walk(node["then"], set(observed), guarded | {field}, tested | {field})
        no = walk(node["else"], set(observed), set(guarded), tested | {field})
        if not yes or not no:
            raise ValueError("each branch must preserve a terminal disposition")
        return True

    if not walk(program, set(), set(), set()) or not success_paths:
        raise ValueError("complete screen with reachable positive path required")
    return {"valid": True, "scope": "static dominance proof only", **stats, "consistent_paths": success_paths}


def inspect_records(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the strong conventional dimensional-schema reference, not the AST."""
    result = []
    for record in request["records"]:
        failures = []
        for name in sorted(request["requirements"]):
            expected = request["requirements"][name]
            reading = record["fields"].get(name)
            if reading is None:
                failures.append({"field": name, "reason": "missing observation"})
            elif UNITS.get(reading["unit"]) != expected:
                failures.append({"field": name, "reason": "unknown or incompatible dimension"})
        result.append({"id": record["id"], "status": "ABSTAIN" if failures else "CONSISTENT", "failures": failures})
    return result


def criticize(request: dict[str, Any]) -> dict[str, Any]:
    """Find a source-bound literal mismatch, with intended correction unknown."""
    validate_request(request)
    try:
        dominance(request["baseline"], request["requirements"], request["budget"])
    except ValueError as error:
        if str(error) != "unguarded CONSISTENT path":
            raise ValueError("baseline defect is not reproduced dimensional admission") from error
    else:
        raise ValueError("baseline already guards specification; no corrective criticism")
    for record in request["records"]:
        for name, reading in record["fields"].items():
            dimension = request["requirements"][name]
            if UNITS.get(reading["unit"]) != dimension:
                source = next(s for s in request["sources"] if s["id"] == record["source_id"])
                # This binds the declared literal; it does not authenticate the URL.
                from fractions import Fraction

                literals = re.findall(
                    r"(?<![\w.])([0-9]+(?:\.[0-9]+)?)\s+" + re.escape(reading["unit"]) + r"(?![\w])", source["excerpt"]
                )
                if not any(Fraction(value) == Fraction(reading["value"]) for value in literals):
                    raise ValueError("quantity and unit witness not in literal source")
                return {
                    "record_id": record["id"],
                    "field": name,
                    "observed_unit": reading["unit"],
                    "required_dimension": dimension,
                    "source_id": source["id"],
                    "source_hash": source["sha256"],
                    "loss_driver": "incompatible dimension could pass specification screen",
                    "uncertainty": "source typo or intended value unknown; no silent correction",
                }
    raise ValueError("no reproduced dimensional counterexample; no correction promoted")


def constrain(request: dict[str, Any], witness: dict[str, Any]) -> dict[str, Any]:
    """Independently reproduce criticism before retaining a typed obligation."""
    if witness != criticize(request):
        raise ValueError("irrelevant or corrupted criticism")
    record = next(r for r in request["records"] if r["id"] == witness["record_id"])
    return {
        "kind": "require-dimension",
        "field": witness["field"],
        "dimension": witness["required_dimension"],
        "record_id": record["id"],
        "source_id": record["source_id"],
        "record_hash": digest(record),
        "baseline_hash": digest(request["baseline"]),
        "witness_hash": digest(witness),
        "validated": True,
    }


def construct(request: dict[str, Any], constraint: dict[str, Any]) -> dict[str, Any]:
    """Construct new nested control flow from typed obligations, not repair-family selection.

    Supplied terminals/predicates form the grammar. Orders and branch composition
    are generated. Enumeration is deliberately bounded and only statically judged.
    The actual host-model proposal is a separately attributed first candidate.
    """
    if constraint != constrain(request, criticize(request)):
        raise ValueError("unvalidated or stale constraint")
    cap = request["budget"]["max_candidates"]
    attempts: list[dict[str, Any]] = []
    accepted = []

    def consider(program: dict[str, Any], origin: str) -> None:
        entry = {"program": deepcopy(program), "origin": origin, "hash": digest(program)}
        try:
            proof = dominance(program, request["requirements"], request["budget"])
            entry["proof"] = proof
            entry["status"] = "STATIC_VALID"
            accepted.append(entry)
        except ValueError as error:
            entry["status"] = "REJECTED"
            entry["failure"] = str(error)
        attempts.append(entry)

    consider(request["proposal"], request["author"]["kind"])
    for order in itertools.permutations(sorted(request["requirements"])):
        if len(attempts) >= cap:
            break
        node: dict[str, Any] = {"op": "emit", "status": "CONSISTENT"}
        for field in reversed(order):
            node = {
                "op": "sequence",
                "steps": [
                    {"op": "observe", "field": field},
                    {
                        "op": "if",
                        "test": {"op": "dimension-is", "field": field, "dimension": request["requirements"][field]},
                        "then": node,
                        "else": {"op": "emit", "status": "ABSTAIN"},
                    },
                ],
            }
        consider(node, "deterministic-constraint-compiler")
    if not accepted:
        raise ValueError("no program satisfies static contract within construction budget")
    # Preserve actual host authorship when valid; no invented proxy-value ranking.
    selected = accepted[0]
    return {
        "program": selected["program"],
        "origin": selected["origin"],
        "attempts": attempts,
        "candidate_count": len(attempts),
        "constraint_used": digest(constraint),
        "static": selected["proof"],
        "runtime_status": "NOT_EXECUTED",
    }
