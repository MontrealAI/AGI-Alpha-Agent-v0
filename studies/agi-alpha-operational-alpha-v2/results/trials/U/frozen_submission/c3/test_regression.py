import copy
import hashlib
import json
import random
import unittest
from engine import ArtifactStore


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ArtifactContract(unittest.TestCase):
    def setUp(self):
        self.store = ArtifactStore()

    def begin(self, owner="a", upload="x", data=b"abcdef"):
        self.store.begin(owner, upload, len(data), digest(data))

    def unchanged_error(self, method, *args):
        before = self.store.snapshot()
        with self.assertRaises(ValueError):
            getattr(self.store, method)(*args)
        self.assertEqual(self.store.snapshot(), before)

    def test_tenant_namespaces_and_snapshot_order(self):
        for owner, upload, data in (("b", "same", b"B"), ("a", "same", b"A"),
                                     ("a", "Same", b"C"), ("a:same", "z", b"D")):
            self.begin(owner, upload, data)
            self.store.put(owner, upload, 0, data)
            self.assertEqual(self.store.commit(owner, upload), data)
        self.assertEqual([(r["owner"], r["upload"]) for r in self.store.snapshot()],
                         [("a", "Same"), ("a", "same"), ("a:same", "z"), ("b", "same")])
        self.unchanged_error("put", "other", "same", 0, b"X")
        self.unchanged_error("commit", "other", "same")
        self.unchanged_error("abort", "other", "same")
        restored = ArtifactStore.restore(json.loads(json.dumps(self.store.snapshot())))
        self.assertEqual(restored.commit("a", "same"), b"A")
        self.assertEqual(restored.commit("b", "same"), b"B")

    def test_conflict_rolls_back_new_prefix_and_complete_write(self):
        self.begin()
        self.store.put("a", "x", 2, b"cd")
        self.unchanged_error("put", "a", "x", 0, b"abXYef")
        self.assertEqual(self.store.snapshot()[0]["cells"], [None, None, 99, 100, None, None])
        self.unchanged_error("commit", "a", "x")
        self.store.put("a", "x", 0, b"abc")
        self.store.put("a", "x", 3, b"def")
        self.store.put("a", "x", 1, b"bcde")
        self.assertEqual(self.store.commit("a", "x"), b"abcdef")
        before = self.store.snapshot()
        self.store.put("a", "x", 2, b"cd")
        self.store.put("a", "x", 6, b"")
        self.assertEqual(self.store.snapshot(), before)
        self.unchanged_error("put", "a", "x", 2, b"XD")
        self.assertEqual(self.store.commit("a", "x"), b"abcdef")

    def test_commit_checks_digest_before_transition_including_empty(self):
        self.begin(data=b"right")
        self.store.put("a", "x", 0, b"wrong")
        self.unchanged_error("commit", "a", "x")
        self.assertEqual(self.store.snapshot()[0]["state"], "active")
        self.begin(upload="empty", data=b"")
        self.assertEqual(self.store.commit("a", "empty"), b"")
        self.store.begin("a", "bad-empty", 0, digest(b"nonempty"))
        self.unchanged_error("commit", "a", "bad-empty")
        self.begin(upload="missing")
        self.store.put("a", "missing", 0, b"abcde")
        self.unchanged_error("commit", "a", "missing")
        self.store.put("a", "missing", 5, b"f")
        self.assertEqual(self.store.commit("a", "missing"), b"abcdef")

    def test_begin_retries_and_abort_lifecycle(self):
        self.begin()
        self.store.put("a", "x", 0, b"abc")
        before = self.store.snapshot()
        self.begin()
        self.assertEqual(before, self.store.snapshot())
        self.unchanged_error("begin", "a", "x", 5, digest(b"abcde"))
        self.unchanged_error("begin", "a", "x", 6, digest(b"ABCDEF"))
        self.store.abort("a", "x")
        self.store.abort("a", "x")
        self.begin()
        self.assertEqual(self.store.snapshot()[0]["state"], "aborted")
        self.assertEqual(self.store.snapshot()[0]["cells"], [None] * 6)
        self.unchanged_error("put", "a", "x", 0, b"")
        self.unchanged_error("commit", "a", "x")
        self.begin(upload="done", data=b"ok")
        self.store.put("a", "done", 0, b"ok")
        self.store.commit("a", "done")
        self.begin(upload="done", data=b"ok")
        self.unchanged_error("abort", "a", "done")

    def test_snapshot_and_restore_are_independent(self):
        self.begin(data=b"abc")
        self.store.put("a", "x", 0, b"a")
        checkpoint = self.store.snapshot()
        restored = ArtifactStore.restore(checkpoint)
        checkpoint[0]["cells"][0] = 0
        checkpoint[0]["owner"] = "changed"
        checkpoint.clear()
        self.assertEqual(restored.snapshot(), self.store.snapshot())
        restored.put("a", "x", 1, b"bc")
        self.assertEqual(restored.commit("a", "x"), b"abc")
        self.assertEqual(self.store.snapshot()[0]["cells"], [97, None, None])
        complete = restored.snapshot()
        second = ArtifactStore.restore(complete)
        complete[0]["cells"][0] = 0
        self.assertEqual(second.commit("a", "x"), b"abc")
        self.store.abort("a", "x")
        aborted = ArtifactStore.restore(self.store.snapshot())
        with self.assertRaises(ValueError):
            aborted.put("a", "x", 0, b"a")
        aborted.abort("a", "x")

    def test_restore_rejects_malformed_records_without_mutating_input(self):
        self.begin(data=b"ab")
        valid = self.store.snapshot()[0]
        malformed = [None, {}, "x", [None], [dict(valid, extra=True)],
                     [{k: v for k, v in valid.items() if k != "size"}], [valid, valid]]
        for field, values in {
            "owner": ["", None, 3], "upload": ["", None, 3],
            "size": [True, -1, 65537, 2.0],
            "digest": ["A" * 64, "f" * 63, "g" * 64, None],
            "state": ["unknown", [], None],
            "cells": [None, (), [], [None], [0, 1, 2], [True, 1], [-1, 0],
                      [256, 0], [0.0, 1], ["a", 1], [[], None]],
        }.items():
            malformed.extend([[dict(valid, **{field: value})] for value in values])
        malformed += [[dict(valid, state="committed")],
                      [dict(valid, state="committed", cells=[0, 0])],
                      [dict(valid, state="aborted", cells=[97, None])]]
        for checkpoint in malformed:
            with self.subTest(checkpoint=checkpoint):
                before = copy.deepcopy(checkpoint)
                with self.assertRaises(ValueError):
                    ArtifactStore.restore(checkpoint)
                self.assertEqual(checkpoint, before)
        self.assertEqual(ArtifactStore.restore([]).snapshot(), [])

    def test_validation_and_maximum_size(self):
        for size in (True, -1, 65537, 1.0, None):
            self.unchanged_error("begin", "a", "x", size, digest(b"x"))
        for value in (None, "", "a" * 63, "A" * 64, "g" * 64, "a" * 64 + "\n"):
            self.unchanged_error("begin", "a", "x", 1, value)
        for value in (None, "", 1, []):
            self.unchanged_error("begin", value, "x", 1, digest(b"x"))
            self.unchanged_error("begin", "a", value, 1, digest(b"x"))
        self.begin(data=b"ab")
        for offset, data in ((True, b"a"), (-1, b"a"), (0.0, b"a"), (3, b""),
                             (2, b"x"), (0, b"abc"), (0, "ab"),
                             (0, bytearray(b"ab")), (0, None)):
            self.unchanged_error("put", "a", "x", offset, data)
        data = bytes(range(256)) * 256
        self.begin(upload="max", data=data)
        self.store.put("a", "max", 0, data)
        self.assertEqual(self.store.commit("a", "max"), data)
        self.assertEqual(ArtifactStore.restore(self.store.snapshot()).commit("a", "max"), data)

    def test_deterministic_overlap_and_checkpoint_sequence(self):
        rng = random.Random(711)
        data = bytes(rng.randrange(256) for _ in range(257))
        self.begin(data=data)
        covered = set()
        for index in range(100):
            start = rng.randrange(len(data) + 1)
            end = rng.randrange(start, len(data) + 1)
            self.store.put("a", "x", start, data[start:end])
            covered.update(range(start, end))
            cells = self.store.snapshot()[0]["cells"]
            self.assertEqual(cells, [v if pos in covered else None for pos, v in enumerate(data)])
            if covered:
                conflict = rng.choice(sorted(covered))
                chunk = data[:conflict] + bytes([data[conflict] ^ 255])
                self.unchanged_error("put", "a", "x", 0, chunk)
            if index % 10 == 0:
                self.store = ArtifactStore.restore(self.store.snapshot())
        self.store.put("a", "x", 0, data)
        self.assertEqual(self.store.commit("a", "x"), data)


if __name__ == "__main__":
    unittest.main()
