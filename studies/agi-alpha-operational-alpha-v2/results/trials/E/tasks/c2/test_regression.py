import unittest
from engine import Scheduler


class Regression(unittest.TestCase):
    def invariant(self, scheduler):
        snapshot = scheduler.snapshot()
        self.assertEqual(snapshot['used'], sum(row['cost'] for row in snapshot['jobs'].values()
                                               if row['state'] == 'running'))
        self.assertTrue(0 <= snapshot['used'] <= snapshot['capacity'])
        for row in snapshot['jobs'].values():
            self.assertEqual(row['lease'] is not None, row['state'] == 'running')

    def rejected(self, scheduler, function, *args):
        before = scheduler.snapshot()
        with self.assertRaises(ValueError):
            function(*args)
        self.assertEqual(scheduler.snapshot(), before)
        self.invariant(scheduler)

    def test_dependencies_only_unlock_after_success(self):
        s = Scheduler(6)
        s.add('a', 'parent', 2, [])
        s.add('a', 'child', 2, ['parent'])
        self.rejected(s, s.claim, 'a', 'child', 'child-lease')
        s.claim('a', 'parent', 'p1')
        self.rejected(s, s.claim, 'a', 'child', 'child-lease')
        s.finish('a', 'parent', 'p1', False)
        self.rejected(s, s.claim, 'a', 'child', 'child-lease')
        s.claim('a', 'parent', 'p2')
        s.finish('a', 'parent', 'p2', True)
        s.claim('a', 'child', 'child-lease')
        self.assertEqual(s.snapshot()['used'], 2)
        self.invariant(s)
        blocked = Scheduler(4)
        blocked.add('a', 'parent', 1, [])
        blocked.add('a', 'child', 1, ['parent'])
        blocked.cancel('a', 'parent')
        self.rejected(blocked, blocked.claim, 'a', 'child', 'l')

    def test_dependency_ownership_and_add_identity(self):
        s = Scheduler(5)
        s.add('a', 'one', 1, [])
        s.add('a', 'two', 1, [])
        self.rejected(s, s.add, 'b', 'foreign', 1, ['one'])
        deps = ['one', 'two']
        added = s.add('a', 'child', 2, deps)
        deps.reverse()
        added['deps'].clear()
        self.assertEqual(s.add('a', 'child', 2, ['one', 'two'])['deps'], ['one', 'two'])
        self.rejected(s, s.add, 'a', 'child', 2, ['two', 'one'])
        self.rejected(s, s.add, 'b', 'child', 2, ['one', 'two'])
        self.rejected(s, s.add, 'a', 'child', 3, ['one', 'two'])
        self.rejected(s, s.add, 'a', 'x', 1, ['x'])
        self.rejected(s, s.add, 'a', 'x', 1, ['one', 'one'])
        self.rejected(s, s.add, 'a', 'x', 1, ['unknown'])

    def test_lease_ids_cannot_be_reused(self):
        s = Scheduler(5)
        for owner, job in [('a', 'first'), ('a', 'second'), ('b', 'third')]:
            s.add(owner, job, 1, [])
        s.claim('a', 'first', 'shared')
        self.rejected(s, s.claim, 'a', 'second', 'shared')
        self.rejected(s, s.claim, 'b', 'third', 'shared')
        s.finish('a', 'first', 'shared', False)
        self.rejected(s, s.claim, 'a', 'first', 'shared')
        self.rejected(s, s.claim, 'a', 'second', 'shared')
        s.claim('a', 'first', 'new')
        s.finish('a', 'first', 'new', True)
        self.rejected(s, s.claim, 'a', 'second', 'new')
        s.claim('a', 'second', 'cancelled')
        s.cancel('a', 'second')
        self.rejected(s, s.claim, 'b', 'third', 'cancelled')
        s.claim('b', 'third', 'SHARED')
        self.invariant(s)

    def test_finish_retries_survive_later_attempts(self):
        s = Scheduler(3)
        s.add('a', 'job', 3, [])
        s.claim('a', 'job', 'old')
        s.finish('a', 'job', 'old', False)
        before = s.snapshot()
        s.finish('a', 'job', 'old', False)
        self.assertEqual(s.snapshot(), before)
        self.rejected(s, s.finish, 'a', 'job', 'old', True)
        s.claim('a', 'job', 'new')
        before = s.snapshot()
        s.finish('a', 'job', 'old', False)
        self.assertEqual(s.snapshot(), before)
        s.finish('a', 'job', 'new', True)
        before = s.snapshot()
        s.finish('a', 'job', 'new', True)
        s.finish('a', 'job', 'old', False)
        self.assertEqual(s.snapshot(), before)
        self.rejected(s, s.finish, 'a', 'job', 'new', False)
        self.rejected(s, s.cancel, 'a', 'job')

    def test_cancel_invalidates_only_active_lease(self):
        s = Scheduler(3)
        s.add('a', 'job', 3, [])
        s.claim('a', 'job', 'failed')
        s.finish('a', 'job', 'failed', False)
        s.claim('a', 'job', 'active')
        s.cancel('a', 'job')
        self.assertEqual(s.snapshot()['used'], 0)
        before = s.snapshot()
        s.cancel('a', 'job')
        s.finish('a', 'job', 'failed', False)
        self.assertEqual(s.snapshot(), before)
        self.rejected(s, s.finish, 'a', 'job', 'active', True)
        self.rejected(s, s.finish, 'a', 'job', 'active', False)
        self.rejected(s, s.claim, 'a', 'job', 'another')

    def test_capacity_rejection_and_caller_mutation(self):
        s = Scheduler(5)
        s.add('a', 'big', 4, [])
        s.add('b', 'small', 2, [])
        claimed = s.claim('a', 'big', 'l1')
        claimed['cost'] = 0
        claimed['deps'].append('bad')
        before = s.snapshot()
        s.claim('a', 'big', 'l1')
        self.assertEqual(s.snapshot(), before)
        self.rejected(s, s.claim, 'a', 'big', 'replacement')
        self.rejected(s, s.claim, 'b', 'small', 'l2')
        self.rejected(s, s.finish, 'b', 'big', 'l1', True)
        self.rejected(s, s.finish, 'a', 'big', 'wrong', True)
        self.rejected(s, s.cancel, 'b', 'big')
        s.cancel('a', 'big')
        s.claim('b', 'small', 'l2')
        snapshot = s.snapshot()
        snapshot['jobs']['small']['cost'] = 100
        snapshot['jobs']['small']['deps'].append('bad')
        self.assertEqual(s.snapshot()['used'], 2)
        self.invariant(s)

    def test_validation_and_literal_identifiers(self):
        for capacity in [0, -1, True, 1.0, '3', None]:
            with self.assertRaises(ValueError):
                Scheduler(capacity)
        s = Scheduler(3)
        for args in [('', 'x', 1, []), ('a', '', 1, []), ('a', 'x', True, []),
                     ('a', 'x', 0, []), ('a', 'x', 4, []), ('a', 'x', 1, ()),
                     ('a', 'x', 1, [None]), ('a', 'x', 1, [[]])]:
            self.rejected(s, s.add, *args)
        s.add('__internal__', '__proto__', 3, [])
        self.rejected(s, s.claim, '__internal__', '__proto__', '')
        self.rejected(s, s.claim, '__INTERNAL__', '__proto__', 'literal')
        self.rejected(s, s.claim, '__internal__', 'missing', 'literal')
        s.claim('__internal__', '__proto__', '__proto__')
        for success in [0, 1, None, 'yes', []]:
            self.rejected(s, s.finish, '__internal__', '__proto__', '__proto__', success)
        s.finish('__internal__', '__proto__', '__proto__', True)
        self.invariant(s)


if __name__ == '__main__':
    unittest.main()
