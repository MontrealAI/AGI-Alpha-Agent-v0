import unittest
from engine import Scheduler


class SchedulerContract(unittest.TestCase):
    def setUp(self):
        self.queue = Scheduler(5)

    def unchanged_error(self, method, *args):
        before = self.queue.snapshot()
        with self.assertRaises(ValueError):
            getattr(self.queue, method)(*args)
        self.assertEqual(self.queue.snapshot(), before)

    def check_used(self, expected):
        snapshot = self.queue.snapshot()
        self.assertEqual(snapshot["used"], expected)
        self.assertEqual(expected, sum(j["cost"] for j in snapshot["jobs"].values()
                                       if j["state"] == "running"))
        self.assertTrue(0 <= expected <= snapshot["capacity"])
        for row in snapshot["jobs"].values():
            self.assertEqual(row["lease"] is None, row["state"] != "running")

    def test_dependency_ownership_and_all_non_success_states_block(self):
        self.queue.add("a", "root", 2, [])
        self.unchanged_error("add", "b", "foreign", 1, ["root"])
        self.queue.add("a", "child", 3, ["root"])
        self.unchanged_error("claim", "a", "child", "child-lease")
        self.queue.claim("a", "root", "r1")
        self.unchanged_error("claim", "a", "child", "child-lease")
        self.queue.finish("a", "root", "r1", False)
        self.unchanged_error("claim", "a", "child", "child-lease")
        self.queue.claim("a", "root", "r2")
        self.queue.finish("a", "root", "r2", True)
        self.queue.claim("a", "child", "child-lease")
        self.check_used(3)
        self.queue.add("a", "canceled", 1, [])
        self.queue.add("a", "blocked", 1, ["canceled"])
        self.queue.cancel("a", "canceled")
        self.unchanged_error("claim", "a", "blocked", "blocked-lease")

    def test_failure_retry_does_not_release_new_attempt(self):
        self.queue.add("a", "job", 5, [])
        self.queue.claim("a", "job", "old")
        self.queue.finish("a", "job", "old", False)
        self.check_used(0)
        self.queue.finish("a", "job", "old", False)
        self.unchanged_error("finish", "a", "job", "old", True)
        self.unchanged_error("claim", "a", "job", "old")
        self.queue.claim("a", "job", "new")
        before = self.queue.snapshot()
        self.queue.finish("a", "job", "old", False)
        self.assertEqual(before, self.queue.snapshot())
        self.check_used(5)
        self.queue.finish("a", "job", "new", True)
        self.queue.finish("a", "job", "new", True)
        self.queue.finish("a", "job", "old", False)
        self.unchanged_error("finish", "a", "job", "new", False)
        self.unchanged_error("cancel", "a", "job")
        self.check_used(0)

    def test_lease_names_never_reused_in_any_lifecycle(self):
        for index, outcome in enumerate(("running", "failed", "succeeded", "canceled")):
            with self.subTest(outcome=outcome):
                self.queue = Scheduler(5)
                self.queue.add("a", "one", 2, [])
                self.queue.add("a", "two", 2, [])
                self.queue.add("b", "three", 1, [])
                self.queue.claim("a", "one", "lease")
                if outcome == "failed":
                    self.queue.finish("a", "one", "lease", False)
                elif outcome == "succeeded":
                    self.queue.finish("a", "one", "lease", True)
                elif outcome == "canceled":
                    self.queue.cancel("a", "one")
                if outcome != "running":
                    self.unchanged_error("claim", "a", "one", "lease")
                self.unchanged_error("claim", "a", "two", "lease")
                self.unchanged_error("claim", "b", "three", "lease")
                self.queue.claim("a", "two", "fresh")
                self.check_used(4 if outcome == "running" else 2)

    def test_capacity_claim_retry_and_unpoisoned_rejected_lease(self):
        self.queue.add("a", "one", 3, [])
        self.queue.add("b", "two", 3, [])
        self.queue.add("a", "small", 2, [])
        original = self.queue.claim("a", "one", "one-lease")
        self.assertEqual(self.queue.claim("a", "one", "one-lease"), original)
        self.unchanged_error("claim", "a", "one", "replacement")
        self.unchanged_error("claim", "b", "two", "retry")
        self.queue.claim("a", "small", "replacement")
        self.check_used(5)
        self.queue.cancel("a", "one")
        self.queue.claim("b", "two", "retry")
        self.check_used(5)

    def test_cancel_invalidates_only_active_lease(self):
        self.queue.add("a", "job", 5, [])
        self.queue.claim("a", "job", "failed")
        self.queue.finish("a", "job", "failed", False)
        self.queue.claim("a", "job", "active")
        self.queue.cancel("a", "job")
        self.queue.cancel("a", "job")
        self.check_used(0)
        for success in (False, True):
            self.unchanged_error("finish", "a", "job", "active", success)
        self.queue.finish("a", "job", "failed", False)
        self.unchanged_error("claim", "a", "job", "later")
        self.assertEqual(self.queue.snapshot()["jobs"]["job"]["state"], "canceled")
        self.queue.add("a", "pending", 1, [])
        self.queue.cancel("a", "pending")
        self.queue.cancel("a", "pending")
        self.check_used(0)

    def test_job_identity_ordering_and_copy_isolation(self):
        self.queue.add("a", "x", 1, [])
        self.queue.add("a", "y", 1, [])
        deps = ["x", "y"]
        result = self.queue.add("a", "z", 1, deps)
        deps.clear()
        result["deps"].clear()
        result["state"] = "running"
        self.assertEqual(self.queue.add("a", "z", 1, ["x", "y"])["deps"], ["x", "y"])
        self.unchanged_error("add", "a", "z", 1, ["y", "x"])
        self.unchanged_error("add", "a", "z", 2, ["x", "y"])
        self.unchanged_error("add", "b", "z", 1, ["x", "y"])
        snap = self.queue.snapshot()
        snap["jobs"]["z"]["deps"].clear()
        snap["jobs"].clear()
        claim = self.queue.claim("a", "x", "lease")
        claim["lease"] = "corrupted"
        finish = self.queue.finish("a", "x", "lease", True)
        finish["state"] = "pending"
        cancel = self.queue.cancel("a", "y")
        cancel["state"] = "pending"
        self.assertEqual(self.queue.snapshot()["jobs"]["x"]["state"], "succeeded")
        self.assertEqual(self.queue.snapshot()["jobs"]["y"]["state"], "canceled")
        self.assertEqual(self.queue.snapshot()["jobs"]["z"]["deps"], ["x", "y"])
        self.queue.add("a", "x", 1, [])
        self.check_used(0)

    def test_invalid_inputs_and_ownership_are_atomic(self):
        for capacity in (0, -1, True, 1.0, None, "5"):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                Scheduler(capacity)
        self.queue.add("a", "root", 1, [])
        for cost in (0, -1, 6, True, 1.0, None):
            self.unchanged_error("add", "a", "new", cost, [])
        for deps in (None, (), "root", ["root", "root"], ["missing"], ["new"], [[]], [""]):
            self.unchanged_error("add", "a", "new", 1, deps)
        for bad in (None, "", 2, True, []):
            self.unchanged_error("add", bad, "new", 1, [])
            self.unchanged_error("add", "a", bad, 1, [])
            self.unchanged_error("claim", "a", "root", bad)
        self.queue.claim("a", "root", "lease")
        for bad in (0, 1, "True", None, []):
            self.unchanged_error("finish", "a", "root", "lease", bad)
        for owner, job in (("b", "root"), ("a", "missing"), ("", "root")):
            self.unchanged_error("claim", owner, job, "lease")
            self.unchanged_error("finish", owner, job, "lease", True)
            self.unchanged_error("cancel", owner, job)
        self.unchanged_error("finish", "a", "root", "missing", True)
        self.check_used(1)

    def test_case_sensitive_identifiers_have_no_reserved_names(self):
        for job in ("used", "capacity", "__proto__", "Job", "job"):
            self.queue.add("owner", job, 1, [])
            self.queue.claim("owner", job, job)
        self.check_used(5)
        for job in ("used", "capacity", "__proto__", "Job", "job"):
            self.queue.finish("owner", job, job, True)
        self.check_used(0)


if __name__ == "__main__":
    unittest.main()
