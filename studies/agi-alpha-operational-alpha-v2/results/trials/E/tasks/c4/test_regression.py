import copy
import random
import unittest
from engine import AccountBook


def move(source='a', target='b', amount=1):
    return {'from': source, 'to': target, 'amount': amount}


class Regression(unittest.TestCase):
    def rejected(self, book, request, operations, expected):
        before = book.snapshot()
        with self.assertRaises(ValueError):
            book.transact(request, operations, expected)
        self.assertEqual(book.snapshot(), before)

    def test_atomic_order_and_failed_request_reuse(self):
        b = AccountBook({'a': 10, 'b': 0, 'c': 0})
        ops = [move(amount=4), move('b', 'c', 5)]
        self.rejected(b, 'x', ops, {'a': 0, 'b': 0, 'c': 0})
        ops[1]['amount'] = 4
        receipt = b.transact('x', ops, {'a': 0, 'b': 0, 'c': 0})
        self.assertEqual(receipt['balances'], {'a': 6, 'b': 0, 'c': 4})
        self.assertEqual(receipt['revisions'], {'a': 1, 'b': 1, 'c': 1})
        self.rejected(b, 'replenish', [move('b', 'a', 1), move('a', 'b', 1)], {'a': 1, 'b': 1})
        self.rejected(b, 'self', [move('b', 'b', 1)], {'b': 1})
        r = b.transact('self', [move('a', 'a', 6), move('a', 'a', 6)], {'a': 1})
        self.assertEqual(r['balances'], {'a': 6})
        self.assertEqual(r['revisions'], {'a': 2})

    def test_exact_retry_and_independent_receipts(self):
        initial = {'a': 10, 'b': 5}
        b = AccountBook(initial)
        initial['a'] = 0
        ops, guards = [move(amount=2)], {'a': 0, 'b': 0}
        original = b.transact('x', ops, guards)
        expected_receipt = copy.deepcopy(original)
        original['balances']['a'] = 999
        ops[0]['amount'] = 9
        guards['a'] = 99
        b.transact('later', [move('b', 'a', 1)], {'a': 1, 'b': 1})
        before = b.snapshot()
        replay = b.transact('x', [{'amount': 2, 'to': 'b', 'from': 'a'}], {'b': 0, 'a': 0})
        self.assertEqual(replay, expected_receipt)
        self.assertEqual(b.snapshot(), before)
        replay['revisions']['b'] = 400
        self.assertEqual(b.transact('x', [move(amount=2)], {'a': 0, 'b': 0}), expected_receipt)
        self.rejected(b, 'x', [move(amount=3)], {'a': 0, 'b': 0})
        self.rejected(b, 'x', [move(amount=2)], {'a': 2, 'b': 2})
        self.rejected(b, 'x', [move(amount=True)], {'a': 0, 'b': 0})
        self.rejected(b, 'x', [move(amount=2)], {'a': False, 'b': 0})
        snapshot = b.snapshot()
        snapshot['balances']['a'] = -100
        self.assertEqual(b.snapshot(), before)

    def test_order_is_part_of_identity(self):
        b = AccountBook({'a': 10, 'b': 10})
        ops = [move(amount=2), move('b', 'a', 3)]
        b.transact('x', ops, {'a': 0, 'b': 0})
        self.rejected(b, 'x', list(reversed(ops)), {'a': 0, 'b': 0})

    def test_validation_and_exact_guards(self):
        for initial in [[], {'': 2}, {'a': True}, {'a': -1}, {1: 0}, {'a': 1.0}]:
            with self.assertRaises(ValueError):
                AccountBook(initial)
        self.assertEqual(AccountBook({}).snapshot(), {'balances': {}, 'revisions': {}})
        b = AccountBook({'a': 3, 'b': 2, 'c': 0})
        cases = [('', [move()], {'a': 0, 'b': 0}),
                 ('x', [], {}), ('x', (move(),), {'a': 0, 'b': 0}),
                 ('x', [None], {}), ('x', [dict(move(), extra=0)], {'a': 0, 'b': 0}),
                 ('x', [move(amount=0)], {'a': 0, 'b': 0}),
                 ('x', [move(amount=-1)], {'a': 0, 'b': 0}),
                 ('x', [move(amount=1.0)], {'a': 0, 'b': 0}),
                 ('x', [move(source='unknown')], {'unknown': 0, 'b': 0}),
                 ('x', [move()], {}), ('x', [move()], {'a': 0}),
                 ('x', [move()], {'a': 0, 'b': 0, 'c': 0}),
                 ('x', [move()], {'a': 1, 'b': 0}),
                 ('x', [move()], {'a': 0, 'b': -1}),
                 ('x', [move()], None)]
        for request, ops, expected in cases:
            with self.subTest(ops=ops, expected=expected):
                self.rejected(b, request, ops, expected)
        self.assertEqual(b.transact('x', [move()], {'a': 0, 'b': 0})['balances'], {'a': 2, 'b': 3})

    def test_seeded_sequential_reference(self):
        rng = random.Random(404)
        b = AccountBook({'a': 10, 'b': 8, 'c': 2})
        balances, revisions = {'a': 10, 'b': 8, 'c': 2}, dict.fromkeys('abc', 0)
        for index in range(100):
            ops = [move(rng.choice('abc'), rng.choice('abc'), rng.randrange(1, 9))
                   for _ in range(rng.randrange(1, 5))]
            touched = {op[key] for op in ops for key in ['from', 'to']}
            guards = {a: revisions[a] for a in touched}
            trial = dict(balances)
            valid = True
            for op in ops:
                if trial[op['from']] < op['amount']:
                    valid = False
                    break
                trial[op['from']] -= op['amount']
                trial[op['to']] += op['amount']
            if valid:
                b.transact(str(index), ops, guards)
                balances = trial
                for account in touched:
                    revisions[account] += 1
            else:
                self.rejected(b, str(index), ops, guards)
            self.assertEqual(b.snapshot(), {'balances': balances, 'revisions': revisions})
            self.assertEqual(sum(balances.values()), 20)


if __name__ == '__main__':
    unittest.main()
