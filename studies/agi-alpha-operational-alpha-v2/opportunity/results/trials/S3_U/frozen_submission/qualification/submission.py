"""Source-bound scientific reuse qualification for the supplied four missions.

This implements the closed, first-order H4 model actually supplied here; it is
not a general SBML simulator. Boehm contrasts are read from reference output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.linalg import expm

CORE_FILES = (
    "model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv",
    "conditions.tsv",
)


def _canonical_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _table(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _identity(directory):
    directory = Path(directory)
    hashes = {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }
    return {
        "source_fingerprint": _canonical_hash({name: hashes[name] for name in CORE_FILES}),
        "source_file_hashes": hashes,
        "evidence_fingerprint": _canonical_hash(hashes),
    }


def _tag(element):
    return element.tag.rsplit("}", 1)[-1]


def _positive(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return result


def _probability(values):
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)) or values.min() < -1e-11:
        raise ValueError("Computed state is not a finite nonnegative distribution")
    if abs(float(values.sum()) - 1.0) > 1e-9:
        raise ValueError("Computed state does not conserve total mass one")
    # Remove only floating-point roundoff, after checking the raw result.
    values = np.maximum(values, 0.0)
    return values / values.sum()


def _species_map(species, state):
    return {name: float(value) for name, value in zip(species, state)}


def _monomial(element, parameters, species_set):
    """Evaluate constant coefficient and species factors in source MathML.

    Explicitly reject expressions outside this source's product-only kinetics,
    rather than silently treating a nonlinear rate as a generator entry.
    """
    kind = _tag(element)
    if kind == "math":
        if len(element) != 1:
            raise ValueError("Expected one MathML expression")
        return _monomial(element[0], parameters, species_set)
    if kind == "ci":
        symbol = element.text.strip()
        if symbol in species_set:
            return 1.0, [symbol]
        if symbol not in parameters:
            raise ValueError(f"Kinetic symbol lacks a nominal parameter: {symbol}")
        return parameters[symbol], []
    if kind == "cn" and len(element) == 0:
        return float(element.text.strip()), []
    if kind == "apply" and len(element) > 1 and _tag(element[0]) == "times":
        coefficient, factors = 1.0, []
        for child in element[1:]:
            factor, names = _monomial(child, parameters, species_set)
            coefficient *= factor
            factors.extend(names)
        return coefficient, factors
    raise ValueError(f"Unsupported H4 kinetic expression: {kind}")


def _load_h4(directory):
    directory = Path(directory)
    model = ET.parse(directory / "model.xml").getroot().find("{*}model")
    if model is None:
        raise ValueError("Missing SBML model")
    forbidden = ("listOfRules", "listOfInitialAssignments", "listOfEvents")
    if any(model.find("{*}" + name) is not None for name in forbidden):
        raise ValueError("This generator construction requires autonomous linear kinetics")
    compartments = model.findall("{*}listOfCompartments/{*}compartment")
    if len(compartments) != 1 or float(compartments[0].get("size", "nan")) != 1.0:
        raise ValueError("Expected the supplied unit-volume H4 compartment")
    species_elements = model.findall("{*}listOfSpecies/{*}species")
    species = [element.attrib["id"] for element in species_elements]
    if len(species) != len(set(species)) or not species:
        raise ValueError("Invalid species identifiers")
    if any(element.get("boundaryCondition", "false") != "false" or
           element.get("constant", "false") != "false" for element in species_elements):
        raise ValueError("Expected a closed dynamic H4 species set")
    initial = _probability([
        float(element.get("initialConcentration", element.get("initialAmount", "0")))
        for element in species_elements
    ])
    rows = _table(directory / "parameters.tsv")
    parameters = {row["parameterId"]: float(row["nominalValue"]) for row in rows}
    if any(not math.isfinite(value) for value in parameters.values()):
        raise ValueError("Nonfinite nominal parameter")
    index = {name: i for i, name in enumerate(species)}
    Q = np.zeros((len(species), len(species)))
    kinetic_parameters = set()
    reactions = model.findall("{*}listOfReactions/{*}reaction")
    for reaction in reactions:
        if reaction.get("reversible", "true") != "false":
            raise ValueError("Expected explicit irreversible transition reactions")
        reactants = reaction.findall("{*}listOfReactants/{*}speciesReference")
        products = reaction.findall("{*}listOfProducts/{*}speciesReference")
        if len(reactants) != 1 or len(products) != 1:
            raise ValueError("H4 transitions must each have one source and one destination")
        if any(float(element.get("stoichiometry", "1")) != 1.0
               for element in reactants + products):
            raise ValueError("H4 transitions must conserve a single molecule")
        source, destination = reactants[0].get("species"), products[0].get("species")
        law = reaction.find("{*}kineticLaw/{*}math")
        if law is None:
            raise ValueError("Missing kinetic law")
        rate, factors = _monomial(law, parameters, set(species))
        if factors != [source] or not math.isfinite(rate) or rate <= 0:
            raise ValueError("Expected positive linear mass-action transition")
        kinetic_parameters.update(
            ci.text.strip() for ci in law.iter() if _tag(ci) == "ci"
            and ci.text.strip() not in index
        )
        i, j = index[source], index[destination]
        Q[j, i] += rate
        Q[i, i] -= rate
    if not np.allclose(Q.sum(axis=0), 0.0, rtol=0, atol=1e-12):
        raise ValueError("Generator violates conservation")
    estimated = {row["parameterId"] for row in rows
                 if int(row["estimate"]) == 1 and row["parameterId"] in kinetic_parameters}
    space = _table(directory / "model_space.tsv")
    selectable_motifs = {
        name for row in space for name, entry in row.items()
        if name in kinetic_parameters and "estimate" in entry.split(";")
    }
    full_superset = selectable_motifs | estimated
    coordinates = len(species) - 1
    dimension = {
        "independent_equilibrium_mean_coordinates_at_most": coordinates,
        "selected_kinetic_parameters": len(estimated),
        "full_superset_kinetic_parameters": len(full_superset),
        "full_superset_rank_deficiency_at_least": max(0, len(full_superset) - coordinates),
        "selected_model_identifiability": "not_decided_by_dimension_bound",
    }
    measurements = _table(directory / "measurements.tsv")
    if not measurements or not all(float(row["time"]) == math.inf for row in measurements):
        raise ValueError("The equilibrium-only H4 qualification requires equilibrium evidence")
    if parameters.get("da_b") != 1.0 or "da_b" in estimated:
        raise ValueError("The supplied fixed da_b=1 normalization is required")
    if model.get("timeUnits") or model.find("{*}listOfUnitDefinitions") is not None:
        raise ValueError("Review qualification if a physical time unit is supplied")
    return {
        "species": species, "Q": Q, "x0": initial, "dimension": dimension,
        "measurement_rows": len(measurements), "motif_count": len(selectable_motifs),
        "reaction_count": len(reactions),
    }


def _stationary(Q):
    # Scaling the equations improves conditioning without changing their nullspace.
    scale = float(np.max(np.abs(Q)))
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid generator scale")
    A = Q / scale
    A = A.copy()
    A[-1, :] = 1.0
    b = np.zeros(Q.shape[0])
    b[-1] = 1.0
    p = _probability(np.linalg.solve(A, b))
    if float(np.max(np.abs((Q / scale) @ p))) > 1e-11:
        raise ValueError("Stationary solution failed its balance equations")
    return p


def _relaxation(Q):
    eigenvalues = np.linalg.eigvals(Q)
    tolerance = 100 * len(Q) * np.finfo(float).eps * max(1.0, np.linalg.norm(Q, 2))
    nonzero = eigenvalues[np.abs(eigenvalues) > tolerance]
    if len(nonzero) != len(Q) - 1 or np.any(nonzero.real >= -tolerance):
        raise ValueError("Expected one conserved mode and stable nonzero modes")
    return float(1.0 / np.min(-nonzero.real))


def _inheritance(directory, inherited_identity, current_identity, request):
    # Read the new model and observation map afresh; do not call the H4 solver.
    model = ET.parse(directory / "model.xml").getroot().find("{*}model")
    observations = _table(directory / "observables.tsv")
    measurement_rows = _table(directory / "measurements.tsv")
    simulations = _table(directory / "simulations.tsv")
    times = sorted({float(row["time"]) for row in measurement_rows})
    observable_ids = [row["observableId"] for row in observations]
    if len(observable_ids) != len(set(observable_ids)):
        raise ValueError("Duplicate observable definitions")
    contrast_times = request["contrast_times"]
    if len(contrast_times) != 2 or not all(math.isfinite(float(t)) for t in contrast_times):
        raise ValueError("Two finite reference-simulation contrast times are required")
    t0, t1 = map(float, contrast_times)
    def value_at(observable, time):
        values = [float(row["simulation"]) for row in simulations
                  if row["observableId"] == observable and float(row["time"]) == time]
        if len(values) != 1 or not math.isfinite(values[0]):
            raise ValueError(f"Reference simulation is absent or ambiguous: {observable} at {time}")
        return values[0]
    contrast = {name: value_at(name, t1) - value_at(name, t0) for name in observable_ids}
    units = [dict(unit.attrib) for definition in model.findall(
        "{*}listOfUnitDefinitions/{*}unitDefinition") if definition.get("id") == "time"
        for unit in definition.findall("{*}listOfUnits/{*}unit")]
    return {
        "decision": "fresh_dynamic_qualification_required",
        "inherited_equilibrium_witness_applicable": False,
        "full_parameter_identifiability_established": False,
        "measurement_rows": len(measurement_rows),
        "observation_times": times,
        "observable_count": len(observable_ids),
        "all_measurements_at_equilibrium": bool(measurement_rows) and all(
            float(row["time"]) == math.inf for row in measurement_rows),
        "previous_source_fingerprint": inherited_identity["source_fingerprint"],
        "previous_evidence_fingerprint": inherited_identity["evidence_fingerprint"],
        "source_identity_changed": current_identity["source_fingerprint"] !=
                                   inherited_identity["source_fingerprint"],
        "finite_prediction_contrast": contrast,
        "contrast_evidence_kind": "provided_reference_simulation_not_observation",
        "time_unit_definition": units,
        "reason": (
            f"The fresh {model.attrib['id']} source has a different model and observation map. "
            "Its observations occur at fixed finite times, so a change x(t) to x(ct) generally "
            "changes the predicted observations there. The equilibrium implication Qp=0 => "
            "(cQ)p=0 therefore cannot automatically be imported as a dynamic equivalence or "
            "approval. The reported differences are read from supplied reference simulations, "
            "not observations, a nonlinear rerun, or a new fit. Finite-time observations alone "
            "establish neither full parameter identifiability nor physical validity. The time "
            "unit's 60-second multiplier records a unit convention; it does not by itself "
            "validate every temporal interpretation. Neither artifact transfers authority."
        ),
    }


def build_packet(source_root, requests_path):
    """Recompute all records from current supplied file bytes and request values."""
    source_root = Path(source_root)
    requests = json.loads(Path(requests_path).read_text(encoding="utf-8"))["missions"]
    identities, h4_models = {}, {}
    def identity(name):
        if name not in identities:
            identities[name] = _identity(source_root / name)
        return identities[name]
    def h4(name):
        if name not in h4_models:
            h4_models[name] = _load_h4(source_root / name)
        return h4_models[name]
    records = []
    for request in requests:
        name, kind = request["source"], request["type"]
        bound = identity(name)
        record = {
            "id": request["id"], "source": name, "type": kind,
            **bound, "request_fingerprint": _canonical_hash(request),
            "authority": [], "biological_validation": False,
        }
        if kind in {"stationary_qualification", "clock_witness", "calibrated_relaxation"}:
            model = h4(name)
            species, Q, x0 = model["species"], model["Q"], model["x0"]
        if kind == "stationary_qualification":
            stationary = _stationary(Q)
            counts = [0 if s == "x_0ac" else 4 if s == "x_4ac" else s.count("k")
                      for s in species]
            record.update({
                "decision": "conditional_model_prediction",
                "conditional_on_supplied_fit": True,
                "full_parameter_identifiability_established": False,
                "stationary": _species_map(species, stationary),
                "mean_acetylation": float(stationary @ np.asarray(counts)),
                "dimension_check": model["dimension"],
                "dimension_explanation": (
                    f"{len(species)} states at total mass one allow at most {len(species)-1} "
                    f"independent equilibrium mean coordinates. The model space includes "
                    f"{model['motif_count']} selectable motif factors plus the common estimated "
                    "basal rate; fixed da_b=1 and observation-noise parameters are excluded. "
                    "Repeated observations improve precision, not the number of independent "
                    "equilibrium mean coordinates. This necessary bound does not decide "
                    "identifiability of the selected fitted model or provide an uncertainty interval."
                ),
            })
        elif kind == "clock_witness":
            scales = request["alternative_clock_scales"]
            if len(scales) != 2:
                raise ValueError("Exactly two alternative clock scales are required")
            c0, c1 = [_positive(c, "clock scale") for c in scales]
            time = _positive(request["normalized_time"], "normalized time")
            states = [_probability(expm(c * Q * time) @ x0) for c in (c0, c1)]
            equilibria = [_stationary(c * Q) for c in (c0, c1)]
            record.update({
                "decision": "needs_clock_calibration", "physical_time_supported": False,
                "same_equilibrium_under_clock_scaling": True,
                "clock_scales": list(scales),
                "state_at_request_time": [_species_map(species, state) for state in states],
                "equilibrium_max_abs_difference": float(np.max(np.abs(equilibria[0]-equilibria[1]))),
                "proof_statement": (
                    "For c>0, Qp=0 implies (cQ)p=0, while exp(cQt)x0=x(ct), so finite-time "
                    "trajectories generally change. These c values are hypothetical external "
                    "physical-clock conversions, not alternative parameter estimates of the fit. "
                    "Fixed da_b=1 remains the original legitimate normalization. The supplied "
                    "equilibrium-only observations and absent declared physical time unit do not "
                    "select a physical clock. This witness neither rejects the stationary "
                    "prediction nor proves every parameter or stationary quantity unidentifiable."
                ),
                "additional_evidence_required": (
                    "An independently supported conversion from normalized model time to a stated "
                    "physical unit, such as compatible time-resolved observations or an independently "
                    "measured rate linking this normalized model to a physical clock, with its "
                    "conditions, provenance and uncertainty documented."
                ),
            })
        elif kind == "calibrated_relaxation":
            calibration = request["calibration"]
            if calibration["evidence_kind"] != "assumed":
                raise ValueError("This mission requires the explicitly assumed calibration label")
            interval = calibration["scale_per_physical_unit"]
            if len(interval) != 2:
                raise ValueError("Calibration interval needs two endpoints")
            lo, hi = [_positive(value, "calibration scale") for value in interval]
            if lo > hi:
                raise ValueError("Calibration interval endpoints are not ordered")
            tau = _relaxation(Q)
            record.update({
                "decision": "conditional_on_assumed_calibration",
                "calibration_evidence_id": calibration["evidence_id"],
                "calibration_evidence_kind": calibration["evidence_kind"],
                "physical_unit": calibration["physical_unit"],
                "tau_model": tau, "tau_physical_interval": [tau / hi, tau / lo],
                "calibration_is_observed": False, "conditional_on_supplied_fit": True,
                "interpretation": (
                    "The inverse slowest nonzero spectral decay rate is an asymptotic exponential "
                    "scale of the supplied model. Dividing by the assumed conversion endpoints "
                    "propagates those deterministic bounds; it is neither a confidence interval, "
                    "a measured biological half-life, nor a finite-time settling guarantee."
                ),
            })
        elif kind == "inheritance_boundary":
            record.update(_inheritance(source_root / name, identity(request["inherited_source"]),
                                        bound, request))
        else:
            raise ValueError(f"Unknown mission type: {kind}")
        records.append(record)
    packet = {"packet_version": 1, "authority": [], "missions": records}
    json.dumps(packet, allow_nan=False)
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--requests", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    packet = build_packet(args.sources, args.requests)
    args.out.write_text(json.dumps(packet, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
