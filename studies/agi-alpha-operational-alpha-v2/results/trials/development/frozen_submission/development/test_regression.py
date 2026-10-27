# SPDX-License-Identifier: Apache-2.0
"""Public-contract regressions; the canonical smoke test is left untouched."""
from copy import deepcopy
import random
import unittest

from contract_probes import (
    assert_idempotent,
    assert_independent_result,
    assert_rejected_unchanged,
)
from engine import Ledger


class LedgerContract(unittest.TestCase):
    def check_invariants(self, ledger, initial):
        state = ledger.snapshot()
        self.assertEqual(set(state), {'wallets', 'requests'})
        self.assertEqual(set(state['wallets']), set(initial))
        reserved = dict.fromkeys(initial, 0)
        spent = dict.fromkeys(initial, 0)
        for request, record in state['requests'].items():
            self.assertIsInstance(request, str)
            self.assertTrue(request)
            self.assertEqual(set(record), {'owner', 'cap', 'state', 'actual'})
            self.assertIn(record['owner'], initial)
            self.assertIs(type(record['cap']), int)
            self.assertGreater(record['cap'], 0)
            self.assertIn(record['state'], ('reserved', 'settled', 'canceled'))
            if record['state'] == 'settled':
                self.assertIs(type(record['actual']), int)
                self.assertGreaterEqual(record['actual'], 0)
                self.assertLessEqual(record['actual'], record['cap'])
                spent[record['owner']] += record['actual']
            else:
                self.assertIsNone(record['actual'])
            if record['state'] == 'reserved':
                reserved[record['owner']] += record['cap']
        for owner, wallet in state['wallets'].items():
            self.assertEqual(set(wallet), {'available', 'reserved', 'spent'})
            for amount in wallet.values():
                self.assertIs(type(amount), int)
                self.assertGreaterEqual(amount, 0)
            self.assertEqual(sum(wallet.values()), initial[owner])
            self.assertEqual(wallet['reserved'], reserved[owner])
            self.assertEqual(wallet['spent'], spent[owner])

    def test_initial_validation_and_independence(self):
        for initial in (None, [], [('a', 1)], 1, {'': 1}, {1: 1},
                        {None: 1}, {'a': -1}, {'a': True}, {'a': False},
                        {'a': 1.0}, {'a': '1'}, {'a': None}):
            with self.subTest(initial=initial), self.assertRaises(ValueError):
                Ledger(initial)
        self.assertEqual(Ledger({}).snapshot(), {'wallets': {}, 'requests': {}})
        original = {'alpha': 7, 'empty': 0}
        ledger = Ledger(original)
        original['alpha'] = -99
        original.clear()
        self.assertEqual(ledger.snapshot()['wallets']['alpha']['available'], 7)
        self.check_invariants(ledger, {'alpha': 7, 'empty': 0})

    def test_reservation_identity_in_every_state(self):
        for terminal in ('reserved', 'settled', 'canceled'):
            with self.subTest(state=terminal):
                ledger = Ledger({'alpha': 10, 'beta': 10})
                record = assert_idempotent(
                    self, ledger.snapshot, lambda: ledger.reserve('alpha', 'job', 10))
                self.assertEqual(record, {'owner': 'alpha', 'cap': 10,
                                          'state': 'reserved', 'actual': None})
                if terminal == 'settled':
                    ledger.settle('alpha', 'job', 7)
                elif terminal == 'canceled':
                    ledger.cancel('alpha', 'job')
                expected = deepcopy(ledger.snapshot()['requests']['job'])
                before = deepcopy(ledger.snapshot())
                self.assertEqual(ledger.reserve('alpha', 'job', 10), expected)
                self.assertEqual(ledger.snapshot(), before)
                for owner, cap in (('alpha', 9), ('alpha', 11), ('beta', 10), ('beta', 9)):
                    with self.subTest(owner=owner, cap=cap):
                        assert_rejected_unchanged(
                            self, ledger.snapshot,
                            lambda owner=owner, cap=cap: ledger.reserve(owner, 'job', cap))
                self.check_invariants(ledger, {'alpha': 10, 'beta': 10})

    def test_settlement_boundaries_and_conflicting_retry(self):
        for actual in (0, 1, 10):
            with self.subTest(actual=actual):
                ledger = Ledger({'alpha': 10})
                ledger.reserve('alpha', 'job', 10)
                result = assert_idempotent(
                    self, ledger.snapshot, lambda: ledger.settle('alpha', 'job', actual))
                self.assertEqual(result, {'owner': 'alpha', 'cap': 10,
                                          'state': 'settled', 'actual': actual})
                self.assertEqual(ledger.snapshot()['wallets']['alpha'],
                                 {'available': 10 - actual, 'reserved': 0, 'spent': actual})
                for changed in ({0, 1, 10, 11} - {actual}):
                    with self.subTest(changed=changed):
                        assert_rejected_unchanged(
                            self, ledger.snapshot,
                            lambda changed=changed: ledger.settle('alpha', 'job', changed))
                assert_rejected_unchanged(
                    self, ledger.snapshot, lambda: ledger.cancel('alpha', 'job'))
                self.check_invariants(ledger, {'alpha': 10})

    def test_cancel_retry_and_terminal_conflicts(self):
        ledger = Ledger({'alpha': 12})
        ledger.reserve('alpha', 'job', 11)
        result = assert_idempotent(
            self, ledger.snapshot, lambda: ledger.cancel('alpha', 'job'))
        self.assertEqual(result, {'owner': 'alpha', 'cap': 11,
                                  'state': 'canceled', 'actual': None})
        self.assertEqual(ledger.snapshot()['wallets']['alpha'],
                         {'available': 12, 'reserved': 0, 'spent': 0})
        for actual in (0, 11):
            assert_rejected_unchanged(
                self, ledger.snapshot, lambda actual=actual: ledger.settle('alpha', 'job', actual))
        self.check_invariants(ledger, {'alpha': 12})

    def test_authorization_in_every_state(self):
        for terminal in ('reserved', 'settled', 'canceled'):
            for owner in ('beta', 'missing'):
                with self.subTest(state=terminal, owner=owner):
                    ledger = Ledger({'alpha': 20, 'beta': 20})
                    ledger.reserve('alpha', 'job', 15)
                    if terminal == 'settled':
                        ledger.settle('alpha', 'job', 6)
                    elif terminal == 'canceled':
                        ledger.cancel('alpha', 'job')
                    for operation in (lambda: ledger.reserve(owner, 'job', 15),
                                      lambda: ledger.settle(owner, 'job', 6),
                                      lambda: ledger.cancel(owner, 'job')):
                        assert_rejected_unchanged(self, ledger.snapshot, operation)
                    self.check_invariants(ledger, {'alpha': 20, 'beta': 20})

    def test_invalid_inputs_and_missing_identifiers_are_atomic(self):
        ledger = Ledger({'alpha': 20, 'beta': 0})
        ledger.reserve('alpha', 'job', 10)
        bad_ids = ('', None, 0, True, [], {})
        for bad in bad_ids:
            for label, action in (
                ('reserve owner', lambda bad=bad: ledger.reserve(bad, 'fresh', 1)),
                ('reserve request', lambda bad=bad: ledger.reserve('alpha', bad, 1)),
                ('settle owner', lambda bad=bad: ledger.settle(bad, 'job', 1)),
                ('settle request', lambda bad=bad: ledger.settle('alpha', bad, 1)),
                ('cancel owner', lambda bad=bad: ledger.cancel(bad, 'job')),
                ('cancel request', lambda bad=bad: ledger.cancel('alpha', bad)),
            ):
                with self.subTest(label=label, bad=bad):
                    assert_rejected_unchanged(self, ledger.snapshot, action)
        for bad in (None, True, False, 0, -1, 1.0, '1', [], {}):
            for request in ('fresh', 'job'):
                with self.subTest(cap=bad, request=request):
                    assert_rejected_unchanged(
                        self, ledger.snapshot,
                        lambda bad=bad, request=request: ledger.reserve('alpha', request, bad))
        for bad in (None, True, False, -1, 11, 1.0, '1', [], {}):
            with self.subTest(actual=bad):
                assert_rejected_unchanged(
                    self, ledger.snapshot, lambda bad=bad: ledger.settle('alpha', 'job', bad))
        for action in (lambda: ledger.reserve('missing', 'fresh', 1),
                       lambda: ledger.settle('alpha', 'missing', 0),
                       lambda: ledger.cancel('alpha', 'missing'),
                       lambda: ledger.settle('missing', 'missing', 0),
                       lambda: ledger.cancel('missing', 'missing')):
            assert_rejected_unchanged(self, ledger.snapshot, action)
        self.check_invariants(ledger, {'alpha': 20, 'beta': 0})

    def test_invalid_numbers_on_terminal_retries(self):
        for state in ('settled', 'canceled'):
            ledger = Ledger({'alpha': 10})
            ledger.reserve('alpha', 'job', 10)
            if state == 'settled':
                ledger.settle('alpha', 'job', 0)
            else:
                ledger.cancel('alpha', 'job')
            for value in (True, False, 0.0, -1, None):
                with self.subTest(state=state, value=value):
                    assert_rejected_unchanged(
                        self, ledger.snapshot, lambda: ledger.settle('alpha', 'job', value))
                    assert_rejected_unchanged(
                        self, ledger.snapshot, lambda: ledger.reserve('alpha', 'job', value))

    def test_insufficient_funds_does_not_claim_request(self):
        ledger = Ledger({'alpha': 7, 'beta': 20, 'empty': 0})
        assert_rejected_unchanged(
            self, ledger.snapshot, lambda: ledger.reserve('alpha', 'reusable', 8))
        assert_rejected_unchanged(
            self, ledger.snapshot, lambda: ledger.reserve('empty', 'zero', 1))
        ledger.reserve('beta', 'reusable', 8)
        ledger.reserve('alpha', 'full', 7)
        assert_rejected_unchanged(
            self, ledger.snapshot, lambda: ledger.reserve('alpha', 'next', 1))
        ledger.cancel('alpha', 'full')
        ledger.reserve('alpha', 'next', 1)
        self.check_invariants(ledger, {'alpha': 7, 'beta': 20, 'empty': 0})

    def test_returned_receipts_are_independent(self):
        ledger = Ledger({'alpha': 30})
        actions = (
            lambda: ledger.reserve('alpha', 'settle-job', 12),
            lambda: ledger.reserve('alpha', 'settle-job', 12),
            lambda: ledger.settle('alpha', 'settle-job', 8),
            lambda: ledger.settle('alpha', 'settle-job', 8),
            lambda: ledger.reserve('alpha', 'settle-job', 12),
            lambda: ledger.reserve('alpha', 'cancel-job', 10),
            lambda: ledger.cancel('alpha', 'cancel-job'),
            lambda: ledger.cancel('alpha', 'cancel-job'),
            lambda: ledger.reserve('alpha', 'cancel-job', 10),
        )
        for index, action in enumerate(actions):
            with self.subTest(index=index):
                assert_independent_result(self, ledger.snapshot, action, lambda result: result.clear())
                self.check_invariants(ledger, {'alpha': 30})

    def test_snapshots_are_independent_at_every_level(self):
        ledger = Ledger({'alpha': 10})
        ledger.reserve('alpha', 'job', 6)
        mutations = (
            lambda result: result['wallets']['alpha'].__setitem__('available', -1),
            lambda result: result['requests']['job'].__setitem__('owner', 'intruder'),
            lambda result: result['wallets'].clear(),
            lambda result: result['requests'].clear(),
            lambda result: result.clear(),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(level=index):
                assert_independent_result(self, ledger.snapshot, ledger.snapshot, mutate)
        older = ledger.snapshot()
        older_expected = deepcopy(older)
        ledger.settle('alpha', 'job', 3)
        self.assertEqual(older, older_expected)
        self.check_invariants(ledger, {'alpha': 10})

    def test_interleaved_requests_and_large_integer_boundaries(self):
        large = 10 ** 100
        initial = {'alpha': large, 'beta': 13}
        ledger = Ledger(initial)
        operations = (
            lambda: ledger.reserve('alpha', 'a1', large - 1),
            lambda: ledger.reserve('alpha', 'a2', 1),
            lambda: ledger.reserve('beta', 'b1', 7),
            lambda: ledger.reserve('beta', 'b2', 6),
            lambda: ledger.settle('alpha', 'a1', large - 2),
            lambda: ledger.cancel('beta', 'b1'),
            lambda: ledger.settle('beta', 'b2', 0),
            lambda: ledger.reserve('beta', 'b3', 13),
            lambda: ledger.settle('beta', 'b3', 13),
            lambda: ledger.cancel('alpha', 'a2'),
            lambda: ledger.reserve('alpha', 'a3', 2),
            lambda: ledger.settle('alpha', 'a3', 2),
        )
        for action in operations:
            action()
            self.check_invariants(ledger, initial)
        self.assertEqual(ledger.snapshot()['wallets'], {
            'alpha': {'available': 0, 'reserved': 0, 'spent': large},
            'beta': {'available': 0, 'reserved': 0, 'spent': 13},
        })

    def test_seeded_sequences_against_record_derived_model(self):
        """An independent accounting oracle derives wallets from request history."""
        rng = random.Random(512038)
        initial = {'alpha': 19, 'beta': 13, 'empty': 0}
        accepted = rejected = 0
        for trial in range(40):
            ledger = Ledger(initial)
            records = {}

            def expected_state():
                wallets = {}
                for owner, total in initial.items():
                    reserved = sum(r['cap'] for r in records.values()
                                   if r['owner'] == owner and r['state'] == 'reserved')
                    spent = sum(r['actual'] for r in records.values()
                                if r['owner'] == owner and r['state'] == 'settled')
                    wallets[owner] = {'available': total - reserved - spent,
                                      'reserved': reserved, 'spent': spent}
                return {'wallets': wallets, 'requests': deepcopy(records)}

            for step in range(80):
                name = rng.choice(('reserve', 'reserve', 'settle', 'cancel'))
                owner = rng.choice(('alpha', 'alpha', 'beta', 'beta', 'empty', 'missing'))
                request = 'job-' + str(rng.randrange(6))
                number = rng.choice((0, 1, 3, 7, 13, 19, 20))
                prior = records.get(request)
                valid = False
                replacement = prior
                if name == 'reserve':
                    if owner in initial and number > 0:
                        if prior is None:
                            valid = expected_state()['wallets'][owner]['available'] >= number
                            replacement = {'owner': owner, 'cap': number,
                                           'state': 'reserved', 'actual': None}
                        else:
                            valid = prior['owner'] == owner and prior['cap'] == number
                elif prior is not None and prior['owner'] == owner:
                    if name == 'settle':
                        valid = ((prior['state'] == 'reserved' and number <= prior['cap'])
                                 or (prior['state'] == 'settled' and number == prior['actual']))
                        replacement = dict(prior, state='settled', actual=number)
                    elif name == 'cancel':
                        valid = prior['state'] in ('reserved', 'canceled')
                        replacement = dict(prior, state='canceled')
                args = (owner, request) if name == 'cancel' else (owner, request, number)
                with self.subTest(trial=trial, step=step, operation=name, args=args):
                    action = lambda: getattr(ledger, name)(*args)
                    if valid:
                        result = action()
                        records[request] = deepcopy(replacement)
                        self.assertEqual(result, replacement)
                        accepted += 1
                    else:
                        assert_rejected_unchanged(self, ledger.snapshot, action)
                        rejected += 1
                    self.assertEqual(ledger.snapshot(), expected_state())
                    self.check_invariants(ledger, initial)
        self.assertGreater(accepted, 100)
        self.assertGreater(rejected, 100)


class GenericProbeChecks(unittest.TestCase):
    def test_rejection_probe_freezes_an_aliasing_observation(self):
        state = {'value': 1}

        def broken_action():
            state['value'] = 2
            raise ValueError('rejected after mutation')

        with self.assertRaises(AssertionError):
            assert_rejected_unchanged(self, lambda: state, broken_action)

    def test_idempotence_probe_detects_repeat_side_effect(self):
        state = {'count': 0}

        def broken_retry():
            state['count'] += 1
            return 'same receipt'

        with self.assertRaises(AssertionError):
            assert_idempotent(self, lambda: state, broken_retry)

    def test_isolation_probe_detects_a_live_result(self):
        state = {'value': 1}
        with self.assertRaises(AssertionError):
            assert_independent_result(self, lambda: state, lambda: state,
                                      lambda result: result.clear())


if __name__ == '__main__':
    unittest.main()
