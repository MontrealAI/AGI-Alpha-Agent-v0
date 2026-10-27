# SPDX-License-Identifier: Apache-2.0
"""Bounded, source-bound scientific model-reuse qualification.

This is a research instrument, not a biological validator or a general SBML solver.
Its executable dynamics scope is a closed, unit-volume, first-order conversion
network with constant parameters and one initial condition. Inventory works more
broadly. Every qualification is recomputed from the current source and request.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, TypeAlias
import xml.etree.ElementTree as ET

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import expm

VERSION = "1.0.0"
SCHEMA = "scientific-model-reuse/1"
SOURCE_FILES = ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")
ARRAY: TypeAlias = NDArray[np.float64]


class ScopeError(ValueError):
    """The request or scientific representation exceeds the checked scope."""


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _tag(child) == name]


def _child(element: ET.Element, name: str) -> ET.Element:
    found = _children(element, name)
    if len(found) != 1:
        raise ScopeError(f"Expected exactly one {name} element")
    return found[0]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ScopeError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise ScopeError(f"{name} must be a finite number") from error
    if not math.isfinite(result) or (positive and result <= 0):
        raise ScopeError(f"{name} must be finite" + (" and positive" if positive else ""))
    return result


def _rows(data: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t")
    if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ScopeError("Missing or duplicate TSV headings")
    result: list[dict[str, str]] = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ScopeError("Malformed TSV row")
        result.append({key: value for key, value in row.items()})
    return result


@dataclass
class _Source:
    model: ET.Element
    raw: dict[str, bytes]
    hashes: dict[str, str]
    fingerprint: str
    parameters: list[dict[str, str]]
    measurements: list[dict[str, str]]
    observables: list[dict[str, str]]
    conditions: list[dict[str, str]]


def _load(path: str | Path) -> _Source:
    supplied = Path(path)
    if supplied.is_file():
        supplied = supplied.parent
    possible = [supplied, supplied / "petab"]
    directories = [item for item in possible if (item / "model.xml").is_file()]
    if len(directories) != 1:
        raise ScopeError("Specify one PEtab directory or its immediate parent")
    directory = directories[0]
    raw: dict[str, bytes] = {}
    for name in SOURCE_FILES:
        file = directory / name
        if not file.is_file():
            raise ScopeError(f"Missing source file: {name}")
        data = file.read_bytes()
        if len(data) > 5_000_000:
            raise ScopeError(f"Source file exceeds five-megabyte scoped limit: {name}")
        raw[name] = data
    model_spaces = [
        ("model_space.tsv", directory / "model_space.tsv"),
        ("../model_space.tsv", directory.parent / "model_space.tsv"),
    ]
    present_spaces = [(name, file) for name, file in model_spaces if file.is_file()]
    if len(present_spaces) > 1:
        raise ScopeError("Ambiguous model-space evidence: supply one table next to or above the PEtab files")
    if present_spaces:
        name, file = present_spaces[0]
        data = file.read_bytes()
        if len(data) > 5_000_000:
            raise ScopeError("Model-space source exceeds five-megabyte scoped limit")
        raw[name] = data
    if b"<!DOCTYPE" in raw["model.xml"].upper() or b"<!ENTITY" in raw["model.xml"].upper():
        raise ScopeError("DTD and entity declarations are outside the parser scope")
    root = ET.fromstring(raw["model.xml"])
    if _tag(root) != "sbml":
        raise ScopeError("Expected an SBML document")
    model = _child(root, "model")
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(raw.items())}
    fingerprint = hashlib.sha256(_canonical(hashes)).hexdigest()
    return _Source(
        model,
        raw,
        hashes,
        fingerprint,
        _rows(raw["parameters.tsv"]),
        _rows(raw["measurements.tsv"]),
        _rows(raw["observables.tsv"]),
        _rows(raw["conditions.tsv"]),
    )


def _inventory(source: _Source) -> dict[str, Any]:
    species = _children(_child(source.model, "listOfSpecies"), "species")
    reactions = _children(_child(source.model, "listOfReactions"), "reaction")
    times: list[float] = []
    condition_ids: set[str] = set()
    observed: set[str] = set()
    for row in source.measurements:
        try:
            time = float(row["time"])
        except (KeyError, ValueError) as error:
            raise ScopeError("Every measurement needs a numeric or positive-infinite time") from error
        if math.isnan(time) or time < 0:
            raise ScopeError("Negative or NaN measurement times exceed this scope")
        times.append(time)
        condition_ids.add(row.get("simulationConditionId", ""))
        observed.add(row.get("observableId", ""))
    declared_observables = {row["observableId"] for row in source.observables}
    if len(declared_observables) != len(source.observables) or not observed.issubset(declared_observables):
        raise ScopeError("Unknown or duplicate observable identifiers")
    parameter_ids = [row["parameterId"] for row in source.parameters]
    if len(set(parameter_ids)) != len(parameter_ids):
        raise ScopeError("Duplicate parameter identifiers")
    fixed = {row["parameterId"]: row["nominalValue"] for row in source.parameters if row.get("estimate") == "0"}
    estimated = [row["parameterId"] for row in source.parameters if row.get("estimate") == "1"]
    return {
        "schema": SCHEMA,
        "instrument_version": VERSION,
        "source_fingerprint": source.fingerprint,
        "source_hashes": source.hashes,
        "model_id": source.model.get("id"),
        "species_count": len(species),
        "reaction_count": len(reactions),
        "species": [item.attrib["id"] for item in species],
        "measurement_rows": len(times),
        "observed_ids": sorted(observed),
        "observed_count": len(observed),
        "simulation_condition_ids": sorted(condition_ids),
        "all_measurements_at_equilibrium": bool(times) and all(math.isinf(time) for time in times),
        "finite_measurement_rows": sum(math.isfinite(time) for time in times),
        "finite_positive_measurement_rows": sum(math.isfinite(time) and time > 0 for time in times),
        "declared_model_time_unit": source.model.get("timeUnits"),
        "fixed_parameters": fixed,
        "estimated_parameters": estimated,
        "physical_calibration_present_in_this_schema": False,
        "scope": "Observed source properties; fixed parameters remain legitimate model assumptions.",
    }


def inventory(path: str | Path) -> dict[str, Any]:
    """Read and hash source evidence without asserting model validity."""
    return _inventory(_load(path))


def _product(element: ET.Element) -> tuple[Fraction, list[str]]:
    """Parse an explicitly bounded MathML monomial without eval or code execution."""
    name = _tag(element)
    if name == "math":
        if len(element) != 1:
            raise ScopeError("Expected one MathML expression")
        return _product(element[0])
    if name == "ci":
        symbol = (element.text or "").strip()
        if not symbol:
            raise ScopeError("Empty MathML symbol")
        return Fraction(1), [symbol]
    if name == "cn":
        if element.get("type", "real") not in ("real", "integer") or len(element):
            raise ScopeError("Unsupported MathML numeric representation")
        return Fraction((element.text or "").strip()), []
    if name == "apply" and len(element) > 1 and _tag(element[0]) == "times":
        coefficient = Fraction(1)
        symbols: list[str] = []
        for item in element[1:]:
            factor, names = _product(item)
            coefficient *= factor
            symbols.extend(names)
        return coefficient, symbols
    raise ScopeError(f"Unsupported kinetic-law MathML node: {name}")


def _network(source: _Source, overrides: dict[str, Any] | None = None) -> tuple[list[str], ARRAY, ARRAY, set[str]]:
    forbidden = {"listOfRules", "listOfEvents", "listOfInitialAssignments", "listOfFunctionDefinitions"}
    if any(_tag(item) in forbidden for item in source.model):
        raise ScopeError("Rules, events, initial assignments and custom functions require a different solver")
    compartments = _children(_child(source.model, "listOfCompartments"), "compartment")
    if len(compartments) != 1 or compartments[0].get("constant", "true") != "true":
        raise ScopeError("Only one constant compartment is supported")
    if Fraction(compartments[0].get("size", "1")) != 1:
        raise ScopeError("Only a unit-volume compartment is supported")
    compartment_id = compartments[0].attrib["id"]
    species_nodes = _children(_child(source.model, "listOfSpecies"), "species")
    names = [item.attrib["id"] for item in species_nodes]
    if len(names) < 2 or len(names) != len(set(names)):
        raise ScopeError("Expected at least two uniquely named species")
    indices = {name: index for index, name in enumerate(names)}
    initial: list[float] = []
    for item in species_nodes:
        if item.get("boundaryCondition", "false") != "false" or item.get("constant", "false") != "false":
            raise ScopeError("Boundary or constant species are outside the closed-network scope")
        if item.get("compartment") != compartment_id:
            raise ScopeError("Species compartment mismatch")
        initial.append(_number(item.get("initialConcentration", item.get("initialAmount", "0")), "initial state"))
    if any(value < 0 for value in initial) or not math.isclose(sum(initial), 1.0, abs_tol=1e-12):
        raise ScopeError("The supported initial state is a nonnegative, normalized abundance vector")
    if len(source.conditions) != 1 or any(
        key != "conditionId" and value for key, value in source.conditions[0].items()
    ):
        raise ScopeError("Condition-specific overrides require a different solver")
    parameter_nodes = _children(_child(source.model, "listOfParameters"), "parameter")
    if any(item.get("constant", "true") != "true" for item in parameter_nodes):
        raise ScopeError("Nonconstant global parameters are unsupported")
    parameters = {item.attrib["id"]: Fraction(item.get("value", "0")) for item in parameter_nodes}
    if len(parameters) != len(parameter_nodes):
        raise ScopeError("Duplicate SBML parameter identifiers")
    table = {row["parameterId"]: row for row in source.parameters}
    for name, row in table.items():
        _number(row["nominalValue"], f"nominal parameter {name}")
        parameters[name] = Fraction(row["nominalValue"])
    for name, value in (overrides or {}).items():
        if name not in parameters:
            raise ScopeError(f"Unknown parameter override: {name}")
        _number(value, f"parameter {name}")
        rational = Fraction(str(value))
        row = table.get(name, {})
        if row.get("lowerBound") and rational < Fraction(row["lowerBound"]):
            raise ScopeError(f"Parameter below declared bound: {name}")
        if row.get("upperBound") and rational > Fraction(row["upperBound"]):
            raise ScopeError(f"Parameter above declared bound: {name}")
        parameters[name] = rational
    exact = [[Fraction(0) for _ in names] for _ in names]
    kinetic_parameters: set[str] = set()
    for reaction in _children(_child(source.model, "listOfReactions"), "reaction"):
        if reaction.get("reversible", "false") != "false":
            raise ScopeError("Reversible reaction shorthand is unsupported")
        reactants = _children(_child(reaction, "listOfReactants"), "speciesReference")
        products = _children(_child(reaction, "listOfProducts"), "speciesReference")
        if len(reactants) != 1 or len(products) != 1:
            raise ScopeError("Only single-species conversions are supported")
        if any(Fraction(item.get("stoichiometry", "1")) != 1 for item in reactants + products):
            raise ScopeError("Only unit stoichiometry is supported")
        start, end = reactants[0].attrib["species"], products[0].attrib["species"]
        if start not in indices or end not in indices:
            raise ScopeError("Reaction references unknown species")
        law = _child(reaction, "kineticLaw")
        if any(_tag(item) != "math" for item in law):
            raise ScopeError("Local kinetic parameters are unsupported")
        coefficient, factors = _product(_child(law, "math"))
        species_factors = [factor for factor in factors if factor in indices]
        if species_factors != [start]:
            raise ScopeError("Kinetic law must be first-order in its sole reactant")
        for factor in factors:
            if factor == start:
                continue
            if factor not in parameters:
                raise ScopeError(f"Unknown kinetic-law factor: {factor}")
            coefficient *= parameters[factor]
            kinetic_parameters.add(factor)
        if coefficient < 0:
            raise ScopeError("Negative transition rate")
        i, j = indices[start], indices[end]
        exact[i][i] -= coefficient
        exact[j][i] += coefficient
    if any(sum(exact[row][column] for row in range(len(names))) != 0 for column in range(len(names))):
        raise ScopeError("Exact column conservation check failed")
    matrix = np.asarray([[float(value) for value in row] for row in exact], dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ScopeError("Nonfinite generator")
    adjacency = matrix > 0
    for graph in (adjacency, adjacency.T):
        reached, frontier = {0}, [0]
        while frontier:
            node = frontier.pop()
            for neighbor in np.flatnonzero(graph[:, node]):
                index = int(neighbor)
                if index not in reached:
                    reached.add(index)
                    frontier.append(index)
        if len(reached) != len(names):
            raise ScopeError("Unique stationary calculation requires a strongly connected positive-rate graph")
    return names, matrix, np.asarray(initial, dtype=np.float64), kinetic_parameters


def _stationary(matrix: ARRAY) -> ARRAY:
    augmented = matrix.copy()
    augmented[-1, :] = 1
    target = np.zeros(matrix.shape[0], dtype=np.float64)
    target[-1] = 1
    try:
        result = np.asarray(np.linalg.solve(augmented, target), dtype=np.float64)
    except np.linalg.LinAlgError as error:
        raise ScopeError("No unique stable stationary solution") from error
    if not np.isfinite(result).all() or np.min(result) < -1e-10:
        raise ScopeError("Stationary probability validation failed")
    if np.linalg.norm(matrix @ result, ord=np.inf) > 1e-9 * max(1.0, float(np.linalg.norm(matrix, ord=np.inf))):
        raise ScopeError("Stationary residual validation failed")
    return result


def _trajectory(matrix: ARRAY, initial: ARRAY, time: float, scale: float = 1.0) -> ARRAY:
    result = np.asarray(expm(matrix * (scale * time)) @ initial, dtype=np.float64)
    if (
        not np.isfinite(result).all()
        or np.min(result) < -1e-9
        or not math.isclose(float(result.sum()), 1.0, abs_tol=1e-8)
    ):
        raise ScopeError("Numerical trajectory failed probability checks")
    return result


def _relaxation(matrix: ARRAY) -> float:
    values = np.linalg.eigvals(matrix)
    nonzero = [float(value.real) for value in values if abs(value) > 1e-9]
    if not nonzero or max(nonzero) >= 0:
        raise ScopeError("No numerically separated decaying spectral mode")
    return -1.0 / max(nonzero)


def build_generator(path: str | Path, param_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a checked numeric generator for the declared first-order scope."""
    source = _load(path)
    names, matrix, initial, parameters = _network(source, param_overrides)
    return {
        "source_fingerprint": source.fingerprint,
        "species": names,
        "matrix": matrix.tolist(),
        "initial": initial.tolist(),
        "kinetic_parameters": sorted(parameters),
        "exact_column_conservation": True,
        "time_unit": "declared model unit; physical mapping not inferred",
    }


def stationary(path: str | Path, param_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute a conditional stationary point; this is not a data-identifiability proof."""
    source = _load(path)
    names, matrix, _, _ = _network(source, param_overrides)
    result = _stationary(matrix)
    return {
        "source_fingerprint": source.fingerprint,
        "species": names,
        "probabilities": result.tolist(),
        "residual_max": float(np.max(np.abs(matrix @ result))),
        "conditional_on": "Supplied nominal parameters and supported model; no parameter uncertainty interval.",
    }


def _clock(
    source: _Source, scales: tuple[float, float], time: float, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    info = _inventory(source)
    if not info["all_measurements_at_equilibrium"]:
        raise ScopeError("Equilibrium-preserving scaling alone is not a witness for finite-time observations")
    one, two = (_number(value, "clock scale", positive=True) for value in scales)
    if one == two:
        raise ScopeError("A separating witness needs distinct clock scales")
    time = _number(time, "time", positive=True)
    names, matrix, initial, _ = _network(source, overrides)
    if any(row.get("observableFormula", "").strip() not in names for row in source.observables):
        raise ScopeError("The clock witness covers direct species-abundance observations only")
    equilibrium_one = _stationary(one * matrix)
    equilibrium_two = _stationary(two * matrix)
    first, second = _trajectory(matrix, initial, time, one), _trajectory(matrix, initial, time, two)
    difference = float(np.max(np.abs(first - second)))
    return {
        "species": names,
        "scales": [one, two],
        "time": time,
        "stationary_world_1": equilibrium_one.tolist(),
        "stationary_world_2": equilibrium_two.tolist(),
        "prediction_world_1": first.tolist(),
        "prediction_world_2": second.tolist(),
        "stationary_difference_max": float(np.max(np.abs(equilibrium_one - equilibrium_two))),
        "transient_difference_max": difference,
        "separates_at_requested_time": difference > 1e-10,
        "normalized_relaxation_time": _relaxation(matrix),
        "physical_relaxation_times": [_relaxation(matrix) / one, _relaxation(matrix) / two],
        "proof": "Q pi=0 implies (c Q) pi=0 for every c>0; exp(c Q t)x0=exp(Q (c t))x0.",
        "likelihood_invariance_scope": "Equilibrium mean observations with unchanged noise model.",
        "interpretation": "Two hypothetical physical embeddings of one normalized model; da_b=1 stays fixed in the original fit.",
        "source_fingerprint": source.fingerprint,
    }


def clock_witness(
    path: str | Path,
    scales: tuple[float, float] = (1.0, 2.0),
    time: float = 1.0,
    param_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a conditional unknown-clock counterexample for equilibrium-only data."""
    return _clock(_load(path), scales, time, param_overrides)


def _bound(source: _Source, kinetic_parameters: int | None = None) -> dict[str, Any]:
    info = _inventory(source)
    if not info["all_measurements_at_equilibrium"]:
        raise ScopeError("This equilibrium mean-coordinate dimension bound does not cover finite-time data")
    names, _, _, kinetic_names = _network(source)
    if any(row.get("observableFormula", "").strip() not in names for row in source.observables):
        raise ScopeError("This dimension bound covers direct species-abundance means only")
    if len(info["simulation_condition_ids"]) != 1:
        raise ScopeError("Only the single-equilibrium dimension bound is implemented")
    selected = sum(row.get("estimate") == "1" and row["parameterId"] in kinetic_names for row in source.parameters)
    candidates: set[str] = {
        row["parameterId"]
        for row in source.parameters
        if row.get("estimate") == "1" and row["parameterId"] in kinetic_names
    }
    model_space_key = next((key for key in ("model_space.tsv", "../model_space.tsv") if key in source.raw), None)
    if model_space_key is not None:
        for row in _rows(source.raw[model_space_key]):
            for name, value in row.items():
                if name in kinetic_names and "estimate" in value.split(";"):
                    candidates.add(name)
    if kinetic_parameters is None:
        count = selected
    elif isinstance(kinetic_parameters, bool) or not isinstance(kinetic_parameters, int) or kinetic_parameters < 0:
        raise ScopeError("kinetic_parameters must be a nonnegative integer")
    else:
        count = kinetic_parameters
    maximum = min(len(names) - 1, int(info["observed_count"]))
    return {
        "source_fingerprint": source.fingerprint,
        "kinetic_parameter_count": count,
        "selected_estimated_kinetic_parameters": selected,
        "candidate_estimated_kinetic_parameters": len(candidates) if model_space_key is not None else None,
        "candidate_space_evidence": "supplied_model_space" if model_space_key is not None else "not_supplied",
        "maximum_independent_mean_coordinates": maximum,
        "minimum_rank_deficiency": max(0, count - maximum),
        "dimension_obstruction": count > maximum,
        "status": "dimension_obstruction" if count > maximum else "not_disqualified_by_dimension_bound",
        "proof": "One normalized equilibrium over n states has at most n-1 mean coordinates; replicates improve precision, not this dimension.",
        "limitations": "Necessary dimension bound only. No sufficiency, individual-parameter identifiability, uncertainty or model-selection criterion validity is certified.",
    }


def dimension_bound(path: str | Path, kinetic_parameters: int | None = None) -> dict[str, Any]:
    """Apply the bounded mean-coordinate check without overstating its implication."""
    return _bound(_load(path), kinetic_parameters)


def _calibration(request: dict[str, Any], source: _Source) -> tuple[float, float, dict[str, Any]]:
    calibration = request.get("calibration")
    if not isinstance(calibration, dict):
        raise ScopeError("An explicit physical-clock calibration is required")
    if calibration.get("model_fingerprint") != source.fingerprint:
        raise ScopeError("Calibration source identity does not match the current model/data")
    if request.get("parameter_overrides"):
        expected = hashlib.sha256(_canonical(request["parameter_overrides"])).hexdigest()
        if calibration.get("parameter_overrides_sha256") != expected:
            raise ScopeError("Calibration does not bind the changed parameter point")
    scope = request.get("scope_id")
    if not isinstance(scope, str) or not scope or calibration.get("scope_id") != scope:
        raise ScopeError("Calibration must match the explicit current mission scope")
    evidence_id = calibration.get("evidence_id")
    unit = calibration.get("physical_unit")
    kind = calibration.get("evidence_kind")
    if not isinstance(evidence_id, str) or not evidence_id or not isinstance(unit, str) or not unit:
        raise ScopeError("Calibration needs an evidence identifier and physical unit")
    if kind not in ("assumed", "observed"):
        raise ScopeError("Calibration must label its evidence kind as assumed or observed")
    values = calibration.get("scale_per_physical_unit")
    if not isinstance(values, list) or len(values) != 2:
        raise ScopeError("Calibration needs [lower,upper] model-time units per physical unit")
    lower, upper = (_number(value, "calibration scale", positive=True) for value in values)
    if lower > upper:
        raise ScopeError("Calibration interval is reversed")
    return (
        lower,
        upper,
        {**calibration, "authentication": "Caller-supplied evidence; authenticity and physical truth unverified."},
    )


def qualify(request: dict[str, Any], path: str | Path) -> dict[str, Any]:
    """Requalify the current mission, returning scoped evidence and no authority.

    Supported types: inventory, stationary, clock_witness, dimension_bound,
    response. response quantity is spectral_relaxation_time or state_at_time.
    Physical responses require a source/scope-bound calibration. A model_unit
    response is explicitly conditional numerical replay only.
    """
    request_bytes = _canonical(request)
    if not isinstance(request.get("mission_id"), str) or not request["mission_id"]:
        raise ScopeError("A nonempty mission_id is required")
    source = _load(path)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "instrument_version": VERSION,
        "mission_id": request["mission_id"],
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "source_fingerprint": source.fingerprint,
        "source_hashes": source.hashes,
        "authority": [],
        "status": "unqualified",
        "current_mission_rechecked": True,
        "physical_validation": False,
        "full_identifiability_proved": False,
        "assumptions": ["Published model and parameter point are conditional premises, not newly validated biology."],
    }
    try:
        expected_identity = request.get("expected_source_fingerprint")
        if expected_identity is not None and expected_identity != source.fingerprint:
            raise ScopeError("The requested source identity does not match the current source")
        kind = request.get("type")
        overrides = request.get("parameter_overrides")
        if overrides is not None and not isinstance(overrides, dict):
            raise ScopeError("parameter_overrides must be an object")
        if kind == "inventory":
            receipt.update(status="inventory_only", result=_inventory(source))
        elif kind == "stationary":
            names, matrix, _, _ = _network(source, overrides)
            result = _stationary(matrix)
            receipt.update(
                status="qualified_conditionally",
                result={
                    "species": names,
                    "probabilities": result.tolist(),
                    "residual_max": float(np.max(np.abs(matrix @ result))),
                    "clock_invariant": True,
                    "meaning": "A stationary point for supplied parameters; no uncertainty or uniqueness across fitted parameter alternatives is claimed.",
                },
            )
        elif kind == "clock_witness":
            scales = request.get("scales", [1.0, 2.0])
            if not isinstance(scales, list) or len(scales) != 2:
                raise ScopeError("scales must contain two positive clock conversions")
            if request.get("calibration") is not None:
                lower, upper, calibration = _calibration(request, source)
                if not all(lower <= _number(value, "clock scale", positive=True) <= upper for value in scales):
                    raise ScopeError("Proposed clock alternatives are excluded by the supplied calibration")
            result = _clock(source, (scales[0], scales[1]), request.get("time", 1.0), overrides)
            if request.get("calibration") is not None:
                result["calibration"] = calibration
                receipt.update(status="clock_uncertainty_within_calibration", result=result)
            else:
                receipt.update(
                    status="unsupported_physical_clock"
                    if result["separates_at_requested_time"]
                    else "nonseparating_witness",
                    result=result,
                )
                receipt["assumptions"].append(
                    "No independent physical-clock calibration is supplied for this hypothetical embedding comparison."
                )
        elif kind == "dimension_bound":
            result = _bound(source, request.get("kinetic_parameters"))
            receipt.update(status=result["status"], result=result)
        elif kind == "response":
            names, matrix, initial, _ = _network(source, overrides)
            unit = request.get("time_basis")
            if unit == "model_unit":
                lower, upper = 1.0, 1.0
                calibration = {"evidence_kind": "model_assumption", "physical_unit": None}
            elif unit == "physical":
                lower, upper, calibration = _calibration(request, source)
            else:
                raise ScopeError("time_basis must explicitly be model_unit or physical")
            quantity = request.get("quantity")
            if quantity == "spectral_relaxation_time":
                nominal = _relaxation(matrix)
                result = {
                    "quantity": quantity,
                    "model_value": nominal,
                    "interval": [nominal / upper, nominal / lower],
                    "interval_method": "Exact inverse common-rate scaling of the numerically computed spectral time.",
                    "definition": "Inverse magnitude of the largest nonzero generator eigenvalue real part; not a general first-passage or half-life time.",
                }
            elif quantity == "state_at_time":
                time = _number(request.get("time"), "time")
                if time < 0:
                    raise ScopeError("Time must be nonnegative")
                midpoint = (lower + upper) / 2
                values = _trajectory(matrix, initial, time, midpoint)
                margin = time * float(np.linalg.norm(matrix, ord=1)) * (upper - lower) / 2
                intervals = [[max(0.0, float(value) - margin), min(1.0, float(value) + margin)] for value in values]
                result = {
                    "quantity": quantity,
                    "species": names,
                    "time": time,
                    "probabilities_at_midpoint": values.tolist(),
                    "intervals": intervals,
                    "interval_method": "Conservative coordinate enclosure from t*||Q||_1 times clock half-width; no endpoint-monotonicity assumption.",
                    "bound_margin": margin,
                }
            else:
                raise ScopeError("Unsupported response quantity")
            result.update(time_basis=unit, calibration=calibration)
            receipt.update(status="qualified_conditionally", result=result)
        else:
            raise ScopeError("Unknown mission type")
    except (ScopeError, ValueError, KeyError, TypeError, OverflowError, np.linalg.LinAlgError) as error:
        receipt.update(status="scope_not_qualified", reason=str(error))
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def main() -> None:
    """Run a JSON request against a local source directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("request", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    request = (
        json.loads(arguments.request.read_text())
        if arguments.request
        else {"mission_id": "inventory", "type": "inventory"}
    )
    result = qualify(request, arguments.source)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if arguments.out:
        arguments.out.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
