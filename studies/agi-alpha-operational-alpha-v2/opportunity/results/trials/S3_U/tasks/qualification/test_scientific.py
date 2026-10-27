"""Scientific and provenance checks independent of the interface smoke test.

All fixtures are constructed from the supplied files, never private answers.
Temporary request variants stay inside the qualification directory.
"""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from submission import build_packet, _load_h4

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
CORE = ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")


def read_table(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def independent_generator():
    """Build the four-site graph from nominal motif names, independently of MathML."""
    species = [s.attrib["id"] for s in ET.parse(SOURCES / "h4/model.xml").getroot().findall(
        ".//{*}listOfSpecies/{*}species")]
    values = {r["parameterId"]: float(r["nominalValue"])
              for r in read_table(SOURCES / "h4/parameters.tsv")}
    q = np.zeros((len(species), len(species)))
    edges = 0
    for name, value in values.items():
        fields = name.split("_")
        if len(fields) == 3 and fields[0] == "a":
            i, j = species.index("x_" + fields[1]), species.index("x_" + fields[2])
            forward, backward = value * values["a_b"], values["da_b"]
            q[j, i] += forward
            q[i, i] -= forward
            q[i, j] += backward
            q[j, j] -= backward
            edges += 1
    if edges != 32:
        raise AssertionError(f"Expected all 32 source motif edges, got {edges}")
    x0 = np.zeros(len(species))
    x0[species.index("x_0ac")] = 1.0
    return species, q, x0


def uniformization(q, x0, time):
    """Positive Poisson series for exp(Q t)x0; independent of scipy.linalg.expm."""
    rate = float(np.max(-np.diag(q)))
    transition = np.eye(len(q)) + q / rate
    mu = rate * time
    weight = math.exp(-mu)
    term = x0.copy()
    result = weight * term
    for k in range(1, 10000):
        term = transition @ term
        weight *= mu / k
        result += weight * term
        if k > mu + 20 * math.sqrt(max(1.0, mu)) and weight < 1e-17:
            return result
    raise AssertionError("Uniformization did not converge")


class ScientificQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = json.loads((HERE / "requests.json").read_text())
        cls.immutable_paths = [HERE / "requests.json", HERE / "BRIEF.md", HERE / "test_public.py",
                               HERE / "SOURCE_FILES.json"] + [
            p for p in SOURCES.rglob("*") if p.is_file()]
        cls.before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.immutable_paths}
        cls.packet = build_packet(SOURCES, HERE / "requests.json")
        cls.records = {m["type"]: m for m in cls.packet["missions"]}
        cls.species, cls.q, cls.x0 = independent_generator()

    @classmethod
    def tearDownClass(cls):
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.immutable_paths}
        if after != cls.before:
            raise AssertionError("An immutable input changed during verification")

    def test_source_manifest_unchanged(self):
        manifest = json.loads((HERE / "SOURCE_FILES.json").read_text())["files"]
        for name, expected in manifest.items():
            data = (HERE / name).read_bytes()
            self.assertEqual(len(data), expected["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected["sha256"])

    def test_complete_bindings_and_decisions(self):
        self.assertEqual(self.packet["packet_version"], 1)
        self.assertEqual(self.packet["authority"], [])
        self.assertEqual([m["id"] for m in self.packet["missions"]],
                         [r["id"] for r in self.requests["missions"]])
        decisions = ["conditional_model_prediction", "needs_clock_calibration",
                     "conditional_on_assumed_calibration", "fresh_dynamic_qualification_required"]
        for request, record, decision in zip(self.requests["missions"], self.packet["missions"], decisions):
            self.assertEqual(record["decision"], decision)
            self.assertEqual(record["authority"], [])
            self.assertIs(record["biological_validation"], False)
            self.assertEqual(record["request_fingerprint"], digest(request))
            directory = SOURCES / request["source"]
            hashes = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in directory.rglob("*") if p.is_file()}
            self.assertEqual(record["source_file_hashes"], hashes)
            self.assertEqual(record["source_fingerprint"], digest({p: hashes[p] for p in CORE}))
            self.assertEqual(record["evidence_fingerprint"], digest(hashes))
            self.assertNotEqual(record["source_fingerprint"], record["evidence_fingerprint"])
        json.dumps(self.packet, allow_nan=False)

    def test_generator_and_initial_state(self):
        parsed = _load_h4(SOURCES / "h4")
        self.assertEqual(parsed["species"], self.species)
        np.testing.assert_allclose(parsed["Q"], self.q, rtol=0, atol=1e-15)
        np.testing.assert_array_equal(parsed["x0"], self.x0)
        self.assertEqual(parsed["reaction_count"], 64)
        np.testing.assert_allclose(self.q.sum(axis=0), 0, atol=1e-14)
        self.assertTrue(np.all((self.q - np.diag(np.diag(self.q))) >= 0))
        self.assertEqual(np.linalg.matrix_rank(self.q), len(self.species) - 1)

    def test_stationary_by_independent_nullspace(self):
        record = self.records["stationary_qualification"]
        _, singular_values, vectors = np.linalg.svd(self.q)
        expected = vectors[-1] / vectors[-1].sum()
        actual = np.array([record["stationary"][s] for s in self.species])
        self.assertLess(singular_values[-1], 1e-13)
        self.assertGreater(singular_values[-2], 1e-4)
        np.testing.assert_allclose(actual, expected, atol=1e-13, rtol=1e-12)
        np.testing.assert_allclose(self.q @ actual, 0, atol=1e-13)
        self.assertAlmostEqual(float(actual.sum()), 1.0, places=14)
        self.assertTrue(np.all(actual >= 0))
        counts = [0 if s == "x_0ac" else 4 if s == "x_4ac" else s.count("k") for s in self.species]
        self.assertAlmostEqual(record["mean_acetylation"], float(actual @ counts), places=14)
        self.assertIs(record["conditional_on_supplied_fit"], True)
        self.assertIs(record["full_parameter_identifiability_established"], False)

    def test_dimension_uses_model_space_and_estimated_kinetics(self):
        check = self.records["stationary_qualification"]["dimension_check"]
        parameters = read_table(SOURCES / "h4/parameters.tsv")
        selected = [r for r in parameters if r["estimate"] == "1" and r["parameterId"].startswith("a_")]
        space = read_table(SOURCES / "h4/model_space.tsv")
        motifs = [name for name, value in space[0].items() if "estimate" in value.split(";")]
        coordinates = len(self.species) - 1
        self.assertEqual(check["selected_kinetic_parameters"], len(selected))
        self.assertEqual(check["independent_equilibrium_mean_coordinates_at_most"], coordinates)
        self.assertEqual(check["full_superset_kinetic_parameters"], len(motifs) + 1)
        self.assertEqual(check["full_superset_rank_deficiency_at_least"], len(motifs) + 1 - coordinates)
        self.assertEqual(check["selected_model_identifiability"], "not_decided_by_dimension_bound")
        self.assertEqual((coordinates, len(selected), len(motifs) + 1), (15, 8, 33))

    def test_clock_by_uniformization(self):
        request = self.requests["missions"][1]
        record = self.records["clock_witness"]
        for scale, state in zip(request["alternative_clock_scales"], record["state_at_request_time"]):
            expected = uniformization(self.q, self.x0, scale * request["normalized_time"])
            actual = [state[s] for s in self.species]
            np.testing.assert_allclose(actual, expected, atol=2e-13, rtol=2e-12)
            self.assertAlmostEqual(sum(actual), 1.0, places=14)
            self.assertGreaterEqual(min(actual), 0)
        a, b = record["state_at_request_time"]
        self.assertGreater(max(abs(a[s] - b[s]) for s in self.species), 0.1)
        self.assertLess(record["equilibrium_max_abs_difference"], 1e-12)
        self.assertIs(record["physical_time_supported"], False)
        self.assertIn("da_b=1", record["proof_statement"])
        self.assertTrue(record["additional_evidence_required"])

    def test_spectral_scale_from_conservation_reduction(self):
        # On sum(dx)=0, eliminate the last coordinate to remove the zero mode.
        reduced = self.q[:-1, :-1] - self.q[:-1, -1, None]
        eigenvalues = np.linalg.eigvals(reduced)
        self.assertTrue(np.all(eigenvalues.real < 0))
        tau = 1 / min(-eigenvalues.real)
        record = self.records["calibrated_relaxation"]
        np.testing.assert_allclose(record["tau_model"], tau, atol=1e-12, rtol=1e-12)
        lo, hi = self.requests["missions"][2]["calibration"]["scale_per_physical_unit"]
        np.testing.assert_allclose(record["tau_physical_interval"], [tau / hi, tau / lo], rtol=1e-12)
        self.assertIs(record["calibration_is_observed"], False)
        self.assertEqual(record["calibration_evidence_kind"], "assumed")

    def test_fresh_dynamic_boundary_and_reference_contrast(self):
        record = self.records["inheritance_boundary"]
        measured = read_table(SOURCES / "boehm/measurements.tsv")
        simulated = read_table(SOURCES / "boehm/simulations.tsv")
        observations = read_table(SOURCES / "boehm/observables.tsv")
        self.assertEqual(record["measurement_rows"], len(measured))
        self.assertEqual(record["observation_times"], sorted(set(float(r["time"]) for r in measured)))
        self.assertEqual(record["observable_count"], len(observations))
        self.assertIs(record["all_measurements_at_equilibrium"], False)
        self.assertIs(record["source_identity_changed"], True)
        self.assertIs(record["inherited_equilibrium_witness_applicable"], False)
        previous = self.records["stationary_qualification"]
        self.assertEqual(record["previous_source_fingerprint"], previous["source_fingerprint"])
        self.assertEqual(record["previous_evidence_fingerprint"], previous["evidence_fingerprint"])
        t0, t1 = self.requests["missions"][3]["contrast_times"]
        lookup = {(r["observableId"], float(r["time"])): float(r["simulation"]) for r in simulated}
        for row in observations:
            name = row["observableId"]
            self.assertEqual(record["finite_prediction_contrast"][name], lookup[name, t1] - lookup[name, t0])
        self.assertEqual(record["contrast_evidence_kind"], "provided_reference_simulation_not_observation")
        self.assertIs(record["full_parameter_identifiability_established"], False)

    def test_changed_request_ids_numbers_units_order_and_contrast(self):
        cases = [
            (0.025, [0.08, 0.6], [0.001, 10], [0, 2.5], "second"),
            (0.7, [3.7, 0.02], [0.8, 0.8], [240, 80], "hour"),
            (4.0, [2.0, 2.0], [2, 8], [15, 120], "day"),
            (10.0, [0.05, 0.15], [1e-4, 1e4], [5, 5], "minute"),
        ]
        simulations = read_table(SOURCES / "boehm/simulations.tsv")
        lookup = {(r["observableId"], float(r["time"])): float(r["simulation"]) for r in simulations}
        baseline_tau = self.records["calibrated_relaxation"]["tau_model"]
        with tempfile.TemporaryDirectory(prefix="request_variants_", dir=HERE) as temporary:
            path = Path(temporary) / "requests.json"
            for i, (time, scales, bounds, contrasts, unit) in enumerate(cases):
                variant = copy.deepcopy(self.requests)
                for request in variant["missions"]:
                    request["id"] = f"variant_{i}_{request['type']}"
                variant["missions"][1].update(normalized_time=time, alternative_clock_scales=scales)
                variant["missions"][2]["calibration"].update(
                    evidence_id=f"ASSUMED-variant-{i}-\u03b1", scale_per_physical_unit=bounds, physical_unit=unit)
                variant["missions"][3]["contrast_times"] = contrasts
                variant["missions"].reverse()
                path.write_text(json.dumps(variant))
                packet = build_packet(SOURCES, path)
                self.assertEqual([m["id"] for m in packet["missions"]], [r["id"] for r in variant["missions"]])
                for request, record in zip(variant["missions"], packet["missions"]):
                    self.assertEqual(record["request_fingerprint"], digest(request))
                    self.assertNotEqual(record["request_fingerprint"], self.records[record["type"]]["request_fingerprint"])
                    self.assertEqual(record["evidence_fingerprint"], self.records[record["type"]]["evidence_fingerprint"])
                records = {m["type"]: m for m in packet["missions"]}
                for scale, state in zip(scales, records["clock_witness"]["state_at_request_time"]):
                    np.testing.assert_allclose([state[s] for s in self.species],
                                               uniformization(self.q, self.x0, scale * time), atol=3e-13, rtol=3e-12)
                calibrated = records["calibrated_relaxation"]
                np.testing.assert_allclose(calibrated["tau_physical_interval"],
                                           [baseline_tau / bounds[1], baseline_tau / bounds[0]], rtol=1e-12)
                self.assertEqual(calibrated["physical_unit"], unit)
                self.assertEqual(calibrated["calibration_evidence_id"], f"ASSUMED-variant-{i}-\u03b1")
                for observable, contrast in records["inheritance_boundary"]["finite_prediction_contrast"].items():
                    self.assertEqual(contrast, lookup[observable, contrasts[1]] - lookup[observable, contrasts[0]])

    def test_out_of_contract_inputs_are_explicitly_rejected(self):
        with tempfile.TemporaryDirectory(prefix="invalid_requests_", dir=HERE) as temporary:
            path = Path(temporary) / "requests.json"
            for invalid in (0, -1, math.inf):
                request = copy.deepcopy(self.requests["missions"][1])
                request["alternative_clock_scales"][0] = invalid
                path.write_text(json.dumps({"missions": [request]}))
                with self.assertRaises(ValueError):
                    build_packet(SOURCES, path)
            for bounds in ([2, 1], [0, 1]):
                request = copy.deepcopy(self.requests["missions"][2])
                request["calibration"]["scale_per_physical_unit"] = bounds
                path.write_text(json.dumps({"missions": [request]}))
                with self.assertRaises(ValueError):
                    build_packet(SOURCES, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
