import copy
import unittest
from engine import Journal


def event(event_id='e1', job='j1', owner='a', kind='reserve', amount=4):
    return dict(id=event_id, job=job, owner=owner, kind=kind, amount=amount)


class Regression(unittest.TestCase):
    def rejected(self, journal, item):
        before, log = journal.snapshot(), journal.export_log()
        with self.assertRaises(ValueError):
            journal.append(item)
        self.assertEqual(journal.snapshot(), before)
        self.assertEqual(journal.export_log(), log)

    def test_exact_identity_and_original_sequence(self):
        j = Journal({'a': 10, 'b': 10})
        first = j.append(event())
        self.assertEqual(first, {'id': 'e1', 'sequence': 1, 'job': 'j1', 'kind': 'reserve'})
        for change in [dict(amount=3), dict(owner='b'), dict(job='j2'), dict(kind='cancel', amount=0)]:
            self.rejected(j, dict(event(), **change))
        j.append(event('e2', 'j2', amount=2))
        before = j.snapshot()
        self.assertEqual(j.append(event()), first)
        self.assertEqual(j.snapshot(), before)
        self.assertEqual(len(j.export_log()), 2)
        first['sequence'] = 999
        self.assertEqual(j.append(event())['sequence'], 1)

    def test_ownership_and_terminal_retry(self):
        j = Journal({'a': 10, 'b': 10})
        j.append(event())
        self.rejected(j, event('terminal', owner='b', kind='settle', amount=2))
        self.rejected(j, event('terminal', owner='b', kind='cancel', amount=0))
        settled = event('terminal', kind='settle', amount=2)
        receipt = j.append(settled)
        self.assertEqual(receipt['sequence'], 2)
        self.assertEqual(j.snapshot()['wallets'], {
            'a': {'available': 8, 'reserved': 0, 'spent': 2},
            'b': {'available': 10, 'reserved': 0, 'spent': 0}})
        self.assertEqual(j.append(settled), receipt)
        self.rejected(j, dict(settled, id='new'))
        self.rejected(j, event('cancel', kind='cancel', amount=0))
        self.rejected(j, event('again', owner='b'))

    def test_failed_ids_and_boundary_terminal_amounts(self):
        j = Journal({'a': 10})
        self.rejected(j, event(amount=11))
        self.assertEqual(j.append(event(amount=10))['sequence'], 1)
        self.rejected(j, event('e2', kind='settle', amount=11))
        j.append(event('e2', kind='settle', amount=0))
        self.assertEqual(j.snapshot()['wallets']['a'], {'available': 10, 'reserved': 0, 'spent': 0})
        j.append(event('e3', 'j2', amount=10))
        self.rejected(j, event('e4', 'j2', kind='cancel', amount=1))
        canceled = event('e4', 'j2', kind='cancel', amount=0)
        j.append(canceled)
        j.append(canceled)
        self.rejected(j, dict(canceled, id='e5'))
        j.append(event('e5', 'j3', amount=10))
        j.append(event('e6', 'j3', kind='settle', amount=10))
        snapshot = j.snapshot()
        self.assertEqual(snapshot['wallets']['a'], {'available': 0, 'reserved': 0, 'spent': 10})
        self.assertEqual(snapshot['jobs']['j1']['state'], 'settled')
        self.assertEqual(snapshot['jobs']['j2']['state'], 'canceled')
        self.assertEqual(len(j.export_log()), 6)

    def test_input_output_and_replay_isolation(self):
        initial = {'a': 10}
        j = Journal(initial)
        initial['a'] = 900
        item = event()
        j.append(item)
        item['amount'] = 999
        self.assertEqual(j.export_log(), [event()])
        exported = j.export_log()
        replayed = Journal.replay({'a': 10}, exported + copy.deepcopy(exported))
        exported[0]['owner'] = 'other'
        self.assertEqual(replayed.export_log(), [event()])
        self.assertEqual(replayed.snapshot(), j.snapshot())
        snapshot = j.snapshot()
        snapshot['wallets']['a']['available'] = -1
        snapshot['jobs']['j1']['cap'] = 999
        self.assertEqual(j.snapshot(), replayed.snapshot())
        replayed.append(event('e2', kind='cancel', amount=0))
        self.assertEqual(j.snapshot()['jobs']['j1']['state'], 'active')
        replayed_export = replayed.export_log()
        replayed_export[0]['amount'] = -1
        self.assertEqual(replayed.export_log()[0], event())

    def test_malformed_input_and_logs(self):
        for initial in [[], {'': 1}, {'a': -1}, {'a': True}, {1: 2}, {'a': 1.5}]:
            with self.assertRaises(ValueError):
                Journal(initial)
        self.assertEqual(Journal({}).snapshot(), {'wallets': {}, 'jobs': {}})
        j = Journal({'a': 10})
        malformed = [None, [], {}, dict(event(), extra=0)]
        for key, value in [('id', ''), ('job', None), ('owner', []), ('kind', {}),
                           ('kind', 'unknown'), ('amount', True), ('amount', 1.0),
                           ('amount', -1), ('amount', 0), ('owner', 'missing')]:
            malformed.append(dict(event(), **{key: value}))
        malformed.append(event(kind='settle', amount=0))
        for item in malformed:
            with self.subTest(item=item):
                self.rejected(j, item)
        for log in [None, {}, (event(),), [None], [event(), dict(event(), amount=3)],
                    [event('terminal', kind='settle', amount=0), event()]]:
            with self.subTest(log=log), self.assertRaises(ValueError):
                Journal.replay({'a': 10}, log)
        self.assertEqual(j.append(event())['sequence'], 1)
        self.rejected(j, dict(event(), amount=True))

    def test_multiple_reservations_conserve_each_owner(self):
        initial = {'a': 100, 'b': 40}
        j = Journal(initial)
        events = [event('1', 'a1', 'a', amount=30), event('2', 'a2', 'a', amount=20),
                  event('3', 'b1', 'b', amount=40), event('4', 'a2', 'a', 'cancel', 0),
                  event('5', 'b1', 'b', 'settle', 17), event('6', 'a1', 'a', 'settle', 30)]
        for item in events:
            j.append(item)
            state = j.snapshot()
            for owner, wallet in state['wallets'].items():
                self.assertEqual(sum(wallet.values()), initial[owner])
                self.assertTrue(all(value >= 0 for value in wallet.values()))
                self.assertEqual(wallet['reserved'], sum(job['cap'] for job in state['jobs'].values()
                                 if job['owner'] == owner and job['state'] == 'active'))
        self.assertEqual(Journal.replay(initial, events + events).snapshot(), j.snapshot())


if __name__ == '__main__':
    unittest.main()
