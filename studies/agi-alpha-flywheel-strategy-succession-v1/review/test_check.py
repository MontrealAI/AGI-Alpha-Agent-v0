import copy
import json
import unittest
from check import check, decode_input, operation_reserve
from challenge import challenge
from adjudicate import adjudicate, evidence_digest
from development_cases import plan, repair, calendar_dip, late_lock, mutation_cases


class IndependentReviewTests(unittest.TestCase):
    def test_useful_valid_plan_and_repair(self):
        for factory in (plan, repair, calendar_dip, late_lock):
            with self.subTest(factory=factory.__name__):
                e = factory()
                r = check(e)
                self.assertTrue(r["valid"], r["errors"])
                self.assertTrue(r["qualified"])
                self.assertEqual(r["lower_bound"], e["result"]["lower_bound"])
                self.assertLessEqual(r["counts"]["total"], operation_reserve(e))

    def test_consequential_mutations_refused(self):
        for name, envelope, expected in mutation_cases():
            with self.subTest(name=name):
                result = check(envelope)
                self.assertFalse(result["valid"])
                self.assertFalse(result["qualified"])
                self.assertIn(expected, [e["code"] for e in result["errors"]])
                self.assertLessEqual(result["counts"]["total"], operation_reserve(envelope))

    def test_deadline_failure_is_feasible_but_unqualified(self):
        e = plan()
        e["task"]["deadline"] = 5
        r = check(e)
        self.assertTrue(r["valid"])
        self.assertFalse(r["qualified"])
        self.assertTrue(r["optimal_if_bound"])

    def test_movement_failure_is_feasible_but_unqualified(self):
        e = repair()
        e["task"]["movement_limit"] = 1
        r = check(e)
        self.assertTrue(r["valid"])
        self.assertFalse(r["qualified"])

    def test_changed_calendar_does_not_reject_old_baseline(self):
        e = repair()
        # Baseline J3 occupies unavailable slots 4,5; the new result repairs it.
        self.assertTrue(check(e)["valid"])

    def test_locked_finish_propagates_through_dependency_chain(self):
        r = check(late_lock())
        self.assertEqual(r["lower_bound"]["critical"], 10)
        self.assertEqual(r["lower_bound"]["locked"], 7)
        self.assertTrue(r["optimal_if_bound"])

    def test_bound_gap_does_not_claim_nonoptimality(self):
        r = check(repair())
        self.assertTrue(r["valid"])
        self.assertFalse(r["optimal_if_bound"])
        self.assertEqual(r["lower_bound"]["value"], 7)

    def test_counts_are_reproducible(self):
        e = repair()
        self.assertEqual(check(e), check(copy.deepcopy(e)))
        r = check(e)
        self.assertEqual(r["counts"]["total"], sum(v for k,v in r["counts"].items() if k != "total"))

    def test_dense_reverse_order_dag_within_reserve(self):
        n, h = 18, 128
        jobs = [dict(id=f"J{i}",duration=1,crew=1,deps=[f"J{j}" for j in range(1,i)]) for i in range(n,0,-1)]
        t = dict(schema="release-plan/v1", id="dense-dev-boundary", kind="plan", jobs=jobs, capacity=[1]*h)
        r = dict(schema="release-plan-result/v1",task_id=t["id"],schedule=[dict(id=f"J{i}",start=i-1,end=i) for i in range(1,n+1)],
                 makespan=n,movement=0,lower_bound=dict(value=n,critical=n,load=n,locked=0),optimal_by_lower_bound=True,
                 dispatch_order=[f"J{i}" for i in range(1,n+1)],lookahead_steps=n,proof=[],authority=[])
        e = dict(task=t,result=r)
        verdict = check(e)
        self.assertTrue(verdict["valid"], verdict["errors"])
        self.assertLessEqual(verdict["counts"]["total"],operation_reserve(e))

    def test_false_criticism_is_refuted(self):
        e = plan()
        digest,_ = evidence_digest(e["task"],e["result"])
        claim = dict(schema="release-plan-challenge/v1",type="capacity",evidence_digest=digest,witness=dict(slot=0),
                     consequence="The jobs overlap, so the critic alleges overload.")
        verdict = adjudicate(e["task"],e["result"],claim)
        self.assertEqual(verdict["decision"],"REFUTED")
        self.assertEqual(verdict["witness_check"]["required_crew"],3)
        self.assertEqual(verdict["witness_check"]["permitted_crew"],3)
        self.assertFalse(verdict["regression_eligible"])

    def test_challenger_has_original_calendar_and_defect_is_checked(self):
        cases = {name:(e,code) for name,e,code in mutation_cases()}
        e,_ = cases["calendar_overload"]
        findings = challenge(e["task"],e["result"])
        self.assertTrue(findings["challenges"])
        for claim in findings["challenges"]:
            verdict = adjudicate(e["task"],e["result"],claim)
            self.assertEqual(verdict["decision"],"SUBSTANTIATED")
            self.assertTrue(verdict["regression_eligible"])

    def test_evidence_substitution_is_unsupported(self):
        e = calendar_dip()
        claim = dict(schema="release-plan-challenge/v1",type="capacity",evidence_digest="0"*64,witness=dict(slot=0))
        verdict = adjudicate(e["task"],e["result"],claim)
        self.assertEqual(verdict["decision"],"UNSUPPORTED")

    def test_protected_confirmation_not_admitted_to_development_memory(self):
        e = calendar_dip()
        digest,_ = evidence_digest(e["task"],e["result"])
        claim = dict(schema="release-plan-challenge/v1",type="capacity",evidence_digest=digest,witness=dict(slot=0))
        verdict = adjudicate(e["task"],e["result"],claim,phase="confirmation")
        self.assertEqual(verdict["decision"],"UNSUPPORTED")
        self.assertFalse(verdict["regression_eligible"])
        self.assertIsNone(verdict["artifact_check"])

    def test_json_conflicting_keys_and_nonfinite_refused(self):
        for raw in ('{"task":{},"task":{}}','{"x":NaN}','{"x":Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    decode_input(raw)

    def test_unrecognized_metadata_has_no_semantic_effect(self):
        e = plan()
        e["task"]["note"] = "A human-readable description only"
        e["result"]["strategy_digest"] = "a"*64
        self.assertTrue(check(e)["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
