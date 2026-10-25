# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import hashlib
import json
import unittest
import shutil
import tempfile
from pathlib import Path
from fixed_worker import FixedWorker, WorkerError

ROOT = Path(__file__).parent


class EngineeringWorkerTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "receipts/engineering-payload.json").read_text())
        self.limits = {
            "service_work": 500000,
            "improvement_work": 3000000,
            "native_calls": 0,
            "native_solve_seconds": 0,
            "allow_native": False,
            "wall_seconds": 60,
            "source_hash": "a" * 64,
        }
        self.debits = []

    def run_worker(self, method, payload, limits=None):
        return FixedWorker().execute(method, payload, limits or self.limits, lambda **x: self.debits.append(x))

    def test_same_project_journey_and_distinct_construction(self):
        out = self.run_worker("run-journey", self.payload)
        phases = out["result"]["phases"]
        caps = out["result"]["capabilities"]
        self.assertTrue(out["verified"])
        self.assertEqual(len(phases), 3)
        self.assertTrue(all(p["verified"] and p["qualified"] for p in phases))
        self.assertEqual(phases[0]["task"]["jobs"][1]["duration"], 4)
        self.assertEqual(phases[1]["task"]["jobs"][1]["duration"], 6)
        self.assertEqual(phases[2]["task"]["baseline"], {x["id"]: x["start"] for x in phases[1]["result"]["schedule"]})
        self.assertEqual(
            phases[2]["task"]["locked"],
            {x["id"]: x["start"] for x in phases[1]["result"]["schedule"] if x["start"] < 9},
        )
        self.assertEqual(phases[2]["baseline_source"]["receipt_hash"], phases[1]["receipt_hash"])
        partials = [x["receipt"] for x in self.debits if "receipt" in x]
        self.assertEqual([p["phase_index"] for p in partials], [0, 1, 2])
        self.assertEqual([p["receipt_hash"] for p in partials], [p["receipt_hash"] for p in phases])
        self.assertEqual([c["stage"] for c in caps], ["dispatch", "lookahead", "repair"])
        self.assertEqual(len({c["asset"]["digest"] for c in caps}), 3)
        self.assertEqual(caps[1]["lineage"]["parent_digest"], caps[0]["asset"]["digest"])
        self.assertEqual(caps[2]["lineage"]["parent_digest"], caps[1]["asset"]["digest"])
        self.assertGreater(caps[1]["lineage"]["parent_calls"], 0)
        self.assertGreater(caps[2]["lineage"]["parent_calls"], 0)
        self.assertEqual(out["result"]["inheritance"]["parent_benefit"], "MEASURED_LOCAL_CONSTRUCTION_COSTS_ONLY")
        self.assertIn("candidate_trial", out["result"]["repair_usefulness"])
        self.assertIn(out["result"]["repair_usefulness"]["consequence"], ("WIN", "TIE", "LOSS"))
        actual = {p["task_id"] for p in phases}
        for cap in caps:
            self.assertFalse(
                actual.intersection(x["id"] for x in cap["corpus"]["training"] + cap["corpus"]["qualification"])
            )
        for diagnostic in out["result"]["inheritance"]["diagnostics"]:
            self.assertEqual([arm["treatment"] for arm in diagnostic["arms"]], ["inherited", "rebuilt", "equivalent"])
            self.assertEqual(len({arm["child_allocation"] for arm in diagnostic["arms"]}), 1)
            self.assertEqual(len({arm["total_allocation"] for arm in diagnostic["arms"]}), 1)
            self.assertGreater(diagnostic["arms"][1]["parent_reconstruction_work"], 0)
        self.assertEqual(
            sum(e["work"] for e in out["result"]["accounting"]["improvement_ledger"]), out["costs"]["improvement_work"]
        )
        for c in caps:
            self.assertEqual(c["asset"]["authority"], [])
            self.assertEqual(c["asset"]["proof"], [])
        for k in ("service_work", "improvement_work", "native_calls", "native_solve_seconds"):
            self.assertAlmostEqual(out["costs"][k], sum(x.get(k, 0) for x in self.debits))

    def test_construct_never_draws_service_account(self):
        a = self.payload["initial"]
        b = copy.deepcopy(a)
        b["id"] = "engineering-changed-qualification"
        b["jobs"][1]["duration"] = 6
        limits = {**self.limits, "service_work": 0}
        out = self.run_worker(
            "construct", {"stage": "dispatch", "training": [a], "validation": [b], "remaining_missions": 1}, limits
        )
        self.assertEqual(out["costs"]["service_work"], 0)
        self.assertGreater(out["costs"]["improvement_work"], 0)

    def test_unfunded_construction_defers_and_service_continues(self):
        out = self.run_worker("run-journey", self.payload, {**self.limits, "improvement_work": 0})
        self.assertEqual(out["costs"]["improvement_work"], 0)
        self.assertEqual(len(out["result"]["phases"]), 3)
        self.assertEqual(
            out["result"]["capabilities"][0]["decision"], "DEFER_PROTECTED_IMPROVEMENT_DIAGNOSTIC_ALLOWANCE"
        )

    def test_browser_cannot_supply_repair_baseline(self):
        self.payload["repair"]["baseline"] = {"J1": 0}
        with self.assertRaisesRegex(WorkerError, "REPAIR_SCHEMA"):
            self.run_worker("run-journey", self.payload)

    def test_identical_requirements_refused(self):
        self.payload["changes"] = {}
        with self.assertRaisesRegex(WorkerError, "CHANGED_REQUIREMENTS_REQUIRED"):
            self.run_worker("run-journey", self.payload)

    def test_imported_strategy_authority_cannot_execute(self):
        strategy = {"kind": "shell", "command": "touch /tmp/forbidden"}
        with self.assertRaises(WorkerError):
            self.run_worker("run-mission", {"task": self.payload["initial"], "strategy": strategy})

    def test_stop_between_actual_project_phases(self):
        w = FixedWorker()
        partials = []

        def stop(**x):
            if x.get("receipt"):
                partials.append(x["receipt"])
            if w.last_progress and w.last_progress["phase"] == "start:Changed requirements":
                raise RuntimeError("OPERATOR_STOP")

        self.payload["construction"]["enabled"] = False
        with self.assertRaisesRegex(WorkerError, "CHECKPOINT_REFUSED") as context:
            w.execute("run-journey", self.payload, self.limits, stop)
        self.assertEqual(str(context.exception.__cause__), "OPERATOR_STOP")
        self.assertGreater(context.exception.costs["service_work"], 0)
        self.assertTrue(context.exception.costs["unknown_costs"])
        self.assertEqual(len(partials), 1)
        self.assertEqual(partials[0]["phase_index"], 0)

    def test_native_is_explicit_separate_and_independently_checked(self):
        self.payload["construction"]["enabled"] = False
        limits = {**self.limits, "allow_native": True, "native_calls": 6, "native_solve_seconds": 20}
        out = self.run_worker("run-journey", self.payload, limits)
        self.assertEqual(out["costs"]["native_calls"], 6)
        self.assertGreater(out["costs"]["native_solve_seconds"], 0)
        self.assertTrue(out["costs"]["unknown_costs"])
        for phase in out["result"]["phases"]:
            native = [r for r in phase["attempts"] if r["method"].startswith("native-")]
            self.assertEqual(len(native), 2)
            self.assertTrue(
                all(r.get("valid") and (r.get("checker") or {}).get("valid") for r in native),
                json.dumps(native, sort_keys=True),
            )
            self.assertEqual(phase["receipt"]["result"], phase["result"])
            self.assertEqual(phase["receipt"]["method"], phase["selected_method"])
            canonical = json.dumps(phase["receipt"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(), phase["receipt_hash"])
            self.assertIn(phase["receipt_hash"], json.dumps(phase["pack"]))

    def test_semantic_collision_defers_without_retuning(self):
        self.payload["changes"] = {"durations": {"J1": 3}, "deadline": 32}
        out = self.run_worker("run-journey", self.payload)
        self.assertEqual(out["result"]["capabilities"][0]["decision"], "DEFER_DEVELOPMENT_CORPUS_COLLISION")
        self.assertEqual(len(out["result"]["phases"]), 3)
        self.assertGreater(out["costs"]["improvement_work"], 0)
        self.assertFalse(any(c.get("search") for c in out["result"]["capabilities"]))

    def test_forecast_is_a_bounded_integer(self):
        task = self.payload["initial"]
        for count in ("1", -1, 0, 1.5, 4):
            with self.subTest(count=count), self.assertRaisesRegex(WorkerError, "FORECAST_MISSIONS_SCOPE"):
                self.run_worker(
                    "construct",
                    {"stage": "dispatch", "training": [task], "validation": [task], "remaining_missions": count},
                )

    def test_failed_native_attempt_debits_allowance_and_preserves_fallback(self):
        with tempfile.TemporaryDirectory(prefix="authored-native-fault-") as temporary:
            root = Path(temporary)
            manifest = json.loads((ROOT / "SOURCE_FILES.json").read_text())
            for entry in manifest["files"]:
                destination = root / entry["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / entry["path"], destination)
            bridge = root / "python_bridge.py"
            text = bridge.read_text().replace(
                'root = Path(__file__).resolve().parent / "scientific"',
                'if sys.argv[1] == "specialist":\n    print(json.dumps({"ok": False, "error": "AUTHORED_NATIVE_FAULT"}), flush=True)\n    sys.exit(0)\nroot = Path(__file__).resolve().parent / "scientific"',
            )
            bridge.write_text(text)
            for entry in manifest["files"]:
                entry["sha256"] = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
            (root / "SOURCE_FILES.json").write_text(json.dumps(manifest))
            limits = {**self.limits, "allow_native": True, "native_calls": 2, "native_solve_seconds": 4}
            out = FixedWorker(root).execute("run-mission", {"task": self.payload["initial"]}, limits, lambda **x: None)
            self.assertTrue(out["verified"])
            self.assertEqual(out["costs"]["native_calls"], 2)
            self.assertEqual(out["costs"]["native_solve_seconds"], 4)
            self.assertEqual(out["result"]["phases"][0]["selected_method"], "ordinary-portfolio")
            self.assertTrue(any("failed" in x for x in out["costs"]["unknown_costs"]))

    def test_explicit_zero_releases_are_not_changed_requirements(self):
        self.payload["changes"] = {"release": {j["id"]: 0 for j in self.payload["initial"]["jobs"]}}
        with self.assertRaisesRegex(WorkerError, "CHANGED_REQUIREMENTS_REQUIRED"):
            self.run_worker("run-journey", self.payload)

    def test_explicit_zero_releases_do_not_evade_corpus_collision(self):
        self.payload["changes"] = {
            "durations": {"J1": 3},
            "deadline": 32,
            "release": {j["id"]: 0 for j in self.payload["initial"]["jobs"]},
        }
        out = self.run_worker("run-journey", self.payload)
        self.assertEqual(out["result"]["capabilities"][0]["decision"], "DEFER_DEVELOPMENT_CORPUS_COLLISION")
        self.assertEqual(len(out["result"]["phases"]), 3)

    def test_invalid_authored_development_corpus_does_not_abort_service(self):
        self.payload = {
            "initial": {
                "schema": "release-plan/v1",
                "id": "one-slot-development-deferral",
                "kind": "plan",
                "jobs": [{"id": "J1", "duration": 1, "crew": 1, "deps": []}],
                "capacity": [1],
                "deadline": 1,
                "release": {},
                "locked": {},
                "public_or_synthetic": "synthetic",
                "planning_only": True,
            },
            "changes": {"capacity": [2]},
            "repair": {"observed_at": 0, "capacity": [2], "deadline": 1},
            "construction": {"enabled": True},
        }
        out = self.run_worker("run-journey", self.payload)
        self.assertTrue(out["verified"])
        self.assertEqual(len(out["result"]["phases"]), 3)
        self.assertEqual(out["result"]["capabilities"][0]["decision"], "DEFER_INVALID_DEVELOPMENT_CORPUS")
        self.assertTrue(all(p["qualified"] for p in out["result"]["phases"]))

    def test_fresh_repair_collision_disables_candidate_and_continues_service(self):
        self.payload["changes"] = {"durations": {"J1": 4}, "deadline": 32, "release": {"J6": 1}}
        capacity = [2] * 32
        for tick in range(8, 11):
            capacity[tick] = 1
        self.payload["repair"] = {"observed_at": 1, "capacity": capacity, "deadline": 32}
        out = self.run_worker("run-journey", self.payload)
        self.assertTrue(out["verified"])
        self.assertEqual(len(out["result"]["phases"]), 3)
        self.assertTrue(
            any(c["decision"] == "DEFER_FRESH_REPAIR_CORPUS_COLLISION" for c in out["result"]["capabilities"])
        )
        self.assertIsNone(out["result"]["repair_usefulness"]["candidate_trial"])
        self.assertEqual(out["result"]["phases"][2]["selected_method"], "ordinary-portfolio")

    def test_unqualified_development_baseline_defers_only_improvement(self):
        with tempfile.TemporaryDirectory(prefix="authored-development-baseline-fault-") as temporary:
            root = Path(temporary)
            manifest = json.loads((ROOT / "SOURCE_FILES.json").read_text())
            for entry in manifest["files"]:
                destination = root / entry["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / entry["path"], destination)
            worker = root / "fixed_worker.mjs"
            source = worker.read_text()
            original = "baselineAttempts.push(row);if(!row.valid||!row.qualified)"
            self.assertEqual(source.count(original), 1)
            worker.write_text(
                source.replace(
                    original, "row.qualified=false;baselineAttempts.push(row);if(!row.valid||!row.qualified)"
                )
            )
            for entry in manifest["files"]:
                entry["sha256"] = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
            (root / "SOURCE_FILES.json").write_text(json.dumps(manifest))
            out = FixedWorker(root).execute("run-journey", self.payload, self.limits, lambda **x: None)
            self.assertTrue(out["verified"])
            self.assertEqual(len(out["result"]["phases"]), 3)
            self.assertTrue(
                any(c["decision"] == "DEFER_DEVELOPMENT_REPAIR_CORPUS" for c in out["result"]["capabilities"])
            )
            self.assertIsNone(out["result"]["repair_usefulness"]["candidate_trial"])


if __name__ == "__main__":
    unittest.main()
