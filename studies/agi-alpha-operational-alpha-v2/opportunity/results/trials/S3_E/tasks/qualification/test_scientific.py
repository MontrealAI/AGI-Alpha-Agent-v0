"""Independent mathematical and contract regression probes for this campaign."""
import copy
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
from numpy.testing import assert_allclose
from scipy.integrate import solve_ivp
from scipy.linalg import expm

import submission

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
REQUESTS = ROOT / "requests.json"


def read_table(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def canonical_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def independent_hypercube(source=SOURCES / "h4"):
    """Derive edges from site subsets and motif IDs, independently of SBML laws."""
    species = ET.parse(source / "model.xml").findall("{*}model/{*}listOfSpecies/{*}species")
    ids = [s.attrib["id"] for s in species]
    all_sites = frozenset(re.findall(r"k\d+", "".join(ids)))
    sites = {name: (all_sites if name == "x_4ac" else frozenset(re.findall(r"k\d+", name))) for name in ids}
    index = {name: i for i, name in enumerate(ids)}
    by_sites = {value: key for key, value in sites.items()}
    values = {r["parameterId"]: float(r["nominalValue"]) for r in read_table(source / "parameters.tsv")}
    Q = np.zeros((len(ids), len(ids)))
    for low in ids:
        for site in all_sites - sites[low]:
            high = by_sites[sites[low] | {site}]
            rate = values["a_b"] * values[f"a_{low[2:]}_{high[2:]}"]
            i, j = index[low], index[high]
            Q[j, i] += rate
            Q[i, i] -= rate
            Q[i, j] += values["da_b"]
            Q[j, j] -= values["da_b"]
    x0 = np.array([float(s.attrib["initialConcentration"]) for s in species])
    return ids, Q, x0


def tree_stationary(Q):
    """Directed matrix-tree cofactors supply a solve-independent stationary law."""
    logs = []
    for omit in range(len(Q)):
        minor = np.delete(np.delete(-Q, omit, axis=0), omit, axis=1)
        sign, logdet = np.linalg.slogdet(minor)
        if sign <= 0:
            raise AssertionError("Expected positive rooted-tree weight")
        logs.append(logdet)
    weights = np.exp(np.array(logs) - max(logs))
    return weights / weights.sum()


class ScientificContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = json.loads(REQUESTS.read_text())
        cls.packet = submission.build_packet(SOURCES, REQUESTS)
        cls.ids, cls.Q, cls.x0 = independent_hypercube()

    def make_packet(self, payload, source_root=SOURCES):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="qualification_test_") as temp:
            path = Path(temp) / "variant.json"
            path.write_text(json.dumps(payload, allow_nan=False))
            return submission.build_packet(source_root, path)

    def vector(self, state):
        self.assertEqual(set(state), set(self.ids))
        return np.array([state[name] for name in self.ids])

    def test_supplied_source_bytes_match_manifest(self):
        manifest = json.loads((ROOT / "SOURCE_FILES.json").read_text())
        for name, record in manifest["files"].items():
            data = (ROOT / name).read_bytes()
            self.assertEqual(len(data), record["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])

    def test_source_and_request_identities(self):
        for request, record in zip(self.requests["missions"], self.packet["missions"]):
            source = SOURCES / request["source"]
            hashes = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source.rglob("*") if p.is_file()}
            core = {name: hashes[name] for name in ("model.xml", "parameters.tsv", "measurements.tsv", "observables.tsv", "conditions.tsv")}
            self.assertEqual(record["source_file_hashes"], hashes)
            self.assertEqual(record["source_fingerprint"], canonical_hash(core))
            self.assertEqual(record["evidence_fingerprint"], canonical_hash(hashes))
            self.assertEqual(record["request_fingerprint"], canonical_hash(request))
            self.assertEqual(record["authority"], [])
            self.assertIs(record["biological_validation"], False)
        self.assertIn("model_space.tsv", self.packet["missions"][0]["source_file_hashes"])
        self.assertIn("simulations.tsv", self.packet["missions"][3]["source_file_hashes"])

    def test_generator_against_independent_site_network(self):
        ids, Q, x0, dimensions, equilibrium = submission._h4_model(SOURCES / "h4")
        self.assertEqual(ids, self.ids)
        assert_allclose(Q, self.Q, atol=2e-15, rtol=2e-15)
        assert_allclose(x0, self.x0, atol=0, rtol=0)
        assert_allclose(np.ones(len(ids)) @ Q, 0, atol=1e-14)
        self.assertTrue(equilibrium)
        self.assertEqual(np.count_nonzero(Q - np.diag(np.diag(Q))), 64)
        self.assertEqual(dimensions, {"independent_equilibrium_mean_coordinates_at_most": 15,
                                     "selected_kinetic_parameters": 8,
                                     "full_superset_kinetic_parameters": 33,
                                     "full_superset_rank_deficiency_at_least": 18,
                                     "selected_model_identifiability": "not_decided_by_dimension_bound"})

    def test_stationary_against_matrix_tree_theorem(self):
        record = self.packet["missions"][0]
        p = self.vector(record["stationary"])
        assert_allclose(p, tree_stationary(self.Q), rtol=2e-12, atol=2e-13)
        assert_allclose(self.Q @ p, 0, atol=1e-13)
        self.assertAlmostEqual(float(p.sum()), 1, places=14)
        self.assertTrue(np.all(p >= 0))
        counts = [4 if s == "x_4ac" else len(re.findall(r"k\d+", s)) for s in self.ids]
        self.assertAlmostEqual(record["mean_acetylation"], float(p @ counts), places=13)
        self.assertEqual(record["decision"], "conditional_model_prediction")
        self.assertFalse(record["full_parameter_identifiability_established"])

    def test_clock_witness_against_ode_integration(self):
        record = self.packet["missions"][1]
        request = self.requests["missions"][1]
        p = tree_stationary(self.Q)
        vectors = []
        for scale, state in zip(request["alternative_clock_scales"], record["state_at_request_time"]):
            end = float(scale) * request["normalized_time"]
            solution = solve_ivp(lambda t, y: self.Q @ y, (0, end), self.x0,
                                 method="DOP853", rtol=2e-12, atol=1e-14)
            self.assertTrue(solution.success)
            vector = self.vector(state)
            assert_allclose(vector, solution.y[:, -1], atol=3e-12, rtol=3e-11)
            assert_allclose((scale * self.Q) @ p, 0, atol=2e-13)
            self.assertAlmostEqual(float(vector.sum()), 1, places=13)
            self.assertTrue(np.all(vector >= 0))
            vectors.append(vector)
        self.assertGreater(float(np.max(np.abs(vectors[0] - vectors[1]))), 0.01)
        self.assertLess(record["equilibrium_max_abs_difference"], 1e-12)
        self.assertEqual(record["decision"], "needs_clock_calibration")
        self.assertFalse(record["physical_time_supported"])
        self.assertIn("da_b=1", record["proof_statement"])

    def test_spectral_scale_by_transition_eigenvalues(self):
        # The spectrum of exp(Q*dt) maps each generator eigenvalue to exp(lambda*dt).
        # Small dt avoids aliasing of complex modes; the second-largest modulus
        # determines the slowest asymptotic real decay independently of eig(Q).
        dt = 0.2
        multipliers = sorted(np.abs(np.linalg.eigvals(expm(self.Q * dt))), reverse=True)
        independent_tau = -dt / math.log(float(multipliers[1]))
        record = self.packet["missions"][2]
        self.assertAlmostEqual(record["tau_model"], independent_tau, places=11)
        lo, hi = self.requests["missions"][2]["calibration"]["scale_per_physical_unit"]
        assert_allclose(record["tau_physical_interval"], [independent_tau / hi, independent_tau / lo], rtol=1e-11)
        self.assertFalse(record["calibration_is_observed"])
        self.assertEqual(record["calibration_evidence_kind"], "assumed")
        self.assertEqual(record["decision"], "conditional_on_assumed_calibration")

    def test_fresh_dynamic_evidence(self):
        record = self.packet["missions"][3]
        data = read_table(SOURCES / "boehm" / "measurements.tsv")
        sim = read_table(SOURCES / "boehm" / "simulations.tsv")
        first, second = self.requests["missions"][3]["contrast_times"]
        self.assertEqual(record["measurement_rows"], len(data))
        self.assertEqual(record["observation_times"], sorted({float(r["time"]) for r in data}))
        self.assertEqual(record["observable_count"], 3)
        self.assertFalse(record["all_measurements_at_equilibrium"])
        for observable, difference in record["finite_prediction_contrast"].items():
            lookup = {float(r["time"]): float(r["simulation"]) for r in sim if r["observableId"] == observable}
            self.assertAlmostEqual(difference, lookup[second] - lookup[first], places=12)
        self.assertEqual(record["previous_source_fingerprint"], self.packet["missions"][0]["source_fingerprint"])
        self.assertEqual(record["previous_evidence_fingerprint"], self.packet["missions"][0]["evidence_fingerprint"])
        self.assertTrue(record["source_identity_changed"])
        self.assertFalse(record["inherited_equilibrium_witness_applicable"])
        self.assertFalse(record["full_parameter_identifiability_established"])
        self.assertEqual(record["contrast_evidence_kind"], "provided_reference_simulation_not_observation")

    def test_request_variants_and_order(self):
        variants = [(0.001, [0.03, 2.1], [0.25, 2.5], [0.0, 2.5]),
                    (2.7, [0.2, 4.0], [3.0, 3.0], [20.0, 80.0]),
                    (0.8, [1.1, 1.1], [0.007, 0.08], [240.0, 10.0])]
        for number, (time, scales, bounds, contrasts) in enumerate(variants):
            payload = copy.deepcopy(self.requests)
            for i, request in enumerate(payload["missions"]):
                request["id"] = f"variant-{number}-{i}"
            payload["missions"][1].update(normalized_time=time, alternative_clock_scales=scales)
            payload["missions"][2]["calibration"].update(scale_per_physical_unit=bounds,
                    evidence_id=f"ASSUMED-{number}", physical_unit="hour")
            payload["missions"][3]["contrast_times"] = contrasts
            payload["missions"] = payload["missions"][::-1]
            packet = self.make_packet(payload)
            self.assertEqual([r["id"] for r in packet["missions"]], [r["id"] for r in payload["missions"]])
            records = dict(zip([r["type"] for r in payload["missions"]], packet["missions"]))
            clock = records["clock_witness"]
            for scale, state in zip(scales, clock["state_at_request_time"]):
                solution = solve_ivp(lambda t, y: self.Q @ y, (0, time * scale), self.x0,
                                     method="DOP853", rtol=1e-11, atol=1e-13)
                assert_allclose(self.vector(state), solution.y[:, -1], rtol=1e-9, atol=2e-11)
            calibration = records["calibrated_relaxation"]
            tau = self.packet["missions"][2]["tau_model"]
            assert_allclose(calibration["tau_physical_interval"], [tau / bounds[1], tau / bounds[0]], rtol=1e-13)
            self.assertEqual(calibration["calibration_evidence_id"], f"ASSUMED-{number}")
            self.assertEqual(calibration["physical_unit"], "hour")
            for request, record in zip(payload["missions"], packet["missions"]):
                self.assertEqual(record["request_fingerprint"], canonical_hash(request))
            if scales[0] == scales[1]:
                self.assertEqual(clock["state_at_request_time"][0], clock["state_at_request_time"][1])

    def test_retries_changed_intent_and_return_mutation(self):
        first = submission.build_packet(SOURCES, REQUESTS)
        self.assertEqual(first, submission.build_packet(SOURCES, REQUESTS))
        first["missions"][0]["stationary"][self.ids[0]] = -999
        first["missions"][0]["source_file_hashes"].clear()
        self.assertEqual(self.packet, submission.build_packet(SOURCES, REQUESTS))
        changed = copy.deepcopy(self.requests)
        changed["missions"][1]["normalized_time"] *= 2
        packet = self.make_packet(changed)
        self.assertEqual(packet["missions"][1]["id"], self.packet["missions"][1]["id"])
        self.assertNotEqual(packet["missions"][1]["request_fingerprint"], self.packet["missions"][1]["request_fingerprint"])
        self.assertNotEqual(packet["missions"][1]["state_at_request_time"], self.packet["missions"][1]["state_at_request_time"])

    def test_evidence_change_without_core_change_in_owned_copy(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="qualification_test_") as temp:
            copied = Path(temp) / "sources"
            shutil.copytree(SOURCES, copied)
            extra = copied / "h4" / "audit" / "provenance.txt"
            extra.parent.mkdir()
            extra.write_text("Synthetic test-only evidence attachment.\n")
            packet = submission.build_packet(copied, REQUESTS)
            original = self.packet["missions"][0]
            revised = packet["missions"][0]
            self.assertEqual(original["source_fingerprint"], revised["source_fingerprint"])
            self.assertNotEqual(original["evidence_fingerprint"], revised["evidence_fingerprint"])
            self.assertIn("audit/provenance.txt", revised["source_file_hashes"])
            self.assertEqual(packet["missions"][3]["previous_evidence_fingerprint"], revised["evidence_fingerprint"])

    def test_nominal_value_recomputed_in_owned_copy(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="qualification_test_") as temp:
            copied = Path(temp) / "sources"
            shutil.copytree(SOURCES, copied)
            path = copied / "h4" / "parameters.tsv"
            rows = read_table(path)
            for row in rows:
                if row["parameterId"] == "a_b":
                    row["nominalValue"] = str(1.5 * float(row["nominalValue"]))
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            packet = submission.build_packet(copied, REQUESTS)
            _, Q, _ = independent_hypercube(copied / "h4")
            assert_allclose(self.vector(packet["missions"][0]["stationary"]), tree_stationary(Q), rtol=1e-11, atol=1e-12)
            self.assertNotEqual(packet["missions"][0]["source_fingerprint"], self.packet["missions"][0]["source_fingerprint"])
            self.assertNotEqual(packet["missions"][0]["mean_acetylation"], self.packet["missions"][0]["mean_acetylation"])

    def test_invalid_request_does_not_replace_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="qualification_test_") as temp:
            request_path, output = Path(temp) / "invalid.json", Path(temp) / "out.json"
            invalid = copy.deepcopy(self.requests)
            invalid["missions"][2]["calibration"]["scale_per_physical_unit"] = [0.0, 1.0]
            request_path.write_text(json.dumps(invalid))
            output.write_bytes(b"previous result")
            with self.assertRaises(ValueError):
                submission.main(["--sources", str(SOURCES), "--requests", str(request_path), "--out", str(output)])
            self.assertEqual(output.read_bytes(), b"previous result")
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ["invalid.json", "out.json"])

    def test_missing_reference_contrast_is_not_interpolated(self):
        payload = copy.deepcopy(self.requests)
        payload["missions"][3]["contrast_times"] = [3.14159, 10]
        with self.assertRaisesRegex(ValueError, "provided simulation"):
            self.make_packet(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
