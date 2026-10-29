# SPDX-License-Identifier: Apache-2.0
"""Finite transfer, adverse-payment and native-accounting regressions."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from .delta_delivery import build_delta, make_request
from .operate import balances, digest, investment_gate
from .settlement_probe import ConditionalExchange, simulate
from .settlement_probe_audit import audit

POLICY = json.loads((Path(__file__).parent / "settlement_probe_policy.json").read_bytes())
BEFORE = "sku,price,note\nA,10.00,keep\nB,20.00,local\n"
DELTA = "sku,price\nA,12.50\n"
REQUEST = make_request(["sku"], ["price"], ["price"])


class ExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = {"before": BEFORE, "delta": DELTA, "request": REQUEST}
        self.packet = build_delta(BEFORE, DELTA, REQUEST)
        self.exchange = ConditionalExchange(digest(self.inputs), 9000000)

    def test_unpaid_release_refused(self) -> None:
        with self.assertRaises(ValueError): self.exchange.commit()

    def test_insufficient_or_boolean_funds_refused(self) -> None:
        for funds in (0, 8999999, True, -1):
            with self.subTest(funds=funds), self.assertRaises(ValueError): self.exchange.lock(funds)

    def test_prepare_before_lock_refused(self) -> None:
        with self.assertRaises(ValueError): self.exchange.prepare(BEFORE, DELTA, REQUEST, self.packet)

    def test_lock_not_income(self) -> None:
        self.exchange.lock(9000000)
        self.assertEqual(balances([])["cash_micro_usd"], 0)
        self.assertEqual(self.exchange.state, "LOCKED")

    def test_wrong_request_refused(self) -> None:
        self.exchange.lock(9000000)
        with self.assertRaises(ValueError): self.exchange.prepare(BEFORE, DELTA + "\n", REQUEST, self.packet)

    def test_corrupt_artifact_refused(self) -> None:
        self.exchange.lock(9000000)
        self.packet["native_package"]["changes"] = []
        with self.assertRaises(ValueError): self.exchange.prepare(BEFORE, DELTA, REQUEST, self.packet)

    def test_accepted_exchange_once(self) -> None:
        self.exchange.lock(9000000)
        self.exchange.prepare(BEFORE, DELTA, REQUEST, self.packet)
        result = self.exchange.commit()
        self.assertEqual(result["receipt"]["amount"], 9000000)
        self.assertIn("B,20.00,local", result["output"])
        with self.assertRaises(ValueError): self.exchange.commit()
        with self.assertRaises(ValueError): self.exchange.abort()

    def test_refund_then_release_refused(self) -> None:
        self.exchange.lock(9000000)
        self.exchange.prepare(BEFORE, DELTA, REQUEST, self.packet)
        self.assertEqual(self.exchange.abort(), 9000000)
        with self.assertRaises(ValueError): self.exchange.commit()
        with self.assertRaises(ValueError): self.exchange.abort()

    def test_caller_mutation_cannot_change_prepared_artifact(self) -> None:
        self.exchange.lock(9000000)
        self.exchange.prepare(BEFORE, DELTA, REQUEST, self.packet)
        self.packet["native_package"]["output_csv"] = "corrupt"
        self.assertNotEqual(self.exchange.commit()["output"], "corrupt")

    def test_zero_negative_boolean_price_refused(self) -> None:
        for price in (0, -1, True, 1.5):
            with self.subTest(price=price), self.assertRaises(ValueError): ConditionalExchange(digest(self.inputs), price)

    def test_unknown_cost_blocks_native_growth_gate(self) -> None:
        facts = {"cash_micro_usd": 1009000000, "profit_micro_usd": 9000000, "liability_micro_usd": 0,
                 "reserves_micro_usd": 0, "unknown_cost_count": 1}
        decision = {"eligible": True, "cost_micro_usd": 530000, "expected_incremental_value_micro_usd": 1000000}
        self.assertFalse(investment_gate(facts, decision, POLICY))
        facts["unknown_cost_count"] = 0
        self.assertTrue(investment_gate(facts, decision, POLICY))

    def test_seed_capital_is_not_earned_profit(self) -> None:
        facts = {"cash_micro_usd": 1000000000, "profit_micro_usd": 0, "liability_micro_usd": 0,
                 "reserves_micro_usd": 0, "unknown_cost_count": 0}
        decision = {"eligible": True, "cost_micro_usd": 530000, "expected_incremental_value_micro_usd": 1000000}
        self.assertFalse(investment_gate(facts, decision, POLICY))


class CommercialTests(unittest.TestCase):
    def test_default_counterexample_and_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old = simulate(base / "old", 41001, "strategic_default", "postpaid", POLICY)
            new = simulate(base / "new", 41001, "strategic_default", "conditional", POLICY)
            self.assertGreater(old["accepted"], 0)
            self.assertEqual(old["collected_orders"], 0)
            self.assertLess(old["model_profit_usd"], 0)
            self.assertGreater(new["collected_orders"], 0)
            self.assertGreater(new["model_profit_usd"], 0)
            self.assertEqual(audit(base / "old")["verdict"], "PASS_IN_SCOPE")
            self.assertEqual(audit(base / "new")["verdict"], "PASS_IN_SCOPE")

    def test_equal_tools_can_destroy_demand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = simulate(Path(tmp) / "parity", 41002, "equal_tool_parity", "conditional", POLICY)
            self.assertEqual(result["accepted"], 0)
            self.assertLess(result["model_profit_usd"], 0)

    def test_no_liquidity_is_not_assumed_payment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = simulate(Path(tmp) / "refusal", 41003, "reference", "conditional", POLICY, lock_failure=1)
            self.assertEqual(result["collected_orders"], 0)
            self.assertGreater(result["refused_locks"], 0)
            self.assertLess(result["model_profit_usd"], 0)

    def test_high_trust_friction_blocks_participation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = simulate(Path(tmp) / "friction", 41004, "reference", "conditional", POLICY, friction=100000000)
            self.assertEqual(result["accepted"], 0)

    def test_summary_corruption_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            simulate(root, 41005, "reference", "conditional", POLICY)
            summary = json.loads((root / "summary.json").read_bytes())
            summary["modeled_balances"]["profit_micro_usd"] += 1
            (root / "summary.json").write_text(json.dumps(summary))
            self.assertEqual(audit(root)["verdict"], "REJECTED")

    def test_refund_case_audits(self) -> None:
        policy = copy.deepcopy(POLICY)
        policy["scenarios"]["reference"]["warranty_rate"] = 1.0
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            result = simulate(root, 41006, "reference", "conditional", policy)
            self.assertGreater(result["accepted"], 0)
            self.assertLess(result["model_profit_usd"], 0)
            self.assertEqual(audit(root)["verdict"], "PASS_IN_SCOPE")

    def test_rehashed_unpaid_delivery_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            simulate(root, 41007, "reference", "conditional", POLICY)
            events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
            index = next(i for i, event in enumerate(events) if event["type"] == "collect")
            events.pop(index)
            previous = "0" * 64
            for n, event in enumerate(events, 1):
                event["seq"], event["previous"] = n, previous
                event["hash"] = digest({key: value for key, value in event.items() if key != "hash"})
                previous = event["hash"]
            (root / "events.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n")
            result = audit(root)
            self.assertEqual(result["verdict"], "REJECTED")
            self.assertTrue(any("Unpaid artifact" in error for error in result["failures"]), result)


if __name__ == "__main__": unittest.main()
