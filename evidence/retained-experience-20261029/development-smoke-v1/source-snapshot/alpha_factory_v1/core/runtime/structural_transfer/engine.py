# SPDX-License-Identifier: Apache-2.0
"""Execute source work, extract typed structure, instantiate and independently check."""

from __future__ import annotations

import base64
import copy
import importlib
from pathlib import Path
import re
from typing import Any, Callable

from .contracts import (
    CAPTURE_SCHEMA,
    PRINCIPLE_SCHEMA,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    SOURCE_SCHEMA,
    MAX_BYTES,
    bounded,
    canonical,
    code_hash,
    digest,
    exact_keys,
    identifier,
    quantity,
    rational,
    strict_acceptance,
    text,
)


def _adapters() -> Any:
    """Load only the installed adapter registry, never a supplied module name."""
    return importlib.import_module(".adaptations", __package__)


def _implementation_hashes(adapters: Any, adapter_id: str) -> dict[str, str]:
    """Bind deeper installed adapter and checker modules when the registry supplies them."""
    function = getattr(adapters, "implementation_hashes", None)
    if function is None:
        return {"adapter_spec": code_hash(adapters.adapter_spec)}
    hashes = function(adapter_id)
    if not isinstance(hashes, dict) or not 1 <= len(hashes) <= 30:
        raise ValueError("bounded installed implementation hashes required")
    for name, value in hashes.items():
        text(name, 200)
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("implementation hash syntax")
    return hashes


def _no_labels(value: Any) -> None:
    """Reject supplied oracle labels and manually asserted validity inside operational inputs."""
    reserved = {
        "hidden_labels",
        "expected_result",
        "expected_artifact",
        "oracle",
        "heldout",
        "validation_passed",
        "validated",
    }
    if isinstance(value, dict):
        if reserved & set(value):
            raise ValueError("operational input contains unsupported labels or validation flags")
        for child in value.values():
            _no_labels(child)
    elif isinstance(value, list):
        for child in value:
            _no_labels(child)


def _graph(spec: dict[str, Any]) -> dict[str, Any]:
    """Normalize a declared typed graph and reject unknown or ambiguous dimensions."""
    family = spec.get("family")
    if family not in {"linear-capacity", "interval-censoring", "precedence"}:
        raise ValueError("unsupported structural family")
    variables = spec.get("variables")
    relations = spec.get("relations")
    if not isinstance(variables, list) or not 1 <= len(variables) <= 20:
        raise ValueError("bounded typed variables required")
    names: set[str] = set()
    roles: set[str] = set()
    normalized = []
    for variable in variables:
        exact_keys(variable, {"name", "dimension", "unit", "role"})
        name = identifier(variable["name"])
        role = identifier(variable["role"])
        dimension = text(variable["dimension"], 80)
        unit = text(variable["unit"], 80)
        if dimension.lower() in {"unknown", "?", "any", "unspecified"} or unit.lower() in {
            "unknown",
            "?",
            "any",
            "unspecified",
        }:
            raise ValueError("unknown dimensions and units cannot transfer")
        if name in names or role in roles:
            raise ValueError("variable names and causal roles must be unique")
        names.add(name)
        roles.add(role)
        normalized.append(dict(variable))
    if not isinstance(relations, list) or not 1 <= len(relations) <= 20:
        raise ValueError("bounded typed relations required")
    known = {"sum", "conservation", "difference", "precedence", "nonnegative", "order", "censoring"}
    checked = []
    by_name = {item["name"]: item for item in normalized}
    for relation in relations:
        exact_keys(relation, {"kind", "inputs", "output"})
        inputs = relation["inputs"]
        if relation["kind"] not in known or not isinstance(inputs, list) or not 1 <= len(inputs) <= 8:
            raise ValueError("unsupported typed relation")
        if any(name not in names for name in inputs) or (
            relation["output"] is not None and relation["output"] not in names
        ):
            raise ValueError("relation references an unknown variable")
        members = [*inputs, *([relation["output"]] if relation["output"] is not None else [])]
        if len({(by_name[name]["dimension"], by_name[name]["unit"]) for name in members}) != 1:
            raise ValueError("relation operands require identical concrete dimensions and units")
        checked.append(dict(relation))
    return {"family": family, "variables": sorted(normalized, key=lambda item: item["role"]), "relations": checked}


def structural_signature(spec: dict[str, Any]) -> str:
    """Hash relation topology, causal roles and dimension equivalence, never prose."""
    graph = _graph(spec)
    by_name = {item["name"]: item for item in graph["variables"]}
    dimensions: dict[str, int] = {}
    variables = []
    for variable in graph["variables"]:
        dimension = dimensions.setdefault(variable["dimension"], len(dimensions))
        variables.append({"role": variable["role"], "dimension_parameter": dimension})
    relations = [
        {
            "kind": item["kind"],
            "inputs": [by_name[name]["role"] for name in item["inputs"]],
            "output": by_name[item["output"]]["role"] if item["output"] is not None else None,
        }
        for item in graph["relations"]
    ]
    return digest(
        {
            "family": graph["family"],
            "variables": variables,
            "relations": sorted(relations, key=lambda item: canonical(item)),
        }
    )


def _builtin_spec(kind: str, task: dict[str, Any]) -> dict[str, Any]:
    dimension, unit = text(task.get("dimension"), 80), text(task.get("unit"), 80)
    if kind == "capacity-ledger":
        family, names = "linear-capacity", ["capacity", "reserved", "remaining"]
        relations = [{"kind": "conservation", "inputs": ["reserved", "remaining"], "output": "capacity"}]
    elif kind == "interval-audit":
        family, names = "interval-censoring", ["lower", "width", "upper"]
        relations = [
            {"kind": "sum", "inputs": ["lower", "width"], "output": "upper"},
            {"kind": "order", "inputs": ["lower", "upper"], "output": None},
        ]
    elif kind == "precedence-schedule":
        if dimension != "time":
            raise ValueError("precedence scheduling requires a known time dimension")
        family, names = "precedence", ["start", "duration", "finish"]
        relations = [
            {"kind": "sum", "inputs": ["start", "duration"], "output": "finish"},
            {"kind": "precedence", "inputs": ["finish", "start"], "output": None},
        ]
    else:
        raise ValueError("unsupported built-in source work")
    return {
        "family": family,
        "variables": [{"name": name, "role": name, "dimension": dimension, "unit": unit} for name in names],
        "relations": relations,
        "assumptions": [],
    }


def execute_source(kind: str, task: dict[str, Any]) -> dict[str, Any]:
    """Execute bounded useful primitive work; these development sources prove no external demand."""
    _builtin_spec(kind, task)
    if kind == "capacity-ledger":
        exact_keys(task, {"dimension", "unit", "capacity", "demands"})
        capacity = quantity(task["capacity"])
        if not isinstance(task["demands"], list) or not 1 <= len(task["demands"]) <= 100:
            raise ValueError("bounded source demands required")
        remaining, accepted, rejected, seen = capacity, [], [], set()
        for demand in task["demands"]:
            exact_keys(demand, {"id", "amount"})
            ident, amount = identifier(demand["id"]), quantity(demand["amount"])
            if ident in seen:
                raise ValueError("duplicate source demand")
            seen.add(ident)
            if amount <= remaining:
                remaining -= amount
                accepted.append(ident)
            else:
                rejected.append(ident)
        return {
            "accepted_ids": accepted,
            "rejected_ids": rejected,
            "capacity": rational(capacity),
            "reserved": rational(capacity - remaining),
            "remaining": rational(remaining),
        }
    if kind == "interval-audit":
        exact_keys(task, {"dimension", "unit", "observations"})
        rows = task["observations"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
            raise ValueError("bounded interval observations required")
        result, seen = [], set()
        for row in rows:
            exact_keys(row, {"id", "lower", "upper"})
            ident = identifier(row["id"])
            low, high = quantity(row["lower"], nonnegative=False), quantity(row["upper"], nonnegative=False)
            if ident in seen or low > high:
                raise ValueError("duplicate or inverted source interval")
            seen.add(ident)
            result.append({"id": ident, "lower": rational(low), "upper": rational(high), "width": rational(high - low)})
        return {"intervals": result, "unknown_point_values": True}
    exact_keys(task, {"dimension", "unit", "jobs"})
    jobs = task["jobs"]
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 100:
        raise ValueError("bounded precedence jobs required")
    pending: dict[str, Any] = {}
    for job in jobs:
        exact_keys(job, {"id", "duration", "after"})
        ident = identifier(job["id"])
        quantity(job["duration"])
        if ident in pending or not isinstance(job["after"], list) or len(job["after"]) > 100:
            raise ValueError("ambiguous precedence job")
        pending[ident] = job
    if any(parent not in pending for job in jobs for parent in job["after"]):
        raise ValueError("unknown predecessor")
    completed: dict[str, Any] = {}
    while pending:
        ready = sorted(ident for ident, job in pending.items() if all(parent in completed for parent in job["after"]))
        if not ready:
            raise ValueError("cyclic source precedence")
        for ident in ready:
            job = pending.pop(ident)
            start = max((quantity(completed[parent]["finish"]) for parent in job["after"]), default=quantity("0"))
            duration = quantity(job["duration"])
            completed[ident] = {
                "id": ident,
                "start": rational(start),
                "duration": rational(duration),
                "finish": rational(start + duration),
            }
    return {
        "jobs": list(completed.values()),
        "makespan": rational(max(quantity(row["finish"]) for row in completed.values())),
    }


def check_source(kind: str, task: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Check source constraints through separate arithmetic, rejecting partial execution."""
    if kind == "capacity-ledger":
        selected = set(result["accepted_ids"])
        rejected = set(result["rejected_ids"])
        amounts = {item["id"]: quantity(item["amount"]) for item in task["demands"]}
        reserved = sum((amounts[item] for item in selected), quantity("0"))
        valid = (
            selected.isdisjoint(rejected)
            and selected | rejected == set(amounts)
            and len(selected) == len(result["accepted_ids"])
            and len(rejected) == len(result["rejected_ids"])
            and quantity(result["capacity"]) == quantity(task["capacity"])
            and reserved == quantity(result["reserved"])
            and reserved + quantity(result["remaining"]) == quantity(task["capacity"])
        )
    elif kind == "interval-audit":
        observed = {item["id"]: item for item in task["observations"]}
        valid = len(result["intervals"]) == len(observed) and result.get("unknown_point_values") is True
        for row in result["intervals"]:
            source = observed.pop(row["id"])
            low, high = quantity(row["lower"], nonnegative=False), quantity(row["upper"], nonnegative=False)
            valid = valid and low == quantity(source["lower"], nonnegative=False)
            valid = (
                valid and high == quantity(source["upper"], nonnegative=False) and high - low == quantity(row["width"])
            )
        valid = valid and not observed
    elif kind == "precedence-schedule":
        jobs = {item["id"]: item for item in task["jobs"]}
        scheduled = {item["id"]: item for item in result["jobs"]}
        valid = len(scheduled) == len(result["jobs"]) and set(scheduled) == set(jobs)
        for ident, item in scheduled.items():
            valid = valid and quantity(item["duration"]) == quantity(jobs[ident]["duration"])
            valid = valid and quantity(item["start"]) + quantity(item["duration"]) == quantity(item["finish"])
            valid = valid and all(
                quantity(scheduled[parent]["finish"]) <= quantity(item["start"]) for parent in jobs[ident]["after"]
            )
        valid = valid and quantity(result["makespan"]) == max(quantity(row["finish"]) for row in scheduled.values())
    else:
        raise ValueError("unsupported source verifier")
    if valid is not True:
        raise ValueError("independent source verification failed")
    return {
        "accepted": True,
        "task_id": digest(task),
        "artifact_hash": digest(result),
        "scope": "exact declared arithmetic and constraints; no external cash or physical attestation",
    }


def _evidence(manifest: Any, *, read_files: bool) -> list[dict[str, Any]]:
    """Capture bounded evidence bytes without treating provenance as semantic acceptance."""
    if manifest is None:
        return []
    if not isinstance(manifest, list) or len(manifest) > 12:
        raise ValueError("bounded source evidence manifest required")
    out, seen, total = [], set(), 0
    for item in manifest:
        exact_keys(item, {"path", "sha256", "role"}, {"url", "captured_base64"})
        path, expected = Path(text(item["path"], 1024)), item["sha256"]
        if item["role"] not in {"source", "task", "artifact", "acceptance", "cost"} or str(path) in seen:
            raise ValueError("ambiguous evidence role or duplicate path")
        seen.add(str(path))
        if "url" in item and not text(item["url"], 2048).startswith(("https://", "urn:agialpha:")):
            raise ValueError("source provenance must be an HTTPS URL or explicit AGIALPHA URN")
        if read_files:
            if path.is_symlink() or not path.is_file():
                raise ValueError("regular evidence file required")
            with path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
        else:
            raw = base64.b64decode(item.get("captured_base64", ""), validate=True)
        total += len(raw)
        import hashlib

        if total > MAX_BYTES // 2 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("evidence capture hash or byte bound mismatch")
        out.append({**item, "captured_base64": base64.b64encode(raw).decode()})
    return out


def _source_execution(
    source: dict[str, Any],
    stage: Callable[[str, dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    kind, task = source["kind"], source["task"]
    if kind == "adapter-work":
        exact_keys(task, {"adapter_id", "target", "constructed"})
        adapters = _adapters()
        adapter_id = identifier(task["adapter_id"])
        spec = adapters.adapter_spec(adapter_id)
        artifact = bounded(adapters.execute(adapter_id, task["constructed"], task["target"]))
        if stage:
            stage(
                "source-execution",
                {"artifact": artifact, "artifact_hash": digest(artifact), "constructed": task["constructed"]},
            )
        verdict = adapters.check(adapter_id, target=task["target"], artifact=artifact, constructed=task["constructed"])
        if stage:
            stage("source-independent-check", {"verdict": bounded(verdict)})
        strict_acceptance(verdict, task["target"]["id"], digest(artifact))
        hashes = {
            "execute": code_hash(adapters.execute),
            "checker": code_hash(adapters.check),
            "adapter_spec": code_hash(adapters.adapter_spec),
            "implementations": _implementation_hashes(adapters, adapter_id),
        }
        return spec, artifact, verdict, hashes
    spec = _builtin_spec(kind, task)
    artifact = execute_source(kind, task)
    if stage:
        stage("source-execution", {"artifact": artifact, "artifact_hash": digest(artifact)})
    verdict = check_source(kind, task, artifact)
    if stage:
        stage("source-independent-check", {"verdict": verdict})
    return spec, artifact, verdict, {"execute": code_hash(execute_source), "checker": code_hash(check_source)}


def _boundary_checks(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Exercise rejected boundary witnesses, rather than trusting declared validity flags."""
    unknown = copy.deepcopy(spec)
    unknown["variables"][0]["dimension"] = "unknown"
    mismatched = copy.deepcopy(spec)
    mismatched["variables"][0]["unit"] += "-incompatible"
    checks = [
        ("unknown dimension", lambda: _graph(unknown)),
        ("incompatible units in a relation", lambda: _graph(mismatched)),
        ("negative nonnegative quantity", lambda: quantity("-1")),
    ]
    observations = []
    for case, operation in checks:
        try:
            operation()
        except ValueError:
            observations.append({"case": case, "rejected": True})
        else:
            raise ValueError("extraction boundary self-check failed")
    return observations


def extract(
    source: dict[str, Any],
    *,
    _captured_evidence: list[dict[str, Any]] | None = None,
    stage: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Perform source work and retain its checked type-parametric arithmetic structure."""
    bounded(source)
    source = copy.deepcopy(source)
    _no_labels(source)
    exact_keys(source, {"schema", "id", "kind", "task", "context"}, {"evidence", "cost_ids"})
    if source["schema"] != SOURCE_SCHEMA:
        raise ValueError("source schema mismatch")
    identifier(source["id"])
    text(source["context"])
    cost_ids = source.get("cost_ids", [])
    if not isinstance(cost_ids, list) or len(cost_ids) > 100 or len(set(cost_ids)) != len(cost_ids):
        raise ValueError("source cost identities must be unique")
    for item in cost_ids:
        identifier(item)
    if source["kind"] == "adapter-work" and (not source.get("evidence") or not cost_ids):
        raise ValueError("primary source work requires immutable evidence provenance and source-work cost identities")
    if _captured_evidence is None:
        manifest = _evidence(source.get("evidence"), read_files=True)
    else:
        manifest = _evidence(_captured_evidence, read_files=False)
        original = [{k: v for k, v in item.items() if k != "captured_base64"} for item in manifest]
        if original != source.get("evidence", []):
            raise ValueError("captured evidence manifest differs from source provenance")
    spec, artifact, verdict, hashes = _source_execution(source, stage)
    # Detect input replacement between capture, actual operation and independent check.
    if _captured_evidence is None and manifest != _evidence(source.get("evidence"), read_files=True):
        raise ValueError("source bytes changed during execution")
    graph = _graph(spec)
    assumptions = spec.get("assumptions", [])
    if not isinstance(assumptions, list) or len(assumptions) > 20:
        raise ValueError("bounded explicit assumptions required")
    for assumption in assumptions:
        text(assumption)
    principle = {
        "schema": PRINCIPLE_SCHEMA,
        "id": source["id"] + "/principle",
        **graph,
        "signature": structural_signature(graph),
        "assumptions": assumptions,
        "constraints": "exact declared relations, dimensional equalities and nonnegative durations/amounts",
        "epistemic_status": "supported-axiom-instantiated-by-checked-execution",
        "extraction_method": "typed relation projection from whitelisted executed algorithm and independent constraint check",
        "applicability_boundaries": [
            "structural instantiation only; no numerical conversion across domains",
            "no inference of an empirical physical law or all source causal relations",
            "external cash, complete demand and unseen outcomes are not attested",
        ],
        "counterexamples": _boundary_checks(spec),
        "source_id": source["id"],
        "source_task_hash": digest(source["task"]),
        "source_result_hash": digest(artifact),
        "extraction_code_hash": code_hash(extract),
    }
    body = {
        "schema": CAPTURE_SCHEMA,
        "source": source,
        "evidence_capture": manifest,
        "observation": {
            "source_hash": digest(source),
            "task_hash": digest(source["task"]),
            "result": artifact,
            "result_hash": digest(artifact),
            "acceptance": verdict,
            "acceptance_hash": digest(verdict),
            "code_hashes": hashes,
        },
        "principle": principle,
        "developmental_only": source["kind"] != "adapter-work",
    }
    body["capture_hash"] = digest(body)
    return bounded(body)


def inspect_capture(capture: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct every source observation and check immutable hashes and code bindings."""
    bounded(capture)
    exact_keys(
        capture,
        {"schema", "source", "evidence_capture", "observation", "principle", "developmental_only", "capture_hash"},
    )
    if capture["schema"] != CAPTURE_SCHEMA or capture["capture_hash"] != digest(
        {k: v for k, v in capture.items() if k != "capture_hash"}
    ):
        raise ValueError("immutable source capture mismatch")
    _evidence(capture["evidence_capture"], read_files=False)
    replay = extract(capture["source"], _captured_evidence=capture["evidence_capture"])
    if replay != capture:
        raise ValueError("source replay, implementation or extraction binding mismatch")
    return {
        "valid": True,
        "capture_hash": capture["capture_hash"],
        "source_id": capture["source"]["id"],
        "principle_id": capture["principle"]["id"],
        "signature": capture["principle"]["signature"],
        "developmental_only": capture["developmental_only"],
        "principle": capture["principle"],
    }


def validate_mapping(principle: dict[str, Any], target: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    """Validate total role-preserving graph isomorphism with explicit dimensional instantiation."""
    spec = _adapters().adapter_spec(identifier(target["adapter_id"]))
    source_graph, target_graph = _graph(principle), _graph(spec)
    if structural_signature(source_graph) != structural_signature(target_graph):
        raise ValueError("typed graph signature does not match target need")
    exact_keys(mapping, {"variables", "bindings"})
    variables, bindings = mapping["variables"], mapping["bindings"]
    if not isinstance(variables, dict) or not isinstance(bindings, list) or not 1 <= len(bindings) <= 20:
        raise ValueError("explicit variable and dimension bindings required")
    source_vars = {item["name"]: item for item in source_graph["variables"]}
    target_vars = {item["name"]: item for item in target_graph["variables"]}
    if (
        set(variables) != set(source_vars)
        or set(variables.values()) != set(target_vars)
        or len(set(variables.values())) != len(variables)
    ):
        raise ValueError("mapping must bind every variable bijectively")
    expected = set()
    for name, destination in variables.items():
        old, new = source_vars[name], target_vars[destination]
        if old["role"] != new["role"]:
            raise ValueError("mapping changes causal roles")
        expected.add((old["dimension"], old["unit"], new["dimension"], new["unit"]))
    provided = set()
    for binding in bindings:
        exact_keys(binding, {"source_dimension", "source_unit", "target_dimension", "target_unit", "mode"})
        if binding["mode"] != "structural-instantiation":
            raise ValueError("numerical conversion and unsupported extrapolation are not authorized")
        provided.add(
            (binding["source_dimension"], binding["source_unit"], binding["target_dimension"], binding["target_unit"])
        )
    if len(provided) != len(bindings) or provided != expected:
        raise ValueError("dimension or unit binding mismatch")
    mapped_relations = [
        {
            "kind": item["kind"],
            "inputs": [variables[name] for name in item["inputs"]],
            "output": variables[item["output"]] if item["output"] is not None else None,
        }
        for item in source_graph["relations"]
    ]
    if sorted(map(canonical, mapped_relations)) != sorted(map(canonical, target_graph["relations"])):
        raise ValueError("mapping changes relation direction or topology")
    assumptions = spec.get("assumptions", [])
    declared = target.get("assumptions", [])
    if not isinstance(declared, list) or any(item not in declared for item in assumptions):
        raise ValueError("target must explicitly acknowledge required assumptions")
    return {
        "valid": True,
        "signature": structural_signature(target_graph),
        "mapping_hash": digest(mapping),
        "mode": "structural-instantiation",
        "numerical_cross_domain_conversion": False,
    }


def validate_costs(costs: Any) -> dict[str, Any]:
    """Keep source, retention, adaptation and research estimates disjoint and attributable."""
    if not isinstance(costs, list) or len(costs) > 100:
        raise ValueError("bounded cost records required")
    seen, totals = set(), {name: quantity("0") for name in ("source", "retention", "adaptation", "research")}
    for cost in costs:
        exact_keys(cost, {"id", "stage", "quantity", "quantity_unit", "rate_per_unit", "currency", "basis"})
        ident = identifier(cost["id"])
        if ident in seen or cost["stage"] not in totals or cost["currency"] != "USD" or cost["basis"] != "estimate":
            raise ValueError("duplicate, unqualified measured or unsupported cost claim")
        seen.add(ident)
        text(cost["quantity_unit"], 80)
        totals[cost["stage"]] += quantity(cost["quantity"]) * quantity(cost["rate_per_unit"])
    return {
        "currency": "USD",
        "basis": "declared-quantity-times-rate-estimates",
        "cost_ids": sorted(seen),
        "by_stage": {name: rational(value) for name, value in totals.items()},
        "total": rational(sum(totals.values(), quantity("0"))),
        "settled": False,
    }


def run(request: dict[str, Any], stage: Callable[[str, dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Run all stages as actual operations and stop only at independently accepted output."""
    bounded(request)
    request = copy.deepcopy(request)
    exact_keys(request, {"schema", "id", "captures", "target", "mapping", "costs", "economic_link"})
    if request["schema"] != REQUEST_SCHEMA:
        raise ValueError("transfer request schema mismatch")
    identifier(request["id"])
    target = request["target"]
    _no_labels(target)
    identifier(target["id"])
    text(target.get("need"))
    economic = request["economic_link"]
    exact_keys(economic, {"beneficiary", "need", "status"})
    text(economic["beneficiary"])
    text(economic["need"])
    if economic["status"] not in {"internal-use", "planning"}:
        raise ValueError("measured demand, paid settlement and successor attribution need separate external evidence")
    captures = request["captures"]
    if not isinstance(captures, list) or not 1 <= len(captures) <= 8:
        raise ValueError("bounded checked source captures required")
    events = []

    def emit(name: str, detail: dict[str, Any]) -> None:
        events.append({"stage": name, "detail": detail})
        if stage:
            stage(name, detail)

    checked = [inspect_capture(item) for item in captures]
    if len({item["capture_hash"] for item in checked}) != len(checked):
        raise ValueError("duplicate source experience")
    emit("source-observation", {"checked": checked})
    emit(
        "principle-extraction",
        {
            "principles": [
                {
                    "principle_id": item["principle"]["id"],
                    "principle_hash": digest(item["principle"]),
                    "method": item["principle"]["extraction_method"],
                }
                for item in captures
            ]
        },
    )
    spec = _adapters().adapter_spec(identifier(target["adapter_id"]))
    signature = structural_signature(spec)
    matches = [item for item in captures if item["principle"]["signature"] == signature]
    emit(
        "structural-retrieval", {"query_signature": signature, "matches": [item["principle"]["id"] for item in matches]}
    )
    if not matches:
        raise ValueError("no typed structural match for target")
    if len(matches) != 1:
        raise ValueError("ambiguous structural matches require a bounded explicit source selection")
    capture = matches[0]
    if capture["developmental_only"] is not False:
        raise ValueError("development source arithmetic alone does not qualify as executed beneficiary work")
    principle = capture["principle"]
    validated = validate_mapping(principle, target, request["mapping"])
    emit("mapping-validation", validated)
    costs = validate_costs(request["costs"])
    source_cost_ids = set(capture["source"].get("cost_ids", []))
    recorded_source_ids = {item["id"] for item in request["costs"] if item["stage"] == "source"}
    if source_cost_ids != recorded_source_ids:
        raise ValueError("source-work cost identities must be retained exactly once in the source stage")
    adapters = _adapters()
    constructed = bounded(
        adapters.construct(target["adapter_id"], principle=principle, target=target, mapping=request["mapping"])
    )
    emit(
        "adaptation-construction",
        {
            "constructed": constructed,
            "constructed_hash": digest(constructed),
            "code_hash": code_hash(adapters.construct),
        },
    )
    artifact = bounded(adapters.execute(target["adapter_id"], constructed, target))
    emit(
        "adaptation-execution",
        {"artifact": artifact, "artifact_hash": digest(artifact), "code_hash": code_hash(adapters.execute)},
    )
    verdict = adapters.check(target["adapter_id"], target=target, artifact=artifact, constructed=constructed)
    emit("independent-acceptance", {"verdict": bounded(verdict), "checker_code_hash": code_hash(adapters.check)})
    strict_acceptance(verdict, target["id"], digest(artifact))
    delivery = {
        "task_id": target["id"],
        "artifact_hash": digest(artifact),
        "acceptance_hash": digest(verdict),
        "beneficiary": economic["beneficiary"],
        "need": economic["need"],
        "economic_status": economic["status"],
        "cash_attestation": False,
        "adapter_implementation_preexisting": True,
        "successor_attribution": "not-established",
    }
    emit("delivery-economic-link", {"delivery": delivery, "costs": costs})
    body = {
        "schema": RESULT_SCHEMA,
        "id": request["id"],
        "method": "executed typed structural instantiation",
        "request_hash": digest(request),
        "source_capture_hash": capture["capture_hash"],
        "principle_hash": digest(principle),
        "target_hash": digest(target),
        "mapping": validated,
        "constructed": constructed,
        "artifact": artifact,
        "acceptance": verdict,
        "delivery": delivery,
        "costs": costs,
        "stages": events,
        "accepted": True,
        "code_hashes": {
            "runtime": code_hash(run),
            "construct": code_hash(adapters.construct),
            "execute": code_hash(adapters.execute),
            "check": code_hash(adapters.check),
            "implementations": _implementation_hashes(adapters, target["adapter_id"]),
        },
    }
    body["result_hash"] = digest(body)
    return bounded(body)


def verify_result(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Replay the entire bounded pipeline and compare the accepted artifact byte for byte."""
    if result.get("accepted") is not True or result != run(request):
        raise ValueError("structural transfer result replay mismatch")
    return {
        "valid": True,
        "passed": True,
        "accepted": True,
        "result_hash": result["result_hash"],
        "artifact_hash": digest(result["artifact"]),
        "task_id": request["target"]["id"],
    }
