# SPDX-License-Identifier: Apache-2.0
"""Protected scientific-packet acceptance, independent of retained instrument.

The H4 numerical oracle uses a generator rebuilt from source reaction identifiers,
an SVD nullspace and a Poisson-uniformization transient, rather than importing the
candidate instrument or conventional implementation. This is internal research
review, not independent external scientific validation.
"""

from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.stats import poisson

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parent / "protocol/public_case"
FILES = ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")


def h(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fp(path):
    return h({name: hashlib.sha256((path / name).read_bytes()).hexdigest() for name in FILES})


def read_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def reference(source):
    root = ET.parse(source / "model.xml").getroot()
    elements = list(root.iter())
    species = [x for x in elements if x.tag.endswith("}species")]
    names = [x.attrib["id"] for x in species]
    initial = np.array([float(x.attrib.get("initialConcentration", "0")) for x in species])
    pars = {x["parameterId"]: float(x["nominalValue"]) for x in read_rows(source / "parameters.tsv")}
    Q = np.zeros((len(names), len(names)))
    forward_count = 0
    for reaction in (x for x in elements if x.tag.endswith("}reaction")):
        reactants = next(x for x in reaction if x.tag.endswith("}listOfReactants"))
        products = next(x for x in reaction if x.tag.endswith("}listOfProducts"))
        assert len(reactants) == len(products) == 1
        a, b = reactants[0].attrib["species"], products[0].attrib["species"]
        assert float(reactants[0].attrib.get("stoichiometry", 1)) == 1
        assert float(products[0].attrib.get("stoichiometry", 1)) == 1
        rid = reaction.attrib["id"]
        if rid.startswith("r_a_"):
            rate = pars["a_" + rid[len("r_a_") :]] * pars["a_b"]
            forward_count += 1
        elif rid.startswith("r_da_"):
            rate = pars["da_b"]
        else:
            raise ValueError("Unrecognized source reaction")
        i, j = names.index(a), names.index(b)
        Q[j, i] += rate
        Q[i, i] -= rate
    assert forward_count == 32 and len(names) == 16
    _, singular, vh = np.linalg.svd(Q)
    assert singular[-1] < 1e-12 and singular[-2] > 1e-5
    p = vh[-1] / vh[-1].sum()
    eigenvalues = np.linalg.eigvals(Q)
    tau = 1 / min(-x.real for x in eigenvalues if x.real < -1e-9)
    return names, Q, initial, p, tau


def uniformized(Q, initial, t):
    rate = float(np.max(-np.diag(Q)))
    mu = rate * t
    P = np.eye(len(Q)) + Q / rate
    cutoff = int(poisson.ppf(1 - 1e-13, mu)) + 8
    term = initial.copy()
    result = np.zeros(len(Q))
    for k in range(cutoff + 1):
        result += float(poisson.pmf(k, mu)) * term
        term = P @ term
    assert abs(result.sum() - 1) < 5e-12
    return result


def close(actual, expected, label, atol=1e-7):
    a, e = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    assert a.shape == e.shape and np.all(np.isfinite(a)), label + ": shape/nonfinite"
    assert np.allclose(a, e, rtol=1e-7, atol=atol), label + ": numerical mismatch"


def check_packet(packet, requests, sources):
    assert packet.get("packet_version") == 1 and packet.get("authority") == []
    records = packet["missions"]
    assert len(records) == len(requests["missions"])
    names, Q, initial, stationary, tau = reference(sources / "h4")
    outcomes = []
    for record, req in zip(records, requests["missions"]):
        checks = []
        try:
            assert record["id"] == req["id"] and record["source"] == req["source"]
            assert record["source_fingerprint"] == fp(sources / req["source"])
            assert record["request_fingerprint"] == h(req)
            assert record["authority"] == [] and record["biological_validation"] is False
            checks.append("fresh source/request identity and no authority")
            kind = req["type"]
            if kind == "stationary_qualification":
                assert record["decision"] == "conditional_model_prediction"
                assert record["conditional_on_supplied_fit"] is True
                assert record["full_parameter_identifiability_established"] is False
                assert set(record["stationary"]) == set(names)
                values = np.array([record["stationary"][n] for n in names])
                close(values, stationary, "stationary")
                assert np.all(values >= -1e-10) and abs(values.sum() - 1) < 1e-8
                assert np.max(np.abs(Q @ values)) < 1e-7
                weights = [0 if n == "x_0ac" else 4 if n == "x_4ac" else n.count("k") for n in names]
                close(record["mean_acetylation"], stationary @ weights, "mean acetylation")
                assert record["dimension_check"] == {
                    "independent_equilibrium_mean_coordinates_at_most": 15,
                    "selected_kinetic_parameters": 8,
                    "full_superset_kinetic_parameters": 33,
                    "full_superset_rank_deficiency_at_least": 18,
                    "selected_model_identifiability": "not_decided_by_dimension_bound",
                }
                checks.extend(["conditional stationary prediction", "necessary-only dimension bound"])
            elif kind == "clock_witness":
                assert record["decision"] == "needs_clock_calibration"
                assert (
                    record["physical_time_supported"] is False
                    and record["same_equilibrium_under_clock_scaling"] is True
                )
                scales = req["alternative_clock_scales"]
                close(record["clock_scales"], scales, "clock scales")
                vectors = record["state_at_request_time"]
                assert len(vectors) == 2
                for c, vector in zip(scales, vectors):
                    assert set(vector) == set(names)
                    close(
                        [vector[n] for n in names],
                        uniformized(c * Q, initial, req["normalized_time"]),
                        "clock transient",
                    )
                assert abs(float(record["equilibrium_max_abs_difference"])) < 1e-7
                assert max(abs(vectors[0][n] - vectors[1][n]) for n in names) > 1e-3
                assert isinstance(record["proof_statement"], str) and len(record["proof_statement"]) > 30
                assert (
                    isinstance(record["additional_evidence_required"], str)
                    and len(record["additional_evidence_required"]) > 20
                )
                checks.extend(
                    [
                        "unchanged equilibrium under scaling",
                        "changed finite-time response",
                        "explicit evidence obligation",
                    ]
                )
            elif kind == "calibrated_relaxation":
                cal = req["calibration"]
                lo, hi = cal["scale_per_physical_unit"]
                assert record["decision"] == "conditional_on_assumed_calibration"
                assert record["calibration_evidence_id"] == cal["evidence_id"]
                assert record["calibration_evidence_kind"] == "assumed" and record["calibration_is_observed"] is False
                assert record["physical_unit"] == cal["physical_unit"] and record["conditional_on_supplied_fit"] is True
                close(record["tau_model"], tau, "relaxation scale")
                close(record["tau_physical_interval"], [tau / hi, tau / lo], "propagated interval")
                checks.extend(["conditional concrete timed output", "hypothetical calibration preserved"])
            elif kind == "inheritance_boundary":
                data = read_rows(sources / "boehm/measurements.tsv")
                simulations = read_rows(sources / "boehm/simulations.tsv")
                obs = sorted({r["observableId"] for r in data})
                times = sorted({float(r["time"]) for r in data})
                lookup = {(r["observableId"], float(r["time"])): float(r["simulation"]) for r in simulations}
                t0, t1 = req["contrast_times"]
                assert record["decision"] == "fresh_dynamic_qualification_required"
                assert record["inherited_equilibrium_witness_applicable"] is False
                assert record["full_parameter_identifiability_established"] is False
                assert record["measurement_rows"] == len(data) == 48
                assert record["observable_count"] == len(obs) == 3
                close(record["observation_times"], times, "observed time grid")
                assert record["all_measurements_at_equilibrium"] is False
                assert record["previous_source_fingerprint"] == fp(sources / req["inherited_source"])
                assert record["previous_source_fingerprint"] != record["source_fingerprint"]
                assert record["source_identity_changed"] is True
                assert record["contrast_evidence_kind"] == "provided_reference_simulation_not_observation"
                assert set(record["finite_prediction_contrast"]) == set(obs)
                close(
                    [record["finite_prediction_contrast"][o] for o in obs],
                    [lookup[o, t1] - lookup[o, t0] for o in obs],
                    "provided simulation contrast",
                )
                assert isinstance(record["reason"], str) and len(record["reason"]) > 30
                checks.extend(
                    [
                        "fresh finite-time observation regime",
                        "inherited scope withdrawn",
                        "reference simulation correctly labeled",
                    ]
                )
            else:
                raise AssertionError("Unknown mission")
            outcomes.append({"id": req["id"], "accepted": True, "checks": checks})
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            outcomes.append(
                {
                    "id": req["id"],
                    "accepted": False,
                    "checks_completed": checks,
                    "error": str(exc) or type(exc).__name__,
                }
            )
    return outcomes


def evaluate(submission, output):
    source_request = json.loads((PUBLIC / "requests.json").read_text())
    variants = [("declared", source_request)]
    changed = json.loads(json.dumps(source_request))
    for mission in changed["missions"]:
        mission["id"] += "-fresh-request"
        if mission["type"] == "clock_witness":
            mission["normalized_time"] = 0.875
            mission["alternative_clock_scales"] = [0.8, 2.2]
        elif mission["type"] == "calibrated_relaxation":
            mission["calibration"].update(
                evidence_id="HYPOTHETICAL-CLOCK-02", scale_per_physical_unit=[0.75, 2.5], physical_unit="second"
            )
        elif mission["type"] == "inheritance_boundary":
            mission["contrast_times"] = [20.0, 60.0]
    variants.append(("changed_requests", changed))
    all_results = []
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="s3-acceptance-") as tmp:
        work = Path(tmp)
        shutil.copytree(PUBLIC / "sources", work / "sources")
        before = {
            str(p.relative_to(work / "sources")): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (work / "sources").rglob("*")
            if p.is_file()
        }
        for name, requests in variants:
            reqpath = work / (name + ".json")
            reqpath.write_text(json.dumps(requests))
            outpath = work / (name + "-packet.json")
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(submission),
                        "--sources",
                        str(work / "sources"),
                        "--requests",
                        str(reqpath),
                        "--out",
                        str(outpath),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=False,
                    cwd=submission.parent,
                )
                if proc.returncode:
                    raise RuntimeError(f"submission exit {proc.returncode}: {proc.stderr[-3000:]}")
                packet = json.loads(outpath.read_text())
                missions = check_packet(packet, requests, work / "sources")
                all_results.append(
                    {"variant": name, "missions": missions, "stdout": proc.stdout, "stderr": proc.stderr}
                )
            except Exception as exc:
                all_results.append(
                    {
                        "variant": name,
                        "error": str(exc),
                        "missions": [{"id": r["id"], "accepted": False} for r in requests["missions"]],
                    }
                )
        after = {
            str(p.relative_to(work / "sources")): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (work / "sources").rglob("*")
            if p.is_file()
        }
    immutable = before == after
    passed = sum(all(v["missions"][i]["accepted"] for v in all_results) for i in range(4)) if immutable else 0
    result = {
        "accepted": passed == 4,
        "passed": passed,
        "total": 4,
        "source_inputs_unchanged": immutable,
        "campaigns": 1,
        "source_families": 2,
        "request_variants_per_mission": 2,
        "unit_of_inference": "one four-mission computational campaign, not eight independent opportunities",
        "variants": all_results,
        "evaluator_elapsed_seconds": time.perf_counter() - started,
        "physical_validation": False,
        "actual_cost": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.submission.resolve(), args.out)
    print(json.dumps({k: v for k, v in result.items() if k != "variants"}, indent=2))
