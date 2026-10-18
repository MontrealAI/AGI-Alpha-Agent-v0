# SPDX-License-Identifier: Apache-2.0
"""Failure evidence is local-only and cannot replace the original failure."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from reconciliation_diagnostics import capture_action_failure, capture_reconciliation_failure, monitor_action_failures


class ReconciliationDiagnosticsTests(unittest.TestCase):
    def test_diagnostics_are_in_source_inventory_and_existing_ci_discovery(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "tests/contracts/scripts/ascension-cycle.js").read_text()
        inventory = source.split("const sourceHashes =", 1)[1].split("const environment =", 1)[0]
        self.assertIn("'tests/nova-studio/reconciliation_diagnostics.py'", inventory)
        self.assertIn("sourceHashes[relative] = sha(fs.readFileSync(path.join(root, relative)))", inventory)
        workflow = (root / ".github/workflows/mark-wallet.yml").read_text()
        self.assertIn("python -m unittest discover -s tests/nova-studio -p 'test_*.py' -v", workflow)

    def test_retains_public_fixture_receipt_and_bounded_state(self):
        page = Mock(url="http://127.0.0.1:8123/ascension/mainnet/")
        page.evaluate.return_value = {"status": "submitted-not-confirmed", "receipt": {"status": "0x1"}}
        with tempfile.TemporaryDirectory() as directory:
            capture_reconciliation_failure(page, Path(directory), "0x" + "ab" * 32)
            report = json.loads((Path(directory) / "reconciliation-failure.json").read_text())
            self.assertEqual(report["state"]["receipt"]["status"], "0x1")
            script, transaction = page.evaluate.call_args.args
            self.assertIn("slice(-100)", script)
            self.assertIn("eth_getTransactionReceipt", script)
            self.assertNotIn("eth_send", script)
            self.assertNotIn("localStorage", script)
            self.assertEqual(transaction, "0x" + "ab" * 32)

    def test_refuses_nonlocal_pages_and_nonhash_values(self):
        for url, transaction in [
            ("https://example.com", "0x" + "ab" * 32),
            ("http://127.0.0.1:8123", "not-a-transaction"),
        ]:
            page = Mock(url=url)
            with tempfile.TemporaryDirectory() as directory:
                capture_reconciliation_failure(page, Path(directory), transaction)
                self.assertEqual(list(Path(directory).iterdir()), [])
                page.evaluate.assert_not_called()

    def test_capture_failure_cannot_mask_original_assertion(self):
        page = Mock(url="http://127.0.0.1:8123")
        page.evaluate.side_effect = RuntimeError("fixture unavailable")
        with tempfile.TemporaryDirectory() as directory:
            capture_reconciliation_failure(page, Path(directory), "0x" + "ab" * 32)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_action_capture_retains_bounded_errors_and_control_state(self) -> None:
        page = Mock(url="http://127.0.0.1:8123/ascension/mainnet/")
        callbacks = {}
        page.on.side_effect = lambda event, callback: callbacks.update({event: callback})
        page.locator.return_value.inner_text.return_value = "Action needs attention: RPC read timed out"
        page.locator.return_value.evaluate.return_value = {"controls": {"deployment-choice": True}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            monitor_action_failures(page, output)
            for index in range(30):
                callbacks["console"](Mock(type="error", text=f"RPC request failed {index}"))
            callbacks["console"](Mock(type="error", text="secret credential must not be retained"))
            callbacks["pageerror"](RuntimeError("fixture page failed"))
            self.assertTrue(capture_action_failure(page, "edge-E03-Enter-refresh-review"))
            raw = (output / "action-failure-edge-E03-Enter-refresh-review.json").read_text()
            report = json.loads(raw)
            self.assertEqual(len(report["console"]), 20)
            self.assertNotIn("secret credential", raw)
            self.assertEqual(report["pageErrors"], ["fixture page failed"])
            self.assertEqual(report["state"]["controls"], {"deployment-choice": True})
            self.assertIn("RPC read timed out", report["state"]["status"])
            script = page.locator.return_value.evaluate.call_args.args[0]
            self.assertIn("pendingReads", script)
            self.assertNotIn("eth_send", script)
            self.assertNotIn("localStorage", script)
            self.assertNotIn(".params", script)
            self.assertEqual(page.screenshot.call_args.kwargs["timeout"], 2000)

    def test_unresponsive_action_keeps_event_evidence_without_hiding_failure(self) -> None:
        page = Mock(url="http://127.0.0.1:8123/ascension/mainnet/")
        page.locator.return_value.inner_text.side_effect = TimeoutError("unresponsive fixture")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            monitor_action_failures(page, output)
            self.assertFalse(capture_action_failure(page, "interruption-reconcile", "0x" + "ab" * 32))
            report = json.loads((output / "action-failure-interruption-reconcile.json").read_text())
            self.assertEqual(report["captureError"], "TimeoutError")
            self.assertEqual(report["transaction"], "0x" + "ab" * 32)
            page.locator.return_value.evaluate.assert_not_called()
            page.screenshot.assert_not_called()

    def test_action_capture_refuses_external_pages(self) -> None:
        page = Mock(url="https://example.com/ascension/mainnet/")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            monitor_action_failures(page, output)
            capture_action_failure(page, "interruption-reconcile")
            self.assertEqual(list(output.iterdir()), [])
            page.locator.assert_not_called()
