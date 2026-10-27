# SPDX-License-Identifier: Apache-2.0
"""Competent conventional construction using source inspection and direct algebra.

Researcher authored after opportunity selection; not a free pre-existing service,
not a human trial, and independent of the retained instrument implementation.
"""

from __future__ import annotations
import argparse
import csv
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.linalg import expm

FILES = ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fingerprint(path):
    return canonical_hash({name: hashlib.sha256((path / name).read_bytes()).hexdigest() for name in FILES})


def evidence_files(path):
    return {
        str(p.relative_to(path).as_posix()): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def tag(element):
    return element.tag.rsplit("}", 1)[-1]


def direct_generator(path):
    tree = ET.parse(path / "model.xml").getroot()
    species = [e for e in tree.iter() if tag(e) == "species"]
    names = [e.attrib["id"] for e in species]
    initial = np.array([float(e.attrib.get("initialConcentration", "0")) for e in species])
    parameters = {r["parameterId"]: float(r["nominalValue"]) for r in rows(path / "parameters.tsv")}
    matrix = np.zeros((len(names), len(names)))
    for reaction in (e for e in tree.iter() if tag(e) == "reaction"):
        reactant = next(e for e in reaction if tag(e) == "listOfReactants")[0].attrib["species"]
        product = next(e for e in reaction if tag(e) == "listOfProducts")[0].attrib["species"]
        kinetic = next(e for e in reaction if tag(e) == "kineticLaw")
        operators = [tag(e) for e in kinetic.iter() if tag(e) not in ("kineticLaw", "math", "apply", "ci")]
        if operators != ["times"]:
            raise ValueError("This direct construction only supports the supplied linear H4 mass-action laws.")
        identifiers = [(e.text or "").strip() for e in kinetic.iter() if tag(e) == "ci"]
        if identifiers.count(reactant) != 1 or any(x in names and x != reactant for x in identifiers):
            raise ValueError("Nonlinear or inconsistent reactant law")
        rate = 1.0
        for symbol in identifiers:
            if symbol != reactant:
                rate *= parameters[symbol]
        a, b = names.index(reactant), names.index(product)
        matrix[b, a] += rate
        matrix[a, a] -= rate
    return names, matrix, initial


def steady(matrix):
    system = matrix.copy()
    rhs = np.zeros(len(matrix))
    system[-1, :] = 1
    rhs[-1] = 1
    return np.linalg.solve(system, rhs)


def build_packet(source_root, requests_path):
    source_root, requests_path = Path(source_root), Path(requests_path)
    requests = json.loads(requests_path.read_text())["missions"]
    names, matrix, initial = direct_generator(source_root / "h4")
    stationary = steady(matrix)
    eigenvalues = np.linalg.eigvals(matrix)
    tau = 1 / min(-z.real for z in eigenvalues if z.real < -1e-9)
    packet = {"packet_version": 1, "authority": [], "missions": []}
    for request in requests:
        source = source_root / request["source"]
        item = {
            "id": request["id"],
            "source": request["source"],
            "source_fingerprint": fingerprint(source),
            "source_file_hashes": evidence_files(source),
            "evidence_fingerprint": canonical_hash(evidence_files(source)),
            "request_fingerprint": canonical_hash(request),
            "authority": [],
            "biological_validation": False,
        }
        kind = request["type"]
        if kind == "stationary_qualification":
            params = rows(source / "parameters.tsv")
            kinetics = [p for p in params if p["parameterId"].startswith("a_")]
            item.update(
                decision="conditional_model_prediction",
                conditional_on_supplied_fit=True,
                full_parameter_identifiability_established=False,
                stationary=dict(zip(names, stationary.tolist())),
                mean_acetylation=float(
                    sum(
                        p * (0 if n == "x_0ac" else 4 if n == "x_4ac" else n.count("k"))
                        for n, p in zip(names, stationary)
                    )
                ),
                dimension_check={
                    "independent_equilibrium_mean_coordinates_at_most": len(names) - 1,
                    "selected_kinetic_parameters": sum(int(p["estimate"]) for p in kinetics),
                    "full_superset_kinetic_parameters": len(kinetics),
                    "full_superset_rank_deficiency_at_least": len(kinetics) - (len(names) - 1),
                    "selected_model_identifiability": "not_decided_by_dimension_bound",
                },
            )
        elif kind == "clock_witness":
            scales = request["alternative_clock_scales"]
            vectors = [(expm(float(c) * matrix * request["normalized_time"]) @ initial) for c in scales]
            item.update(
                decision="needs_clock_calibration",
                physical_time_supported=False,
                same_equilibrium_under_clock_scaling=True,
                clock_scales=scales,
                state_at_request_time=[dict(zip(names, x.tolist())) for x in vectors],
                equilibrium_max_abs_difference=float(
                    np.max(np.abs(steady(scales[0] * matrix) - steady(scales[1] * matrix)))
                ),
                proof_statement="For the stationary p, Qp=0 implies (cQ)p=0 for positive c. At finite time exp(cQt)x0=x(ct), which changes the requested response. These c values are hypothetical physical-clock conversions; the original fixed da_b=1 normalization is preserved.",
                additional_evidence_required="An independently supported conversion from this normalized model clock to the requested physical time unit, with current scope and uncertainty.",
            )
        elif kind == "calibrated_relaxation":
            calibration = request["calibration"]
            lo, hi = calibration["scale_per_physical_unit"]
            item.update(
                decision="conditional_on_assumed_calibration",
                calibration_evidence_id=calibration["evidence_id"],
                calibration_evidence_kind="assumed",
                physical_unit=calibration["physical_unit"],
                tau_model=float(tau),
                tau_physical_interval=[float(tau / hi), float(tau / lo)],
                calibration_is_observed=False,
                conditional_on_supplied_fit=True,
            )
        elif kind == "inheritance_boundary":
            data = rows(source / "measurements.tsv")
            simulations = rows(source / "simulations.tsv")
            times = sorted({float(r["time"]) for r in data})
            observables = sorted({r["observableId"] for r in data})
            lookup = {(r["observableId"], float(r["time"])): float(r["simulation"]) for r in simulations}
            t0, t1 = request["contrast_times"]
            item.update(
                decision="fresh_dynamic_qualification_required",
                inherited_equilibrium_witness_applicable=False,
                full_parameter_identifiability_established=False,
                measurement_rows=len(data),
                observation_times=times,
                observable_count=len(observables),
                all_measurements_at_equilibrium=False,
                previous_source_fingerprint=fingerprint(source_root / request["inherited_source"]),
                previous_evidence_fingerprint=canonical_hash(evidence_files(source_root / request["inherited_source"])),
                source_identity_changed=True,
                finite_prediction_contrast={o: lookup[o, t1] - lookup[o, t0] for o in observables},
                contrast_evidence_kind="provided_reference_simulation_not_observation",
                reason="The new source contains finite, fixed observation times and a different observation map. Equilibrium scaling invariance does not establish equality at those times. The inherited H4 receipt does not qualify this mission; no full identifiability or physical validity follows merely from timed observations.",
            )
        else:
            raise ValueError("Unknown mission type")
        packet["missions"].append(item)
    return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--requests", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    result = build_packet(args.sources, args.requests)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "missions": len(result["missions"]),
                "elapsed_seconds": time.perf_counter() - started,
                "actual_cost": None,
                "implementation": "researcher-authored conventional direct algebra",
            }
        )
    )


if __name__ == "__main__":
    main()
