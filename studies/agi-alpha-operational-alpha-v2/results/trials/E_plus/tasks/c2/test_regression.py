import unittest
from copy import deepcopy
from engine import Scheduler
from contract_probes import assert_rejected_unchanged, assert_idempotent, assert_independent_result


class SchedulerRegression(unittest.TestCase):
    def setUp(self):
        self.q = Scheduler(5)
        self.q.add('alpha', 'a', 3, [])
        self.q.add('alpha', 'b', 2, ['a'])
        self.q.add('beta', 'other', 2, [])

    def observe(self):
        return self.q.snapshot(), deepcopy(self.q.leases)

    def rejected(self, action):
        assert_rejected_unchanged(self, self.observe, action)

    def test_dependency_authority_and_state(self):
        self.rejected(lambda: self.q.add('beta', 'bad', 1, ['a']))
        self.rejected(lambda: self.q.claim('alpha', 'b', 'blocked'))
        self.q.claim('alpha', 'a', 'first')
        self.rejected(lambda: self.q.claim('alpha', 'b', 'blocked'))
        self.q.finish('alpha', 'a', 'first', False)
        self.rejected(lambda: self.q.claim('alpha', 'b', 'blocked'))
        self.q.cancel('alpha', 'a')
        self.rejected(lambda: self.q.claim('alpha', 'b', 'blocked'))

    def test_failure_finish_retry_and_old_receipt(self):
        self.q.claim('alpha', 'a', 'first')
        first = assert_idempotent(self, self.observe, lambda: self.q.finish('alpha', 'a', 'first', False))
        self.q.claim('alpha', 'a', 'second')
        before = deepcopy(self.observe())
        self.assertEqual(self.q.finish('alpha', 'a', 'first', False), first)
        self.assertEqual(self.observe(), before)
        self.rejected(lambda: self.q.finish('alpha', 'a', 'first', True))
        self.q.finish('alpha', 'a', 'second', True)
        self.assertEqual(self.q.finish('alpha', 'a', 'first', False), first)
        self.assertEqual(self.q.snapshot()['used'], 0)

    def test_lease_namespace_and_lifetime(self):
        self.q.claim('alpha', 'a', 'a')
        self.rejected(lambda: self.q.claim('beta', 'other', 'a'))
        self.q.finish('alpha', 'a', 'a', False)
        self.rejected(lambda: self.q.claim('alpha', 'a', 'a'))
        self.rejected(lambda: self.q.claim('beta', 'other', 'a'))
        self.q.claim('alpha', 'a', 'b')
        self.q.finish('alpha', 'a', 'b', True)
        self.rejected(lambda: self.q.claim('beta', 'other', 'b'))
        self.q.claim('beta', 'other', 'c')
        self.q.cancel('beta', 'other')
        self.rejected(lambda: self.q.claim('alpha', 'b', 'c'))

    def test_active_claim_and_capacity(self):
        assert_idempotent(self, self.observe, lambda: self.q.claim('alpha', 'a', 'one'))
        self.rejected(lambda: self.q.claim('alpha', 'a', 'two'))
        self.q.claim('beta', 'other', 'three')
        self.assertEqual(self.q.snapshot()['used'], 5)
        self.q.add('alpha', 'extra', 1, [])
        self.rejected(lambda: self.q.claim('alpha', 'extra', 'four'))
        self.q.finish('alpha', 'a', 'one', True)
        self.q.claim('alpha', 'b', 'four')
        self.assertEqual(self.q.snapshot()['used'], 4)

    def test_cancel_invalidates_only_active_lease(self):
        self.q.claim('alpha', 'a', 'one')
        receipt = self.q.finish('alpha', 'a', 'one', False)
        self.q.claim('alpha', 'a', 'two')
        assert_idempotent(self, self.observe, lambda: self.q.cancel('alpha', 'a'))
        self.assertEqual(self.q.snapshot()['used'], 0)
        self.rejected(lambda: self.q.finish('alpha', 'a', 'two', True))
        self.rejected(lambda: self.q.finish('alpha', 'a', 'two', False))
        before = deepcopy(self.observe())
        self.assertEqual(self.q.finish('alpha', 'a', 'one', False), receipt)
        self.assertEqual(self.observe(), before)

    def test_success_retry_and_terminal_behavior(self):
        self.q.claim('alpha', 'a', 'one')
        assert_idempotent(self, self.observe, lambda: self.q.finish('alpha', 'a', 'one', True))
        self.rejected(lambda: self.q.finish('alpha', 'a', 'one', False))
        self.rejected(lambda: self.q.cancel('alpha', 'a'))
        self.rejected(lambda: self.q.claim('alpha', 'a', 'two'))

    def test_job_identity_and_order(self):
        assert_idempotent(self, self.observe, lambda: self.q.add('alpha', 'a', 3, []))
        self.rejected(lambda: self.q.add('beta', 'a', 3, []))
        self.rejected(lambda: self.q.add('alpha', 'a', 2, []))
        self.q.add('alpha', 'x', 1, [])
        self.q.add('alpha', 'z', 1, ['a', 'x'])
        self.rejected(lambda: self.q.add('alpha', 'z', 1, ['x', 'a']))
        self.rejected(lambda: self.q.add('alpha', 'new', 1, ['new']))
        self.rejected(lambda: self.q.add('alpha', 'new', 1, ['a', 'a']))
        self.rejected(lambda: self.q.add('alpha', 'new', 1, ['missing']))

    def test_authority_rejections(self):
        self.q.claim('alpha', 'a', 'one')
        for action in [lambda: self.q.claim('beta', 'a', 'one'),
                       lambda: self.q.finish('beta', 'a', 'one', True),
                       lambda: self.q.finish('alpha', 'b', 'one', True),
                       lambda: self.q.cancel('beta', 'a'),
                       lambda: self.q.finish('alpha', 'a', 'missing', True),
                       lambda: self.q.cancel('alpha', 'missing')]:
            self.rejected(action)

    def test_strict_input_boundaries(self):
        for value in [False, True, 0, -1, 1.0, '5', None]:
            with self.assertRaises(ValueError):
                Scheduler(value)
        for cost in [True, False, 0, -1, 6, 1.0, None]:
            self.rejected(lambda cost=cost: self.q.add('alpha', 'new', cost, []))
        for deps in [None, (), {}, 'a', [None], ['']]:
            self.rejected(lambda deps=deps: self.q.add('alpha', 'new', 1, deps))
        for bad in ['', None, 7, [], {}]:
            self.rejected(lambda bad=bad: self.q.add(bad, 'new', 1, []))
            self.rejected(lambda bad=bad: self.q.claim('alpha', 'a', bad))
        self.q.claim('alpha', 'a', 'valid')
        for bad in [0, 1, None, 'true']:
            self.rejected(lambda bad=bad: self.q.finish('alpha', 'a', 'valid', bad))

    def test_copy_isolation(self):
        deps = ['a']
        self.q.add('alpha', 'copy', 1, deps)
        deps.append('other')
        self.assertEqual(self.q.snapshot()['jobs']['copy']['deps'], ['a'])
        assert_independent_result(self, self.observe, self.q.snapshot,
                                  lambda r: r['jobs']['copy']['deps'].append('other'))
        assert_independent_result(self, self.observe, lambda: self.q.add('alpha', 'new', 1, []),
                                  lambda r: r['deps'].append('other'))
        assert_independent_result(self, self.observe, lambda: self.q.claim('alpha', 'a', 'one'),
                                  lambda r: r.update(state='canceled'))
        assert_independent_result(self, self.observe, lambda: self.q.finish('alpha', 'a', 'one', False),
                                  lambda r: r['deps'].append('other'))
        assert_independent_result(self, self.observe, lambda: self.q.finish('alpha', 'a', 'one', False),
                                  lambda r: r.update(state='canceled'))
        assert_independent_result(self, self.observe, lambda: self.q.cancel('alpha', 'a'),
                                  lambda r: r.update(cost=100))

    def test_many_attempts_and_capacity_invariant(self):
        q = Scheduler(7)
        for job in range(7):
            q.add('o', str(job), 1, [])
        for attempt in range(30):
            for job in range(7):
                q.claim('o', str(job), '%s:%s' % (attempt, job))
                snapshot = q.snapshot()
                self.assertEqual(snapshot['used'], sum(r['cost'] for r in snapshot['jobs'].values() if r['state'] == 'running'))
                self.assertLessEqual(snapshot['used'], 7)
            for job in range(7):
                action = lambda job=job: q.finish('o', str(job), '%s:%s' % (attempt, job), False)
                assert_idempotent(self, q.snapshot, action)
            self.assertEqual(q.snapshot()['used'], 0)


if __name__ == '__main__':
    unittest.main()
