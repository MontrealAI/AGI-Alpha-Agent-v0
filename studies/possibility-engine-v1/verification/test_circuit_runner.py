# SPDX-License-Identifier: Apache-2.0
"""Analytic controls for the independent netlist parser and time integration."""

import math
import tempfile
import unittest
from pathlib import Path

from circuit_runner import integrate_netlist, parse_netlist


class CircuitControls(unittest.TestCase):
    def evaluate(self, body: str, observed: str = "n0") -> float:
        with tempfile.TemporaryDirectory(prefix="possibility-circuit-control-") as directory:
            path = Path(directory) / "control.cir"
            path.write_text(
                "* Independent analytic RC control\n"
                + body
                + f"\n.tran .01 1 0 .001 uic\n.measure tran observation FIND v({observed}) AT=1\n.end\n"
            )
            return float(integrate_netlist(parse_netlist(path))["value"])

    def test_single_capacitor_discharge(self) -> None:
        value = self.evaluate("C0 n0 0 1 IC=1\nR0 n0 0 1")
        self.assertAlmostEqual(value, math.exp(-1), delta=1e-9)

    def test_two_capacitor_charge_transfer(self) -> None:
        value = self.evaluate("C0 n0 0 1 IC=1\nC1 n1 0 1 IC=0\nR01 n0 n1 1", "n1")
        self.assertAlmostEqual(value, (1 - math.exp(-2)) / 2, delta=1e-9)

    def test_isolated_gain_readout(self) -> None:
        value = self.evaluate(
            ".param gain=2.5\nC0 n0 0 1 IC=1\nR0 n0 0 1\nEREAD readout 0 n0 0 {gain}", "readout"
        )
        self.assertAlmostEqual(value, 2.5 * math.exp(-1), delta=1e-9)

    def test_external_include_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported circuit directive"):
            self.evaluate("C0 n0 0 1 IC=1\nR0 n0 0 1\n.include missing.lib")

    def test_capacitor_without_initial_condition_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit IC"):
            self.evaluate("C0 n0 0 1\nR0 n0 0 1")

    def test_readout_feedback_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Resistor node has no capacitor"):
            self.evaluate("C0 n0 0 1 IC=1\nR0 readout n0 1\nEREAD readout 0 n0 0 2", "readout")


if __name__ == "__main__":
    unittest.main()
