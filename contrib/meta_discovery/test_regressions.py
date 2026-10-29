# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from alpha_factory_v1.core.runtime.meta_discovery.instrument import compile_plan, digest, update_belief, write_new
from alpha_factory_v1.core.runtime.meta_discovery.checker import check, reference
from alpha_factory_v1.core.runtime.meta_discovery.models import make_task, investigate
from alpha_factory_v1.core.runtime.meta_discovery.exchange import Exchange
from alpha_factory_v1.core.runtime.meta_discovery.economics import (
    Financials,
    Budget,
    decisions,
    priced_costs,
    correct_claim,
    requalify,
)
from alpha_factory_v1.core.runtime.meta_discovery.governance import (
    freeze,
    check_freeze,
    admit,
    training_view,
    compare_complete,
    research_admission,
)


class Rules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/dev/shm")
        self.root = Path(self.temp.name)
        self.task, self.private = make_task("membrane", 3)
        self.plan = compile_plan(self.task)
        self.db = Exchange(self.root / "x.sqlite")
        self.db.provision_simulated_buyer("buyer", "manager-usdc", 10000)
        self.db.offer("o", "campaign", "buyer", "manager-usdc", "USDC", 6, 1000, self.task, 10)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def fund(self):
        self.db.event("o", "consent", "consent", {"buyer": "buyer", "termsHash": self.db.terms_hash("o")})
        self.db.event("o", "fund", "fund", {"buyer": "buyer"})

    def ready(self):
        self.fund()
        self.db.event("o", "deliver", "deliver", {"artifact": self.plan})
        self.db.event("o", "verify", "verify", {})

    def settled(self):
        self.ready()
        self.db.event("o", "settle", "settle", {})

    def gate(self, **kw):
        d = dict(
            operation=True,
            causal_gain=False,
            fresh=True,
            bridge=False,
            blue_sky=False,
            profit=10,
            investment=False,
            successor_net=0,
            installed=True,
            full_gates=False,
        )
        d.update(kw)
        return decisions(**d)

    def test_01_conventional_profitable(self):
        self.assertEqual(reference(self.task)["cost"], self.plan["cost"])
        self.assertEqual(self.gate()["COMMERCIAL VIABILITY"], "CONTINUE")

    def test_02_novel_losing(self):
        self.assertEqual(self.gate(causal_gain=True, profit=-1)["COMMERCIAL VIABILITY"], "PIVOT")

    def test_03_base_specialist(self):
        f = Financials(revenue=100, collections=100)
        self.assertEqual(f.invest(20, -1)["decision"], "HOLD INVESTMENT")
        self.assertGreater(f.report()["profit"], 0)

    def test_04_cash_is_not_profit(self):
        f = Financials(opening=1000, expenses=100, payments=100)
        self.assertGreater(f.report()["cash"], 0)
        self.assertLess(f.report()["profit"], 0)

    def test_05_profit_before_payback(self):
        f = Financials(revenue=100, collections=100, historical_investment=1000)
        r = f.invest(20, 1)
        self.assertEqual(r["decision"], "CONTINUE")
        self.assertFalse(r["paybackComplete"])

    def test_06_liquidity_regression(self):
        f = Financials(revenue=1000, expenses=600, collections=650, payments=600, reserve=20, working_capital=30)
        self.assertEqual(
            (f.report()["profit"], f.report()["cash"], f.report()["receivables"], f.report()["available"]),
            (400, 50, 350, 0),
        )
        self.assertEqual(f.invest(200, 1)["shortfall"], 200)

    def test_07_liability_retained(self):
        r = Financials(expenses=60, payments=10).report()
        self.assertEqual(r["payables"], 50)
        self.assertEqual(r["profit"], -60)

    def test_08_capitalization_once(self):
        r = Financials(opening=1000, capex=200, amortization=20).report()
        self.assertEqual((r["cash"], r["profit"]), (800, -20))

    def test_09_false_funding(self):
        f = Financials(opening=1000, debt=100)
        self.assertEqual(f.invest(10, 1)["decision"], "HOLD INVESTMENT")
        self.assertEqual(f.invest(10, 1, "equity")["funding"], "equity")

    def test_10_failed_delivery_refund(self):
        self.fund()
        bad = copy.deepcopy(self.plan)
        bad["taskHash"] = "0" * 64
        self.db.event("o", "deliver", "deliver", {"artifact": bad})
        with self.assertRaises(ValueError):
            self.db.event("o", "verify", "verify", {})
        self.db.event("o", "refund", "refund", {})
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 0)

    def test_11_no_successor_advantage(self):
        self.assertEqual(self.gate(successor_net=-1)["SUCCESSOR VALUE"], "HOLD")
        self.assertEqual(self.gate()["COMMERCIAL VIABILITY"], "CONTINUE")

    def test_12_probe_not_flagship(self):
        authority = {"seed_budget": 10, "probe_budget": 3}
        self.assertTrue(admit({"cost": 2}, authority, "probe"))
        self.assertFalse(admit({"cost": 2}, authority, "flagship"))
        self.assertTrue(admit({}, authority, "meta"))

    def test_13_protected_resources(self):
        b = Budget(10, 3)
        b.charge(7)
        with self.assertRaises(ValueError):
            b.charge(1)
        b.charge(3, True)
        self.assertEqual(b.used, 10)

    def test_14_cost_quantities(self):
        rows = [
            dict(id="a", layer="A", basis="estimated", quantity=2, rate=3, justification="two calls"),
            dict(id="b", layer="B", basis="estimated", quantity=100, rate=1, justification="", fictional_human=True),
        ]
        self.assertEqual(priced_costs(rows)["conditionalTotal"], "6")
        with self.assertRaises(ValueError):
            priced_costs(rows + [rows[0]])

    def test_15_free_completed_alternative(self):
        from alpha_factory_v1.core.runtime.meta_discovery.market import operate

        r = operate(self.root / "market", 1, "free_completed_alternative", 1000000, "instrument")
        self.assertEqual(r["accepted"], 0)
        self.assertLess(r["financial"]["profit"], 0)

    def test_16_unsupported_friction(self):
        r = priced_costs([dict(id="friction", layer="A", basis="estimated", quantity=100, rate=10, justification="")])
        self.assertEqual(len(r["rejected"]), 1)

    def test_17_originals_fresh(self):
        p = self.root / "original.json"
        write_new(p, {"failure": True})
        with self.assertRaises(FileExistsError):
            write_new(p, {"failure": False})
        self.assertTrue(json.loads(p.read_text())["failure"])

    def test_18_funding_without_fake_build(self):
        self.settled()
        f = Financials(revenue=1000, collections=1000, expenses=200, payments=200)
        self.assertEqual(f.invest(100, 1)["decision"], "CONTINUE")
        self.assertEqual(self.gate(investment=True, successor_net=0)["SUCCESSOR VALUE"], "HOLD")

    def test_19_fresh_settings(self):
        a, _ = make_task("catalyst", 1)
        b, _ = make_task("photovoltaic", 1)
        self.assertNotEqual(a["source"], b["source"])
        self.assertNotEqual(a["experiments"][0]["action"], b["experiments"][0]["action"])

    def test_20_price_not_blue_sky(self):
        self.assertEqual(self.gate(profit=1000000)["BLUE SKY FLAGSHIP"], "HOLD")
        self.assertEqual(self.gate(profit=1, blue_sky=True, bridge=True)["BLUE SKY FLAGSHIP"], "CONTINUE")

    def test_21_old_asset_no_fresh_authority(self):
        asset = dict(agent="a", skillVersion="1", sourceHash="s", model="m", context="c", authority="x")
        self.assertFalse(requalify(asset, asset))
        self.assertTrue(requalify(asset, {**asset, "revoked": False}))

    def test_22_declined_prefunding(self):
        with self.assertRaises(ValueError):
            self.db.event("o", "f", "fund", {"buyer": "buyer"})
        self.assertEqual(self.db.preview("o")["state"], "offered")

    def test_23_forged_receipt(self):
        with self.assertRaises(ValueError):
            self.db.event("o", "f", "fund", {"buyer": "buyer", "confirmed": True})
        with self.assertRaises(PermissionError):
            self.db.download("o", "buyer")

    def test_24_preview_no_payload(self):
        self.ready()
        for _ in range(5):
            preview = self.db.preview("o")
            self.assertNotIn("key", preview)
            self.assertNotIn("ciphertext", preview)
            self.assertNotIn("selected", preview)
        with self.assertRaises(PermissionError):
            self.db.download("o", "buyer")

    def test_25_independent_acceptance(self):
        self.ready()
        self.db.event("o", "dispute", "dispute", {})
        self.assertEqual(json.loads(self.db.download("o", "buyer"))["taskHash"], digest(self.task))
        with self.assertRaises(ValueError):
            self.db.event("o", "forged", "settle", {"accepted": True})

    def test_26_duplicate_concurrency(self):
        self.ready()
        errors = []

        def run(action):
            d = Exchange(self.root / "x.sqlite")
            try:
                d.event("o", action, action, {})
            except ValueError as e:
                errors.append(str(e))
            finally:
                d.close()

        a = threading.Thread(target=run, args=("settle",))
        b = threading.Thread(target=run, args=("refund",))
        a.start()
        b.start()
        a.join()
        b.join()
        r = self.db.accounting("manager-usdc")
        self.assertEqual(r["cash"], 0)
        self.assertEqual(r["restricted"], 0)
        self.assertEqual(r["revenue"], 0)

    def test_27_interruption(self):
        self.fund()
        with self.assertRaises(InterruptedError):
            self.db.event("o", "deliver", "deliver", {"artifact": self.plan}, crash=True)
        self.db.close()
        self.db = Exchange(self.root / "x.sqlite")
        self.assertEqual(self.db.preview("o")["state"], "funded")
        self.db.event("o", "deliver", "deliver", {"artifact": self.plan})
        self.db.event("o", "verify", "verify", {})
        with self.assertRaises(InterruptedError):
            self.db.event("o", "settle", "settle", {}, crash=True)
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 0)
        self.db.event("o", "settle", "settle", {})
        self.db.event("o", "settle", "settle", {})
        self.assertEqual(self.db.accounting("manager-usdc")["cash"], 1000)

    def test_28_escrow_restricted(self):
        self.fund()
        a = self.db.accounting("manager-usdc")
        self.assertEqual(a["restricted"], 1000)
        self.assertEqual(a["revenue"], 0)
        r = Financials(opening=100, expenses=70, reserve=30, restricted=1000).report()
        self.assertEqual(r["available"], 0)

    def test_29_late_reversal(self):
        self.settled()
        self.db.event("o", "cb", "chargeback", {})
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 0)
        with self.assertRaises(PermissionError):
            self.db.download("o", "buyer")

    def test_30_credit_disabled(self):
        with self.assertRaisesRegex(ValueError, "credit disabled"):
            self.db.event("o", "credit", "credit", {})

    def test_31_protected_uneconomic(self):
        self.settled()
        self.assertEqual(self.gate(profit=-1)["COMMERCIAL VIABILITY"], "PIVOT")
        self.assertGreater(len(self.db.download("o", "buyer")), 0)

    def test_32_frozen_policy(self):
        p = self.root / "code"
        p.write_text("source")
        r = freeze([p], {"price": 1}, self.root / "freeze.json")
        check_freeze(r, {"price": 1})
        with self.assertRaises(ValueError):
            check_freeze(r, {"price": 2})

    def test_33_preflight_no_capture(self):
        self.assertFalse(admit({"installed_old_demo": True}, {"seed_budget": 1}, "flagship"))

    def test_34_detached_demo(self):
        self.assertEqual(self.gate(installed=False)["NATIVE INTEGRATION"], "HOLD")

    def test_35_exact_source(self):
        p = self.root / "code"
        p.write_text("source")
        r = freeze([p], {}, self.root / "freeze.json")
        p.write_text("changed")
        with self.assertRaises(ValueError):
            check_freeze(r, {})

    def test_36_mandatory_boundary(self):
        a = dict(agent="a", skillVersion="1", sourceHash="s", model="m", context="c", authority="x")
        self.assertFalse(requalify(a, {**a, "revoked": True}))

    def test_37_release_authority(self):
        self.assertFalse(admit({}, dict(seed_budget=10, remote_action=True), "meta"))
        self.assertEqual(self.gate()["RELEASE"], "HOLD")

    def test_38_no_solution_leak(self):
        with self.assertRaises(ValueError):
            training_view({**self.task, "truth": 2})

    def test_39_strong_comparator_retained(self):
        with self.assertRaises(ValueError):
            compare_complete([dict(id="1", comparator="weak", cost=1, status="accepted")], ["1"], "exact")

    def test_40_complete_denominator(self):
        r = compare_complete([dict(id="1", comparator="exact", cost=3, status="timeout")], ["1"], "exact")
        self.assertEqual((r["failed"], r["cost"]), (1, 3))

    def test_41_tie_preserved(self):
        self.assertEqual(self.gate()["META VALUE"], "IMPROVE")

    def test_42_rejection_not_business(self):
        self.assertEqual(self.gate(causal_gain=True, bridge=False)["BLUE SKY FLAGSHIP"], "HOLD")

    def test_43_lifecycle_loss(self):
        self.assertEqual(self.gate(causal_gain=True, profit=-30)["COMMERCIAL VIABILITY"], "PIVOT")

    def test_44_seed_before_downstream(self):
        self.assertTrue(admit({}, dict(seed_budget=10), "meta"))

    def test_45_route_units(self):
        with self.assertRaises(ValueError):
            self.db.offer("bad", "c", "buyer", "jobs-agialpha", "USDC", 6, 1, self.task, 2)

    def test_46_route_balances_distinct(self):
        self.db.offer("j", "c", "buyer", "jobs-agialpha", "AGIALPHA", 18, 1, self.task, 2)
        self.db.event("j", "jc", "consent", {"buyer": "buyer", "termsHash": self.db.terms_hash("j")})
        with self.assertRaises(ValueError):
            self.db.event("j", "jf", "fund", {"buyer": "buyer"})

    def test_47_raw_claim_refusal(self):
        self.assertEqual(research_admission("raw_generated", False, True, True), "HOLD")

    def test_48_formal_not_physical(self):
        self.assertEqual(research_admission("formally_verified_model", True, True, True), "HOLD")

    def test_49_correction_propagates(self):
        original = [
            dict(id="premise"),
            dict(id="delivery", depends=["premise"], cash=1000),
            dict(id="investment", depends=["delivery"]),
        ]
        result = correct_claim(original, "premise", "v2")
        self.assertEqual(result[2]["qualification"], "REQUALIFY")
        self.assertEqual(result[1]["cash"], 1000)
        self.assertNotIn("qualification", original[0])

    def test_50_paper_no_product(self):
        self.assertEqual(research_admission("independently_checked", False, False, True), "HOLD")

    def test_51_checked_product(self):
        self.assertEqual(research_admission("independently_checked", False, True, True), "CONTINUE")

    def test_52_model_change(self):
        a = dict(agent="a", skillVersion="1", sourceHash="s", model="m", context="c", authority="x")
        self.assertFalse(requalify(a, {**a, "model": "new", "revoked": False}))

    def test_53_optimal_plan(self):
        self.assertTrue(check(self.task, self.plan)["accepted"])

    def test_54_false_acceptance(self):
        p = copy.deepcopy(self.plan)
        p["cost"] += 1
        self.assertFalse(check(self.task, p)["accepted"])

    def test_55_timeout_preserved(self):
        p = compile_plan(self.task, max_states=1)
        self.assertEqual(p["status"], "INCONCLUSIVE")
        self.assertFalse(check(self.task, p)["accepted"])

    def test_56_actual_investigation(self):
        obs = investigate(self.task, self.private, self.plan["selected"])
        self.assertEqual(update_belief(self.task, obs)["status"], "DECISIVE")

    def test_57_out_of_model(self):
        self.assertEqual(update_belief(self.task, {"e0": "1000000"})["status"], "MODEL_MISMATCH")

    def test_58_event_rebinding(self):
        self.fund()
        with self.assertRaises(ValueError):
            self.db.event("o", "fund", "refund", {})

    def test_59_substituted_bytes(self):
        self.settled()
        self.db.db.execute("UPDATE orders SET artifact_hash='bad' WHERE id='o'")
        with self.assertRaises(ValueError):
            self.db.download("o", "buyer")

    def test_60_silent_buyer_timeout(self):
        self.fund()
        self.db.event("o", "timeout", "timeout", {}, 11)
        self.assertEqual(self.db.accounting("manager-usdc")["restricted"], 0)

    def test_61_fraction_exponent_refused(self):
        self.task["experiments"][0]["prediction"]["m0"] = ["1e999999999", "2e999999999"]
        with self.assertRaises(ValueError):
            compile_plan(self.task)

    def test_62_forged_impossibility(self):
        bad = copy.deepcopy(self.plan)
        bad["unseparable"] = [["m0", "m1"]]
        self.assertFalse(check(self.task, bad)["accepted"])

    def test_63_duplicate_witness(self):
        bad = copy.deepcopy(self.plan)
        bad["witnesses"].append(copy.deepcopy(bad["witnesses"][0]))
        self.assertFalse(check(self.task, bad)["accepted"])

    def test_64_physical_claim_escalation(self):
        bad = copy.deepcopy(self.plan)
        bad["physicalQualified"] = True
        self.assertFalse(check(self.task, bad)["accepted"])

    def test_65_malformed_witness(self):
        for value in [None, True, {}, [{"models": [{}, []], "experiments": []}]]:
            bad = copy.deepcopy(self.plan)
            bad["witnesses"] = value
            self.assertFalse(check(self.task, bad)["accepted"])

    def test_66_event_time_regression(self):
        self.db.event("o", "consent", "consent", {"buyer": "buyer", "termsHash": self.db.terms_hash("o")}, 3)
        with self.assertRaises(ValueError):
            self.db.event("o", "fund", "fund", {"buyer": "buyer"}, 2)
        self.assertEqual(self.db.preview("o")["state"], "offered")

    def test_67_crash_consent_and_funding(self):
        consent = {"buyer": "buyer", "termsHash": self.db.terms_hash("o")}
        with self.assertRaises(InterruptedError):
            self.db.event("o", "c", "consent", consent, crash=True)
        with self.assertRaises(ValueError):
            self.db.event("o", "f", "fund", {"buyer": "buyer"})
        self.db.event("o", "c", "consent", consent)
        with self.assertRaises(InterruptedError):
            self.db.event("o", "f", "fund", {"buyer": "buyer"}, crash=True)
        self.assertEqual(self.db.accounting("manager-usdc")["restricted"], 0)
        self.db.event("o", "f", "fund", {"buyer": "buyer"})
        self.assertEqual(self.db.accounting("manager-usdc")["restricted"], 1000)

    def test_68_crash_verify_and_refund(self):
        self.fund()
        self.db.event("o", "d", "deliver", {"artifact": self.plan})
        with self.assertRaises(InterruptedError):
            self.db.event("o", "v", "verify", {}, crash=True)
        self.assertEqual(self.db.preview("o")["state"], "delivered")
        self.db.event("o", "v", "verify", {})
        with self.assertRaises(InterruptedError):
            self.db.event("o", "r", "refund", {}, crash=True)
        self.assertEqual(self.db.accounting("manager-usdc")["restricted"], 1000)
        self.db.event("o", "r", "refund", {})
        self.db.event("o", "r", "refund", {})
        self.assertEqual(self.db.accounting("manager-usdc")["restricted"], 0)

    def test_69_crash_chargeback(self):
        self.settled()
        with self.assertRaises(InterruptedError):
            self.db.event("o", "cb", "chargeback", {}, crash=True)
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 1000)
        self.db.event("o", "cb", "chargeback", {})
        self.db.event("o", "cb", "chargeback", {})
        self.assertEqual(self.db.accounting("manager-usdc")["cash"], 0)

    def test_70_observation_resource_bound(self):
        with self.assertRaises(ValueError):
            update_belief(self.task, {"e0": "1e999999999"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
