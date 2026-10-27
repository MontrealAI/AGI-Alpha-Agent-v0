import copy
import hashlib
import unittest
from engine import ArtifactStore


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Regression(unittest.TestCase):
    def rejected(self, store, function, *args):
        before = store.snapshot()
        with self.assertRaises(ValueError):
            function(*args)
        self.assertEqual(store.snapshot(), before)

    def test_scope_replay_and_lifecycle(self):
        s = ArtifactStore()
        for owner, data in [('z', b'abc'), ('a', b'xyz')]:
            s.begin(owner, 'same', 3, digest(data))
            s.put(owner, 'same', 0, data)
            self.assertEqual(s.commit(owner, 'same'), data)
            self.assertEqual(s.commit(owner, 'same'), data)
            s.begin(owner, 'same', 3, digest(data))
            s.put(owner, 'same', 1, data[1:])
            self.rejected(s, s.begin, owner, 'same', 4, digest(data))
            self.rejected(s, s.abort, owner, 'same')
            self.rejected(s, s.put, owner, 'same', 0, b'!')
        self.assertEqual([r['owner'] for r in s.snapshot()], ['a', 'z'])
        self.rejected(s, s.commit, 'other', 'same')
        s.begin('a', 'aborted', 2, digest(b'ab'))
        s.put('a', 'aborted', 0, b'a')
        s.abort('a', 'aborted')
        s.abort('a', 'aborted')
        s.begin('a', 'aborted', 2, digest(b'ab'))
        self.rejected(s, s.put, 'a', 'aborted', 0, b'ab')
        self.rejected(s, s.commit, 'a', 'aborted')

    def test_overlap_atomicity_and_digest(self):
        s = ArtifactStore()
        s.begin('a', 'x', 4, digest(b'abcd'))
        s.put('a', 'x', 2, b'cd')
        self.rejected(s, s.put, 'a', 'x', 0, b'abX')
        self.rejected(s, s.commit, 'a', 'x')
        s.put('a', 'x', 0, b'abc')
        self.assertEqual(s.commit('a', 'x'), b'abcd')
        s.begin('a', 'bad', 3, digest(b'yes'))
        s.put('a', 'bad', 0, b'bad')
        self.rejected(s, s.commit, 'a', 'bad')

    def test_input_validation_and_boundaries(self):
        s = ArtifactStore()
        for args in [('', 'x', 0, digest(b'')), ('a', '', 0, digest(b'')),
                     ('a', 'x', True, digest(b'')), ('a', 'x', -1, digest(b'')),
                     ('a', 'x', 65537, digest(b'')), ('a', 'x', 1, 'A' * 64),
                     ('a', 'x', 0, digest(b'wrong'))]:
            self.rejected(s, s.begin, *args)
        s.begin('a', 'empty', 0, digest(b''))
        s.put('a', 'empty', 0, b'')
        self.assertEqual(s.commit('a', 'empty'), b'')
        data = bytes(range(256)) * 256
        s.begin('a', 'max', len(data), digest(data))
        for offset, chunk in [(True, b''), (-1, b''), (65537, b''),
                              (65536, b'a'), (0, bytearray(b'a')), (0, 'a')]:
            self.rejected(s, s.put, 'a', 'max', offset, chunk)
        s.put('a', 'max', 65536, b'')
        s.put('a', 'max', 0, data)
        self.assertEqual(s.commit('a', 'max'), data)

    def test_snapshot_and_restore_independence(self):
        s = ArtifactStore()
        s.begin('a', 'x', 3, digest(b'abc'))
        s.put('a', 'x', 0, b'a')
        snapshot = s.snapshot()
        restored = ArtifactStore.restore(snapshot)
        snapshot[0]['cells'][0] = 255
        snapshot[0]['state'] = 'aborted'
        self.assertEqual(restored.snapshot(), s.snapshot())
        restored.put('a', 'x', 1, b'bc')
        self.assertEqual(restored.commit('a', 'x'), b'abc')
        self.assertEqual(s.snapshot()[0]['cells'], [97, None, None])
        self.assertEqual(ArtifactStore.restore(restored.snapshot()).commit('a', 'x'), b'abc')

    def test_restore_rejects_invalid_records(self):
        s = ArtifactStore()
        s.begin('a', 'x', 1, digest(b'a'))
        base = s.snapshot()[0]
        invalid = [None, {}, [base, copy.deepcopy(base)], [dict(base, extra=1)]]
        for key, value in [('owner', ''), ('upload', 2), ('size', True),
                           ('digest', 'x' * 64), ('state', []), ('state', 'lost'),
                           ('cells', []), ('cells', [True]), ('cells', [256]),
                           ('cells', [-1]), ('cells', ['a'])]:
            invalid.append([dict(base, **{key: value})])
        invalid += [[dict(base, state='committed')],
                    [dict(base, state='committed', cells=[98])],
                    [dict(base, state='aborted', cells=[97])]]
        for snapshot in invalid:
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                ArtifactStore.restore(snapshot)
        self.assertEqual(ArtifactStore.restore([]).snapshot(), [])
        self.assertEqual(ArtifactStore.restore([dict(base, state='aborted')]).snapshot(),
                         [dict(base, state='aborted')])


if __name__ == '__main__':
    unittest.main()
