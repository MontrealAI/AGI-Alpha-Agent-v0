# SPDX-License-Identifier: Apache-2.0
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
import tempfile

STUB = "alpha_factory_v1/demos/aiga_meta_evolution/alpha_conversion_stub.py"


class TestAlphaConversionStub(unittest.TestCase):
    def test_generate_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "plan.json"
            result = subprocess.run(
                [sys.executable, STUB, "--alpha", "test opportunity", "--ledger", str(ledger)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(ledger.exists())
            data = json.loads(ledger.read_text())
            self.assertIsInstance(data, dict)
            self.assertIn("steps", data)

    def test_default_ledger_path(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["HOME"] = home
            env.pop("ALPHA_CONVERSION_LEDGER", None)
            ledger = Path(home) / ".aiga" / "alpha_conversion_log.json"
            result = subprocess.run(
                [sys.executable, STUB, "--alpha", "test opportunity"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(ledger.exists())

    def test_no_log_skips_directory(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["HOME"] = home
            env.pop("ALPHA_CONVERSION_LEDGER", None)
            result = subprocess.run(
                [sys.executable, STUB, "--alpha", "skip", "--no-log"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            default_dir = Path(home) / ".aiga"
            self.assertFalse(default_dir.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
