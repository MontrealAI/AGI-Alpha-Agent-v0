import random
import unittest
from copy import deepcopy
from engine import Journal
from contract_probes import assert_rejected_unchanged, assert_idempotent, assert_independent_result


def event(eid='e1', job='j1', owner='alpha', kind='reserve', amount=40):
    return dict(id=eid, job=job, owner=owner, kind=kind, amount=amount)


class JournalRegression(unittest.TestCase):
    def setUp(self):
        self.initial = {'alpha': 100, 'beta': 70, 'zero': 0}
        self.j = Journal(self.initial)

    def observe(self):
        return self.j.snapshot(), self.j.export_log(), deepcopy(self.j.receipts)

    def rejected(self, action):
        assert_rejected_unchanged(self, self.observe, action)

    def test_full_event_identity(self):
        original = event()
        receipt = assert_idempotent(self, self.observe, lambda: self.j.append(original))
        self.assertEqual(receipt, dict(id='e1', sequence=1, job='j1', kind='reserve'))
        for change in [dict(job='different'), dict(owner='beta'), dict(amount=39), dict(kind='cancel', amount=0)]:
            changed = dict(original, **change)
            self.rejected(lambda changed=changed: self.j.append(changed))
        self.j.append(event('e2', kind='settle', amount=25))
        before = deepcopy(self.observe())
        self.assertEqual(self.j.append(original), receipt)
        self.assertEqual(self.observe(), before)

    def test_wrong_owner_terminal_is_atomic(self):
        self.j.append(event())
        for kind, amount in [('settle', 20), ('cancel', 0)]:
            self.rejected(lambda kind=kind, amount=amount: self.j.append(event('terminal', owner='beta', kind=kind, amount=amount)))
        self.assertEqual(self.j.append(event('terminal', kind='settle', amount=20))['sequence'], 2)
        self.assertEqual(self.j.snapshot()['wallets']['alpha'], dict(available=80, reserved=0, spent=20))
        self.assertEqual(self.j.snapshot()['wallets']['beta'], dict(available=70, reserved=0, spent=0))

    def test_terminal_retry_and_new_id_rejection(self):
        for kind, amount in [('settle', 0), ('settle', 40), ('cancel', 0)]:
            with self.subTest(kind=kind, amount=amount):
                self.setUp()
                self.j.append(event())
                terminal = event('e2', kind=kind, amount=amount)
                assert_idempotent(self, self.observe, lambda: self.j.append(terminal))
                self.rejected(lambda: self.j.append(dict(terminal, id='new')))
                self.rejected(lambda: self.j.append(event('new', amount=1)))
                self.assertEqual(len(self.j.export_log()), 2)

    def test_failed_events_do_not_poison_ids_or_sequences(self):
        failures = [event('reuse', amount=101), event('reuse', owner='unknown'),
                    event('reuse', kind='settle', amount=0), event('reuse', kind='unknown'),
                    event('reuse', amount=0)]
        for value in failures:
            self.rejected(lambda value=value: self.j.append(value))
        self.assertEqual(self.j.append(event('reuse'))['sequence'], 1)
        self.rejected(lambda: self.j.append(event('second', kind='settle', amount=41)))
        self.rejected(lambda: self.j.append(event('second', kind='cancel', amount=1)))
        self.assertEqual(self.j.append(event('second', kind='cancel', amount=0))['sequence'], 2)

    def test_deep_copy_at_every_boundary(self):
        self.initial['alpha'] = 0
        self.assertEqual(self.j.snapshot()['wallets']['alpha']['available'], 100)
        source = event()
        self.j.append(source)
        source['amount'] = 90
        source['id'] = 'mutated'
        self.assertEqual(self.j.export_log(), [event()])
        assert_independent_result(self, self.observe, self.j.export_log,
                                  lambda log: log[0].update(amount=99))
        assert_independent_result(self, self.observe, self.j.snapshot,
                                  lambda snapshot: snapshot['jobs']['j1'].update(cap=99))
        assert_independent_result(self, self.observe, lambda: self.j.append(event()),
                                  lambda receipt: receipt.update(sequence=999))
        assert_independent_result(self, self.observe, lambda: self.j.append(event('done', kind='cancel', amount=0)),
                                  lambda receipt: receipt.update(id='mutated'))
        log = self.j.export_log()
        other = Journal.replay({'alpha': 100, 'beta': 70, 'zero': 0}, log)
        log[0]['owner'] = 'beta'
        self.assertEqual(other.snapshot(), self.j.snapshot())
        self.assertEqual(other.export_log(), self.j.export_log())

    def test_replay_duplicates_order_and_rejection(self):
        reserve = event()
        settle = event('done', kind='settle', amount=12)
        log = [reserve, reserve.copy(), settle, reserve.copy(), settle.copy()]
        replayed = Journal.replay(self.initial, log)
        self.assertEqual(replayed.export_log(), [reserve, settle])
        self.assertEqual(replayed.append(settle)['sequence'], 2)
        self.assertEqual(replayed.snapshot()['wallets']['alpha'], dict(available=88, reserved=0, spent=12))
        for bad in [None, (), {}, 'events', [settle, reserve], [reserve, dict(reserve, amount=1)], [reserve, None]]:
            with self.assertRaises(ValueError):
                Journal.replay(self.initial, bad)
        self.assertEqual(self.j.export_log(), [])

    def test_input_validation(self):
        for value in [None, [], 1, {'': 1}, {3: 1}, {'a': True}, {'a': -1}, {'a': 1.0}]:
            with self.assertRaises(ValueError):
                Journal(value)
        for value in [None, [], {}, dict(event(), extra=1), {k: v for k, v in event().items() if k != 'amount'}]:
            self.rejected(lambda value=value: self.j.append(value))
        for key in ['id', 'job', 'owner', 'kind']:
            for bad in ['', None, [], {}, 5]:
                value = dict(event(), **{key: bad})
                self.rejected(lambda value=value: self.j.append(value))
        for bad in [True, False, -1, 1.0, None, '40']:
            self.rejected(lambda bad=bad: self.j.append(event(amount=bad)))
        self.rejected(lambda: self.j.append(event(owner='zero', amount=1)))
        self.assertEqual(Journal({}).snapshot(), dict(wallets={}, jobs={}))

    def test_case_sensitive_names_and_multiple_reservations(self):
        j = Journal({'owner': 10, 'Owner': 10})
        j.append(event('owner', 'owner', 'owner', amount=7))
        j.append(event('Owner', 'Owner', 'Owner', amount=6))
        j.append(event('third', 'third', 'owner', amount=3))
        self.assertEqual(j.snapshot()['wallets']['owner'], dict(available=0, reserved=10, spent=0))
        j.append(event('finish', 'owner', 'owner', 'settle', 4))
        self.assertEqual(j.snapshot()['wallets']['owner'], dict(available=3, reserved=3, spent=4))
        self.assertEqual(j.snapshot()['wallets']['Owner'], dict(available=4, reserved=6, spent=0))

    def test_seeded_accounting_and_replay(self):
        rng = random.Random(62891)
        initial = {'a': 10000, 'b': 10000, 'c': 10000}
        j = Journal(initial)
        expected = {owner: dict(available=value, reserved=0, spent=0) for owner, value in initial.items()}
        for index in range(200):
            owner = rng.choice(list(initial))
            cap = rng.randint(1, 50)
            job = str(index)
            reserve = event('r' + job, job, owner, 'reserve', cap)
            assert_idempotent(self, j.snapshot, lambda: j.append(reserve))
            expected[owner]['available'] -= cap
            expected[owner]['reserved'] += cap
            self.assertEqual(j.snapshot()['wallets'], expected)
            kind = rng.choice(['cancel', 'settle'])
            spent = rng.randint(0, cap) if kind == 'settle' else 0
            terminal = event('t' + job, job, owner, kind, spent)
            assert_idempotent(self, j.snapshot, lambda: j.append(terminal))
            expected[owner]['available'] += cap - spent
            expected[owner]['reserved'] -= cap
            expected[owner]['spent'] += spent
            self.assertEqual(j.snapshot()['wallets'], expected)
            for who, wallet in expected.items():
                self.assertEqual(sum(wallet.values()), initial[who])
                self.assertTrue(all(value >= 0 for value in wallet.values()))
        restored = Journal.replay(initial, j.export_log())
        self.assertEqual(restored.snapshot(), j.snapshot())
        self.assertEqual(restored.export_log(), j.export_log())
        self.assertEqual(restored.append(terminal)['sequence'], 400)


if __name__ == '__main__':
    unittest.main()
