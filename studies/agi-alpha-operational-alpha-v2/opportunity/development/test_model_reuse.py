# SPDX-License-Identifier: Apache-2.0
"""Development checks, including a separately formulated H4 transition oracle.

These tests are researcher-authored development evidence, not the protected
confirmation evaluator and not independent biological validation.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "instrument"))
import model_reuse as instrument

SOURCE = ROOT / "discovery/science/source_checkout/petab_select/test_cases/0009/petab"


def oracle() -> tuple[list[str], np.ndarray, np.ndarray]:
    """Use motif bitsets and documented reaction rules, not kinetic-law parsing."""
    with (SOURCE / "parameters.tsv").open() as handle:
        parameters = {row["parameterId"]: float(row["nominalValue"]) for row in csv.DictReader(handle, delimiter="\t")}
    motifs = [
        "0ac",
        "k05",
        "k08",
        "k12",
        "k16",
        "k05k08",
        "k05k12",
        "k05k16",
        "k08k12",
        "k08k16",
        "k12k16",
        "k05k08k12",
        "k05k08k16",
        "k05k12k16",
        "k08k12k16",
        "4ac",
    ]
    bits = [
        set() if motif == "0ac" else ({"05", "08", "12", "16"} if motif == "4ac" else set(re.findall(r"k(\d+)", motif)))
        for motif in motifs
    ]
    q = np.zeros((16, 16))
    for i, first in enumerate(bits):
        for j, second in enumerate(bits):
            if len(first ^ second) != 1:
                continue
            if len(second) > len(first):
                rate = parameters[f"a_{motifs[i]}_{motifs[j]}"] * parameters["a_b"]
            else:
                rate = parameters["da_b"]
            q[j, i] += rate
            q[i, i] -= rate
    initial = np.zeros(16)
    initial[0] = 1
    return ["x_" + motif for motif in motifs], q, initial


class ModelReuseDevelopment(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.case = Path(self.temporary.name) / "case"
        shutil.copytree(SOURCE.parent, self.case)
        self.path = self.case / "petab"
        self.identity = instrument.inventory(self.path)["source_fingerprint"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def calibration(self) -> dict:
        return {
            "model_fingerprint": self.identity,
            "scope_id": "research-only",
            "scale_per_physical_unit": [0.7, 1.9],
            "physical_unit": "minute",
            "evidence_kind": "assumed",
            "evidence_id": "development-hypothesis-no-physical-measurement",
        }

    def test_inventory_matches_actual_source(self) -> None:
        result = instrument.inventory(self.path)
        self.assertEqual((result["species_count"], result["reaction_count"], result["measurement_rows"]), (16, 64, 252))
        self.assertEqual(result["observed_count"], 15)
        self.assertTrue(result["all_measurements_at_equilibrium"])
        self.assertIsNone(result["declared_model_time_unit"])
        self.assertEqual(result["fixed_parameters"]["da_b"], "1.0")

    def test_generator_against_motif_rule_oracle(self) -> None:
        names, q, initial = oracle()
        result = instrument.build_generator(self.path)
        self.assertEqual(result["species"], names)
        np.testing.assert_allclose(result["matrix"], q, rtol=2e-15, atol=2e-15)
        np.testing.assert_array_equal(result["initial"], initial)

    def test_stationarity_against_independent_integration(self) -> None:
        _, q, initial = oracle()
        expected = solve_ivp(lambda time, state: q @ state, (0, 60), initial, rtol=1e-11, atol=1e-13).y[:, -1]
        result = instrument.stationary(self.path)
        np.testing.assert_allclose(result["probabilities"], expected, atol=1e-10, rtol=1e-9)
        self.assertLess(result["residual_max"], 1e-12)

    def test_clock_counterexample_against_independent_integration(self) -> None:
        _, q, initial = oracle()
        result = instrument.clock_witness(self.path, (0.37, 2.31), 1.27)
        for number, scale in enumerate((0.37, 2.31), 1):
            expected = solve_ivp(lambda time, state: scale * q @ state, (0, 1.27), initial, rtol=1e-11, atol=1e-13).y[
                :, -1
            ]
            np.testing.assert_allclose(result[f"prediction_world_{number}"], expected, rtol=1e-8, atol=1e-10)
        self.assertTrue(result["separates_at_requested_time"])
        self.assertLess(result["stationary_difference_max"], 1e-12)

    def test_dimension_does_not_disqualify_selected_fit(self) -> None:
        selected = instrument.dimension_bound(self.path)
        full = instrument.dimension_bound(self.path, 33)
        self.assertEqual(selected["selected_estimated_kinetic_parameters"], 8)
        self.assertEqual(selected["candidate_estimated_kinetic_parameters"], 33)
        self.assertFalse(selected["dimension_obstruction"])
        self.assertEqual(full["minimum_rank_deficiency"], 18)
        self.assertIn("Necessary", full["limitations"])

    def test_flat_and_parent_model_space_layouts_have_explicit_identity(self) -> None:
        shutil.move(self.case / "model_space.tsv", self.path / "model_space.tsv")
        flat = instrument.dimension_bound(self.path)
        self.assertEqual(flat["candidate_estimated_kinetic_parameters"], 33)
        self.assertNotEqual(flat["source_fingerprint"], self.identity)
        (self.path / "model_space.tsv").unlink()
        missing = instrument.dimension_bound(self.path)
        self.assertIsNone(missing["candidate_estimated_kinetic_parameters"])
        self.assertEqual(missing["candidate_space_evidence"], "not_supplied")

    def test_replicates_and_sixteenth_motif_do_not_create_a_clock(self) -> None:
        file = self.path / "measurements.tsv"
        lines = file.read_text().splitlines()
        file.write_text("\n".join(lines + lines[1:]) + "\n")
        self.assertEqual(instrument.dimension_bound(self.path, 33)["maximum_independent_mean_coordinates"], 15)
        observable = self.path / "observables.tsv"
        with observable.open("a") as handle:
            handle.write("observable_x_k05k16\ty_missing\tx_k05k16\tlog\tsigma_\tnormal\n")
        with file.open() as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        new = dict(rows[0])
        new["observableId"] = "observable_x_k05k16"
        rows.append(new)
        with file.open("w") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        self.assertEqual(instrument.inventory(self.path)["observed_count"], 16)
        self.assertEqual(instrument.dimension_bound(self.path, 33)["maximum_independent_mean_coordinates"], 15)
        self.assertTrue(instrument.clock_witness(self.path)["separates_at_requested_time"])

    def test_finite_observation_invalidates_equilibrium_witness(self) -> None:
        file = self.path / "measurements.tsv"
        file.write_text(file.read_text().replace("\tinf\t", "\t0.4\t", 1))
        self.assertEqual(instrument.inventory(self.path)["finite_positive_measurement_rows"], 1)
        result = instrument.qualify({"mission_id": "changed-data", "type": "clock_witness"}, self.path)
        self.assertEqual(result["status"], "scope_not_qualified")
        self.assertIn("finite-time", result["reason"])

    def test_calibrated_spectral_time_uses_inverse_interval(self) -> None:
        request = {
            "mission_id": "calibrated",
            "type": "response",
            "quantity": "spectral_relaxation_time",
            "time_basis": "physical",
            "scope_id": "research-only",
            "calibration": self.calibration(),
        }
        result = instrument.qualify(request, self.path)
        self.assertEqual(result["status"], "qualified_conditionally")
        nominal = result["result"]["model_value"]
        np.testing.assert_allclose(result["result"]["interval"], [nominal / 1.9, nominal / 0.7], rtol=1e-14)
        self.assertFalse(result["physical_validation"])
        self.assertEqual(result["authority"], [])

    def test_uncertain_clock_state_enclosure_contains_interior_values(self) -> None:
        calibration = self.calibration()
        calibration["scale_per_physical_unit"] = [0.9, 1.1]
        request = {
            "mission_id": "enclosure",
            "type": "response",
            "quantity": "state_at_time",
            "time": 0.8,
            "time_basis": "physical",
            "scope_id": "research-only",
            "calibration": calibration,
        }
        result = instrument.qualify(request, self.path)
        intervals = np.asarray(result["result"]["intervals"])
        _, q, initial = oracle()
        for scale in np.linspace(0.9, 1.1, 21):
            state = solve_ivp(lambda time, value: scale * q @ value, (0, 0.8), initial, rtol=1e-10, atol=1e-12).y[:, -1]
            self.assertTrue(np.all(state >= intervals[:, 0] - 1e-10))
            self.assertTrue(np.all(state <= intervals[:, 1] + 1e-10))

    def test_stale_or_wrong_scope_calibration_rejected(self) -> None:
        request = {
            "mission_id": "new-scope",
            "type": "response",
            "quantity": "spectral_relaxation_time",
            "time_basis": "physical",
            "scope_id": "changed",
            "calibration": self.calibration(),
        }
        self.assertEqual(instrument.qualify(request, self.path)["status"], "scope_not_qualified")
        request["scope_id"] = "research-only"
        (self.path / "parameters.tsv").write_text((self.path / "parameters.tsv").read_text() + "\n")
        self.assertEqual(instrument.qualify(request, self.path)["status"], "scope_not_qualified")

    def test_parameter_change_requires_calibration_binding(self) -> None:
        request = {
            "mission_id": "parameter-change",
            "type": "response",
            "quantity": "spectral_relaxation_time",
            "time_basis": "physical",
            "scope_id": "research-only",
            "calibration": self.calibration(),
            "parameter_overrides": {"a_b": 0.08},
        }
        self.assertEqual(instrument.qualify(request, self.path)["status"], "scope_not_qualified")
        request["calibration"]["parameter_overrides_sha256"] = hashlib.sha256(
            json.dumps(request["parameter_overrides"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(instrument.qualify(request, self.path)["status"], "qualified_conditionally")

    def test_calibration_excludes_invalid_clock_alternatives(self) -> None:
        request = {
            "mission_id": "bounded-clock",
            "type": "clock_witness",
            "scales": [1, 2],
            "scope_id": "research-only",
            "calibration": self.calibration(),
        }
        self.assertEqual(instrument.qualify(request, self.path)["status"], "scope_not_qualified")
        request["scales"] = [0.9, 1.8]
        self.assertEqual(instrument.qualify(request, self.path)["status"], "clock_uncertainty_within_calibration")

    def test_new_mission_never_inherits_authority(self) -> None:
        first = instrument.qualify({"mission_id": "first", "type": "stationary"}, self.path)
        request = {
            "mission_id": "second",
            "type": "response",
            "time_basis": "physical",
            "quantity": "spectral_relaxation_time",
            "parent_receipt": first,
            "authority": ["production"],
        }
        result = instrument.qualify(request, self.path)
        self.assertEqual(result["status"], "scope_not_qualified")
        self.assertEqual(result["authority"], [])
        self.assertNotEqual(result["request_sha256"], first["request_sha256"])
        self.assertTrue(result["current_mission_rechecked"])

    def test_source_identity_is_part_of_request(self) -> None:
        result = instrument.qualify(
            {"mission_id": "stale", "type": "stationary", "expected_source_fingerprint": "bad"}, self.path
        )
        self.assertEqual(result["status"], "scope_not_qualified")

    def test_unsupported_events_and_flux_observables_not_certified(self) -> None:
        file = self.path / "model.xml"
        file.write_text(file.read_text().replace("</model>", "<listOfEvents/></model>"))
        self.assertEqual(
            instrument.qualify({"mission_id": "event", "type": "stationary"}, self.path)["status"],
            "scope_not_qualified",
        )
        shutil.copy2(SOURCE / "model.xml", file)
        observable = self.path / "observables.tsv"
        observable.write_text(observable.read_text().replace("\tx_0ac\t", "\ta_b*x_0ac\t", 1))
        self.assertEqual(
            instrument.qualify({"mission_id": "flux", "type": "clock_witness"}, self.path)["status"],
            "scope_not_qualified",
        )
        self.assertEqual(
            instrument.qualify({"mission_id": "flux-bound", "type": "dimension_bound"}, self.path)["status"],
            "scope_not_qualified",
        )

    def test_request_and_result_mutations_are_isolated(self) -> None:
        request = {"mission_id": "repeat", "type": "stationary"}
        before = copy.deepcopy(request)
        first = instrument.qualify(request, self.path)
        self.assertEqual(request, before)
        first["result"]["probabilities"][0] = -100
        second = instrument.qualify(request, self.path)
        self.assertGreater(second["result"]["probabilities"][0], 0)

    def test_invalid_numeric_inputs_rejected(self) -> None:
        for scales in ([True, 2], [1, float("inf")], [1, 1], [-1, 2]):
            if any(isinstance(value, float) and not np.isfinite(value) for value in scales):
                with self.assertRaises(ValueError):
                    instrument.qualify({"mission_id": "bad", "type": "clock_witness", "scales": scales}, self.path)
            else:
                self.assertEqual(
                    instrument.qualify({"mission_id": "bad", "type": "clock_witness", "scales": scales}, self.path)[
                        "status"
                    ],
                    "scope_not_qualified",
                )


if __name__ == "__main__":
    unittest.main()
