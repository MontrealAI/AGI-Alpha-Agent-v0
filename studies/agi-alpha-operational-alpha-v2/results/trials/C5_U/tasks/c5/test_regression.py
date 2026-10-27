"""Public-contract regression tests; standard library, no private fixtures."""
from copy import deepcopy
import hashlib
import json
import random
import unittest

from engine import audit
from test_public import sample_packet


def digest(packet):
    try:
        encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None


def build(specs, initial=None, capacity=5):
    """Build independently from (owner, id, cap, cost, deps, upload, actual, data)."""
    initial = dict(initial if initial is not None else {s[0]: 1000 for s in specs})
    packet = {"version": 1, "initial_credits": initial, "capacity": capacity,
              "jobs": [], "journal_events": [], "schedule_commands": [],
              "artifacts": [], "settlements": []}
    spent = {owner: 0 for owner in initial}
    revisions = {owner: 0 for owner in initial}
    revisions["__usage__"] = 0
    for owner, identity, cap, cost, deps, upload, actual, data in specs:
        packet["jobs"].append(dict(owner=owner, job=identity, cap=cap, cost=cost,
                                   deps=list(deps), artifact=upload))
        packet["journal_events"].extend([
            dict(id="reserve:" + identity, job=identity, owner=owner, kind="reserve", amount=cap),
            dict(id="settle:" + identity, job=identity, owner=owner, kind="settle", amount=actual)])
        packet["schedule_commands"].extend([
            dict(action="claim", owner=owner, job=identity, lease="lease:" + identity),
            dict(action="finish", owner=owner, job=identity, lease="lease:" + identity, success=True)])
        packet["artifacts"].append(dict(owner=owner, upload=upload, size=len(data),
                                        digest=hashlib.sha256(data).hexdigest(),
                                        state="committed", cells=list(data)))
        if actual:
            packet["settlements"].append(dict(request="settlement:" + identity,
                operations=[{"from": owner, "to": "__usage__", "amount": actual}],
                expected={owner: revisions[owner], "__usage__": revisions["__usage__"]}))
            revisions[owner] += 1
            revisions["__usage__"] += 1
        spent[owner] += actual
    expected = dict(jobs=len(specs), succeeded=len(specs), running_units=0,
                    artifact_bytes=sum(len(s[-1]) for s in specs),
                    wallets={owner: dict(available=credit - spent[owner], reserved=0, spent=spent[owner])
                             for owner, credit in initial.items()},
                    settled_credits=spent, usage_sink=sum(spent.values()))
    return packet, expected


def campaign():
    return build([
        ("alpha", "job-a", 40, 2, [], "report", 12, b"abc"),
        ("alpha", "job-b", 30, 3, ["job-a"], "summary", 7, b"summary"),
        ("beta", "job-c", 10, 1, [], "report", 0, b"\x00\xff"),
        ("beta", "job-d", 20, 1, ["job-c"], "empty", 5, b"")],
        initial={"alpha": 100, "beta": 35, "idle": 0})


def set_path(packet, path, value):
    parent = packet
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value


class AuditRegression(unittest.TestCase):
    def assertEnvelope(self, packet, result):
        self.assertEqual(set(result), {"schema", "decision", "packet_sha256", "reasons", "summary"})
        self.assertEqual(result["schema"], "campaign-audit/1")
        self.assertEqual(result["packet_sha256"], digest(packet))
        self.assertIn(result["decision"], ("release", "hold"))
        if result["decision"] == "hold":
            self.assertEqual(result["summary"], {})
            self.assertIsInstance(result["reasons"], list)
            self.assertTrue(result["reasons"])
            self.assertTrue(all(isinstance(x, str) and x for x in result["reasons"]))
        else:
            self.assertEqual(result["reasons"], [])
        return result

    def release(self, packet, expected=None):
        result = self.assertEnvelope(packet, audit(packet))
        self.assertEqual(result["decision"], "release", result["reasons"])
        if expected is not None:
            self.assertEqual(result["summary"], expected)
        return result

    def hold(self, packet):
        result = self.assertEnvelope(packet, audit(packet))
        self.assertEqual(result["decision"], "hold")
        return result

    def test_multi_tenant_dag_zero_cost_empty_artifact_and_idle_wallet(self):
        packet, expected = campaign()
        self.release(packet, expected)

    def test_failed_attempt_concurrency_and_late_exact_retries(self):
        packet, expected = campaign()
        a_claim, a_finish = packet["schedule_commands"][:2]
        old_claim = dict(a_claim, lease="old-a")
        old_finish = dict(a_finish, lease="old-a", success=False)
        b_claim, b_finish, c_claim, c_finish, d_claim, d_finish = packet["schedule_commands"][2:]
        packet["schedule_commands"] = [old_claim, old_finish, a_claim, c_claim,
            deepcopy(old_finish), c_finish, d_claim, deepcopy(a_claim), a_finish,
            deepcopy(a_finish), b_claim, d_finish, b_finish, deepcopy(old_finish)]
        packet["journal_events"].extend(deepcopy(packet["journal_events"][:2]))
        packet["settlements"].extend(deepcopy(packet["settlements"][:2]))
        self.release(packet, expected)

    def test_full_packet_hash_and_retries(self):
        packet = sample_packet()
        first = self.release(packet)
        packet["journal_events"].append(deepcopy(packet["journal_events"][0]))
        packet["settlements"].append(deepcopy(packet["settlements"][0]))
        second = self.release(packet)
        self.assertEqual(first["summary"], second["summary"])
        self.assertNotEqual(first["packet_sha256"], second["packet_sha256"])
        packet["journal_events"] = [packet["journal_events"][0], packet["journal_events"][2],
                                     packet["journal_events"][1]]
        third = self.release(packet)
        self.assertEqual(second["summary"], third["summary"])
        self.assertNotEqual(second["packet_sha256"], third["packet_sha256"])

    def test_mapping_order_unicode_and_literal_request_ids(self):
        packet, expected = build([("租户 Ω", "settlement:job:/\n", 4, 1, [], "结果", 1, b"x")])
        def reverse(value):
            if isinstance(value, dict):
                return {k: reverse(v) for k, v in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse(v) for v in value]
            return value
        self.assertEqual(self.release(packet, expected), self.release(reverse(packet), expected))

    def test_input_and_output_isolation(self):
        packet, expected = campaign()
        saved = deepcopy(packet)
        first = self.release(packet, expected)
        self.assertEqual(packet, saved)
        first["summary"]["wallets"]["alpha"]["spent"] = 99999
        first["summary"]["settled_credits"]["alpha"] = 99999
        first["reasons"].append("caller edit")
        second = self.release(packet, expected)
        packet["initial_credits"]["alpha"] = 0
        packet["artifacts"][0]["cells"][0] = 0
        self.assertEqual(second["summary"], expected)
        self.release(saved, expected)
        self.hold(packet)
        self.release(saved, expected)

    def test_unfinished_scheduler_states(self):
        for commands in ([],
            [{"action": "cancel", "owner": "alpha", "job": "job-a"}],
            sample_packet()["schedule_commands"][:1],
            [sample_packet()["schedule_commands"][0],
             dict(sample_packet()["schedule_commands"][1], success=False)]):
            with self.subTest(commands=commands):
                packet = sample_packet()
                packet["schedule_commands"] = commands
                self.hold(packet)

    def test_invalid_scheduler_commands_cannot_be_waived(self):
        bad_commands = [
            {"action": "add", "owner": "alpha", "job": "extra"},
            {"action": "claim", "owner": "alpha", "job": "extra", "lease": "new"},
            dict(sample_packet()["schedule_commands"][1], owner="beta"),
            dict(sample_packet()["schedule_commands"][1], lease="wrong"),
            dict(sample_packet()["schedule_commands"][1], success=False),
            dict(sample_packet()["schedule_commands"][1], success=1),
            dict(sample_packet()["schedule_commands"][1], extra=True),
            {"action": []}, None]
        for command in bad_commands:
            with self.subTest(command=command):
                packet = sample_packet()
                packet["schedule_commands"].append(command)
                self.hold(packet)

    def test_duplicate_declarations_and_artifact_reuse(self):
        packet = sample_packet()
        packet["jobs"].append(deepcopy(packet["jobs"][0]))
        self.hold(packet)
        packet, _ = campaign()
        packet["jobs"][1]["artifact"] = "report"
        self.hold(packet)

    def test_dependency_scope_and_order(self):
        changes = [(1, "job-a"), (1, ["job-a", "job-a"]), (1, ["job-b"]),
                   (1, ["job-d"]), (3, ["job-a"]), (1, [None])]
        for index, deps in changes:
            with self.subTest(index=index, deps=deps):
                packet, _ = campaign()
                packet["jobs"][index]["deps"] = deps
                self.hold(packet)

    def test_journal_exact_job_set_and_settled_state(self):
        packet = sample_packet()
        packet["journal_events"].pop()
        self.hold(packet)
        packet = sample_packet()
        packet["journal_events"][1].update(kind="cancel", amount=0)
        self.hold(packet)
        packet = sample_packet()
        packet["journal_events"] += [
            dict(id="extra-r", owner="alpha", job="extra", kind="reserve", amount=1),
            dict(id="extra-s", owner="alpha", job="extra", kind="settle", amount=0)]
        self.hold(packet)
        packet = sample_packet()
        packet["journal_events"] = []
        self.hold(packet)

    def test_journal_owner_cap_and_conflicting_retries(self):
        packet = sample_packet()
        packet["journal_events"][0]["amount"] = 39
        self.hold(packet)
        packet = sample_packet()
        packet["initial_credits"]["beta"] = 100
        for event in packet["journal_events"]:
            event["owner"] = "beta"
        self.hold(packet)
        for change in ({"id": "new-terminal"}, {"amount": 13}, {"kind": "cancel", "amount": 0}):
            with self.subTest(change=change):
                packet = sample_packet()
                packet["journal_events"].append(dict(packet["journal_events"][1], **change))
                self.hold(packet)


    def test_numeric_exact_event_retries_still_require_integer_amounts(self):
        for index, value in ((0, 40.0), (1, 12.0)):
            with self.subTest(index=index, value=value):
                packet = sample_packet()
                retry = deepcopy(packet["journal_events"][index])
                retry["amount"] = value
                packet["journal_events"].append(retry)
                self.hold(packet)

    def test_zero_consumption_has_no_batch(self):
        packet = sample_packet()
        packet["journal_events"][1]["amount"] = 0
        packet["settlements"] = []
        result = self.release(packet)
        self.assertEqual(result["summary"]["usage_sink"], 0)
        self.assertEqual(result["summary"]["wallets"]["alpha"],
                         {"available": 100, "reserved": 0, "spent": 0})
        packet["settlements"] = sample_packet()["settlements"]
        self.hold(packet)
        packet["settlements"][0]["operations"][0]["amount"] = 0
        self.hold(packet)

    def test_artifact_tenant_binding_and_exact_record_set(self):
        packet = sample_packet()
        packet["artifacts"][0]["owner"] = "other"
        self.hold(packet)
        packet = sample_packet()
        packet["artifacts"].append(dict(packet["artifacts"][0], owner="other"))
        self.hold(packet)
        packet = sample_packet()
        packet["artifacts"].append(deepcopy(packet["artifacts"][0]))
        self.hold(packet)
        packet = sample_packet()
        packet["artifacts"] = []
        self.hold(packet)

    def test_artifacts_must_already_be_committed_and_verified(self):
        changes = [dict(state="active"), dict(state="active", cells=[97, None, 99]),
                   dict(state="aborted", cells=[None, None, None]), dict(cells=[97, None, 99]),
                   dict(digest="0" * 64), dict(cells=[97, 98]), dict(cells=[97, 98, 300]),
                   dict(cells=[97, True, 99]), dict(size=True), dict(extra=0)]
        for change in changes:
            with self.subTest(change=change):
                packet = sample_packet()
                packet["artifacts"][0].update(change)
                self.hold(packet)

    def test_artifact_size_boundaries(self):
        for data in (b"", bytes(65536)):
            with self.subTest(size=len(data)):
                packet, expected = build([("alpha", "a", 1, 1, [], "file", 0, data)])
                self.release(packet, expected)
        packet, _ = build([("alpha", "a", 1, 1, [], "file", 0, bytes(65537))])
        self.hold(packet)

    def test_per_job_amounts_cannot_be_swapped_even_when_totals_match(self):
        packet, _ = campaign()
        first, second = packet["settlements"][:2]
        first["operations"][0]["amount"], second["operations"][0]["amount"] = 7, 12
        self.hold(packet)

    def test_balanced_indirect_route_is_forbidden(self):
        packet, _ = build([("alpha", "a", 20, 1, [], "report", 12, b"a"),
                           ("beta", "b", 20, 1, [], "report", 12, b"b")])
        packet["settlements"] = [
            {"request": "settlement:a", "operations": [{"from": "alpha", "to": "beta", "amount": 12}],
             "expected": {"alpha": 0, "beta": 0}},
            {"request": "settlement:b", "operations": [{"from": "beta", "to": "__usage__", "amount": 24}],
             "expected": {"beta": 1, "__usage__": 0}}]
        self.hold(packet)

    def test_settlement_presence_shapes_and_literal_identity(self):
        changes = [("request", "other"), ("request", "job-a"), ("operations", []),
                   ("operations", {}), ("operations", [None]), ("expected", {}),
                   ("expected", {"alpha": 0, "__usage__": 0, "extra": 0}),
                   ("expected", {"alpha": 1, "__usage__": 0})]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                packet = sample_packet()
                packet["settlements"][0][key] = value
                self.hold(packet)
        packet = sample_packet()
        packet["settlements"] = []
        self.hold(packet)
        packet = sample_packet()
        packet["settlements"][0]["operations"] *= 2
        self.hold(packet)
        packet = sample_packet()
        packet["settlements"].append(dict(deepcopy(packet["settlements"][0]), request="settlement:extra"))
        self.hold(packet)

    def test_retry_revision_conflict_and_integer_types(self):
        packet, _ = campaign()
        bad = deepcopy(packet["settlements"][0])
        bad["expected"]["alpha"] = 1
        packet["settlements"].append(bad)
        self.hold(packet)
        for value in (False, True, 0.0, -1, None):
            with self.subTest(value=value):
                packet = sample_packet()
                packet["settlements"][0]["expected"]["alpha"] = value
                self.hold(packet)

    def test_all_numeric_fields_reject_booleans_and_fractional_values(self):
        paths = [("version",), ("initial_credits", "alpha"), ("capacity",),
                 ("jobs", 0, "cap"), ("jobs", 0, "cost"),
                 ("journal_events", 0, "amount"), ("journal_events", 1, "amount"),
                 ("artifacts", 0, "size"), ("artifacts", 0, "cells", 0),
                 ("settlements", 0, "operations", 0, "amount"),
                 ("settlements", 0, "expected", "alpha"),
                 ("settlements", 0, "expected", "__usage__")]
        for path in paths:
            for value in (True, 0.5):
                with self.subTest(path=path, value=value):
                    packet = sample_packet()
                    set_path(packet, path, value)
                    self.hold(packet)

    def test_packet_structure_and_required_identity(self):
        for packet in (None, True, 1, "packet", [], {}, {"extra": 1}):
            self.hold(packet)
        for key in sample_packet():
            packet = sample_packet()
            del packet[key]
            self.hold(packet)
        packet = sample_packet()
        packet["extra"] = []
        self.hold(packet)
        for path, value in [(("version",), 2), (("initial_credits",), {}),
            (("initial_credits",), {"__usage__": 100}), (("initial_credits",), {"": 100}),
            (("initial_credits",), {"alpha": -1}), (("capacity",), 0), (("jobs",), []),
            (("jobs", 0, "cap"), 0), (("jobs", 0, "cost"), 6),
            (("jobs", 0, "job"), ""), (("jobs", 0, "artifact"), ""),
            (("jobs", 0, "owner"), "missing")]:
            with self.subTest(path=path, value=value):
                packet = sample_packet()
                set_path(packet, path, value)
                self.hold(packet)

    def test_malformed_nested_json_never_escapes_the_result_envelope(self):
        paths = [("jobs",), ("jobs", 0), ("jobs", 0, "deps"), ("jobs", 0, "owner"),
                 ("schedule_commands",), ("schedule_commands", 0),
                 ("schedule_commands", 0, "action"), ("schedule_commands", 0, "job"),
                 ("journal_events",), ("journal_events", 0), ("journal_events", 0, "kind"),
                 ("journal_events", 0, "id"), ("artifacts",), ("artifacts", 0),
                 ("artifacts", 0, "cells"), ("settlements",), ("settlements", 0),
                 ("settlements", 0, "request"), ("settlements", 0, "operations"),
                 ("settlements", 0, "operations", 0), ("settlements", 0, "expected")]
        for path in paths:
            for value in (None, [], {}, "", True, -1, 0.5):
                with self.subTest(path=path, value=value):
                    packet = sample_packet()
                    set_path(packet, path, value)
                    self.assertEnvelope(packet, audit(packet))

    def test_unencodable_packet_hash_is_null(self):
        for value in (float("nan"), float("inf"), float("-inf"), "\ud800"):
            packet = sample_packet()
            packet["extra"] = value
            self.assertIsNone(self.hold(packet)["packet_sha256"])
        nested = []
        for _ in range(1100):
            nested = [nested]
        # Runtime recursion limits vary; a digest is required if encoding succeeds.
        self.hold(nested)

    def test_generated_finite_campaigns_against_independent_totals(self):
        rng = random.Random(20261027)
        for case in range(80):
            capacity = rng.randint(1, 6)
            owners = ["tenant-" + str(i) for i in range(rng.randint(1, 3))]
            prior = {owner: [] for owner in owners}
            specs = []
            for i in range(rng.randint(1, 12)):
                owner = rng.choice(owners)
                identity = "case-%d-job-%d" % (case, i)
                cap = rng.randint(1, 50)
                deps = [j for j in prior[owner] if rng.random() < 0.25]
                data = bytes(rng.randrange(256) for _ in range(rng.randint(0, 16)))
                specs.append((owner, identity, cap, rng.randint(1, capacity), deps,
                              "upload-%d" % len(prior[owner]), rng.randint(0, cap), data))
                prior[owner].append(identity)
            packet, expected = build(specs, {**{o: 1000 for o in owners}, "idle": 0}, capacity)
            rng.shuffle(packet["settlements"])
            revisions = {o: 0 for o in owners}
            revisions["__usage__"] = 0
            for batch in packet["settlements"]:
                owner = batch["operations"][0]["from"]
                batch["expected"] = {owner: revisions[owner], "__usage__": revisions["__usage__"]}
                revisions[owner] += 1
                revisions["__usage__"] += 1
            if case % 2 == 0:
                packet["journal_events"] += deepcopy(packet["journal_events"])
                packet["settlements"] += deepcopy(packet["settlements"])
            with self.subTest(case=case):
                self.release(packet, expected)


if __name__ == "__main__":
    unittest.main()

