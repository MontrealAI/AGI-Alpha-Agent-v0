import copy
import random
import unittest
from engine import Journal


def event(eid="e1", job="j1", owner="alice", kind="reserve", amount=40):
    return dict(id=eid, job=job, owner=owner, kind=kind, amount=amount)


class JournalContract(unittest.TestCase):
    def setUp(self):
        self.journal = Journal({"alice": 100, "bob": 50})

    def reject_unchanged(self, value):
        before = (self.journal.snapshot(), self.journal.export_log())
        with self.assertRaises(ValueError):
            self.journal.append(value)
        self.assertEqual(before, (self.journal.snapshot(), self.journal.export_log()))

    def test_full_identity_and_original_receipt(self):
        accepted = event()
        receipt = self.journal.append(accepted)
        for field, value in (("job", "j2"), ("owner", "bob"),
                             ("kind", "cancel"), ("amount", 41)):
            with self.subTest(field=field):
                self.reject_unchanged(dict(accepted, **{field: value}))
        self.journal.append(event("e2", kind="settle", amount=25))
        self.assertEqual(self.journal.append(accepted), receipt)
        self.assertEqual(receipt, dict(id="e1", sequence=1, job="j1", kind="reserve"))
        self.assertEqual(len(self.journal.export_log()), 2)

    def test_ownership_and_terminal_rejections(self):
        self.journal.append(event())
        for kind, amount in (("settle", 20), ("cancel", 0)):
            self.reject_unchanged(event("wrong", owner="bob", kind=kind, amount=amount))
        terminal = event("done", kind="cancel", amount=0)
        self.journal.append(terminal)
        self.assertEqual(self.journal.snapshot()["wallets"]["alice"],
                         dict(available=100, reserved=0, spent=0))
        self.reject_unchanged(dict(terminal, id="new"))
        self.reject_unchanged(event("new", kind="settle", amount=0))
        self.reject_unchanged(event("new"))
        self.assertEqual(self.journal.append(terminal)["sequence"], 2)

    def test_rejected_id_can_be_corrected_and_sequence_is_contiguous(self):
        self.reject_unchanged(event(amount=101))
        self.assertEqual(self.journal.append(event())["sequence"], 1)
        self.reject_unchanged(event("e2", kind="settle", amount=41))
        self.assertEqual(self.journal.append(event("e2", kind="settle", amount=40))["sequence"], 2)
        self.assertEqual(self.journal.snapshot()["wallets"]["alice"],
                         dict(available=60, reserved=0, spent=40))

    def test_validation_and_zero_settlement(self):
        invalid = [None, [], {}, dict(event(), extra=1)]
        for key in ("id", "job", "owner", "kind"):
            for value in ("", None, 3, True, []):
                invalid.append(dict(event(), **{key: value}))
        for value in (True, False, 1.0, -1, "1", None, 0):
            invalid.append(event(amount=value))
        invalid.extend([event(owner="missing"), event(kind="unknown"),
                        event(kind="cancel", amount=0), event(kind="settle", amount=0)])
        for value in invalid:
            with self.subTest(value=value):
                self.reject_unchanged(value)
        self.journal.append(event())
        self.reject_unchanged(event("e2", kind="cancel", amount=1))
        self.journal.append(event("e2", kind="settle", amount=0))
        self.assertEqual(self.journal.snapshot()["wallets"]["alice"],
                         dict(available=100, reserved=0, spent=0))
        for initial in ([], None, {"": 1}, {3: 1}, {"a": -1}, {"a": True}, {"a": 1.0}):
            with self.subTest(initial=initial), self.assertRaises(ValueError):
                Journal(initial)
        self.assertEqual(Journal({}).snapshot(), dict(wallets={}, jobs={}))

    def test_all_caller_owned_values_are_isolated(self):
        initial = {"alice": 100}
        journal = Journal(initial)
        initial["alice"] = 0
        original = event()
        receipt = journal.append(original)
        original["amount"] = 99
        receipt["sequence"] = 999
        snap = journal.snapshot()
        snap["wallets"]["alice"]["available"] = -1
        snap["jobs"]["j1"]["owner"] = "bob"
        log = journal.export_log()
        log[0]["id"] = "corrupted"
        log.clear()
        self.assertEqual(journal.export_log(), [event()])
        self.assertEqual(journal.append(event())["sequence"], 1)
        self.assertEqual(journal.snapshot()["wallets"]["alice"],
                         dict(available=60, reserved=40, spent=0))

    def test_replay_order_duplicates_conflicts_and_mutation(self):
        reserve, settle = event(), event("e2", kind="settle", amount=7)
        log = [reserve, reserve, settle, reserve, settle]
        journal = Journal.replay({"alice": 100}, log)
        self.assertEqual(journal.export_log(), [reserve, settle])
        self.assertEqual(journal.append(settle)["sequence"], 2)
        log[0]["amount"] = 100
        self.assertEqual(journal.export_log()[0]["amount"], 40)
        for bad in (None, {}, "x", [settle], [event(), dict(event(), amount=41)],
                    [event(), {}], [event(), settle, dict(settle, id="e3")]):
            with self.subTest(log=bad), self.assertRaises(ValueError):
                Journal.replay({"alice": 100}, bad)

    def test_many_interleaved_jobs_conserve_balances_and_replay(self):
        rng = random.Random(918)
        initial = {"alice": 10000, "bob": 10000, "carol": 0}
        journal = Journal(initial)
        spent = {owner: 0 for owner in initial}
        reserved = {owner: 0 for owner in initial}
        for index in range(80):
            owner = rng.choice(["alice", "bob"])
            cap = rng.randrange(1, 101)
            job = "job" + str(index)
            reserve = event("r" + str(index), job, owner, amount=cap)
            journal.append(reserve)
            reserved[owner] += cap
            if index % 3:
                amount = rng.randrange(cap + 1) if index % 2 else 0
                kind = "settle" if index % 2 else "cancel"
                terminal = event("t" + str(index), job, owner, kind, amount)
                journal.append(terminal)
                journal.append(terminal)
                reserved[owner] -= cap
                spent[owner] += amount
            journal.append(reserve)
            for name, balance in initial.items():
                self.assertEqual(journal.snapshot()["wallets"][name],
                                 dict(available=balance-reserved[name]-spent[name],
                                      reserved=reserved[name], spent=spent[name]))
        replay = Journal.replay(initial, journal.export_log())
        self.assertEqual(replay.snapshot(), journal.snapshot())
        self.assertEqual(replay.export_log(), journal.export_log())


if __name__ == "__main__":
    unittest.main()
