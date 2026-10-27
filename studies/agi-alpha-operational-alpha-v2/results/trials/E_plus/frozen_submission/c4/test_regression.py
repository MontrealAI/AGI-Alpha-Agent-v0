import random
import unittest
from copy import deepcopy
from engine import AccountBook
from contract_probes import assert_rejected_unchanged, assert_idempotent, assert_independent_result


def transfer(source='a', target='b', amount=10):
    return {'from': source, 'to': target, 'amount': amount}


class AccountBatchRegression(unittest.TestCase):
    def setUp(self):
        self.initial = {'a': 100, 'b': 20, 'c': 0}
        self.book = AccountBook(self.initial)

    def observe(self):
        return self.book.snapshot(), deepcopy(self.book.receipts)

    def rejected(self, action):
        assert_rejected_unchanged(self, self.observe, action)

    def test_late_overdraft_is_atomic_and_id_reusable(self):
        operations = [transfer(amount=10), transfer('b', 'c', 31)]
        self.rejected(lambda: self.book.transact('request', operations, {'a': 0, 'b': 0, 'c': 0}))
        result = self.book.transact('request', [transfer()], {'a': 0, 'b': 0})
        self.assertEqual(result['balances'], {'a': 90, 'b': 30})
        self.assertEqual(result['revisions'], {'a': 1, 'b': 1})

    def test_full_request_identity(self):
        operations = [transfer()]
        expected = {'a': 0, 'b': 0}
        assert_idempotent(self, self.observe, lambda: self.book.transact('request', operations, expected))
        for ops, exp in [([transfer(amount=11)], expected),
                         ([transfer('b', 'a', 10)], expected),
                         (operations, {'a': 1, 'b': 1}),
                         (operations, {'a': 0}),
                         ([transfer(), transfer()], expected)]:
            self.rejected(lambda ops=ops, exp=exp: self.book.transact('request', ops, exp))
        # Mapping order is immaterial to exactness.
        result = self.book.transact('request', [{'amount': 10, 'to': 'b', 'from': 'a'}], {'b': 0, 'a': 0})
        self.assertEqual(result['balances'], {'a': 90, 'b': 30})

    def test_historical_receipt_survives_later_batches(self):
        first = self.book.transact('first', [transfer()], {'a': 0, 'b': 0})
        self.book.transact('second', [transfer('b', 'c', 5)], {'b': 1, 'c': 0})
        before = deepcopy(self.observe())
        self.assertEqual(self.book.transact('first', [transfer()], {'a': 0, 'b': 0}), first)
        self.assertEqual(self.observe(), before)
        self.assertEqual(first['balances']['b'], 30)
        self.assertEqual(self.book.snapshot()['balances']['b'], 25)

    def test_exact_guard_and_stale_revision(self):
        for guard in [{}, {'a': 0}, {'b': 0}, {'a': 0, 'b': 0, 'c': 0}, {'a': 0, 'unknown': 0}, {'a': 1, 'b': 0}]:
            self.rejected(lambda guard=guard: self.book.transact('request', [transfer()], guard))
        self.book.transact('request', [transfer()], {'a': 0, 'b': 0})
        self.rejected(lambda: self.book.transact('later', [transfer()], {'a': 0, 'b': 1}))
        self.assertEqual(self.book.transact('later', [transfer()], {'a': 1, 'b': 1})['revisions'], {'a': 2, 'b': 2})

    def test_ordered_operations_and_no_temporary_overdraft(self):
        ordered = [transfer('b', 'c', 20), transfer('c', 'a', 20)]
        guard = {'a': 0, 'b': 0, 'c': 0}
        self.rejected(lambda: self.book.transact('early', list(reversed(ordered)), guard))
        result = self.book.transact('ok', ordered, guard)
        self.assertEqual(result['balances'], {'a': 120, 'b': 0, 'c': 0})
        self.rejected(lambda: self.book.transact('ok', list(reversed(ordered)), guard))

    def test_revisions_once_for_touched_accounts(self):
        result = self.book.transact('many', [transfer(), transfer('b', 'a', 5), transfer('a', 'a', 95)], {'a': 0, 'b': 0})
        self.assertEqual(result, dict(request='many', balances={'a': 95, 'b': 25}, revisions={'a': 1, 'b': 1}))
        self.assertEqual(self.book.snapshot()['revisions']['c'], 0)
        result = self.book.transact('self', [transfer('a', 'a', 95)], {'a': 1})
        self.assertEqual(result['balances'], {'a': 95})
        self.assertEqual(result['revisions'], {'a': 2})
        self.rejected(lambda: self.book.transact('too-much', [transfer('a', 'a', 96)], {'a': 2}))
        self.rejected(lambda: self.book.transact('zero-self', [transfer('c', 'c', 1)], {'c': 0}))

    def test_caller_mutation_isolation(self):
        self.initial['a'] = 0
        self.assertEqual(self.book.snapshot()['balances']['a'], 100)
        operations = [transfer()]
        expected = {'a': 0, 'b': 0}
        result = self.book.transact('request', operations, expected)
        operations[0]['amount'] = 100
        expected['a'] = 99
        result['balances']['a'] = -50
        self.assertEqual(self.book.transact('request', [transfer()], {'a': 0, 'b': 0})['balances'], {'a': 90, 'b': 30})
        assert_independent_result(self, self.observe, lambda: self.book.transact('request', [transfer()], {'a': 0, 'b': 0}),
                                  lambda r: r['revisions'].update(a=999))
        assert_independent_result(self, self.observe, self.book.snapshot,
                                  lambda r: r['balances'].update(a=-999))
        assert_independent_result(self, self.observe, lambda: self.book.transact('next', [transfer()], {'a': 1, 'b': 1}),
                                  lambda r: r['balances'].clear())

    def test_malformed_operations_even_on_retry(self):
        self.book.transact('request', [transfer(amount=1)], {'a': 0, 'b': 0})
        for operation in [None, [], {}, dict(transfer(), extra=0), {'from': 'a', 'to': 'b'},
                          transfer(amount=True), transfer(amount=False), transfer(amount=0), transfer(amount=-1),
                          transfer(amount=1.0), transfer(amount='1'), transfer(source=[]), transfer(target=''),
                          transfer(target='missing')]:
            for request in ['new', 'request']:
                self.rejected(lambda request=request, operation=operation: self.book.transact(request, [operation], {'a': 0, 'b': 0}))
        for operations in [[], (), {}, None, 'operations']:
            self.rejected(lambda operations=operations: self.book.transact('new', operations, {}))

    def test_identifier_and_integer_validation(self):
        for initial in [None, [], {'': 0}, {1: 0}, {'a': True}, {'a': -1}, {'a': 1.0}]:
            with self.assertRaises(ValueError):
                AccountBook(initial)
        for request in ['', None, 5, [], {}]:
            self.rejected(lambda request=request: self.book.transact(request, [transfer()], {'a': 0, 'b': 0}))
        for revision in [True, False, -1, 0.0, None, '0']:
            self.rejected(lambda revision=revision: self.book.transact('new', [transfer()], {'a': revision, 'b': 0}))
        for guard in [None, [], (), {'a': 0, 3: 0}]:
            self.rejected(lambda guard=guard: self.book.transact('new', [transfer()], guard))
        self.assertEqual(AccountBook({}).snapshot(), dict(balances={}, revisions={}))

    def test_invalid_late_operation_and_revision_preserve_state(self):
        self.rejected(lambda: self.book.transact('request', [transfer(), {'from': 'b'}], {'a': 0, 'b': 0}))
        self.rejected(lambda: self.book.transact('request', [transfer(), transfer('b', 'c', 1)], {'a': 0, 'b': 0, 'c': True}))
        self.assertEqual(self.book.snapshot(), {'balances': self.initial, 'revisions': {'a': 0, 'b': 0, 'c': 0}})

    def test_seeded_batches_against_accounting_model(self):
        rng = random.Random(720)
        balances = {'a': 100, 'b': 100, 'c': 100}
        revisions = dict.fromkeys(balances, 0)
        book = AccountBook(balances)
        for index in range(250):
            trial = dict(balances)
            operations = []
            touched = set()
            for step in range(rng.randint(1, 5)):
                source = rng.choice([a for a in trial if trial[a] > 0])
                target = rng.choice(list(trial))
                amount = rng.randint(1, trial[source])
                operations.append(transfer(source, target, amount))
                trial[source] -= amount
                trial[target] += amount
                touched.update([source, target])
            guard = {a: revisions[a] for a in touched}
            if index % 5 == 0:
                source = rng.choice(list(trial))
                bad = operations + [transfer(source, source, trial[source] + 1)]
                bad_guard = dict(guard, **{source: revisions[source]})
                assert_rejected_unchanged(self, book.snapshot, lambda: book.transact(str(index), bad, bad_guard))
            receipt = assert_idempotent(self, book.snapshot, lambda: book.transact(str(index), operations, guard))
            balances = trial
            for account in touched:
                revisions[account] += 1
            self.assertEqual(book.snapshot(), dict(balances=balances, revisions=revisions))
            self.assertEqual(receipt, dict(request=str(index), balances={a: balances[a] for a in touched}, revisions={a: revisions[a] for a in touched}))
            self.assertEqual(sum(balances.values()), 300)
            self.assertTrue(all(balance >= 0 for balance in balances.values()))


if __name__ == '__main__':
    unittest.main()
