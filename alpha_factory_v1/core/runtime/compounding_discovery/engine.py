# SPDX-License-Identifier: Apache-2.0
"""Execute switchable transfer, bounded strategy programs and extra falsification.

All configurations use the same independent mathematical certificate checker.
This is a deterministic model investigation, not a model inference service or
an operational vehicle-safety certificate. Source-pinned promotion is separate
from economic funding and the existing signed mission journal owns approval.
"""

from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
from pathlib import Path
import random
import time
from typing import Any, Callable, cast

from ..structural_transfer import adaptations, eadarp, eadarp_check, engine as transfer
from ..structural_transfer.contracts import bounded, digest, exact_keys, identifier
from . import programs

SCHEMA = "agialpha/discovery-request/v1"
CPU_RATE = "1/36000"
OPERATION_RATE = "0"
DEFAULT_PROGRAM = {"op": "per-vehicle-lp", "method": "highs", "presolve": True}


class BudgetExceeded(ValueError):
    """The shared resource cap was exhausted; retain the failure and its costs."""


def source_hashes() -> dict[str, str]:
    """Return exact installed code bindings; callers keep a trusted external copy."""
    paths = sorted(Path(__file__).parent.glob("*.py")) + sorted(Path(transfer.__file__).parent.glob("*.py"))
    return {str(p.relative_to(Path(__file__).parents[1])): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _sealed(body: dict[str, Any], key: str) -> dict[str, Any]:
    return {**body, key: digest(body)}


def empty_memory() -> dict[str, Any]:
    """Create the frozen initial state, with no solved tasks or retained assets."""
    return _sealed(
        {
            "schema": "agialpha/discovery-memory/v1",
            "version": 0,
            "parent_hash": None,
            "history": [],
            "assets": [],
            "principles": [],
        },
        "memory_hash",
    )


def structure_key(target: dict[str, Any]) -> str:
    """Index actual model structure, excluding updates, outcomes and task names."""
    ins = eadarp.parse(target)
    return str(
        digest(
            {
                "adapter": target["adapter_id"],
                "vehicles": ins["vehicles"],
                "users": ins["n"],
                "route_lengths": [len(r) for r in target["routes"]],
                "assumptions": target["assumptions"],
            }
        )
    )


def validate_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Replay retained certificates; hashes detect damage but do not authenticate an owner."""
    bounded(memory)
    exact_keys(memory, {"schema", "version", "parent_hash", "history", "assets", "principles", "memory_hash"})
    if memory["schema"] != "agialpha/discovery-memory/v1" or memory["memory_hash"] != digest(
        {k: v for k, v in memory.items() if k != "memory_hash"}
    ):
        raise ValueError("corrupted memory identity")
    if type(memory["version"]) is not int or memory["version"] != len(memory["history"]) or memory["version"] > 16:
        raise ValueError("bounded chronological memory required")
    if (memory["version"] == 0) != (memory["parent_hash"] is None):
        raise ValueError("invalid memory parent")
    known, tasks = {}, set()
    prefix = empty_memory()
    principles: list[Any] = []
    for record in memory["history"]:
        exact_keys(
            record,
            {
                "id",
                "task",
                "artifact",
                "program",
                "structure",
                "source_hashes",
                "result_hash",
                "cost_total",
                "counterexamples",
                "principle_ids",
                "captures",
            },
        )
        if record["id"] in tasks or record["source_hashes"] != source_hashes():
            raise ValueError("duplicate history or stale source qualification")
        tasks.add(record["id"])
        programs.validate_program(record["program"])
        verdict = eadarp_check.check(record["task"], record["artifact"], {})
        if verdict.get("accepted") is not True or record["structure"] != structure_key(record["task"]):
            raise ValueError("unsupported memory promotion")
        if Fraction(record["cost_total"]) < 0:
            raise ValueError("negative historical resource cost")
        if record["counterexamples"]:
            _verify_critique_records(record["task"], record["artifact"], record["counterexamples"])
        known[record["id"]] = record
        for capture in record["captures"]:
            transfer.inspect_capture(capture)
            if capture not in principles:
                principles.append(capture)
        asset = _asset(record, prefix["version"] + 1)
        prefix = _sealed(
            {
                "schema": memory["schema"],
                "version": prefix["version"] + 1,
                "parent_hash": prefix["memory_hash"],
                "history": [*prefix["history"], record],
                "assets": [*prefix["assets"], asset],
                "principles": copy.deepcopy(principles),
            },
            "memory_hash",
        )
    for asset in memory["assets"]:
        exact_keys(asset, {"id", "kind", "structure", "program", "support", "limits", "counterexamples"})
        support = known.get(asset["support"])
        if (
            support is None
            or asset["kind"] != "validated-strategy"
            or asset["program"] != support["program"]
            or asset["structure"] != support["structure"]
            or not asset["limits"]
        ):
            raise ValueError("unsupported retained asset")
    if prefix != memory:
        raise ValueError("chronological memory prefix mismatch")
    return memory


def _asset(record: dict[str, Any], version: int) -> dict[str, Any]:
    return {
        "id": f"strategy-{version}",
        "kind": "validated-strategy",
        "structure": record["structure"],
        "program": record["program"],
        "support": record["id"],
        "limits": ["same declared linear model and route cardinalities; no general performance guarantee"],
        "counterexamples": [
            {"kind": criticism["kind"], "record_hash": digest(criticism)} for criticism in record["counterexamples"]
        ],
    }


class Meter:
    """Prospectively count all stages and LP invocations under a common cap."""

    def __init__(self, budget: dict[str, Any], callback: Callable[[dict[str, Any]], None] | None = None):
        exact_keys(budget, {"operations", "solver_calls", "cpu_seconds"})
        if any(type(x) is not int or x < 1 for x in budget.values()):
            raise ValueError("positive integer resource ceilings required")
        if budget["operations"] > 1000 or budget["solver_calls"] > 128 or budget["cpu_seconds"] > 120:
            raise ValueError("resource ceiling exceeds offline mission authority")
        self.budget, self.callback = budget, callback
        self.operations = self.calls = 0
        self.start = time.process_time_ns()
        self.costs: list[dict[str, Any]] = []

    def remaining(self) -> float:
        remaining = int(self.budget["cpu_seconds"]) - (time.process_time_ns() - self.start) / 1e9
        if remaining <= 0:
            raise BudgetExceeded("CPU ceiling reached")
        return max(0.001, remaining)

    def solver(self) -> None:
        if self.calls >= self.budget["solver_calls"]:
            raise BudgetExceeded("solver-call ceiling reached")
        self.remaining()
        self.calls += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "costs": self.costs,
            "operations": self.operations,
            "solver_calls": self.calls,
            "elapsed_cpu_ns": time.process_time_ns() - self.start,
        }

    def stage(self, name: str, fn: Callable[[], Any]) -> Any:
        if self.operations >= self.budget["operations"]:
            raise BudgetExceeded("operation ceiling reached")
        self.remaining()
        self.operations += 1
        started = time.process_time_ns()
        try:
            return fn()
        finally:
            elapsed = time.process_time_ns() - started
            quantity = str(Fraction(elapsed, 10**9))
            self.costs.append(
                {
                    "id": f"event-{self.operations:04d}",
                    "stage": name,
                    "quantity": quantity,
                    "rate": CPU_RATE,
                    "amount": str(Fraction(quantity) * Fraction(CPU_RATE)),
                    "basis": "measured-cpu",
                }
            )
            if self.callback:
                self.callback(self.snapshot())


def _validate_request(request: dict[str, Any]) -> None:
    bounded(request)
    exact_keys(
        request, {"schema", "id", "target", "capabilities", "budget", "seed"}, {"captures", "mapping", "memory_mode"}
    )
    if request["schema"] != SCHEMA:
        raise ValueError("unsupported discovery request")
    identifier(request["id"])
    transfer._no_labels(request)
    exact_keys(request["capabilities"], {"A", "S", "C"})
    if any(type(x) is not bool for x in request["capabilities"].values()):
        raise ValueError("literal capability booleans required")
    if type(request["seed"]) is not int or not 0 <= request["seed"] < 2**32:
        raise ValueError("bounded strategy seed required")
    if request.get("memory_mode", "structured") not in {"structured", "retrieval"}:
        raise ValueError("unsupported retrieval mode")
    Meter(request["budget"])


def _transfer(request: dict[str, Any]) -> dict[str, Any]:
    captures = request.get("captures", [])
    if not 1 <= len(captures) <= 4:
        raise ValueError("A requires completed source experiences")
    matches = []
    signature = transfer.structural_signature(adaptations.adapter_spec(request["target"]["adapter_id"]))
    for capture in captures:
        transfer.inspect_capture(capture)
        if capture["principle"]["signature"] == signature and capture["developmental_only"] is False:
            matches.append(capture)
    if len(matches) != 1:
        raise ValueError("exactly one qualified structural principle required")
    capture = matches[0]
    transfer.validate_mapping(capture["principle"], request["target"], request.get("mapping", {}))
    return cast(
        dict[str, Any],
        adaptations.construct(
            request["target"]["adapter_id"],
            principle=capture["principle"],
            target=request["target"],
            mapping=request["mapping"],
        ),
    )


def _choose(memory: dict[str, Any], key: str, mode: str) -> tuple[dict[str, Any] | None, list[str]]:
    if mode == "structured":
        assets = [x for x in memory["assets"] if x["structure"] == key]
        return (copy.deepcopy(assets[-1]["program"]), [assets[-1]["id"]]) if assets else (None, [])
    # Ordinary retrieval receives exactly the same records and may discover the same reusable strategy.
    history = [x for x in memory["history"] if x["structure"] == key]
    return (copy.deepcopy(history[-1]["program"]), [history[-1]["id"]]) if history else (None, [])


def _critique(
    target: dict[str, Any], artifact: dict[str, Any], model: dict[str, Any], meter: Meter, seed: int
) -> list[Any]:
    observations = []
    # A concrete altered certificate is a falsifiable criticism; its rejection is independently checked.
    bad = copy.deepcopy(artifact)
    if bad["status"] == "FEASIBLE":
        bad["vehicles"][0]["arrival_kwh"][0] = "-1"
    else:
        bad["witness"]["rows"] = []
    verdict = meter.stage("critic-independent-mutation-check", lambda: eadarp_check.check(target, bad, {}))
    observations.append(
        {"kind": "certificate-corruption", "artifact": bad, "independently_rejected": verdict.get("accepted") is False}
    )
    rng = random.Random(seed)
    # Search moderate operator perturbations, then retain only independently
    # certified evidence of a boundary. No found failure is a permitted outcome.
    for index, parameter in enumerate(rng.sample(["travel_multiplier", "consumption_multiplier", "window_scale"], 2)):
        adverse = copy.deepcopy(target)
        adverse["id"] = target["id"] + f"/critic-{index}"
        factor = (
            Fraction(rng.randrange(110, 181), 100)
            if parameter != "window_scale"
            else Fraction(rng.randrange(45, 91), 100)
        )
        from decimal import Decimal

        old = Decimal(adverse["updates"][parameter])
        adverse["updates"][parameter] = str(old * Decimal(factor.numerator) / Decimal(factor.denominator))
        adverse_model = meter.stage("critic-constraint-construction", lambda: eadarp.compile_model(adverse))
        counterexample = meter.stage(
            "critic-search", lambda: programs.solve_program(adverse, adverse_model, DEFAULT_PROGRAM, meter)
        )
        checked = meter.stage(
            "critic-independent-counterexample-check", lambda: eadarp_check.check(adverse, counterexample, {})
        )
        observations.append(
            {
                "kind": "operator-perturbation-boundary-search",
                "parameter": parameter,
                "factor": str(factor),
                "target": adverse,
                "artifact": counterexample,
                "acceptance": checked,
                "certified_boundary_found": checked.get("accepted") is True
                and artifact["status"] == "FEASIBLE"
                and counterexample["status"] == "INFEASIBLE",
                "limit": "conservation alone does not establish temporal or energy feasibility",
            }
        )
    return observations


def execute(
    request: dict[str, Any],
    memory: dict[str, Any] | None = None,
    *,
    _checkpoint: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one bounded task without mutating memory or weakening final acceptance."""
    _validate_request(request)
    request = copy.deepcopy(request)
    memory = copy.deepcopy(memory if memory is not None else empty_memory())
    meter = Meter(request["budget"], _checkpoint)
    meter.stage("validate-retained-memory", lambda: validate_memory(memory))
    target, caps = request["target"], request["capabilities"]
    # Strict independent parser refuses unsupported physical or resource assumptions before search.
    meter.stage("independent-input-contract", lambda: eadarp_check._read(target))
    key = meter.stage("structural-index", lambda: structure_key(target))
    used: list[str] = []
    if caps["A"]:
        constructed = meter.stage("extract-retrieve-map-construct", lambda: _transfer(request))
        model = constructed["model"]
        used += [x["principle"]["id"] for x in request["captures"]]
    else:
        model = meter.stage("direct-model-construction", lambda: eadarp.compile_model(target))
    remembered, ids = meter.stage(
        "current-history-retrieval", lambda: _choose(memory, key, request.get("memory_mode", "structured"))
    )
    used += ids
    proposed = [remembered or copy.deepcopy(DEFAULT_PROGRAM)]
    if caps["S"] and remembered is None:
        proposed = meter.stage("invent-strategy-programs", lambda: programs.invent(request["seed"]))
    candidates = []
    for program in proposed:
        started = meter.calls
        try:
            artifact = meter.stage("execute-candidate", lambda: programs.solve_program(target, model, program, meter))
            verdict = meter.stage("candidate-independent-check", lambda: eadarp_check.check(target, artifact, {}))
            candidates.append(
                {"program": program, "artifact": artifact, "acceptance": verdict, "solver_calls": meter.calls - started}
            )
        except BudgetExceeded:
            raise
        except (ValueError, ArithmeticError) as exc:
            candidates.append(
                {"program": program, "failure": type(exc).__name__, "solver_calls": meter.calls - started}
            )
    good = [x for x in candidates if x.get("acceptance", {}).get("accepted") is True]
    if not good:
        raise ValueError("no independently accepted candidate; retain failed attempt")
    # Minimize accepted solver work, then objective; timings never tune a later held panel.
    selected = min(good, key=lambda x: (x["solver_calls"], Fraction(x["artifact"]["objective"]), digest(x["program"])))
    artifact = selected["artifact"]
    critiques = _critique(target, artifact, model, meter, request["seed"]) if caps["C"] else []
    acceptance = meter.stage("final-independent-acceptance", lambda: eadarp_check.check(target, artifact, {}))
    if acceptance.get("accepted") is not True:
        raise ValueError("final acceptance refused")
    meter.remaining()
    costs = copy.deepcopy(meter.costs)
    body = {
        "schema": "agialpha/discovery-result/v1",
        "id": request["id"],
        "method": "bounded-compositional-discovery",
        "request": request,
        "request_hash": digest(request),
        "source_hashes": source_hashes(),
        "artifact": artifact,
        "acceptance": acceptance,
        "accepted": True,
        "program": selected["program"],
        "structure": key,
        "candidates": candidates,
        "critiques": critiques,
        "costs": costs,
        "budget_cap": request["budget"],
        "resources": {"operations": meter.operations, "solver_calls": meter.calls},
        "memory_before_hash": memory["memory_hash"],
        "memory_used": used,
        "funding": {"earned": False, "source": "seed-funded-research"},
        "scope": "known-public-fixed-route-linear-model; no new-domain or operational qualification",
    }
    elapsed = Fraction(time.process_time_ns() - meter.start, 10**9)
    prior_cpu = sum((Fraction(x["quantity"]) for x in costs), Fraction(0))
    overhead = elapsed - prior_cpu
    costs.append(
        {
            "id": "closing-envelope",
            "stage": "execution-overhead",
            "quantity": str(overhead),
            "rate": CPU_RATE,
            "amount": str(overhead * Fraction(CPU_RATE)),
            "basis": "measured-cpu",
        }
    )
    body["resources"]["operations"] += 1
    body["resources"]["cpu_seconds"] = str(elapsed)
    body["cost_total"] = str(sum((Fraction(x["amount"]) for x in costs), Fraction(0)))
    if body["resources"]["operations"] > request["budget"]["operations"] or elapsed > request["budget"]["cpu_seconds"]:
        raise BudgetExceeded("closing envelope exceeds resource cap")
    return _sealed(body, "result_hash")


def _verify_critique_records(
    target: dict[str, Any], artifact: dict[str, Any], critiques: list[Any], seed: int | None = None
) -> None:
    """Reconstruct falsification inputs and independently replay every claimed finding."""
    from decimal import Decimal

    if not isinstance(critiques, list) or len(critiques) != 3:
        raise ValueError("three declared independently checked criticism records required")
    mutation = critiques[0]
    exact_keys(mutation, {"kind", "artifact", "independently_rejected"})
    bad = copy.deepcopy(artifact)
    if bad["status"] == "FEASIBLE":
        bad["vehicles"][0]["arrival_kwh"][0] = "-1"
    else:
        bad["witness"]["rows"] = []
    if (
        mutation["kind"] != "certificate-corruption"
        or mutation["artifact"] != bad
        or mutation["independently_rejected"] is not True
        or eadarp_check.check(target, bad, {}).get("accepted") is not False
    ):
        raise ValueError("unsupported certificate-corruption criticism")
    rng = random.Random(seed) if seed is not None else None
    expected_parameters = (
        rng.sample(["travel_multiplier", "consumption_multiplier", "window_scale"], 2)
        if rng is not None
        else [item.get("parameter") for item in critiques[1:]]
    )
    if len(set(expected_parameters)) != 2:
        raise ValueError("criticism search must use distinct declared parameters")
    for index, (record, parameter) in enumerate(zip(critiques[1:], expected_parameters)):
        exact_keys(
            record,
            {"kind", "parameter", "factor", "target", "artifact", "acceptance", "certified_boundary_found", "limit"},
        )
        if parameter not in {"travel_multiplier", "consumption_multiplier", "window_scale"}:
            raise ValueError("unknown criticism parameter")
        factor = Fraction(record["factor"])
        if rng is not None:
            expected_factor = (
                Fraction(rng.randrange(110, 181), 100)
                if parameter != "window_scale"
                else Fraction(rng.randrange(45, 91), 100)
            )
            if factor != expected_factor:
                raise ValueError("criticism factor differs from frozen seeded search")
        elif not (
            (Fraction(45, 100) <= factor <= Fraction(90, 100))
            if parameter == "window_scale"
            else (Fraction(110, 100) <= factor <= Fraction(180, 100))
        ):
            raise ValueError("criticism factor outside declared search")
        adverse = copy.deepcopy(target)
        adverse["id"] = target["id"] + f"/critic-{index}"
        old = Decimal(adverse["updates"][parameter])
        adverse["updates"][parameter] = str(old * Decimal(factor.numerator) / Decimal(factor.denominator))
        checked = eadarp_check.check(adverse, record["artifact"], {})
        boundary = (
            checked.get("accepted") is True
            and artifact["status"] == "FEASIBLE"
            and record["artifact"]["status"] == "INFEASIBLE"
        )
        if (
            record["kind"] != "operator-perturbation-boundary-search"
            or record["parameter"] != parameter
            or record["target"] != adverse
            or record["acceptance"] != checked
            or type(record["certified_boundary_found"]) is not bool
            or record["certified_boundary_found"] is not boundary
            or record["limit"] != "conservation alone does not establish temporal or energy feasibility"
        ):
            raise ValueError("unsupported independently checked boundary criticism")


def verify_result(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Check immutable result identities, costs and final certificate without rerunning paid work."""
    if (
        result.get("result_hash") != digest({k: v for k, v in result.items() if k != "result_hash"})
        or result.get("request_hash") != digest(request)
        or result.get("source_hashes") != source_hashes()
        or result.get("request") != request
    ):
        raise ValueError("result or trusted installed source mismatch")
    _validate_request(request)
    programs.validate_program(result["program"])
    if request["capabilities"]["A"]:
        _transfer(request)
    if not isinstance(result.get("candidates"), list) or not result["candidates"]:
        raise ValueError("recorded executable candidate evidence required")
    selected_found = False
    for candidate in result["candidates"]:
        programs.validate_program(candidate["program"])
        if type(candidate.get("solver_calls")) is not int or candidate["solver_calls"] < 0:
            raise ValueError("candidate solver resource count")
        if "artifact" in candidate:
            checked = eadarp_check.check(request["target"], candidate["artifact"], {})
            if candidate.get("acceptance") != checked:
                raise ValueError("candidate independent acceptance differs")
            if (
                candidate["program"] == result["program"]
                and candidate["artifact"] == result["artifact"]
                and checked.get("accepted") is True
            ):
                selected_found = True
        elif not isinstance(candidate.get("failure"), str):
            raise ValueError("candidate result or explicit failure required")
    if not selected_found:
        raise ValueError("chosen programme/artifact lacks corresponding accepted execution candidate")
    if request["capabilities"]["C"]:
        _verify_critique_records(request["target"], result["artifact"], result["critiques"], request["seed"])
    elif result.get("critiques") != []:
        raise ValueError("disabled criticism cannot claim adversarial search")
    accepted = eadarp_check.check(request["target"], result["artifact"], {})
    if accepted.get("accepted") is not True or accepted != result["acceptance"]:
        raise ValueError("independent acceptance mismatch")
    seen, total = set(), Fraction(0)
    for cost in result["costs"]:
        if cost["id"] in seen or Fraction(cost["quantity"]) < 0 or Fraction(cost["rate"]) != Fraction(CPU_RATE):
            raise ValueError("duplicate or unqualified resource cost")
        seen.add(cost["id"])
        amount = Fraction(cost["quantity"]) * Fraction(cost["rate"])
        if amount != Fraction(cost["amount"]):
            raise ValueError("resource cost arithmetic")
        total += amount
    resources = result["resources"]
    if (
        str(total) != result["cost_total"]
        or resources["operations"] != len(result["costs"])
        or type(resources["operations"]) is not int
        or resources["operations"] < 1
        or type(resources["solver_calls"]) is not int
        or resources["solver_calls"] < 1
        or resources["solver_calls"] < sum(x["solver_calls"] for x in result["candidates"])
        or Fraction(resources["cpu_seconds"]) != sum((Fraction(x["quantity"]) for x in result["costs"]), Fraction(0))
        or resources["operations"] > request["budget"]["operations"]
        or resources["solver_calls"] > request["budget"]["solver_calls"]
        or Fraction(resources["cpu_seconds"]) > request["budget"]["cpu_seconds"]
        or result["funding"] != {"earned": False, "source": "seed-funded-research"}
    ):
        raise ValueError("resource, funding or budget mismatch")
    return {
        "passed": True,
        "accepted": True,
        "artifact_hash": digest(result["artifact"]),
        "task_id": request["target"]["id"],
        "result_hash": result["result_hash"],
    }


def learn(memory: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Promote checked chronological experience; evaluation panels never call this function."""
    validate_memory(memory)
    verify_result(result["request"], result)
    if result["memory_before_hash"] != memory["memory_hash"] or memory["version"] >= 16:
        raise ValueError("out-of-order or exhausted learning history")
    task_id = digest(result["request"]["target"])
    if any(x["id"] == task_id for x in memory["history"]):
        raise ValueError("duplicate chronological experience")
    record = {
        "id": task_id,
        "task": result["request"]["target"],
        "artifact": result["artifact"],
        "program": result["program"],
        "structure": result["structure"],
        "source_hashes": result["source_hashes"],
        "result_hash": result["result_hash"],
        "cost_total": result["cost_total"],
        "counterexamples": copy.deepcopy(result["critiques"]),
        "principle_ids": result["memory_used"],
        "captures": result["request"].get("captures", []),
    }
    asset = _asset(record, memory["version"] + 1)
    principles = copy.deepcopy(memory["principles"])
    for capture in record["captures"]:
        if capture not in principles:
            principles.append(capture)
    body = {
        "schema": memory["schema"],
        "version": memory["version"] + 1,
        "parent_hash": memory["memory_hash"],
        "history": [*memory["history"], record],
        "assets": [*memory["assets"], asset],
        "principles": principles,
    }
    return validate_memory(_sealed(body, "memory_hash"))


def resume(request: dict[str, Any], directory: Path, memory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Use the durable offline operator path without changing mission authority."""
    from .operator import resume as durable_resume

    return durable_resume(request, directory, memory)
