"""Public-contract regressions with independently constructed evidence."""
from copy import deepcopy
import hashlib
import json
import random
import unittest
from contract_probes import assert_idempotent, assert_independent_result
from engine import audit
from test_public import sample_packet


def digest(packet):
    return hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def changed(packet, path, value):
    packet = deepcopy(packet)
    target = packet
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return packet


def campaign(rows, initial=None):
    """Rows: owner, job, cap, actual, cost, dependencies, upload, bytes."""
    if initial is None:
        initial = {o: sum(r[2] for r in rows if r[0] == o) + 10 for o in sorted({r[0] for r in rows})}
    packet = dict(version=1, initial_credits=dict(initial), capacity=5, jobs=[],
                  journal_events=[], schedule_commands=[], artifacts=[], settlements=[])
    revisions = dict.fromkeys(initial, 0)
    sink_revision = 0
    for owner, job, cap, actual, cost, deps, upload, data in rows:
        packet["jobs"].append(dict(owner=owner, job=job, cap=cap, cost=cost, deps=list(deps), artifact=upload))
        packet["journal_events"].extend([
            dict(id="reserve:" + job, owner=owner, job=job, kind="reserve", amount=cap),
            dict(id="settle:" + job, owner=owner, job=job, kind="settle", amount=actual)])
        packet["schedule_commands"].extend([
            dict(action="claim", owner=owner, job=job, lease="lease:" + job),
            dict(action="finish", owner=owner, job=job, lease="lease:" + job, success=True)])
        packet["artifacts"].append(dict(owner=owner, upload=upload, size=len(data),
            digest=hashlib.sha256(data).hexdigest(), state="committed", cells=list(data)))
        if actual:
            packet["settlements"].append(dict(request="settlement:" + job,
                operations=[{"from": owner, "to": "__usage__", "amount": actual}],
                expected={owner: revisions[owner], "__usage__": sink_revision}))
            revisions[owner] += 1
            sink_revision += 1
    return packet


def multiple():
    return campaign([
        ("alpha", "first", 20, 3, 2, [], "shared", b"a"),
        ("alpha", "second", 15, 7, 3, ["first"], "report", b"bcd"),
        ("beta", "third", 10, 5, 2, [], "shared", b"xyz123"),
        ("alpha", "zero", 5, 0, 1, ["second"], "empty", b""),
    ], {"alpha": 100, "beta": 80, "idle": 0})


class AuditRegression(unittest.TestCase):
    def hold(self, packet):
        before = deepcopy(packet)
        result = audit(packet)
        self.assertEqual(set(result), {"schema", "decision", "packet_sha256", "reasons", "summary"})
        self.assertEqual(result["schema"], "campaign-audit/1")
        self.assertEqual(result["decision"], "hold", result)
        self.assertEqual(result["summary"], {})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(v, str) and v for v in result["reasons"]))
        self.assertEqual(result["packet_sha256"], digest(packet))
        self.assertEqual(packet, before)

    def test_entire_packet_hash(self):
        p = sample_packet()
        r = audit(p)
        self.assertEqual(r["decision"], "release")
        self.assertEqual(r["packet_sha256"], digest(p))
        self.assertEqual(r["summary"], dict(jobs=1, succeeded=1, running_units=0, artifact_bytes=3,
            wallets={"alpha": dict(available=88, reserved=0, spent=12)},
            settled_credits={"alpha": 12}, usage_sink=12))

    def test_requires_every_job_succeeded(self):
        for commands in ([], [{"action": "cancel", "owner": "alpha", "job": "job-a"}],
                         sample_packet()["schedule_commands"][:1]):
            self.hold(changed(sample_packet(), ["schedule_commands"], commands))
        self.hold(changed(sample_packet(), ["schedule_commands", 1, "success"], False))

    def test_artifact_tenant_binding(self):
        self.hold(changed(sample_packet(), ["artifacts", 0, "owner"], "other-tenant"))

    def test_active_complete_is_not_committed(self):
        self.hold(changed(sample_packet(), ["artifacts", 0, "state"], "active"))

    def test_per_job_amounts_not_just_total(self):
        p = multiple()
        p["settlements"][0]["operations"][0]["amount"] = 7
        p["settlements"][1]["operations"][0]["amount"] = 3
        self.hold(p)

    def test_per_job_owners_not_just_owner_totals(self):
        p = campaign([("alpha", "a", 10, 5, 1, [], "a", b"a"),
                      ("beta", "b", 10, 5, 1, [], "b", b"b")])
        for batch, owner, revision in zip(p["settlements"], ("beta", "alpha"), (0, 1)):
            batch["operations"][0]["from"] = owner
            batch["expected"] = {owner: 0, "__usage__": revision}
        self.hold(p)

    def test_multi_tenant_zero_job_empty_artifact_unused_owner(self):
        r = audit(multiple())
        self.assertEqual(r["decision"], "release", r)
        self.assertEqual(r["summary"], dict(jobs=4, succeeded=4, running_units=0, artifact_bytes=10,
            wallets={"alpha": dict(available=90, reserved=0, spent=10),
                     "beta": dict(available=75, reserved=0, spent=5),
                     "idle": dict(available=0, reserved=0, spent=0)},
            settled_credits={"alpha": 10, "beta": 5, "idle": 0}, usage_sink=15))

    def test_all_zero_consumption_and_unexpected_settlement(self):
        p = campaign([("a", "free", 2, 0, 1, [], "empty", b"")], {"a": 2})
        r = audit(p)
        self.assertEqual(r["decision"], "release", r)
        self.assertEqual(r["summary"]["usage_sink"], 0)
        self.assertEqual(r["summary"]["settled_credits"], {"a": 0})
        p["settlements"] = [dict(request="settlement:free",
            operations=[{"from": "a", "to": "__usage__", "amount": 1}], expected={"a": 0, "__usage__": 0})]
        self.hold(p)

    def test_exact_retries_change_hash_not_financial_result(self):
        p = multiple()
        baseline = audit(p)
        p["journal_events"] += deepcopy(p["journal_events"])
        p["settlements"] += deepcopy(p["settlements"])
        p["schedule_commands"].insert(1, deepcopy(p["schedule_commands"][0]))
        p["schedule_commands"].append(deepcopy(p["schedule_commands"][-1]))
        r = audit(p)
        self.assertEqual(r["decision"], "release", r)
        self.assertEqual(r["summary"], baseline["summary"])
        self.assertNotEqual(r["packet_sha256"], baseline["packet_sha256"])
        self.assertEqual(r["packet_sha256"], digest(p))

    def test_scheduler_failure_recovery_and_old_finish_retry(self):
        p = sample_packet()
        claim, finish = deepcopy(p["schedule_commands"])
        failure = dict(finish, success=False)
        new_claim, new_finish = dict(claim, lease="new"), dict(finish, lease="new")
        p["schedule_commands"] = [claim, failure, new_claim, deepcopy(failure),
                                  deepcopy(new_claim), new_finish, deepcopy(new_finish)]
        self.assertEqual(audit(p)["decision"], "release")
        p["schedule_commands"][3]["success"] = True
        self.hold(p)

    def test_hash_mapping_order_and_list_order(self):
        def reverse_maps(value):
            if isinstance(value, dict):
                return {k: reverse_maps(v) for k, v in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse_maps(v) for v in value]
            return value
        p = multiple()
        baseline = audit(p)
        self.assertEqual(audit(reverse_maps(p)), baseline)
        p["artifacts"].reverse()
        r = audit(p)
        self.assertEqual(r["summary"], baseline["summary"])
        self.assertNotEqual(r["packet_sha256"], baseline["packet_sha256"])

    def test_literal_unicode_ids(self):
        p = campaign([("租户🌱", "settlement:résumé:Δ", 4, 4, 1, [], "报告", b"ok")])
        r = audit(p)
        self.assertEqual(r["decision"], "release", r)
        self.assertEqual(r["packet_sha256"], digest(p))
        self.assertEqual(r["summary"]["settled_credits"], {"租户🌱": 4})

    def test_helpers_for_determinism_and_output_isolation(self):
        p = multiple()
        original = deepcopy(p)
        assert_idempotent(self, lambda: p, lambda: audit(p))
        self.assertEqual(p, original)
        def mutate(result):
            result["summary"]["wallets"]["alpha"]["spent"] = 9999
            result["summary"]["settled_credits"]["alpha"] = 9999
            result["reasons"].append("caller mutation")
        assert_independent_result(self, lambda: (p, audit(p)), lambda: audit(p), mutate)
        saved = audit(p)
        p["initial_credits"]["alpha"] = 0
        p["artifacts"][0]["cells"][0] = 0
        self.assertEqual(audit(p)["decision"], "hold")
        self.assertEqual(audit(original), saved)

    def test_journal_binding_and_failed_replays(self):
        p = sample_packet()
        variants = [changed(p, ["journal_events"], []),
            changed(p, ["journal_events"], p["journal_events"][:1]),
            changed(p, ["journal_events", 0, "amount"], 39),
            changed(p, ["journal_events", 1, "owner"], "intruder"),
            changed(p, ["journal_events", 1, "amount"], 41),
            changed(p, ["journal_events", 1], dict(p["journal_events"][1], kind="cancel", amount=0))]
        for event in (dict(p["journal_events"][1], id="new-terminal"),
                      dict(p["journal_events"][1], amount=11),
                      dict(id="extra", job="extra", owner="alpha", kind="reserve", amount=1)):
            variants.append(changed(p, ["journal_events"], p["journal_events"] + [event]))
        for i, v in enumerate(variants):
            with self.subTest(i=i):
                self.hold(v)

    def test_artifact_corruption_missing_and_duplicate_records(self):
        p = sample_packet()
        for updates in (dict(state="aborted", cells=[None] * 3), dict(cells=[97, None, 99]),
                        dict(digest="0" * 64), dict(cells=[97, 98]), dict(cells=[97, 98, 256]),
                        dict(cells=[97, True, 99]), dict(size=True), dict(digest="A" * 64),
                        dict(upload="wrong"), dict(state="unknown")):
            self.hold(changed(p, ["artifacts", 0], dict(p["artifacts"][0], **updates)))
        for records in ([], p["artifacts"] * 2, p["artifacts"] + [dict(p["artifacts"][0], upload="extra")]):
            self.hold(changed(p, ["artifacts"], records))

    def test_duplicate_or_unauthorized_declarations(self):
        p = sample_packet()
        self.hold(changed(p, ["jobs"], p["jobs"] * 2))
        self.hold(changed(multiple(), ["jobs", 1, "artifact"], "shared"))
        self.hold(changed(p, ["jobs", 0, "owner"], "unknown"))
        self.hold(changed(p, ["initial_credits"], {"alpha": 100, "__usage__": 0}))

    def test_scheduler_rejections(self):
        for path, value in ((["jobs", 0, "deps"], ["second"]), (["jobs", 2, "deps"], ["first"]),
                            (["jobs", 1, "deps"], ["first", "first"])):
            self.hold(changed(multiple(), path, value))
        p = multiple()
        p["schedule_commands"][:4] = p["schedule_commands"][2:4] + p["schedule_commands"][:2]
        self.hold(p)
        for path, value in ((["schedule_commands", 0, "job"], "undeclared"),
                            (["schedule_commands", 1, "lease"], "wrong"),
                            (["schedule_commands", 0, "owner"], "intruder"),
                            (["schedule_commands", 1, "success"], 1)):
            self.hold(changed(sample_packet(), path, value))
        p = campaign([("a", "a", 5, 1, 3, [], "a", b"a"), ("a", "b", 5, 1, 3, [], "b", b"b")])
        p["schedule_commands"][1:3] = list(reversed(p["schedule_commands"][1:3]))
        self.hold(p)

    def test_settlement_routes_shape_revisions_and_missing_batches(self):
        p = sample_packet()
        for updates in (dict(request="wrong"), dict(operations=[]), dict(operations={}), dict(expected={}),
                        dict(expected={"alpha": 1, "__usage__": 0}),
                        dict(expected={"alpha": 0, "__usage__": 0, "extra": 0})):
            self.hold(changed(p, ["settlements", 0], dict(p["settlements"][0], **updates)))
        for operation in ({"from": "alpha", "to": "alpha", "amount": 12},
                          {"from": "__usage__", "to": "alpha", "amount": 12},
                          {"from": "alpha", "to": "__usage__", "amount": 13},
                          {"from": "alpha", "to": "__usage__", "amount": 0},
                          {"from": "alpha", "to": "__usage__", "amount": 12, "extra": 0}):
            self.hold(changed(p, ["settlements", 0, "operations"], [operation]))
        self.hold(changed(p, ["settlements"], []))
        self.hold(changed(p, ["settlements", 0, "operations"], p["settlements"][0]["operations"] * 2))
        q = multiple(); q["settlements"].reverse(); self.hold(q)
        q = deepcopy(p); q["settlements"].append(deepcopy(q["settlements"][0]))
        q["settlements"][-1]["expected"]["alpha"] = 1; self.hold(q)

    def test_retry_numeric_equality_cannot_bypass_types(self):
        for field, value in (("amount", 12.0), ("alpha", 0.0), ("alpha", False), ("__usage__", False)):
            p = sample_packet()
            retry = deepcopy(p["settlements"][0])
            target = retry["operations"][0] if field == "amount" else retry["expected"]
            target[field] = value
            p["settlements"].append(retry)
            self.hold(p)
        p = campaign([("a", "one", 1, 1, 1, [], "a", b"a")])
        retry = deepcopy(p["settlements"][0]); retry["operations"][0]["amount"] = True
        p["settlements"].append(retry); self.hold(p)

    def test_integer_types_and_bounds(self):
        paths = [["version"], ["capacity"], ["initial_credits", "alpha"], ["jobs", 0, "cap"],
                 ["jobs", 0, "cost"], ["journal_events", 0, "amount"], ["artifacts", 0, "size"],
                 ["artifacts", 0, "cells", 0], ["settlements", 0, "operations", 0, "amount"],
                 ["settlements", 0, "expected", "alpha"]]
        for path in paths:
            for value in (True, False, 1.0, -1):
                with self.subTest(path=path, value=value):
                    self.hold(changed(sample_packet(), path, value))
        for path in (["capacity"], ["jobs", 0, "cap"], ["jobs", 0, "cost"]):
            self.hold(changed(sample_packet(), path, 0))
        self.hold(changed(sample_packet(), ["jobs", 0, "cost"], 6))
        self.hold(changed(sample_packet(), ["initial_credits", "alpha"], 39))

    def test_malformed_json_shapes(self):
        for value in (None, False, 1, "packet", [], {}):
            self.hold(value)
        for field in sample_packet():
            p = sample_packet(); del p[field]; self.hold(p)
            for value in (None, "bad", True):
                self.hold(changed(sample_packet(), [field], value))
        p = sample_packet(); p["extra"] = "included in hash"; self.hold(p)
        for field in ("jobs", "journal_events", "schedule_commands", "artifacts", "settlements"):
            for value in (None, [], "bad", {}, {"extra": 1}):
                self.hold(changed(sample_packet(), [field, 0], value))
        for value in (None, {}, [None], ["missing"], "job-a"):
            self.hold(changed(sample_packet(), ["jobs", 0, "deps"], value))

    def test_unencodable_hash_is_null(self):
        for value in (float("nan"), float("inf"), {1, 2}):
            p = sample_packet(); p["extra"] = value
            r = audit(p)
            self.assertEqual(r["decision"], "hold")
            self.assertIsNone(r["packet_sha256"])
            self.assertEqual(r["summary"], {})
            self.assertTrue(r["reasons"])

    def test_seeded_campaigns_and_corruptions(self):
        for seed in range(120):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                owners = ["tenant-" + str(i) for i in range(rng.randint(1, 3))]
                previous = {o: [] for o in owners}
                rows = []
                for i in range(rng.randint(1, 8)):
                    owner = rng.choice(owners); job = "job:" + str(i); cap = rng.randint(1, 20)
                    deps = rng.sample(previous[owner], rng.randint(0, len(previous[owner])))
                    data = bytes(rng.randrange(256) for _ in range(rng.randint(0, 16)))
                    rows.append((owner, job, cap, rng.randint(0, cap), rng.randint(1, 5), deps,
                                 "delivery:" + str(len(previous[owner])), data))
                    previous[owner].append(job)
                initial = {o: sum(r[2] for r in rows if r[0] == o) + rng.randint(0, 9) for o in owners}
                p = campaign(rows, initial)
                if p["settlements"] and seed % 2 == 0:
                    p["settlements"].append(deepcopy(p["settlements"][0]))
                if seed % 3 == 0:
                    p["journal_events"].append(deepcopy(p["journal_events"][0]))
                result = audit(p)
                self.assertEqual(result["decision"], "release", result)
                spent = {o: sum(r[3] for r in rows if r[0] == o) for o in owners}
                self.assertEqual(result["summary"], dict(jobs=len(rows), succeeded=len(rows), running_units=0,
                    artifact_bytes=sum(len(r[7]) for r in rows), settled_credits=spent, usage_sink=sum(spent.values()),
                    wallets={o: dict(available=initial[o] - spent[o], reserved=0, spent=spent[o]) for o in owners}))
                self.assertEqual(result["packet_sha256"], digest(p))
                if p["settlements"]:
                    p["settlements"][0]["operations"][0]["amount"] += 1
                    self.hold(p)


if __name__ == "__main__":
    unittest.main()
