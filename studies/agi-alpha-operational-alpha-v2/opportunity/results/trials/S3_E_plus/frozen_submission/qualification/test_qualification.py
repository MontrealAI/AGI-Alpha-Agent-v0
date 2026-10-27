# SPDX-License-Identifier: Apache-2.0
"""Recipient-authored numerical, evidence-binding, and mission-scope probes.

These are public local development checks, not private acceptance evidence.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np
from scipy.integrate import solve_ivp

import submission as candidate

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
REQUESTS = HERE / "requests.json"


def read_table(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def raw_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def independent_h4(directory):
    """Construct rates from site-subset adjacency, not the capsule's reaction parser."""
    model = ET.parse(directory / "model.xml").getroot()
    nodes = [node for node in model.iter() if node.tag.endswith("}species")]
    names = [node.attrib["id"] for node in nodes]
    parameters = {row["parameterId"]: float(row["nominalValue"]) for row in read_table(directory / "parameters.tsv")}
    sites = [frozenset(("05", "08", "12", "16")) if name == "x_4ac" else frozenset(re.findall(r"k(\d+)", name)) for name in names]
    matrix = np.zeros((len(names), len(names)))
    for start, left in enumerate(sites):
        for end, right in enumerate(sites):
            if len(right) == len(left) + 1 and left < right:
                factor = "a_" + names[start][2:] + "_" + names[end][2:]
                matrix[end, start] = parameters["a_b"] * parameters[factor]
            elif len(right) + 1 == len(left) and right < left:
                matrix[end, start] = parameters["da_b"]
    for column in range(len(names)):
        matrix[column, column] = -matrix[:, column].sum()
    initial = np.array([float(node.get("initialConcentration", node.get("initialAmount", 0))) for node in nodes])
    return names, matrix, initial, np.array([len(site) for site in sites])


def uniformization(matrix, initial, elapsed):
    """Independent positive Poisson-series propagation of a Markov generator."""
    rate = float(max(-np.diag(matrix)))
    mean = rate * elapsed
    transition = np.eye(len(matrix)) + matrix / rate
    weight = math.exp(-mean)
    vector = initial.copy()
    answer = weight * vector
    limit = max(100, int(mean + 15 * math.sqrt(mean) + 100))
    for k in range(1, limit):
        vector = transition @ vector
        weight *= mean / k
        answer += weight * vector
    return answer


class ScientificQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = json.loads(REQUESTS.read_text())
        cls.packet = candidate.build_packet(SOURCES, REQUESTS)
        cls.names, cls.q, cls.initial, cls.counts = independent_h4(SOURCES / "h4")
        cls.records = dict(zip((r["type"] for r in cls.requests["missions"]), cls.packet["missions"]))

    def run_variant(self, data, source_root=SOURCES):
        with tempfile.TemporaryDirectory(prefix="qualification_probe_", dir=HERE) as temp:
            path = Path(temp) / "requests.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return candidate.build_packet(source_root, path)

    def assert_distribution(self, mapping):
        self.assertEqual(set(mapping), set(self.names))
        array = np.array([mapping[name] for name in self.names])
        self.assertTrue(np.isfinite(array).all())
        self.assertGreaterEqual(array.min(), -1e-12)
        self.assertAlmostEqual(float(array.sum()), 1.0, places=11)
        return array

    def test_supplied_source_and_capsule_integrity(self):
        manifest = json.loads((HERE / "SOURCE_FILES.json").read_text())
        for name, expected in manifest["files"].items():
            raw = (HERE / name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected["sha256"], name)
            self.assertEqual(len(raw), expected["bytes"], name)
        capsule = json.loads((HERE / "capability" / "manifest.json").read_text())
        for name, expected in capsule["files"].items():
            self.assertEqual(hashlib.sha256((HERE / "capability" / name).read_bytes()).hexdigest(), expected, name)

    def test_generator_against_independent_site_graph(self):
        generator = candidate.instrument.build_generator(SOURCES / "h4")
        self.assertEqual(generator["species"], self.names)
        np.testing.assert_allclose(generator["matrix"], self.q, rtol=3e-15, atol=3e-15)
        np.testing.assert_array_equal(generator["initial"], self.initial)
        np.testing.assert_allclose(self.q.sum(axis=0), 0.0, rtol=0, atol=2e-15)
        self.assertEqual(np.linalg.matrix_rank(self.q, tol=1e-10), len(self.names) - 1)
        self.assertEqual(len(self.names), 16)
        self.assertEqual(np.count_nonzero(self.q - np.diag(np.diag(self.q))), 64)

    def test_stationary_with_ode_and_residual(self):
        record = self.records["stationary_qualification"]
        stationary = self.assert_distribution(record["stationary"])
        np.testing.assert_allclose(self.q @ stationary, 0, atol=5e-14)
        reduced = self.q[:-1, :-1] - self.q[:-1, -1, None]
        spectral_tau = -1.0 / float(np.linalg.eigvals(reduced).real.max())
        integrated = solve_ivp(lambda time, x: self.q @ x, (0, 40 * spectral_tau), self.initial,
                               method="DOP853", rtol=1e-12, atol=1e-14)
        self.assertTrue(integrated.success)
        np.testing.assert_allclose(stationary, integrated.y[:, -1], rtol=3e-10, atol=3e-12)
        self.assertAlmostEqual(record["mean_acetylation"], float(self.counts @ stationary), places=13)
        self.assertEqual(record["decision"], "conditional_model_prediction")
        self.assertIs(record["conditional_on_supplied_fit"], True)
        self.assertIs(record["full_parameter_identifiability_established"], False)

    def test_dimension_derived_from_free_kinetics_and_model_space(self):
        table = read_table(SOURCES / "h4" / "parameters.tsv")
        space = read_table(SOURCES / "h4" / "model_space.tsv")
        motif_names = {name for row in space for name, value in row.items() if "estimate" in value.split(";")}
        estimated = {row["parameterId"] for row in table if row["estimate"] == "1" and row["parameterId"] != "sigma_"}
        self.assertEqual(len(motif_names), 32)
        self.assertEqual(estimated - motif_names, {"a_b"})
        fixed_da = next(row for row in table if row["parameterId"] == "da_b")
        self.assertEqual(fixed_da["estimate"], "0")
        self.assertEqual(float(fixed_da["nominalValue"]), 1.0)
        dimension = self.records["stationary_qualification"]["dimension_check"]
        self.assertEqual(dimension, {
            "independent_equilibrium_mean_coordinates_at_most": len(self.names) - 1,
            "selected_kinetic_parameters": len(estimated),
            "full_superset_kinetic_parameters": len(estimated | motif_names),
            "full_superset_rank_deficiency_at_least": len(estimated | motif_names) - len(self.names) + 1,
            "selected_model_identifiability": "not_decided_by_dimension_bound",
        })
        self.assertEqual((len(estimated), len(estimated | motif_names)), (8, 33))

    def test_clock_witness_against_uniformization(self):
        request = next(r for r in self.requests["missions"] if r["type"] == "clock_witness")
        record = self.records["clock_witness"]
        for scale, mapping in zip(request["alternative_clock_scales"], record["state_at_request_time"]):
            actual = self.assert_distribution(mapping)
            expected = uniformization(self.q, self.initial, scale * request["normalized_time"])
            np.testing.assert_allclose(actual, expected, rtol=5e-12, atol=2e-13)
        first, second = record["state_at_request_time"]
        self.assertGreater(max(abs(first[key] - second[key]) for key in first), 1e-3)
        self.assertLess(record["equilibrium_max_abs_difference"], 1e-12)
        self.assertIs(record["same_equilibrium_under_clock_scaling"], True)
        self.assertIs(record["physical_time_supported"], False)
        self.assertIn("da_b=1", record["proof_statement"])
        self.assertTrue(record["additional_evidence_required"])

    def test_calibration_with_conservation_reduced_eigenvalues(self):
        reduced = self.q[:-1, :-1] - self.q[:-1, -1, None]
        values = np.linalg.eigvals(reduced)
        self.assertTrue(np.all(values.real < 0))
        tau = -1 / float(values.real.max())
        record = self.records["calibrated_relaxation"]
        request = next(r for r in self.requests["missions"] if r["type"] == "calibrated_relaxation")
        lo, hi = request["calibration"]["scale_per_physical_unit"]
        self.assertAlmostEqual(record["tau_model"], tau, places=12)
        np.testing.assert_allclose(record["tau_physical_interval"], [tau / hi, tau / lo], rtol=3e-13)
        self.assertEqual(record["calibration_evidence_kind"], "assumed")
        self.assertFalse(record["calibration_is_observed"])
        self.assertEqual(record["physical_unit"], request["calibration"]["physical_unit"])

    def test_fresh_boundary_and_simulation_contrast(self):
        record = self.records["inheritance_boundary"]
        measurements = read_table(SOURCES / "boehm" / "measurements.tsv")
        observations = read_table(SOURCES / "boehm" / "observables.tsv")
        simulations = read_table(SOURCES / "boehm" / "simulations.tsv")
        lookup = {(r["observableId"], float(r["time"])): float(r["simulation"]) for r in simulations}
        request = next(r for r in self.requests["missions"] if r["type"] == "inheritance_boundary")
        t1, t2 = request["contrast_times"]
        expected = {r["observableId"]: lookup[r["observableId"], t2] - lookup[r["observableId"], t1] for r in observations}
        self.assertEqual(record["measurement_rows"], len(measurements))
        self.assertEqual(record["measurement_rows"], 48)
        self.assertEqual(record["observation_times"], sorted({float(r["time"]) for r in measurements}))
        self.assertEqual(record["observable_count"], 3)
        self.assertEqual(record["finite_prediction_contrast"], expected)
        self.assertFalse(record["all_measurements_at_equilibrium"])
        self.assertFalse(record["inherited_equilibrium_witness_applicable"])
        self.assertTrue(record["source_identity_changed"])
        self.assertFalse(record["full_parameter_identifiability_established"])
        self.assertEqual(record["previous_source_fingerprint"], self.records["stationary_qualification"]["source_fingerprint"])
        self.assertEqual(record["previous_evidence_fingerprint"], self.records["stationary_qualification"]["evidence_fingerprint"])
        self.assertEqual(record["contrast_evidence_kind"], "provided_reference_simulation_not_observation")
        self.assertIn("60-second", record["reason"])
        declined = candidate.instrument.qualify({"mission_id": "fresh-scope-test", "type": "clock_witness"}, SOURCES / "boehm")
        self.assertEqual(declined["status"], "scope_not_qualified")
        self.assertEqual(declined["authority"], [])

    def test_contract_hashes_cover_core_full_evidence_and_requests(self):
        for request, record in zip(self.requests["missions"], self.packet["missions"]):
            directory = SOURCES / request["source"]
            hashes = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in directory.rglob("*") if p.is_file()}
            core = {key: hashes[key] for key in ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")}
            self.assertEqual(record["source_file_hashes"], hashes)
            self.assertEqual(record["source_fingerprint"], raw_hash(core))
            self.assertEqual(record["evidence_fingerprint"], raw_hash(hashes))
            self.assertEqual(record["request_fingerprint"], raw_hash(request))
            self.assertNotEqual(record["source_fingerprint"], record["evidence_fingerprint"])
        self.assertIn("model_space.tsv", self.records["stationary_qualification"]["source_file_hashes"])
        self.assertIn("simulations.tsv", self.records["inheritance_boundary"]["source_file_hashes"])

    def test_request_variants_order_unicode_and_equal_bounds(self):
        scenarios = [
            (0.2, [0.07, 7.0], [0.03, 0.07], [0.0, 240.0]),
            (2.3, [4.0, 0.25], [3.0, 12.0], [20.0, 5.0]),
            (0.5, [1.0, 1.0], [0.75, 0.75], [5.0, 5.0]),
        ]
        for index, (time, scales, interval, contrast_times) in enumerate(scenarios):
            changed = deepcopy(self.requests)
            changed["missions"].reverse()
            for request in changed["missions"]:
                request["id"] = "variant-\u03bc-" + str(index) + "-" + request["type"]
                if request["type"] == "clock_witness":
                    request["normalized_time"] = time
                    request["alternative_clock_scales"] = scales
                elif request["type"] == "calibrated_relaxation":
                    request["calibration"].update(scale_per_physical_unit=interval, evidence_id="hypothesis-\u03b1-" + str(index), physical_unit="hour")
                elif request["type"] == "inheritance_boundary":
                    request["contrast_times"] = contrast_times
            packet = self.run_variant(changed)
            self.assertEqual([r["id"] for r in packet["missions"]], [r["id"] for r in changed["missions"]])
            for request, record in zip(changed["missions"], packet["missions"]):
                self.assertEqual(record["request_fingerprint"], raw_hash(request))
                if request["type"] == "clock_witness":
                    self.assertEqual(record["clock_scales"], scales)
                    for scale, mapping in zip(scales, record["state_at_request_time"]):
                        np.testing.assert_allclose(self.assert_distribution(mapping), uniformization(self.q, self.initial, scale * time), atol=3e-13, rtol=2e-11)
                elif request["type"] == "calibrated_relaxation":
                    tau = record["tau_model"]
                    np.testing.assert_allclose(record["tau_physical_interval"], [tau / interval[1], tau / interval[0]], rtol=1e-13)
                    self.assertEqual(record["calibration_evidence_id"], request["calibration"]["evidence_id"])
                    self.assertEqual(record["physical_unit"], "hour")
                elif request["type"] == "inheritance_boundary":
                    simulation = read_table(SOURCES / "boehm" / "simulations.tsv")
                    table = {(r["observableId"], float(r["time"])): float(r["simulation"]) for r in simulation}
                    for observable, difference in record["finite_prediction_contrast"].items():
                        self.assertEqual(difference, table[observable, contrast_times[1]] - table[observable, contrast_times[0]])

    def test_repeat_calls_and_caller_mutation(self):
        first = candidate.build_packet(SOURCES, REQUESTS)
        second = candidate.build_packet(SOURCES, REQUESTS)
        self.assertEqual(first, second)
        first["missions"][0]["authority"].append("not-authorized")
        first["missions"][0]["stationary"][self.names[0]] = -1
        third = candidate.build_packet(SOURCES, REQUESTS)
        self.assertEqual(second, third)
        json.dumps(third, allow_nan=False)
        for record in third["missions"]:
            self.assertEqual(record["authority"], [])
            self.assertIs(record["biological_validation"], False)

    def test_recompute_source_and_recursive_evidence_on_temporary_copies(self):
        # Original supplied files are never modified. Copies exercise current-byte
        # source binding, including nested extra evidence, and nominal replay.
        with tempfile.TemporaryDirectory(prefix="qualification_source_probe_", dir=HERE) as temp:
            root = Path(temp) / "sources"
            shutil.copytree(SOURCES, root)
            added = root / "h4" / "notes" / "extra.txt"
            added.parent.mkdir()
            added.write_text("Additional supplied context for a binding probe.\n")
            extra_packet = candidate.build_packet(root, REQUESTS)
            base = self.packet["missions"][0]
            extra = extra_packet["missions"][0]
            self.assertEqual(base["source_fingerprint"], extra["source_fingerprint"])
            self.assertNotEqual(base["evidence_fingerprint"], extra["evidence_fingerprint"])
            self.assertIn("notes/extra.txt", extra["source_file_hashes"])
            parameter_file = root / "h4" / "parameters.tsv"
            table = read_table(parameter_file)
            for row in table:
                if row["parameterId"] == "a_b":
                    row["nominalValue"] = str(float(row["nominalValue"]) * 1.25)
            with parameter_file.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(table[0]), delimiter="\t")
                writer.writeheader()
                writer.writerows(table)
            changed = candidate.build_packet(root, REQUESTS)["missions"][0]
            self.assertNotEqual(base["source_fingerprint"], changed["source_fingerprint"])
            self.assertNotEqual(base["stationary"], changed["stationary"])
            names, matrix, _, _ = independent_h4(root / "h4")
            np.testing.assert_allclose(matrix @ np.array([changed["stationary"][name] for name in names]), 0, atol=1e-13)
        self.test_supplied_source_and_capsule_integrity()

    def test_invalid_clock_and_calibration_requests_fail_without_source_mutation(self):
        for value in (0, -1, math.inf, math.nan, True):
            changed = deepcopy(self.requests)
            clock = next(r for r in changed["missions"] if r["type"] == "clock_witness")
            clock["alternative_clock_scales"][0] = value
            with self.assertRaises(ValueError):
                self.run_variant(changed)
        for lower, upper in ((2, 1), (0, 1), (-1, 2)):
            changed = deepcopy(self.requests)
            calibration = next(r for r in changed["missions"] if r["type"] == "calibrated_relaxation")["calibration"]
            calibration["scale_per_physical_unit"] = [lower, upper]
            with self.assertRaises(ValueError):
                self.run_variant(changed)
        self.test_supplied_source_and_capsule_integrity()


if __name__ == "__main__":
    unittest.main(verbosity=2)
