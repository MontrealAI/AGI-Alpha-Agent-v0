# SPDX-License-Identifier: Apache-2.0
"""Failure evidence is local-only and cannot replace the original failure."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from reconciliation_diagnostics import capture_reconciliation_failure


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
