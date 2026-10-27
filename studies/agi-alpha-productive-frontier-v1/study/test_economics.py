# SPDX-License-Identifier: Apache-2.0
import copy
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("frontier_economics", Path(__file__).with_name("economics.py"))
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)


def config(days=3):
    c = json.loads(ec.CONFIG.read_text())
    c["days"] = days
    c["offers"] = [copy.deepcopy(c["offers"][0])]
    c["offers"][0].update(model_seconds_assumed=0, core_deadline_seconds=100)
    c["price_fractions"] = [0.25]
    c["base"].update(
        origin_exact_jobs=0, origin_collection_usd=0, production_setup_usd=0, seed_capital_usd=2500, reserve_usd=0,
        leads_per_day=0, model_pipeline_usd=1, tools_storage_network_usd=0, intake_cost_usd=0,
        daily_operating_overhead_usd=0, qualified_lead_acquisition_usd=0,
        setup_capacity_seconds=0, retention_capacity_seconds=0, gym_capacity_seconds=0,
        collection_default_probability=0, collection_delay_days=[0], collection_delay_probabilities=[1],
        package_acceptance_probability=1, initial_paid_cost_fraction=1, payment_delay_cost_days=7,
        daily_capacity_seconds=1000, shift_probability=0, transfer_success_probability=1,
        obsolescence_day=999,
    )
    return c


def measured(beta=1.0, work=0.1, gym=0.2):
    s = {"beta": [beta], "work": [work], "gym": [gym]}
    return {
        "confirmation": copy.deepcopy(s), "shift": copy.deepcopy(s),
        "selection_raw": {"summary": {
            "adaptive_fallback": {"seconds_total": 0.5, "accepted": 8, "n": 8},
            "work48_fallback": {"seconds_total": 0.2, "accepted": 8, "n": 8},
            "gym48_fallback": {"seconds_total": 0.7, "accepted": 8, "n": 8},
        }},
    }


def technical_fixture(path):
    rows = [dict(case=0, method=name, seconds=secs, accepted=accepted)
            for name, secs, accepted in [
                ("adaptive_krylov", 2, "False"), ("schur", 3, "True"),
                ("work_pod48", 1, "False"), ("gym_pod48", 1, "False")]]
    for split in ("confirmation", "shift"):
        with (path / f"{split}.csv").open("w") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    chains = [dict(split=split, case=0, method=name, seconds=seconds, accepted="True")
              for split in ("confirmation", "shift")
              for name, seconds in [("adaptive_fallback", 7), ("work48_fallback", 11),
                                    ("gym48_fallback", 13)]]
    with (path / "fallback_validation.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=chains[0].keys())
        writer.writeheader()
        writer.writerows(chains)
    (path / "selection_results.json").write_text(json.dumps(measured()["selection_raw"]))


def event(**changes):
    e = dict(id="test-order", offer=0, value_z=0, compatible=0, quality=0.1,
             default=0.9, delay_u=0.1, shift=0.9, transfer=0.1, sample=0)
    e.update(changes)
    return e


def run(c, daily, policy="competent_beta", m=None):
    return ec.simulate(123, "base", policy, c, m or measured(), daily)


class UnobservedLead:
    def __getitem__(self, key):
        raise AssertionError(f"Unacquired lead field was inspected: {key}")


def prototype_config(days):
    c = config(days)
    offer = copy.deepcopy(c["offers"][0])
    offer.update(id="screen", productization_usd=1)
    c["offers"].append(offer)
    c["base"].update(offer_probabilities=[0.5, 0.5, 0], daily_capacity_seconds=400,
                     prototype_capacity_seconds=900, prototype_success_probability=0.01)
    return c


class EconomicIntegrityTests(unittest.TestCase):
    def test_setup_work_carries_across_days_before_audit_is_available(self):
        c = config(3)
        c["base"].update(setup_capacity_seconds=900, daily_capacity_seconds=400, production_setup_usd=19)
        r = run(c, [[event(id=f"day-{day}")] for day in range(3)])
        self.assertEqual([x["preparation_backlog_end_seconds"] for x in r["path"]], [500, 100, 0])
        self.assertEqual([x["preparation_consumed_seconds"] for x in r["path"]], [400, 400, 100])
        self.assertEqual([x["ready_offers"] for x in r["path"]], [[], [], ["audit"]])
        self.assertEqual([x["orders_total"] for x in r["path"]], [0, 0, 1])
        self.assertEqual([x["production_reserved_seconds"] for x in r["path"]], [0, 0, 100])
        self.assertEqual([x["unused_capacity_seconds"] for x in r["path"]], [0, 0, 200])
        self.assertEqual(r["cost_C"], 19)
        self.assertEqual(r["preparation_committed_seconds"], 900)
        self.assertEqual(r["preparation_consumed_seconds"], 900)
        self.assertEqual(r["gross_capacity_seconds"], 1200)
        self.assertEqual(r["weighted_units_per_total_capacity_hour"], 3)
        self.assertEqual(r["weighted_units_per_processing_hour"], 3600)

    def test_exact_preparation_boundary_activates_without_free_production(self):
        c = config(2)
        c["base"].update(setup_capacity_seconds=400, daily_capacity_seconds=400)
        r = run(c, [[event(id="first")], [event(id="second")]])
        self.assertTrue(r["path"][0]["setup_ready"])
        self.assertEqual(r["path"][0]["orders_total"], 0)
        self.assertEqual(r["path"][0]["unused_capacity_seconds"], 0)
        self.assertEqual(r["path"][1]["orders_total"], 1)
        self.assertEqual(r["production_reserved_seconds"], 100)
        self.assertEqual(r["unused_capacity_seconds"], 300)

    def test_horizon_does_not_complete_or_erase_unfinished_setup(self):
        c = config(2)
        c["base"].update(setup_capacity_seconds=900, daily_capacity_seconds=400, production_setup_usd=17)
        r = run(c, [[], []])
        self.assertFalse(r["setup_ready"])
        self.assertEqual(r["ready_offerings"], 0)
        self.assertEqual(r["unfinished_preparation_seconds"], 100)
        self.assertEqual(r["unfinished_preparation_tasks"], 1)
        self.assertEqual(r["preparation_consumed_seconds"], 800)
        self.assertEqual(r["preparation_tasks"][0]["status"], "pending")
        self.assertIsNone(r["preparation_tasks"][0]["completed_day"])
        self.assertEqual(r["profit"], -17)
        self.assertEqual(r["cost_C"], 17)

    def test_retention_and_gym_cannot_activate_before_all_preparation_finishes(self):
        for policy, retention, gym, target in [("shared_work", 900, 0, "work"),
                                                ("shared_gym", 300, 600, "gym"),
                                                ("private_work", 225, 0, "work")]:
            with self.subTest(policy=policy):
                c = config(3)
                c["base"].update(retention_capacity_seconds=retention, gym_capacity_seconds=gym,
                                 daily_capacity_seconds=400)
                r = run(c, [[], [], []], policy)
                self.assertEqual([x["mode"] for x in r["path"]], ["beta", "beta", target])
                self.assertEqual([x["committed_mode"] for x in r["path"]], [target] * 3)
                self.assertEqual([x["pending_mode"] for x in r["path"]], [target, target, None])
                self.assertEqual(r["preparation_consumed_seconds"], 900)
                self.assertEqual(r["preparation_tasks"][1]["completed_day"], 2)

    def test_pending_selective_investment_is_not_purchased_again_at_next_checkpoint(self):
        c = config(8)
        c["base"].update(retention_capacity_seconds=5000, daily_capacity_seconds=400,
                         compute_usd_per_hour=1000, seed_capital_usd=100000)
        r = run(c, [[] for _ in range(8)], "selective", measured(beta=100, work=1, gym=2))
        self.assertEqual(sum(x["action"] == "invest" for x in r["decisions"]), 1)
        self.assertEqual(r["mode"], "beta")
        self.assertEqual(r["committed_mode"], "work")
        self.assertEqual(r["pending_mode"], "work")
        self.assertEqual(r["preparation_committed_seconds"], 5000)
        self.assertEqual(r["preparation_consumed_seconds"], 3200)
        self.assertEqual(r["unfinished_preparation_seconds"], 1800)
        self.assertEqual(r["cost_B"], 52)

    def test_failed_prototype_requires_complete_work_and_retains_cost(self):
        pending = run(prototype_config(2), [[], []])
        task = next(x for x in pending["preparation_tasks"] if x["kind"] == "prototype")
        self.assertEqual(task["remaining_seconds"], 100)
        self.assertNotIn("success", task)
        self.assertEqual(pending.get("failed_prototypes", 0), 0)
        self.assertEqual(pending["cost_C"], 1)
        completed = run(prototype_config(3), [[], [], []])
        task = next(x for x in completed["preparation_tasks"] if x["kind"] == "prototype")
        self.assertEqual(task["completed_day"], 2)
        self.assertFalse(task["success"])
        self.assertEqual(completed["failed_prototypes"], 1)
        self.assertEqual(completed["preparation_consumed_seconds"], 900)
        self.assertEqual(completed["cost_C"], 1)
        self.assertEqual(completed["path"][-1]["ready_offers"], ["audit"])
        commitment = next(x for x in completed["decisions"] if x["action"] == "prototype")
        self.assertNotIn("success", commitment)

    def test_successful_prototype_is_not_offered_until_its_work_is_done(self):
        c = prototype_config(3)
        c["base"]["prototype_success_probability"] = 1
        r = run(c, [[event(offer=1, id=f"screen-{day}")] for day in range(3)])
        self.assertEqual([x["ready_offers"] for x in r["path"]],
                         [["audit"], ["audit"], ["audit", "screen"]])
        self.assertEqual([x["orders_total"] for x in r["path"]], [0, 0, 1])
        completions = [x for x in r["decisions"] if x["action"] == "prototype_completed"]
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0]["day"], 2)
        self.assertTrue(completions[0]["success"])

    def test_unready_or_exhausted_capacity_never_reads_or_buys_a_lead(self):
        for preparation in (400, 500):
            with self.subTest(preparation=preparation):
                c = config(1)
                c["base"].update(setup_capacity_seconds=preparation, daily_capacity_seconds=400,
                                 qualified_lead_acquisition_usd=8)
                r = run(c, [[UnobservedLead()]])
                self.assertEqual(r.get("leads", 0), 0)
                self.assertEqual(r.get("orders", 0), 0)
                self.assertEqual(r["cost_A"], 0)
                self.assertEqual(r["preparation_consumed_seconds"], 400)

    def test_capacity_gate_rechecks_before_buying_the_next_hidden_lead(self):
        c = config(1)
        c["base"].update(daily_capacity_seconds=100, qualified_lead_acquisition_usd=8)
        r = run(c, [[event(), UnobservedLead()]])
        self.assertEqual(r["leads"], 1)
        self.assertEqual(r["orders"], 1)
        self.assertEqual(r["production_reserved_seconds"], 100)
        acquisition = [x for x in r["charges"] if x["reason"] == "assumed qualified lead acquisition"]
        self.assertEqual(len(acquisition), 1)

    def test_zero_duration_preparation_completes_with_zero_capacity(self):
        c = config(1)
        c["base"]["daily_capacity_seconds"] = 0
        r = run(c, [[UnobservedLead()]], "shared_work")
        self.assertTrue(r["setup_ready"])
        self.assertEqual(r["mode"], "work")
        self.assertIsNone(r["pending_mode"])
        self.assertEqual(r["unfinished_preparation_tasks"], 0)
        self.assertEqual(r["preparation_consumed_seconds"], 0)
        self.assertEqual(r["gross_capacity_seconds"], 0)
        self.assertEqual(r.get("orders", 0), 0)

    def test_future_suffix_cannot_change_a_pending_preparation_prefix(self):
        c = config(8)
        c["base"].update(setup_capacity_seconds=900, retention_capacity_seconds=900,
                         daily_capacity_seconds=400)
        prefix = [[event(id=f"prefix-{day}")] for day in range(3)]
        a = run(c, prefix + [[] for _ in range(5)], "shared_work")
        b = run(c, prefix + [[event(id=f"later-{day}-{j}") for j in range(3)] for day in range(5)],
                "shared_work")
        self.assertEqual(a["path"][:3], b["path"][:3])
        self.assertEqual([x for x in a["decisions"] if x["day"] < 3],
                         [x for x in b["decisions"] if x["day"] < 3])

    def test_unsupported_kernel_overrun_fails_instead_of_borrowing_capacity(self):
        c = config(1)
        c["offers"][0]["core_deadline_seconds"] = 5
        c["base"]["daily_capacity_seconds"] = 5
        with self.assertRaisesRegex(ValueError, "unsupported overrun"):
            run(c, [[event()]], m=measured(beta=6))

    def test_unprofitable_acquisition_blocks_optional_productization(self):
        c = config(60)
        protocol = json.loads(ec.CONFIG.read_text())
        c["offers"] = copy.deepcopy(protocol["offers"])
        c["price_fractions"] = protocol["price_fractions"]
        c["base"].update(qualified_lead_acquisition_usd=8, intake_cost_usd=0.15)
        result = ec.simulate(123, "low_wtp", "competent_beta", c, measured(), [[] for _ in range(60)])
        self.assertEqual(result.get("leads", 0), 0)
        self.assertEqual(result["cost_C"], 0)
        self.assertFalse(any(d["action"] == "prototype" for d in result["decisions"]))
        self.assertEqual(result["path"][-1]["offers"], 1)

    def test_seed_money_is_not_earned_revenue(self):
        c = config()
        a = run(c, [[], [], []])
        c["base"]["seed_capital_usd"] += 1000
        b = run(c, [[], [], []])
        self.assertEqual((a["collections"], a["profit"]), (0, 0))
        self.assertEqual(a["profit"], b["profit"])
        self.assertAlmostEqual(b["cash"] - a["cash"], 1000)

    def test_cash_and_accrued_obligations_reconcile(self):
        c = config()
        c["base"].update(initial_paid_cost_fraction=0.7, reserve_usd=20)
        r = run(c, [[event()], [], []])
        costs = sum(r[k] for k in ("cost_A", "cost_B", "cost_C"))
        self.assertAlmostEqual(r["profit"], r["collections"] - costs)
        self.assertAlmostEqual(r["cash"], r["seed_capital"] + r["collections"] - r["paid_costs"])
        self.assertAlmostEqual(r["obligations"], costs - r["paid_costs"])
        self.assertAlmostEqual(r["available"], r["seed_capital"] + r["profit"] - r["reserves"])

    def test_default_does_not_create_a_collection(self):
        c = config()
        c["base"]["collection_default_probability"] = 0.5
        r = run(c, [[event(default=0.1)], [], []])
        self.assertEqual(r["orders"], 1)
        self.assertEqual(r["collections"], 0)
        self.assertLess(r["profit"], 0)
        self.assertGreater(r["cost_A"], 0)

    def test_failed_delivery_refunds_the_full_customer_price(self):
        c = config()
        c["base"]["package_acceptance_probability"] = 0.97
        r = run(c, [[event(quality=0.99)], [], []])
        self.assertEqual(r["orders"], 1)
        self.assertEqual(r["accepted"], 0)
        self.assertEqual(r["quality_adjusted_units"], 0)
        self.assertAlmostEqual(r["refunds"], r["collections"])
        self.assertLess(r["profit"], 0)

    def test_delayed_invoice_is_excluded_from_available_funds(self):
        c = config()
        c["base"]["collection_delay_days"] = [30]
        r = run(c, [[event()], [], []])
        self.assertEqual(r["collections"], 0)
        self.assertGreater(r["receivables_excluded"], 0)
        self.assertLess(r["available"], r["seed_capital"])

    def test_future_lead_suffix_cannot_change_prior_actions_or_balances(self):
        c = config(8)
        prefix = [[event(id="prefix")], [], []]
        a = run(c, prefix + [[] for _ in range(5)], "selective")
        b = run(c, prefix + [[event(id=f"future-{d}-{j}") for j in range(3)] for d in range(5)], "selective")
        self.assertEqual(a["path"][:3], b["path"][:3])
        self.assertEqual([d for d in a["decisions"] if d["day"] < 3],
                         [d for d in b["decisions"] if d["day"] < 3])

    def test_identical_library_contents_and_permissions_add_no_graph_benefit(self):
        c = config()
        daily = [[event()], [], []]
        a = run(c, daily, "shared_work")
        b = run(c, daily, "ordinary_library")
        for key in ("profit", "collections", "cost_A", "cost_B", "cost_C", "path", "orders", "accepted"):
            self.assertEqual(a.get(key, 0), b.get(key, 0))

    def test_final_prototype_schema_can_be_used_for_every_policy(self):
        m = measured()
        self.assertEqual(ec.selection_seconds(m, "beta"), 0.5)
        self.assertEqual(ec.selection_seconds(m, "work"), 0.2)
        self.assertEqual(ec.selection_seconds(m, "gym"), 0.7)

    def test_selective_and_forced_same_investment_do_not_bill_upkeep_twice(self):
        c = config(31)
        c["base"].update(compute_usd_per_hour=1000, seed_capital_usd=100000)
        m = measured(beta=100, work=1, gym=2)
        daily = [[] for _ in range(31)]
        selected = run(c, daily, "selective", m)
        forced = run(c, daily, "shared_work", m)
        self.assertEqual(selected["mode"], "work")
        self.assertEqual(sum(d["action"] == "invest" for d in selected["decisions"]), 1)
        self.assertEqual(forced["mode"], "work")
        self.assertAlmostEqual(selected["cost_B"], forced["cost_B"])
        self.assertAlmostEqual(selected["cost_C"], forced["cost_C"])

    def test_realized_transfer_or_runtime_does_not_grant_free_capacity_lookahead(self):
        c = config(1)
        c["base"]["daily_capacity_seconds"] = 5
        m = measured()
        m["confirmation"]["beta"] = [1, 10]
        a = run(c, [[event(sample=0)]], m=m)
        b = run(c, [[event(sample=1)]], m=m)
        self.assertEqual(a.get("orders", 0), b.get("orders", 0))

    def test_job_commitment_respects_available_cost_budget(self):
        c = config(1)
        c["base"].update(seed_capital_usd=10, model_pipeline_usd=100)
        c["offers"][0]["human_hours_estimate"] = 8
        r = run(c, [[event()]])
        self.assertEqual(r.get("orders", 0), 0)
        self.assertGreaterEqual(r["available"], 0)

    def test_common_technology_upgrade_scales_complete_measured_chains_equally(self):
        c = config()
        c["base"]["post_upgrade_ordinary_time_factor"] = 0.5
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            technical_fixture(path)
            m = ec.measured_costs(path)
        for mode, expected in [("beta", 3.5), ("work", 5.5), ("gym", 6.5)]:
            seconds = ec.core_seconds(m, mode, c["offers"][0], event(), c["base"], True)
            self.assertAlmostEqual(seconds, expected)

    def test_missing_acceptance_evidence_cannot_become_a_timing_only_success(self):
        for missing_from in ("fallback", "selection"):
            with self.subTest(missing_from=missing_from), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                technical_fixture(path)
                if missing_from == "fallback":
                    target = path / "fallback_validation.csv"
                    with target.open() as handle:
                        rows = list(csv.DictReader(handle))
                    for row in rows:
                        del row["accepted"]
                    with target.open("w") as handle:
                        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                else:
                    target = path / "selection_results.json"
                    result = json.loads(target.read_text())
                    del result["summary"]["adaptive_fallback"]["accepted"]
                    target.write_text(json.dumps(result))
                with self.assertRaises((KeyError, ValueError)):
                    ec.measured_costs(path)

    def test_numerically_rejected_outputs_cannot_become_billable_from_short_runtime(self):
        for rejected_in in ("fallback", "selection"):
            with self.subTest(rejected_in=rejected_in), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                technical_fixture(path)
                if rejected_in == "fallback":
                    target = path / "fallback_validation.csv"
                    with target.open() as handle:
                        rows = list(csv.DictReader(handle))
                    rows[0]["accepted"] = "False"
                    with target.open("w") as handle:
                        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                else:
                    target = path / "selection_results.json"
                    result = json.loads(target.read_text())
                    result["summary"]["adaptive_fallback"]["accepted"] = 7
                    target.write_text(json.dumps(result))
                with self.assertRaises(ValueError):
                    ec.measured_costs(path)

    def test_cash_limited_enterprise_cannot_buy_an_unaffordable_lead(self):
        c = config(1)
        c["base"].update(seed_capital_usd=3, qualified_lead_acquisition_usd=8)
        r = run(c, [[event()]])
        self.assertEqual(r.get("leads", 0), 0)
        self.assertEqual(r.get("orders", 0), 0)
        self.assertEqual(r["available"], 3)

    def test_uncollected_invoice_balance_does_not_peek_at_future_defaults(self):
        c = config(1)
        c["base"].update(collection_delay_days=[30], collection_default_probability=0.5)
        a = run(c, [[event(default=0.1)]])
        b = run(c, [[event(default=0.9)]])
        self.assertEqual(a["collections"], b["collections"])
        self.assertEqual(a["available"], b["available"])
        self.assertEqual(a["receivables_excluded"], b["receivables_excluded"])


if __name__ == "__main__":
    unittest.main()
