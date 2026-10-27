"""Source-bound qualification for the supplied H4 and Boehm evidence.

The H4 interpreter deliberately accepts only the closed, first-order reaction
form present in this package. It is not a general SBML simulator or an
identifiability solver. Nominal PEtab values are already in linear units.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from scipy.linalg import expm

CORE_FILES = ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")


def _canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _table(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _identity(source):
    source = Path(source)
    hashes = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(source.rglob("*")) if p.is_file()}
    missing = set(CORE_FILES) - hashes.keys()
    if missing:
        raise ValueError(f"Missing core source files: {sorted(missing)}")
    return {"source_fingerprint": _canonical_hash({name: hashes[name] for name in CORE_FILES}),
            "source_file_hashes": hashes, "evidence_fingerprint": _canonical_hash(hashes)}


def _tag(element):
    return element.tag.rsplit("}", 1)[-1]


def _product_terms(element):
    """Read the supplied product-only MathML without eval or guessed rates."""
    tag = _tag(element)
    if tag == "math" and len(element) == 1:
        return _product_terms(element[0])
    if tag == "apply" and len(element) >= 2 and _tag(element[0]) == "times":
        return [term for child in list(element)[1:] for term in _product_terms(child)]
    if tag == "ci":
        return [("symbol", (element.text or "").strip())]
    if tag == "cn" and not len(element):
        return [("number", float((element.text or "").strip()))]
    raise ValueError(f"Unsupported H4 kinetic MathML: {tag}")


def _probability(values):
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)) or np.min(values) < -1e-10:
        raise ValueError("Computed state is not a finite nonnegative distribution")
    total = float(values.sum())
    if not math.isclose(total, 1.0, abs_tol=1e-8, rel_tol=1e-8):
        raise ValueError(f"Computed probability mass is {total}, not one")
    values = np.maximum(values, 0.0)
    return values / values.sum()


def _h4_model(source):
    source = Path(source)
    model = ET.parse(source / "model.xml").getroot().find("{*}model")
    if model is None:
        raise ValueError("Missing SBML model")
    if any(model.find("{*}" + name) is not None for name in
           ("listOfRules", "listOfEvents", "listOfInitialAssignments")):
        raise ValueError("This H4 linear interpreter does not support rules or events")
    compartments = model.findall("{*}listOfCompartments/{*}compartment")
    if any(float(c.get("size", "1")) != 1.0 or c.get("constant", "true") != "true" for c in compartments):
        raise ValueError("This package requires fixed unit compartments")
    species = model.findall("{*}listOfSpecies/{*}species")
    ids = [s.attrib["id"] for s in species]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Missing or duplicate species IDs")
    if any(s.get("boundaryCondition", "false") != "false" or s.get("constant", "false") != "false" for s in species):
        raise ValueError("Expected a closed dynamic H4 state space")
    index = {name: i for i, name in enumerate(ids)}
    x0 = _probability([float(s.get("initialConcentration", s.get("initialAmount", "0"))) for s in species])
    rows = _table(source / "parameters.tsv")
    parameters = {r["parameterId"]: r for r in rows}
    nominal = {name: float(row["nominalValue"]) for name, row in parameters.items()}
    Q = np.zeros((len(ids), len(ids)), dtype=float)
    kinetic_parameters = set()
    for reaction in model.findall("{*}listOfReactions/{*}reaction"):
        if reaction.get("reversible", "true") != "false":
            raise ValueError("Expected explicit irreversible transitions")
        reactants = reaction.findall("{*}listOfReactants/{*}speciesReference")
        products = reaction.findall("{*}listOfProducts/{*}speciesReference")
        if len(reactants) != 1 or len(products) != 1:
            raise ValueError("Expected one reactant and one product per H4 reaction")
        if any(float(ref.get("stoichiometry", "1")) != 1 for ref in reactants + products):
            raise ValueError("Expected unit transition stoichiometry")
        src, dst = reactants[0].attrib["species"], products[0].attrib["species"]
        math_node = reaction.find("{*}kineticLaw/{*}math")
        if math_node is None:
            raise ValueError("Missing kinetic law")
        terms = _product_terms(math_node)
        state_terms = [value for kind, value in terms if kind == "symbol" and value in index]
        if state_terms != [src]:
            raise ValueError("H4 kinetics must be first order in the reactant only")
        rate = 1.0
        for kind, value in terms:
            if kind == "number":
                rate *= value
            elif value not in index:
                if value not in nominal:
                    raise ValueError(f"No nominal PEtab value for kinetic symbol {value}")
                kinetic_parameters.add(value)
                rate *= nominal[value]
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("The supplied irreducible H4 transition rates must be positive and finite")
        Q[index[dst], index[src]] += rate
        Q[index[src], index[src]] -= rate
    if not np.allclose(Q.sum(axis=0), 0, atol=1e-12, rtol=0):
        raise ValueError("H4 generator does not conserve mass")
    off_diagonal = Q.copy()
    np.fill_diagonal(off_diagonal, 0)
    if np.any(off_diagonal < 0):
        raise ValueError("Invalid generator off-diagonal sign")
    model_space = _table(source / "model_space.tsv")
    if not model_space:
        raise ValueError("Missing motif model-space evidence")
    motif_parameters = {name for name in model_space[0] if name in kinetic_parameters}
    selected = {name for name in kinetic_parameters if int(parameters[name]["estimate"]) == 1}
    superset = motif_parameters | selected
    coordinates = len(ids) - 1
    dimensions = {
        "independent_equilibrium_mean_coordinates_at_most": coordinates,
        "selected_kinetic_parameters": len(selected),
        "full_superset_kinetic_parameters": len(superset),
        "full_superset_rank_deficiency_at_least": max(0, len(superset) - coordinates),
        "selected_model_identifiability": "not_decided_by_dimension_bound",
    }
    measurements = _table(source / "measurements.tsv")
    all_equilibrium = bool(measurements) and all(float(r["time"]) == math.inf for r in measurements)
    return ids, Q, x0, dimensions, all_equilibrium


def _stationary(Q):
    # Scaling rows to order one improves conditioning for alternative clocks.
    magnitude = float(np.max(np.abs(Q)))
    if not math.isfinite(magnitude) or magnitude <= 0:
        raise ValueError("Invalid generator magnitude")
    A = (Q / magnitude).copy()
    b = np.zeros(len(Q))
    A[-1, :] = 1.0
    b[-1] = 1.0
    p = _probability(np.linalg.solve(A, b))
    if np.max(np.abs((Q / magnitude) @ p)) > 1e-10:
        raise ValueError("Stationary residual exceeds tolerance")
    return p


def _spectral_tau(Q):
    eigenvalues = np.linalg.eigvals(Q)
    tolerance = 1e-10 * max(1.0, float(np.max(np.abs(Q))))
    zero = np.abs(eigenvalues) <= tolerance
    if np.count_nonzero(zero) != 1:
        raise ValueError("Expected one conservation eigenvalue")
    decay_rates = -eigenvalues[~zero].real
    if np.min(decay_rates) <= 0:
        raise ValueError("No positive asymptotic spectral relaxation scale")
    return float(1.0 / np.min(decay_rates))


def _state_map(ids, values):
    return {name: float(value) for name, value in zip(ids, values)}


def _positive(value, label):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be positive and finite")
    return result


def _inheritance(source, inherited, request):
    measurements = _table(source / "measurements.tsv")
    observables = _table(source / "observables.tsv")
    simulations = _table(source / "simulations.tsv")
    conditions = _table(source / "conditions.tsv")
    parameters = _table(source / "parameters.tsv")
    model = ET.parse(source / "model.xml").getroot().find("{*}model")
    if model is None or not conditions or not parameters or not measurements or not observables:
        raise ValueError("Incomplete fresh dynamic source")
    times = sorted({float(r["time"]) for r in measurements})
    if any(math.isnan(t) for t in times):
        raise ValueError("NaN observation time")
    requested_times = request["contrast_times"]
    if len(requested_times) != 2 or any(not math.isfinite(float(t)) for t in requested_times):
        raise ValueError("Contrast requires two finite provided simulation times")
    contrast = {}
    for observable in observables:
        oid = observable["observableId"]
        values = []
        for target in requested_times:
            matches = [float(row["simulation"]) for row in simulations
                       if row["observableId"] == oid and float(row["time"]) == float(target)]
            if len(matches) != 1 or not math.isfinite(matches[0]):
                raise ValueError(f"Expected one provided simulation for {oid} at time {target}")
            values.append(matches[0])
        contrast[oid] = values[1] - values[0]
    previous = _identity(inherited)
    current = _identity(source)
    return {
        "decision": "fresh_dynamic_qualification_required",
        "inherited_equilibrium_witness_applicable": False,
        "full_parameter_identifiability_established": False,
        "measurement_rows": len(measurements),
        "observation_times": times,
        "observable_count": len(observables),
        "all_measurements_at_equilibrium": all(t == math.inf for t in times),
        "previous_source_fingerprint": previous["source_fingerprint"],
        "previous_evidence_fingerprint": previous["evidence_fingerprint"],
        "source_identity_changed": current["source_fingerprint"] != previous["source_fingerprint"],
        "finite_prediction_contrast": contrast,
        "contrast_evidence_kind": "provided_reference_simulation_not_observation",
        "reason": (
            "The fresh Boehm model and its relative observation map have measurements at fixed finite times. "
            "H4's equilibrium identity Qp=0 implies (cQ)p=0, but generally does not preserve predictions "
            "at fixed finite observation times, so neither that witness nor an earlier qualification transfers. "
            "The contrasts are differences read from the provided reference simulations, not a nonlinear "
            "rerun, a fit, or new physical observations. Finite-time observations alone establish neither "
            "complete parameter identifiability nor physical validity. The Boehm time-unit definition's "
            "60-second multiplier records a unit convention; it does not by itself calibrate every temporal "
            "interpretation. Fresh dynamic qualification is required and no authority transfers."
        ),
    }


def build_packet(source_root, requests_path):
    """Compute a new independent packet from immutable source and request bytes."""
    source_root = Path(source_root)
    requests = json.loads(Path(requests_path).read_text(encoding="utf-8"))
    records = []
    # No persistent cache: repeated and changed requests cannot inherit old answers.
    h4_models = {}
    for request in requests["missions"]:
        source = source_root / request["source"]
        record = {"id": request["id"], "source": request["source"], **_identity(source),
                  "request_fingerprint": _canonical_hash(request), "authority": [],
                  "biological_validation": False}
        mission = request["type"]
        if mission in ("stationary_qualification", "clock_witness", "calibrated_relaxation"):
            if request["source"] not in h4_models:
                h4_models[request["source"]] = _h4_model(source)
            ids, Q, x0, dimensions, all_equilibrium = h4_models[request["source"]]
        if mission == "stationary_qualification":
            p = _stationary(Q)
            acetylation_counts = [4 if name == "x_4ac" else name.count("k") for name in ids]
            record.update(decision="conditional_model_prediction", conditional_on_supplied_fit=True,
                          full_parameter_identifiability_established=False,
                          stationary=_state_map(ids, p), mean_acetylation=float(np.dot(p, acetylation_counts)),
                          dimension_check=dimensions.copy())
        elif mission == "clock_witness":
            if not all_equilibrium:
                raise ValueError("The equilibrium-only clock witness requires equilibrium-only measurements")
            raw_scales = request["alternative_clock_scales"]
            if len(raw_scales) != 2:
                raise ValueError("Exactly two hypothetical clock scales are required")
            scales = [_positive(c, "clock scale") for c in raw_scales]
            time = _positive(request["normalized_time"], "normalized_time")
            equilibria = [_stationary(c * Q) for c in scales]
            states = [_state_map(ids, _probability(expm((c * time) * Q) @ x0)) for c in scales]
            record.update(
                decision="needs_clock_calibration", physical_time_supported=False,
                same_equilibrium_under_clock_scaling=True, clock_scales=list(raw_scales),
                state_at_request_time=states,
                equilibrium_max_abs_difference=float(np.max(np.abs(equilibria[0] - equilibria[1]))),
                proof_statement=(
                    "For every positive external clock conversion c, Qp=0 implies (cQ)p=c(Qp)=0; "
                    "normalization of p is unchanged. The finite-time solution becomes exp(cQt)x0=x(ct) "
                    "and generally changes at fixed t. These are hypothetical physical-clock conversions, "
                    "not different fitted parameters or observed biological rates. Fixed da_b=1 remains "
                    "the original legitimate normalization. The steady-state data and undeclared physical "
                    "time unit do not identify this conversion; this witness does not show every stationary "
                    "quantity or fitted parameter to be unidentifiable."
                ),
                additional_evidence_required=(
                    "An independently supported mapping from normalized model time to a specified physical "
                    "unit, such as a compatible time-course calibration or an independent kinetic reference, "
                    "with its provenance, conditions, and conversion uncertainty."
                ),
            )
        elif mission == "calibrated_relaxation":
            calibration = request["calibration"]
            if calibration["evidence_kind"] != "assumed":
                raise ValueError("This mission requires an explicitly assumed calibration")
            bounds = calibration["scale_per_physical_unit"]
            if len(bounds) != 2:
                raise ValueError("Calibration requires [lo, hi]")
            lo, hi = [_positive(value, "calibration scale") for value in bounds]
            if lo > hi:
                raise ValueError("Calibration bounds must be ordered")
            tau = _spectral_tau(Q)
            record.update(
                decision="conditional_on_assumed_calibration",
                calibration_evidence_id=calibration["evidence_id"], calibration_evidence_kind="assumed",
                physical_unit=calibration["physical_unit"], tau_model=tau,
                tau_physical_interval=[tau / hi, tau / lo], calibration_is_observed=False,
                conditional_on_supplied_fit=True,
                interpretation=("Asymptotic spectral exponential scale of the supplied model. The interval "
                                "deterministically propagates hypothetical conversion bounds; it is not a "
                                "confidence interval, biological half-life, or finite-time settling guarantee."),
            )
        elif mission == "inheritance_boundary":
            record.update(_inheritance(source, source_root / request["inherited_source"], request))
        else:
            raise ValueError(f"Unsupported mission type: {mission}")
        records.append(record)
    packet = {"packet_version": 1, "authority": [], "missions": records}
    json.dumps(packet, allow_nan=False)
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--requests", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    # All evidence and numerical validation finish before touching the output.
    packet = build_packet(args.sources, args.requests)
    rendered = json.dumps(packet, indent=2, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.out.parent,
                                         prefix=args.out.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(rendered)
        os.replace(temporary, args.out)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
