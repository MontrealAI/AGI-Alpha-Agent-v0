# SPDX-License-Identifier: Apache-2.0
"""Development-only controls for exact primary-wheel admission before install."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepared_environment", ROOT / "curation/prepare_environment.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class SelectedWheelControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = ROOT / "data/development-target-environment"
        cls.wheels = json.loads((cls.environment / "preparation.json").read_text())["wheels"]
        cls.plan = json.loads((ROOT / "data/development-target-plan.json").read_text())
        cls.plan["phase"] = "confirmation"
        cls.plan["selected_primary_package"] = "starlette"
        wheel = next(row for row in cls.wheels if row["name"] == "starlette")
        cls.plan["selected_primary_wheel"] = {"filename": wheel["filename"], "sha256": wheel["sha256"]}

    def test_exact_development_wheel_is_accepted_by_identity_rule(self):
        result = BUILDER.validate_selected_primary_wheel(self.plan, self.wheels)
        self.assertTrue(result["matched_before_install"])
        self.assertEqual(result["version"], "1.10.0")

    def test_different_digest_is_refused(self):
        plan = copy.deepcopy(self.plan)
        plan["selected_primary_wheel"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "FROZEN_PRIMARY_WHEEL_IDENTITY"):
            BUILDER.validate_selected_primary_wheel(plan, self.wheels)

    def test_different_filename_is_refused(self):
        plan = copy.deepcopy(self.plan)
        plan["selected_primary_wheel"]["filename"] = "different-release.whl"
        with self.assertRaisesRegex(ValueError, "FROZEN_PRIMARY_WHEEL_IDENTITY"):
            BUILDER.validate_selected_primary_wheel(plan, self.wheels)

    def test_support_package_cannot_impersonate_selected_cluster(self):
        plan = copy.deepcopy(self.plan)
        plan["selected_primary_package"] = "anyio"
        with self.assertRaisesRegex(ValueError, "FROZEN_PRIMARY_SELECTION_REQUIRED"):
            BUILDER.validate_selected_primary_wheel(plan, self.wheels)

    def test_development_plan_does_not_gain_confirmation_requirements(self):
        plan = copy.deepcopy(self.plan)
        plan["phase"] = "development"
        del plan["selected_primary_wheel"]
        self.assertIsNone(BUILDER.validate_selected_primary_wheel(plan, self.wheels))

    def test_mismatch_stops_before_install_and_retains_failure(self):
        # This synthetic control reuses only already exposed development wheels.
        # The fixture below is a test input, never an authorization or study freeze.
        with tempfile.TemporaryDirectory(prefix="development-wheel-guard-") as temporary:
            directory = Path(temporary)
            fixture = directory / "synthetic-guard-input.json"
            fixture.write_text('{"role":"development-only guard fixture; not a study freeze"}\n')
            plan = copy.deepcopy(self.plan)
            plan["confirmation_freeze_sha256"] = hashlib.sha256(fixture.read_bytes()).hexdigest()
            plan["selected_primary_wheel"]["sha256"] = "0" * 64
            plan["native_lock"] = str(ROOT / "discovery/requirements/requirements-agent.lock")
            plan["incoming_constraint_metadata"] = [
                str(ROOT / "discovery/release-metadata/fastapi-0.141.1.json"),
                str(ROOT / "discovery/release-metadata/pydantic-settings-2.15.0.json"),
            ]
            plan_path = directory / "synthetic-plan.json"
            plan_path.write_text(json.dumps(plan, indent=2) + "\n")
            target = directory / "negative-control-attempt"
            arguments = argparse.Namespace(plan=plan_path, out=target,
                                           metadata_reuse=[self.environment / "metadata"],
                                           wheel_reuse=[self.environment / "wheels"],
                                           confirmation_freeze=fixture, offline=True)
            result = BUILDER.Preparation(arguments).run()
            self.assertFalse(result["complete"])
            self.assertEqual(result["error"], "ValueError: FROZEN_PRIMARY_WHEEL_IDENTITY")
            self.assertEqual(result["network_requests"], 0)
            self.assertEqual(result["steps"], [])
            self.assertFalse((target / "venv").exists())
            self.assertFalse((target / "requirements.lock").exists())
            self.assertTrue((target / "preparation.json").is_file())
            report = {"schema": "development-selected-wheel-preinstall-control/v1",
                      "role": "Synthetic negative control using only exposed Starlette1.10/Pydantic2.14.1 wheels",
                      "not_a_primary_confirmation_attempt": True, "not_a_study_freeze": True,
                      "source_sha256": hashlib.sha256((ROOT / "curation/prepare_environment.py").read_bytes()).hexdigest(),
                      "fixture": json.loads(fixture.read_text()), "fixture_plan": plan,
                      "preparation_report": result,
                      "operations": [json.loads(line) for line in (target / "operations.jsonl").read_text().splitlines()],
                      "verified_no_install_or_lock_written": True,
                      "temporary_directory_removed_after_control": True,
                      "retained_failure_report_sha256": hashlib.sha256((target / "preparation.json").read_bytes()).hexdigest()}
            (ROOT / "discovery/selected-wheel-preinstall-control.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
