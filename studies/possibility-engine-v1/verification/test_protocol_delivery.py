# SPDX-License-Identifier: Apache-2.0
"""Independent end-to-end controls for scoped numerical delivery."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from check_protocol import check
from independent_math import construct_graphs


class ProtocolDeliveryTests(unittest.TestCase):
    """Test the public local CLI without importing its implementation."""

    def test_nondefault_box_and_zero_leak_delivery(self) -> None:
        """Nominal values and circuits must honor an uncertainty box excluding defaults."""
        data = {"schema": "possibility-engine-input-v1", "models": construct_graphs()["models"],
                "uncertainty": {"rate": [2.0, 2.4], "leak": [0.0, 0.0], "gain": [1.2, 1.4], "noise": 0.005},
                "times": [0.05, 0.1, 0.15, 0.2, 0.25],
                "experiments": [{"actuator": 1, "sensor": 3, "cost_units": 12}], "failure_mode": "none"}
        with tempfile.TemporaryDirectory(prefix="possibility-nondefault-") as directory:
            path = Path(directory)
            source = path / "input.json"
            source.write_text(json.dumps(data))
            process = subprocess.run([sys.executable, str(Path(__file__).parents[1] / "src/engine.py"),
                                      str(source), "--output", str(path / "delivery")], capture_output=True,
                                     text=True, timeout=45, check=False)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads((path / "delivery/result.json").read_text())
            self.assertEqual(check(data, result)["status"], "pass")
            self.assertEqual(result["nominal_parameters"], {"rate": 2.2, "leak": 0, "gain": 1.2999999999999998})
            for netlist in (path / "delivery").glob("*.cir"):
                text = netlist.read_text()
                self.assertNotIn("RL0 ", text)
                self.assertIn("EREAD readout 0 n3 0 {gain}", text)
            altered = copy.deepcopy(result)
            altered["selected"][0]["nominal_outputs"].pop()
            with self.assertRaises(AssertionError):
                check(data, altered)
            altered = copy.deepcopy(result)
            altered["input_sha256"] = "0" * 64
            with self.assertRaises(AssertionError):
                check(data, altered)


if __name__ == "__main__":
    unittest.main()
