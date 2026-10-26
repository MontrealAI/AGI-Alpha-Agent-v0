# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

SOURCE = Path(__file__).resolve().parents[1] / "src/production_campaign.py"
SPEC = importlib.util.spec_from_file_location("production_driver", SOURCE)
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class ProductionControls(unittest.TestCase):
    def freeze(self, folder: Path) -> tuple[Path, Path, str]:
        root = folder / "repo/studies/test"
        root.mkdir(parents=True)
        (root / "source.txt").write_text("frozen source\n")
        data = (root / "source.txt").read_bytes()
        manifest = root / "freeze.json"
        manifest.write_text(
            json.dumps({"files": [{"path": "source.txt", "bytes": len(data), "sha256": DRIVER.sha(data)}]})
        )
        return root, manifest, DRIVER.sha(manifest.read_bytes())

    def test_exact_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, digest = self.freeze(Path(folder))
            self.assertTrue(DRIVER.verify_freeze(root, manifest, digest)["accepted"])

    def test_source_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, digest = self.freeze(Path(folder))
            (root / "source.txt").write_text("changed source\n")
            with self.assertRaises(ValueError):
                DRIVER.verify_freeze(root, manifest, digest)

    def test_manifest_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, digest = self.freeze(Path(folder))
            manifest.write_text("{}")
            with self.assertRaises(ValueError):
                DRIVER.verify_freeze(root, manifest, digest)

    def test_missing_source_is_custody_failure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, digest = self.freeze(Path(folder))
            (root / "source.txt").unlink()
            with self.assertRaisesRegex(ValueError, "SOURCE_CUSTODY_FAILED"):
                DRIVER.verify_freeze(root, manifest, digest)

    def test_all_keys_are_strings(self) -> None:
        value = DRIVER.normalized_yaml(
            b"paths:\n  /x:\n    get:\n      responses:\n        200:\n          schema:\n            type: string\n"
        )
        self.assertIn("200", value["paths"]["/x"]["get"]["responses"])

    def test_key_collision_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DRIVER.normalized_yaml(b"200: a\n'200': b\n")

    def test_nonfinite_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DRIVER.normalized_yaml(b"minimum: .inf\n")

    def test_timestamp_stays_string(self) -> None:
        value = DRIVER.normalized_yaml(b"example: 2026-10-26T12:00:00Z\n")
        self.assertEqual(value["example"], "2026-10-26T12:00:00Z")

    def test_rotated_pairs_source(self) -> None:
        protocol: dict[str, Any] = {"primary_pairs": [["v1.0.0", "v2.0.0"]], "transfer_pairs": [["v2.0.0", "v2.1.0"]]}
        self.assertEqual(len(DRIVER.selected_pairs(protocol, "all")), 2)
        self.assertEqual(len(DRIVER.selected_pairs(protocol, "primary")), 1)

    def test_child_execution_and_capture(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            record = DRIVER.run_process(
                [sys.executable, "-c", "print('complete')"], path, path / "command", lambda: None, 2
            )
            self.assertEqual(record["exit"], 0)
            self.assertEqual((path / "command.stdout").read_text().strip(), "complete")
            self.assertGreaterEqual(record["cpuSeconds"], 0)
            self.assertGreater(record["maxRssKiB"], 0)

    def test_child_failure_retained(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            record = DRIVER.run_process(
                [sys.executable, "-c", "import sys; print('failed'); sys.exit(7)"],
                path,
                path / "command",
                lambda: None,
                2,
            )
            self.assertEqual(record["exit"], 7)
            self.assertEqual((path / "command.stdout").read_text().strip(), "failed")

    def test_failed_guard_prevents_execution(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)

            def reject() -> None:
                raise ValueError("SOURCE_CUSTODY_FAILED")

            with self.assertRaises(ValueError):
                DRIVER.run_process([sys.executable, "-c", "print('must not run')"], path, path / "command", reject, 2)
            self.assertEqual((path / "command.stdout").read_bytes(), b"")

    def test_timeout_keeps_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            record = DRIVER.run_process(
                [sys.executable, "-c", "import time; print('partial',flush=True); time.sleep(1)"],
                path,
                path / "command",
                lambda: None,
                0.08,
            )
            self.assertTrue(record["timedOut"])
            self.assertNotEqual(record["exit"], 0)
            self.assertEqual((path / "command.stdout").read_text().strip(), "partial")


if __name__ == "__main__":
    unittest.main()
