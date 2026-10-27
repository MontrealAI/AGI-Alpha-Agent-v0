import copy
import itertools
import unittest
from engine import AccountBook


def transfer(source="a", target="b", amount=10):
    return {"from": source, "to": target, "amount": amount}


class AccountContract(unittest.TestCase):
    def setUp(self):
        self.book = AccountBook({"a": 100, "b": 20, "c": 0})

    def unchanged_error(self, request, operations, expected):
        before = self.book.snapshot()
        with self.assertRaises(ValueError):
            self.book.transact(request, operations, expected)
        self.assertEqual(self.book.snapshot(), before)

    def test_late_overdraft_is_atomic_and_request_can_be_retried(self):
        self.unchanged_error("retry", [transfer(amount=50), transfer("b", "c", 71)],
                             {"a": 0, "b": 0, "c": 0})
        result = self.book.transact("retry", [transfer(amount=50), transfer("b", "c", 70)],
                                    {"a": 0, "b": 0, "c": 0})
        self.assertEqual(result["balances"], {"a": 50, "b": 0, "c": 70})
        self.assertEqual(result["revisions"], {"a": 1, "b": 1, "c": 1})

    def test_intermediate_order_and_self_transfer_solvency(self):
        self.unchanged_error("order", [transfer("c", "a", 10), transfer("a", "c", 10)],
                             {"a": 0, "c": 0})
        result = self.book.transact("order", [transfer("a", "c", 10), transfer("c", "a", 10)],
                                    {"a": 0, "c": 0})
        self.assertEqual(result["balances"], {"a": 100, "c": 0})
        self.assertEqual(result["revisions"], {"a": 1, "c": 1})
        self.unchanged_error("self", [transfer("c", "c", 1)], {"c": 1})
        self.unchanged_error("self", [transfer("a", "a", 101)], {"a": 1})
        result = self.book.transact("self", [transfer("a", "a", 100)] * 3, {"a": 1})
        self.assertEqual(result, dict(request="self", balances={"a": 100}, revisions={"a": 2}))
        self.assertEqual(self.book.snapshot()["revisions"], {"a": 2, "b": 0, "c": 1})

    def test_exact_guard_and_stale_guard_reject_without_consuming_id(self):
        operations = [transfer()]
        for expected in ({}, {"a": 0}, {"b": 0}, {"a": 0, "b": 0, "c": 0},
                         {"a": 0, "b": 1}, {"a": 0, "b": -1},
                         {"a": 0, "b": False}, {"a": 0, "b": 0.0},
                         {"a": 0, "unknown": 0}):
            self.unchanged_error("request", operations, expected)
        self.book.transact("request", operations, {"a": 0, "b": 0})
        self.unchanged_error("new", operations, {"a": 0, "b": 0})
        self.book.transact("new", operations, {"a": 1, "b": 1})
        self.assertEqual(self.book.snapshot()["balances"], {"a": 80, "b": 40, "c": 0})

    def test_exact_retry_returns_original_receipt_after_other_batches(self):
        operations = [transfer(amount=10), transfer("b", "a", 5)]
        expected = {"a": 0, "b": 0}
        original = self.book.transact("first", operations, expected)
        self.book.transact("second", [transfer("a", "c", 50)], {"a": 1, "c": 0})
        before = self.book.snapshot()
        reordered_maps = [{"amount": 10, "to": "b", "from": "a"},
                          {"to": "a", "from": "b", "amount": 5}]
        self.assertEqual(self.book.transact("first", reordered_maps, {"b": 0, "a": 0}), original)
        self.assertEqual(self.book.snapshot(), before)
        self.unchanged_error("first", list(reversed(operations)), expected)
        self.unchanged_error("first", [transfer(amount=11), transfer("b", "a", 5)], expected)
        self.unchanged_error("first", operations, {"a": 2, "b": 1})
        self.unchanged_error("first", operations + [transfer()], expected)
        self.assertEqual(self.book.transact("first", operations, expected), original)

    def test_caller_mutations_cannot_rewrite_state_or_idempotency(self):
        initial = {"a": 100, "b": 0}
        self.book = AccountBook(initial)
        initial["a"] = 0
        operations, expected = [transfer()], {"a": 0, "b": 0}
        result = self.book.transact("r", operations, expected)
        original = copy.deepcopy(result)
        operations[0]["amount"] = 80
        expected["a"] = 99
        result["balances"]["a"] = -1
        result["revisions"]["a"] = -1
        snap = self.book.snapshot()
        snap["balances"].clear()
        snap["revisions"].clear()
        retry = self.book.transact("r", [transfer()], {"a": 0, "b": 0})
        self.assertEqual(retry, original)
        retry["balances"].clear()
        retry["revisions"]["b"] = 999
        self.assertEqual(self.book.transact("r", [transfer()], {"a": 0, "b": 0}), original)
        self.assertEqual(self.book.snapshot(), dict(balances={"a": 90, "b": 10}, revisions={"a": 1, "b": 1}))

    def test_retry_does_not_bypass_strict_types(self):
        self.book.transact("r", [transfer(amount=1)], {"a": 0, "b": 0})
        for amount in (True, 1.0):
            self.unchanged_error("r", [transfer(amount=amount)], {"a": 0, "b": 0})
        for revision in (False, 0.0):
            self.unchanged_error("r", [transfer(amount=1)], {"a": revision, "b": 0})

    def test_malformed_inputs_and_initial_values(self):
        for initial in (None, [], {"": 1}, {3: 1}, {"a": -1}, {"a": True}, {"a": 1.0}):
            with self.subTest(initial=initial), self.assertRaises(ValueError):
                AccountBook(initial)
        self.assertEqual(AccountBook({}).snapshot(), dict(balances={}, revisions={}))
        for request in (None, "", 1, []):
            self.unchanged_error(request, [transfer()], {"a": 0, "b": 0})
        for operations in (None, (), [], {}, [None], [transfer(), {}],
                           [dict(transfer(), extra=1)], [{"from": "a", "to": "b"}]):
            self.unchanged_error("r", operations, {"a": 0, "b": 0})
        for amount in (0, -1, True, 1.0, "1", None):
            self.unchanged_error("r", [transfer(amount=amount)], {"a": 0, "b": 0})
        for name in (None, "", 1, [], "missing"):
            self.unchanged_error("r", [transfer(source=name)], {"a": 0, "b": 0})
            self.unchanged_error("r", [transfer(target=name)], {"a": 0, "b": 0})
        for expected in (None, [], (), "a"):
            self.unchanged_error("r", [transfer()], expected)
        self.book.transact("r", [transfer()], {"a": 0, "b": 0})

    def test_large_balances_and_repeated_accounts_increment_once(self):
        large = 10 ** 100
        self.book = AccountBook({"a": large, "b": 0, "c": 7})
        result = self.book.transact("r", [transfer(amount=large), transfer("b", "a", large),
                                         transfer("a", "a", large)], {"a": 0, "b": 0})
        self.assertEqual(result["balances"], {"a": large, "b": 0})
        self.assertEqual(result["revisions"], {"a": 1, "b": 1})
        self.assertEqual(self.book.snapshot()["revisions"]["c"], 0)
        self.assertEqual(sum(self.book.snapshot()["balances"].values()), large + 7)

    def test_exhaustive_two_operation_small_balance_prefixes(self):
        # Independent oracle: each prefix's balance is its initial balance plus
        # cumulative incoming amounts minus outgoing amounts from earlier rows.
        choices = [transfer(source, target, amount)
                   for source, target, amount in itertools.product("ab", "ab", range(1, 4))]
        for a, b in itertools.product(range(4), repeat=2):
            initial = {"a": a, "b": b}
            for operations in itertools.product(choices, repeat=2):
                operations = list(operations)
                book = AccountBook(initial)
                touched = {op[field] for op in operations for field in ("from", "to")}
                expected = {name: 0 for name in touched}
                valid = all(initial[op["from"]] + sum(
                    prior["amount"] * ((prior["to"] == op["from"]) - (prior["from"] == op["from"]))
                    for prior in operations[:index]) >= op["amount"]
                    for index, op in enumerate(operations))
                if not valid:
                    before = book.snapshot()
                    with self.assertRaises(ValueError):
                        book.transact("r", operations, expected)
                    self.assertEqual(book.snapshot(), before)
                else:
                    result = book.transact("r", operations, expected)
                    final = {name: initial[name] + sum(
                        op["amount"] * ((op["to"] == name) - (op["from"] == name))
                        for op in operations) for name in "ab"}
                    self.assertEqual(book.snapshot()["balances"], final)
                    self.assertEqual(result["revisions"], {name: 1 for name in touched})
                    self.assertEqual(sum(final.values()), a + b)
                    self.assertEqual(book.transact("r", operations, expected), result)


if __name__ == "__main__":
    unittest.main()
