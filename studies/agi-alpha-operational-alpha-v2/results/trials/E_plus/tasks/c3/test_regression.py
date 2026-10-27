import hashlib
import json
import random
import unittest
from copy import deepcopy
from engine import ArtifactStore
from contract_probes import assert_rejected_unchanged, assert_idempotent, assert_independent_result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(owner='a', upload='u', data=b'abc', state='active', cells=None):
    return dict(owner=owner, upload=upload, size=len(data), digest=digest(data), state=state,
                cells=[None] * len(data) if cells is None else cells)


class ArtifactRegression(unittest.TestCase):
    def setUp(self):
        self.store = ArtifactStore()
        self.data = b'abcde'
        self.store.begin('alpha', 'same', len(self.data), digest(self.data))

    def rejected(self, action):
        assert_rejected_unchanged(self, self.store.snapshot, action)

    def test_tenant_scoping_and_unknown_owner(self):
        self.store.begin('beta', 'same', 3, digest(b'xyz'))
        self.store.put('alpha', 'same', 0, self.data)
        self.store.put('beta', 'same', 0, b'xyz')
        self.assertEqual(self.store.commit('alpha', 'same'), self.data)
        self.assertEqual(self.store.commit('beta', 'same'), b'xyz')
        for action in [lambda: self.store.put('unknown', 'same', 0, b''),
                       lambda: self.store.commit('unknown', 'same'),
                       lambda: self.store.abort('unknown', 'same'),
                       lambda: self.store.commit('alpha', 'unknown')]:
            self.rejected(action)

    def test_conflicting_overlap_is_whole_write_atomic(self):
        self.store.put('alpha', 'same', 2, b'c')
        self.rejected(lambda: self.store.put('alpha', 'same', 0, b'abXde'))
        self.assertEqual(self.store.snapshot()[0]['cells'], [None, None, 99, None, None])
        assert_idempotent(self, self.store.snapshot, lambda: self.store.put('alpha', 'same', 0, b'abc'))
        self.store.put('alpha', 'same', 1, b'bcde')
        self.assertEqual(self.store.commit('alpha', 'same'), self.data)

    def test_digest_and_completeness_before_commit(self):
        self.rejected(lambda: self.store.commit('alpha', 'same'))
        self.store.put('alpha', 'same', 0, b'abcd')
        self.rejected(lambda: self.store.commit('alpha', 'same'))
        self.store.put('alpha', 'same', 4, b'X')
        self.rejected(lambda: self.store.commit('alpha', 'same'))
        self.assertEqual(self.store.snapshot()[0]['state'], 'active')
        self.store.abort('alpha', 'same')
        self.assertEqual(self.store.snapshot()[0]['cells'], [None] * 5)

    def test_empty_artifact_digest(self):
        self.store.begin('a', 'empty', 0, digest(b''))
        self.store.put('a', 'empty', 0, b'')
        self.assertEqual(assert_idempotent(self, self.store.snapshot, lambda: self.store.commit('a', 'empty')), b'')
        self.store.begin('a', 'wrong', 0, digest(b'x'))
        self.rejected(lambda: self.store.commit('a', 'wrong'))
        invalid = record(data=b'', state='committed', cells=[])
        invalid['digest'] = digest(b'x')
        with self.assertRaises(ValueError):
            ArtifactStore.restore([invalid])

    def test_begin_idempotent_in_every_state(self):
        for state in ['active', 'committed', 'aborted']:
            store = ArtifactStore()
            store.begin('o', 'u', 1, digest(b'x'))
            if state == 'committed':
                store.put('o', 'u', 0, b'x')
                store.commit('o', 'u')
            elif state == 'aborted':
                store.abort('o', 'u')
            assert_idempotent(self, store.snapshot, lambda: store.begin('o', 'u', 1, digest(b'x')))
            self.assertEqual(store.snapshot()[0]['state'], state)
            for size, sha in [(2, digest(b'x')), (1, digest(b'y'))]:
                assert_rejected_unchanged(self, store.snapshot, lambda size=size, sha=sha: store.begin('o', 'u', size, sha))

    def test_aborted_upload_remains_aborted(self):
        self.store.put('alpha', 'same', 0, b'ab')
        assert_idempotent(self, self.store.snapshot, lambda: self.store.abort('alpha', 'same'))
        self.store.begin('alpha', 'same', 5, digest(self.data))
        self.rejected(lambda: self.store.put('alpha', 'same', 0, b''))
        self.rejected(lambda: self.store.put('alpha', 'same', 0, self.data))
        self.rejected(lambda: self.store.commit('alpha', 'same'))
        self.assertEqual(self.store.snapshot()[0]['state'], 'aborted')

    def test_committed_consistent_writes_only(self):
        self.store.put('alpha', 'same', 0, self.data)
        assert_idempotent(self, self.store.snapshot, lambda: self.store.commit('alpha', 'same'))
        assert_idempotent(self, self.store.snapshot, lambda: self.store.put('alpha', 'same', 1, b'bcd'))
        assert_idempotent(self, self.store.snapshot, lambda: self.store.put('alpha', 'same', 5, b''))
        self.rejected(lambda: self.store.put('alpha', 'same', 1, b'bcX'))
        self.rejected(lambda: self.store.abort('alpha', 'same'))
        self.assertEqual(self.store.commit('alpha', 'same'), self.data)

    def test_checkpoint_and_snapshot_independence(self):
        self.store.put('alpha', 'same', 0, b'ab')
        checkpoint = self.store.snapshot()
        restored = ArtifactStore.restore(checkpoint)
        expected = deepcopy(restored.snapshot())
        checkpoint[0]['cells'][0] = 0
        checkpoint[0]['owner'] = 'changed'
        self.assertEqual(restored.snapshot(), expected)
        assert_independent_result(self, self.store.snapshot, self.store.snapshot,
                                  lambda rows: rows[0]['cells'].__setitem__(0, 0))
        restored.put('alpha', 'same', 2, b'cde')
        self.assertEqual(restored.commit('alpha', 'same'), self.data)
        self.assertEqual(self.store.snapshot()[0]['cells'], [97, 98, None, None, None])
        json.loads(json.dumps(restored.snapshot()))

    def test_restore_validation(self):
        base = record()
        bad_records = [None, [], {}, dict(base, extra=1), {k: v for k, v in base.items() if k != 'cells'},
                       dict(base, owner=''), dict(base, upload=1), dict(base, size=True),
                       dict(base, size=-1), dict(base, size=65537), dict(base, size=3.0),
                       dict(base, digest='A' * 64), dict(base, digest='0' * 63),
                       dict(base, state='other'), dict(base, state=[]),
                       dict(base, cells=()), dict(base, cells=[None]),
                       dict(base, cells=[True, None, None]), dict(base, cells=[-1, None, None]),
                       dict(base, cells=[256, None, None]), dict(base, cells=[1.0, None, None]),
                       dict(base, cells=['a', None, None]),
                       dict(base, state='aborted', cells=[97, None, None]),
                       dict(base, state='committed'),
                       dict(base, state='committed', cells=[97, 98, 100])]
        for bad in bad_records:
            with self.subTest(bad=bad):
                original = deepcopy(bad)
                with self.assertRaises(ValueError):
                    ArtifactStore.restore([bad])
                self.assertEqual(bad, original)
        for checkpoint in [None, {}, (), 'checkpoint', [base, deepcopy(base)]]:
            with self.assertRaises(ValueError):
                ArtifactStore.restore(checkpoint)
        self.assertEqual(ArtifactStore.restore([]).snapshot(), [])

    def test_restored_states_sorting_and_same_id(self):
        rows = [record('z', 'same', b'abc', 'committed', [97, 98, 99]),
                record('a', 'same', b'xyz', 'active', [120, None, 122]),
                record('a', 'Same', b'abc', 'aborted'),
                record('A', 'same', b'', 'committed', [])]
        restored = ArtifactStore.restore(rows)
        self.assertEqual([(r['owner'], r['upload']) for r in restored.snapshot()], [('A', 'same'), ('a', 'Same'), ('a', 'same'), ('z', 'same')])
        self.assertEqual(restored.commit('z', 'same'), b'abc')
        self.assertEqual(restored.commit('A', 'same'), b'')
        restored.put('a', 'same', 1, b'y')
        self.assertEqual(restored.commit('a', 'same'), b'xyz')
        assert_rejected_unchanged(self, restored.snapshot, lambda: restored.put('a', 'Same', 0, b''))
        self.assertEqual(ArtifactStore.restore(restored.snapshot()).snapshot(), restored.snapshot())

    def test_strict_input_boundaries(self):
        for bad in ['', None, 1, [], {}]:
            self.rejected(lambda bad=bad: self.store.begin(bad, 'u', 0, digest(b'')))
            self.rejected(lambda bad=bad: self.store.commit('alpha', bad))
        for size in [True, False, -1, 65537, 1.0, None]:
            self.rejected(lambda size=size: self.store.begin('alpha', 'new', size, digest(b'a')))
        for sha in ['', 'A' * 64, '0' * 63, 'g' * 64, '0' * 64 + '\n', None, 0]:
            self.rejected(lambda sha=sha: self.store.begin('alpha', 'new', 1, sha))
        for offset in [True, False, -1, 6, 1.0, None]:
            self.rejected(lambda offset=offset: self.store.put('alpha', 'same', offset, b''))
        for data in [None, '', [], bytearray(b'a'), memoryview(b'a')]:
            self.rejected(lambda data=data: self.store.put('alpha', 'same', 0, data))
        self.rejected(lambda: self.store.put('alpha', 'same', 4, b'ef'))
        self.store.put('alpha', 'same', 5, b'')
        self.store.begin('alpha', 'max', 65536, digest(bytes(65536)))
        self.store.put('alpha', 'max', 0, bytes(65536))
        self.assertEqual(self.store.commit('alpha', 'max'), bytes(65536))

    def test_seeded_overlaps_and_checkpoint_resume(self):
        rng = random.Random(9107)
        for index in range(25):
            data = bytes(rng.randrange(256) for _ in range(rng.randint(1, 120)))
            store = ArtifactStore()
            store.begin('o', str(index), len(data), digest(data))
            present = [None] * len(data)
            for write in range(40):
                start = rng.randrange(len(data) + 1)
                end = rng.randrange(start, len(data) + 1)
                chunk = data[start:end]
                assert_idempotent(self, store.snapshot, lambda: store.put('o', str(index), start, chunk))
                present[start:end] = chunk
                self.assertEqual(store.snapshot()[0]['cells'], present)
                if write % 8 == 0:
                    store = ArtifactStore.restore(store.snapshot())
            store.put('o', str(index), 0, data)
            assert_idempotent(self, store.snapshot, lambda: store.commit('o', str(index)))
            self.assertEqual(ArtifactStore.restore(store.snapshot()).commit('o', str(index)), data)


if __name__ == '__main__':
    unittest.main()
