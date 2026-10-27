# SPDX-License-Identifier: Apache-2.0
"""Source-bound adapter for the supplied four-mission qualification contract.

The frozen instrument validates and solves its supported H4 dynamics. This
adapter supplies the portfolio-specific bindings, functionals, and fresh-source
boundary. Nothing here fits parameters or establishes biological validity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
from scipy.linalg import expm

# Load the immutable adjacent capsule even when imported from another cwd.
_CAPSULE_PATH = Path(__file__).resolve().parent / "capability" / "model_reuse.py"
_SPEC = importlib.util.spec_from_file_location("_qualification_model_reuse_v1", _CAPSULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Cannot load the supplied scientific-model-reuse instrument")
instrument = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = instrument
_SPEC.loader.exec_module(instrument)

CORE_FILES = ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")


def canonical_bytes(value: Any) -> bytes:
    # The external contract uses json.dumps's default ensure_ascii=True.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"Missing or duplicate column headers: {path.name}")
        result = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in result):
        raise ValueError(f"Malformed table: {path.name}")
    return result


def source_bindings(directory: Path) -> dict[str, Any]:
    if not directory.is_dir():
        raise ValueError(f"Missing source directory: {directory}")
    all_hashes = {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*")) if p.is_file()
    }
    core_hashes = {name: all_hashes[name] for name in CORE_FILES}
    return {
        "source_fingerprint": digest(core_hashes),
        "source_file_hashes": all_hashes,
        "evidence_fingerprint": digest(all_hashes),
    }


def _source_path(root: Path, source_id: Any) -> Path:
    if not isinstance(source_id, str) or not source_id or Path(source_id).name != source_id or source_id in (".", ".."):
        raise ValueError("A source must name one supplied source directory")
    return root / source_id


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive finite number")
    answer = float(value)
    if not math.isfinite(answer) or answer <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return answer


def _pair(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must have two values")
    return _positive(value[0], label), _positive(value[1], label)


def _probabilities(values: Any) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or not np.isfinite(result).all() or result.min() < -1e-10:
        raise ValueError("A computed state failed finite probability checks")
    if not np.isclose(result.sum(), 1.0, rtol=0.0, atol=1e-9):
        raise ValueError("A computed state failed total-mass conservation")
    return result


def _mapping(names: list[str], values: Any) -> dict[str, float]:
    vector = _probabilities(values)
    if len(names) != len(vector):
        raise ValueError("State names and computed vector have different lengths")
    return dict(zip(names, map(float, vector)))


def _stationary_scaled(matrix: np.ndarray, scale: float) -> np.ndarray:
    # Each scaled matrix is independently solved; common rescaling improves
    # conditioning without changing the nullspace or the normalization equation.
    scaled = scale * matrix
    norm = float(np.max(np.abs(scaled)))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("Scaled generator is outside finite numerical range")
    augmented = scaled / norm
    augmented[-1, :] = 1.0
    target = np.zeros(len(matrix))
    target[-1] = 1.0
    result = _probabilities(np.linalg.solve(augmented, target))
    if np.max(np.abs((scaled / norm) @ result)) > 1e-10:
        raise ValueError("Stationary residual exceeds tolerance")
    return result


def _acetylation_count(species: str) -> int:
    if species == "x_0ac":
        return 0
    if species == "x_4ac":
        return 4
    if not species.startswith("x_k"):
        raise ValueError("Unexpected H4 species name for the requested functional")
    return species.count("k")


def _stationary_record(directory: Path) -> dict[str, Any]:
    point = instrument.stationary(directory)
    bound = instrument.dimension_bound(directory)
    selected = int(bound["selected_estimated_kinetic_parameters"])
    full = bound["candidate_estimated_kinetic_parameters"]
    if full is None:
        raise ValueError("The full-superset dimension statement requires model-space evidence")
    maximum = int(bound["maximum_independent_mean_coordinates"])
    stationary = _mapping(point["species"], point["probabilities"])
    return {
        "decision": "conditional_model_prediction",
        "conditional_on_supplied_fit": True,
        "full_parameter_identifiability_established": False,
        "stationary": stationary,
        "mean_acetylation": float(sum(_acetylation_count(name) * abundance for name, abundance in stationary.items())),
        "dimension_check": {
            "independent_equilibrium_mean_coordinates_at_most": maximum,
            "selected_kinetic_parameters": selected,
            "full_superset_kinetic_parameters": int(full),
            "full_superset_rank_deficiency_at_least": max(0, int(full) - maximum),
            "selected_model_identifiability": "not_decided_by_dimension_bound",
        },
        "dimension_reason": (
            "One normalized equilibrium over the supplied species has at most n-1 independent mean coordinates. "
            "The model-space table allows the motif-specific factors to be estimated; the selected estimated "
            "basal rate is also counted. Fixed da_b=1 and the noise parameter are not extra free kinetic coordinates. "
            "Repeated observations improve precision without adding equilibrium mean coordinates. "
            "This necessary dimension bound does not decide identifiability of the selected fit."
        ),
    }


def _clock_record(request: dict[str, Any], directory: Path) -> dict[str, Any]:
    one, two = _pair(request["alternative_clock_scales"], "alternative clock scales")
    time = _positive(request["normalized_time"], "normalized_time")
    if one != two:
        result = instrument.clock_witness(directory, scales=(one, two), time=time)
        names = result["species"]
        states = [result["prediction_world_1"], result["prediction_world_2"]]
        equilibrium_difference = float(result["stationary_difference_max"])
    else:
        # The portfolio contract permits any positive pair. Equal alternatives
        # do not separate, but they cannot establish an unsupported calibration.
        info = instrument.inventory(directory)
        generator = instrument.build_generator(directory)
        names = generator["species"]
        if not info["all_measurements_at_equilibrium"] or any(
            row["observableFormula"].strip() not in names for row in rows(directory / "observables.tsv")
        ):
            raise ValueError("The equilibrium witness is outside this source's measurement scope")
        matrix = np.asarray(generator["matrix"])
        initial = np.asarray(generator["initial"])
        states = [expm(scale * matrix * time) @ initial for scale in (one, two)]
        points = [_stationary_scaled(matrix, scale) for scale in (one, two)]
        equilibrium_difference = float(np.max(np.abs(points[0] - points[1])))
    return {
        "decision": "needs_clock_calibration",
        "physical_time_supported": False,
        "same_equilibrium_under_clock_scaling": True,
        "clock_scales": list(request["alternative_clock_scales"]),
        "state_at_request_time": [_mapping(names, values) for values in states],
        "equilibrium_max_abs_difference": equilibrium_difference,
        "proof_statement": (
            "For every c>0, Qp=0 implies (cQ)p=0, while exp(cQt)x0=exp(Q(ct))x0=x(ct), "
            "so finite-time trajectories generally change. These scales are hypothetical physical-clock "
            "conversions of the same normalized model; fixed da_b=1 remains the original legitimate normalization, "
            "not a newly estimated parameter. Equilibrium scaling alone makes no general identifiability verdict."
        ),
        "additional_evidence_required": (
            "An independently supported conversion from this normalized model clock to the requested physical "
            "time unit, applicable to the same model, condition, and parameter point, with documented evidence "
            "and uncertainty; for example, independently timed dynamic measurements that calibrate that conversion."
        ),
    }


def _calibration_record(request: dict[str, Any], directory: Path) -> dict[str, Any]:
    calibration = request["calibration"]
    if not isinstance(calibration, dict) or calibration.get("evidence_kind") != "assumed":
        raise ValueError("This mission requires explicitly hypothetical, assumed calibration evidence")
    lower, upper = _pair(calibration.get("scale_per_physical_unit"), "calibration interval")
    if lower > upper:
        raise ValueError("Calibration interval is reversed")
    # Bind the caller's assumption to this current mission in the capsule's own
    # schema. Its six-file identity is never substituted for the contract's
    # five-file identity or its complete evidence identity.
    generic_identity = instrument.inventory(directory)["source_fingerprint"]
    adapted = {
        "mission_id": request["id"],
        "scope_id": request["id"],
        "type": "response",
        "quantity": "spectral_relaxation_time",
        "time_basis": "physical",
        "calibration": {
            **calibration,
            "model_fingerprint": generic_identity,
            "scope_id": request["id"],
        },
    }
    receipt = instrument.qualify(adapted, directory)
    if receipt["status"] != "qualified_conditionally":
        raise ValueError("Calibration calculation is outside instrument scope: " + receipt.get("reason", "unknown"))
    tau = float(receipt["result"]["model_value"])
    interval = [tau / upper, tau / lower]
    if not all(math.isfinite(value) and value > 0 for value in [tau, *interval]):
        raise ValueError("Relaxation interval is outside finite numerical range")
    return {
        "decision": "conditional_on_assumed_calibration",
        "calibration_evidence_id": calibration["evidence_id"],
        "calibration_evidence_kind": calibration["evidence_kind"],
        "physical_unit": calibration["physical_unit"],
        "tau_model": tau,
        "tau_physical_interval": interval,
        "calibration_is_observed": False,
        "conditional_on_supplied_fit": True,
        "relaxation_definition": "Inverse of the minimum -Re(lambda) over nonzero generator eigenvalues; an asymptotic exponential scale.",
        "interval_interpretation": (
            "Deterministic propagation of hypothetical conversion bounds in model-time units per physical unit. "
            "This is not a confidence interval, observed biological half-life, or finite-time settling guarantee."
        ),
    }


def _inheritance_record(request: dict[str, Any], directory: Path, root: Path, current: dict[str, Any]) -> dict[str, Any]:
    info = instrument.inventory(directory)  # Inventory applies beyond the linear solver's scope.
    measured = rows(directory / "measurements.tsv")
    observables = rows(directory / "observables.tsv")
    observed_times = sorted({float(row["time"]) for row in measured})
    if not observed_times or not all(math.isfinite(t) and t >= 0 for t in observed_times):
        raise ValueError("This fresh dynamic boundary requires supplied finite observation times")
    times = request["contrast_times"]
    if not isinstance(times, list) or len(times) != 2 or any(
        isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(float(t)) or t < 0 for t in times
    ):
        raise ValueError("contrast_times must contain two finite nonnegative times")
    simulations = rows(directory / "simulations.tsv")
    contrast: dict[str, float] = {}
    for observable in observables:
        name = observable["observableId"]
        values = []
        for time in times:
            matches = [float(row["simulation"]) for row in simulations
                       if row["observableId"] == name and math.isclose(float(row["time"]), float(time), rel_tol=1e-12, abs_tol=1e-12)]
            if len(matches) != 1 or not math.isfinite(matches[0]):
                raise ValueError(f"Need one finite supplied reference prediction for {name} at {time}")
            values.append(matches[0])
        contrast[name] = values[1] - values[0]
    previous = source_bindings(_source_path(root, request["inherited_source"]))
    # Read the fresh model's actual unit definition; units alone do not calibrate it.
    model = ET.parse(directory / "model.xml").getroot()
    time_units = [node for node in model.iter() if node.tag.rsplit("}", 1)[-1] == "unitDefinition" and node.get("id") == "time"]
    unit_note = ""
    if time_units:
        seconds = [node for node in time_units[0].iter() if node.tag.rsplit("}", 1)[-1] == "unit" and node.get("kind") == "second"]
        if seconds:
            unit_note = f" Its time definition includes a {seconds[0].get('multiplier', '1')}-second multiplier; that declaration alone does not establish temporal calibration."
    return {
        "decision": "fresh_dynamic_qualification_required",
        "inherited_equilibrium_witness_applicable": False,
        "full_parameter_identifiability_established": False,
        "measurement_rows": len(measured),
        "observation_times": observed_times,
        "observable_count": len(observables),
        "all_measurements_at_equilibrium": bool(info["all_measurements_at_equilibrium"]),
        "previous_source_fingerprint": previous["source_fingerprint"],
        "previous_evidence_fingerprint": previous["evidence_fingerprint"],
        "source_identity_changed": current["source_fingerprint"] != previous["source_fingerprint"],
        "finite_prediction_contrast": contrast,
        "contrast_evidence_kind": "provided_reference_simulation_not_observation",
        "reason": (
            "The fresh model and its observation map differ from H4, and measurements occur at fixed finite times. "
            "Preserving an equilibrium under common clock scaling does not automatically preserve predictions "
            "at those fixed times; the earlier equilibrium-only witness and qualification receipt cannot be imported "
            "as a current approval. The contrast is read from supplied reference simulations, not observations, "
            "a rerun, or new physical evidence. Finite-time data alone establish neither complete parameter "
            "identifiability nor physical validity. No authority transfers." + unit_note
        ),
    }


def build_packet(source_root: str | Path, requests_path: str | Path) -> dict[str, Any]:
    """Recompute all mission records from current source bytes and request values."""
    root = Path(source_root)
    request_data = json.loads(Path(requests_path).read_text(encoding="utf-8"))
    if request_data.get("packet_version") != 1 or not isinstance(request_data.get("missions"), list):
        raise ValueError("Expected version 1 portfolio with a missions list")
    records = []
    for request in request_data["missions"]:
        if not isinstance(request, dict) or not isinstance(request.get("id"), str) or not request["id"]:
            raise ValueError("Every mission requires a nonempty string id")
        directory = _source_path(root, request.get("source"))
        bindings = source_bindings(directory)
        record = {
            "id": request["id"],
            "source": request["source"],
            **bindings,
            "request_fingerprint": digest(request),
            "authority": [],
            "biological_validation": False,
        }
        kind = request.get("type")
        if kind == "stationary_qualification":
            result = _stationary_record(directory)
        elif kind == "clock_witness":
            result = _clock_record(request, directory)
        elif kind == "calibrated_relaxation":
            result = _calibration_record(request, directory)
        elif kind == "inheritance_boundary":
            result = _inheritance_record(request, directory, root, bindings)
        else:
            raise ValueError(f"Unsupported mission type: {kind}")
        record.update(result)
        # Detect a source changing during calculation instead of issuing a stale binding.
        if source_bindings(directory) != bindings:
            raise ValueError("Source evidence changed while this mission was calculated")
        records.append(record)
    packet = {"packet_version": 1, "authority": [], "missions": records}
    canonical_bytes(packet)  # Enforce finite JSON serialization before returning.
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--requests", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    packet = build_packet(args.sources, args.requests)
    args.out.write_text(json.dumps(packet, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
