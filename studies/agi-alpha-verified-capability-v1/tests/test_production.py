# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.acceptance import ROOT, check_completed_packet, mission_key, read_json, reverify, sha256, validate_job
from src.production import run_direct_pipeline, run_pipeline


class ProductionAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        parent = ROOT / "evidence/development"
        parent.mkdir(parents=True, exist_ok=True)
        cls.work = Path(tempfile.mkdtemp(prefix="production-controls-", dir=parent))
        cls.job = ROOT / "inputs/missions-v1/development-unchanged-lock/job.json"
        cls.native = run_pipeline(cls.job, cls.work / "native-baseline")
        cls.direct = run_direct_pipeline(cls.job, cls.work / "direct-baseline")

    def clone_job(self, name: str) -> Path:
        folder = self.work / name
        shutil.copytree(self.job.parent, folder)
        path = folder / "job.json"
        job = read_json(path)
        job["wheelhouse_path"] = os.path.relpath(ROOT / "inputs/wheels", folder)
        path.write_text(json.dumps(job, indent=2) + "\n")
        return path

    def clone_packet(self, name: str, *, native: bool = True) -> Path:
        original = self.work / ("native-baseline" if native else "direct-baseline") / "execution"
        target = self.work / name
        shutil.copytree(original, target, ignore=shutil.ignore_patterns("selected-wheels"))
        return target

    def test_native_real_baseline_complete(self) -> None:
        self.assertTrue(self.native["accepted"], self.native["errors"])
        self.assertEqual(self.native["decision"], "CONSISTENT")
        self.assertEqual(self.native["certificate"]["status"], "COMPLETE")
        self.assertGreater(len(self.native["certificate"]["dependency_edges"]), 0)

    def test_direct_real_baseline_same_outcome(self) -> None:
        self.assertTrue(self.direct["accepted"], self.direct["errors"])
        self.assertEqual(self.direct["decision"], self.native["decision"])
        self.assertEqual(self.direct["mission_key"], self.native["mission_key"])
        self.assertEqual(self.direct["certificate"]["substantiated_witnesses"],
                         self.native["certificate"]["substantiated_witnesses"])

    def test_packet_has_real_captures_and_bilingual_report(self) -> None:
        folder = self.work / "native-baseline"
        for name in ("report.en.md", "report.fr.md", "decision-packet.zip", "payload-manifest.json",
                     "execution/delivery/pip.stdout.txt", "execution/delivery/pip.stderr.txt",
                     "execution/delivery/pip-report.json", "execution/pack.json", "execution/inspection.json"):
            self.assertTrue((folder / name).is_file(), name)
        self.assertEqual(self.native["tools"]["pip_resolutions"], 1)
        self.assertEqual(self.native["tools"]["runtime_model_calls"] if "runtime_model_calls" in self.native["tools"]
                         else self.native["tools"]["model_calls"], 0)

    def test_historical_record_has_no_live_grant(self) -> None:
        inspection = read_json(self.work / "native-baseline/execution/inspection.json")
        self.assertEqual(inspection["activeAuthority"], [])
        self.assertEqual(inspection["activeProof"], [])
        self.assertEqual(self.native["native_history"]["admission"], "HOLD")
        self.assertIsNone(self.native["customer_acceptance"])

    def test_independent_recomputation_accepts_baseline(self) -> None:
        result = reverify(self.job, self.work / "native-baseline/execution/delivery/result.json")
        self.assertEqual(result["status"], "COMPLETE", result["errors"])

    def test_alias_does_not_create_new_job(self) -> None:
        path = self.clone_job("alias-only")
        data = read_json(path)
        data["id"] = "an-alias-is-not-another-job"
        path.write_text(json.dumps(data))
        self.assertEqual(mission_key(path), mission_key(self.job))

    def test_comment_does_not_create_new_job(self) -> None:
        path = self.clone_job("comment-only")
        project = path.parent / "pyproject.toml"
        project.write_text(project.read_text() + "\n# Same substantive requirements\n")
        data = read_json(path)
        data["pyproject_sha256"] = sha256(project)
        path.write_text(json.dumps(data))
        self.assertEqual(mission_key(path), mission_key(self.job))

    def test_requirement_change_changes_mission_key_without_running_outcome(self) -> None:
        path = self.clone_job("changed-requirement-key-only")
        project = path.parent / "pyproject.toml"
        project.write_text(project.read_text().replace("cryptography>=50.0.1,<51", "cryptography>=50.0.1,<52"))
        data = read_json(path)
        data["pyproject_sha256"] = sha256(project)
        path.write_text(json.dumps(data))
        self.assertNotEqual(mission_key(path), mission_key(self.job))

    def test_duplicate_json_fields_refused(self) -> None:
        path = self.work / "duplicate.json"
        path.write_text('{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_FIELD"):
            read_json(path)

    def test_nonfinite_json_refused(self) -> None:
        path = self.work / "nonfinite.json"
        path.write_text('{"value":NaN}')
        with self.assertRaisesRegex(ValueError, "NONFINITE_JSON"):
            read_json(path)

    def test_stale_input_hash_refused_before_production(self) -> None:
        path = self.clone_job("stale-input")
        (path.parent / "requirements.lock").write_text("# tampered\n")
        packet = run_pipeline(path, self.work / "stale-input-refusal")
        self.assertFalse(packet["accepted"])
        self.assertEqual(packet["commands"], [])
        self.assertEqual(packet["tools"]["pip_resolutions"], 0)

    def test_symlink_input_refused(self) -> None:
        path = self.work / "symlink-job.json"
        path.symlink_to(self.job)
        with self.assertRaisesRegex(ValueError, "SYMLINK"):
            validate_job(path)

    def test_duplicate_normalized_wheel_refused(self) -> None:
        path = self.clone_job("duplicate-wheel")
        data = read_json(path)
        data["wheels"].append(copy.deepcopy(data["wheels"][0]))
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "WHEEL_IDENTITY"):
            validate_job(path)

    def test_unknown_extra_refused(self) -> None:
        path = self.clone_job("unknown-extra")
        data = read_json(path)
        data["project_extras"] = ["invented-extra"]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "UNKNOWN_PROJECT_EXTRA"):
            validate_job(path)

    def test_stale_certificate_refused(self) -> None:
        folder = self.clone_packet("stale-certificate")
        path = folder / "verification.json"
        data = read_json(path)
        data["job_sha256"] = "0" * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "OUTPUT_JOB_BINDING"):
            check_completed_packet(self.job, folder, native=True)

    def test_changed_capture_refused(self) -> None:
        folder = self.clone_packet("changed-capture")
        (folder / "delivery/pip.stdout.txt").write_text("different execution\n")
        with self.assertRaisesRegex(ValueError, "CAPTURE_CHANGED"):
            check_completed_packet(self.job, folder, native=True)

    def test_missing_capture_refused(self) -> None:
        folder = self.clone_packet("missing-capture")
        (folder / "delivery/pip.stderr.txt").unlink()
        with self.assertRaises(ValueError):
            check_completed_packet(self.job, folder, native=True)

    def test_artifact_path_escape_refused(self) -> None:
        folder = self.clone_packet("escaping-artifact", native=False)
        path = folder / "delivery/result.json"
        data = read_json(path)
        data["files"]["stdout"] = "../../native-baseline/native.stdout.txt"
        path.write_text(json.dumps(data))
        certificate = reverify(self.job, path)
        self.assertEqual(certificate["status"], "INCOMPLETE")

    def test_false_consistency_is_rejected_by_independent_verifier(self) -> None:
        folder = self.clone_packet("false-builder-decision", native=False)
        path = folder / "delivery/result.json"
        data = read_json(path)
        data["decision"] = "CONFLICT"
        path.write_text(json.dumps(data))
        certificate = reverify(self.job, path)
        self.assertEqual(certificate["status"], "INCOMPLETE")
        self.assertTrue(any("builder verdict" in x for x in certificate["errors"]))

    def test_pip_report_metadata_tamper_rejected(self) -> None:
        folder = self.clone_packet("pip-metadata-tamper", native=False)
        path = folder / "delivery/pip-report.json"
        data = read_json(path)
        data["install"][0]["metadata"]["version"] = "99999.0"
        path.write_text(json.dumps(data))
        certificate = reverify(self.job, folder / "delivery/result.json")
        self.assertEqual(certificate["status"], "INCOMPLETE")

    def test_pip_report_missing_distribution_rejected(self) -> None:
        folder = self.clone_packet("pip-incomplete-report", native=False)
        path = folder / "delivery/pip-report.json"
        data = read_json(path)
        data["install"].pop()
        path.write_text(json.dumps(data))
        certificate = reverify(self.job, folder / "delivery/result.json")
        self.assertEqual(certificate["status"], "INCOMPLETE")

    def test_new_authority_cannot_be_inherited(self) -> None:
        folder = self.clone_packet("invented-authority")
        path = folder / "inspection.json"
        data = read_json(path)
        data["activeAuthority"] = ["production"]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "HISTORICAL_IMPORT"):
            check_completed_packet(self.job, folder, native=True)

    def test_output_is_never_overwritten(self) -> None:
        before = sha256(self.work / "native-baseline/packet.json")
        with self.assertRaises(FileExistsError):
            run_pipeline(self.job, self.work / "native-baseline")
        self.assertEqual(before, sha256(self.work / "native-baseline/packet.json"))


if __name__ == "__main__":
    unittest.main()
