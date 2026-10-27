"""Finite contract regressions for the campaign auditor; no private fixtures."""
from copy import deepcopy
import hashlib
import json
import unittest

from engine import audit
from test_public import sample_packet


def digest(packet):
    try:
        data = json.dumps(packet, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    except (ValueError, TypeError, UnicodeError):
        return None


def two_jobs():
    packet = sample_packet()
    packet["jobs"].append({"owner": "alpha", "job": "job-b", "cap": 30,
                           "cost": 1, "deps": ["job-a"], "artifact": "report-b"})
    packet["journal_events"] += [
        {"id": "reserve-b", "job": "job-b", "owner": "alpha", "kind": "reserve", "amount": 30},
        {"id": "settle-b", "job": "job-b", "owner": "alpha", "kind": "settle", "amount": 7}]
    packet["schedule_commands"] += [
        {"action": "claim", "owner": "alpha", "job": "job-b", "lease": "lease-b"},
        {"action": "finish", "owner": "alpha", "job": "job-b", "lease": "lease-b", "success": True}]
    packet["artifacts"].append({"owner": "alpha", "upload": "report-b", "size": 2,
        "digest": hashlib.sha256(b"xy").hexdigest(), "state": "committed", "cells": [120, 121]})
    packet["settlements"].append({"request": "settlement:job-b",
        "operations": [{"from": "alpha", "to": "__usage__", "amount": 7}],
        "expected": {"alpha": 1, "__usage__": 1}})
    return packet


def two_tenants(equal_amounts=False):
    packet = two_jobs()
    packet["initial_credits"].update(beta=50, idle=0)
    packet["jobs"][1].update(owner="beta", deps=[], artifact="report")
    for event in packet["journal_events"][2:]:
        event["owner"] = "beta"
    for command in packet["schedule_commands"][2:]:
        command["owner"] = "beta"
    packet["artifacts"][1].update(owner="beta", upload="report")
    batch = packet["settlements"][1]
    batch["operations"][0]["from"] = "beta"
    batch["expected"] = {"beta": 0, "__usage__": 1}
    if equal_amounts:
        packet["journal_events"][3]["amount"] = 12
        batch["operations"][0]["amount"] = 12
    return packet


class AuditContract(unittest.TestCase):
    def check_result(self, packet, decision):
        before = deepcopy(packet)
        result = audit(packet)
        self.assertEqual(set(result), {"schema", "decision", "packet_sha256", "reasons", "summary"})
        self.assertEqual(result["schema"], "campaign-audit/1")
        self.assertEqual(result["decision"], decision, result)
        self.assertEqual(result["packet_sha256"], digest(packet))
        if decision == "hold":
            self.assertEqual(result["summary"], {})
            self.assertIsInstance(result["reasons"], list)
            self.assertTrue(result["reasons"])
            self.assertTrue(all(isinstance(x, str) and x for x in result["reasons"]))
        else:
            self.assertEqual(result["reasons"], [])
            self.assertEqual(set(result["summary"]), {"jobs", "succeeded", "running_units", "artifact_bytes",
                "wallets", "settled_credits", "usage_sink"})
        self.assertEqual(packet, before)
        return result

    def test_sample_and_summary(self):
        summary = self.check_result(sample_packet(), "release")["summary"]
        self.assertEqual(summary, {"jobs": 1, "succeeded": 1, "running_units": 0, "artifact_bytes": 3,
            "wallets": {"alpha": {"available": 88, "reserved": 0, "spent": 12}},
            "settled_credits": {"alpha": 12}, "usage_sink": 12})

    def test_multitenant_same_upload_name_and_idle_owner(self):
        summary = self.check_result(two_tenants(), "release")["summary"]
        self.assertEqual(summary["settled_credits"], {"alpha": 12, "beta": 7, "idle": 0})
        self.assertEqual(summary["artifact_bytes"], 5)
        self.assertEqual(summary["usage_sink"], 19)

    def test_zero_consumption_empty_artifact(self):
        packet = sample_packet()
        packet["journal_events"][1]["amount"] = 0
        packet["settlements"] = []
        packet["artifacts"][0].update(size=0, cells=[], digest=hashlib.sha256(b"").hexdigest())
        summary = self.check_result(packet, "release")["summary"]
        self.assertEqual(summary["settled_credits"], {"alpha": 0})
        self.assertEqual(summary["usage_sink"], 0)
        self.assertEqual(summary["artifact_bytes"], 0)

    def test_cap_boundary(self):
        packet = sample_packet()
        packet["initial_credits"]["alpha"] = 40
        packet["journal_events"][1]["amount"] = 40
        packet["settlements"][0]["operations"][0]["amount"] = 40
        packet["jobs"][0]["cost"] = packet["capacity"]
        self.assertEqual(self.check_result(packet, "release")["summary"]["wallets"]["alpha"]["available"], 0)

    def test_exact_retries_after_later_events_and_batches(self):
        packet = two_jobs()
        base = audit(packet)
        packet["journal_events"] += deepcopy([packet["journal_events"][0], packet["journal_events"][3]])
        packet["settlements"].append(deepcopy(packet["settlements"][0]))
        packet["schedule_commands"].insert(1, deepcopy(packet["schedule_commands"][0]))
        result = self.check_result(packet, "release")
        self.assertEqual(result["summary"], base["summary"])
        self.assertNotEqual(result["packet_sha256"], base["packet_sha256"])

    def test_failed_attempt_can_recover_with_new_lease(self):
        packet = sample_packet()
        claim, finish = deepcopy(packet["schedule_commands"])
        failed = dict(finish, success=False)
        claim2, finish2 = dict(claim, lease="new"), dict(finish, lease="new")
        packet["schedule_commands"] = [claim, failed, claim2, deepcopy(failed), finish2, deepcopy(finish2)]
        self.check_result(packet, "release")

    def test_unsuccessful_scheduler_states_hold(self):
        for state in ("pending", "running", "failed", "canceled"):
            with self.subTest(state=state):
                packet = sample_packet()
                if state == "pending":
                    packet["schedule_commands"] = []
                elif state == "running":
                    packet["schedule_commands"].pop()
                elif state == "failed":
                    packet["schedule_commands"][1]["success"] = False
                else:
                    packet["schedule_commands"] = [{"action": "cancel", "owner": "alpha", "job": "job-a"}]
                self.check_result(packet, "hold")

    def test_scheduler_component_failures_hold(self):
        for variant in ("wrong_owner", "undeclared", "lease_reused", "flag_conflict", "bad_success", "cancel_then_finish"):
            with self.subTest(variant=variant):
                packet = two_jobs()
                commands = packet["schedule_commands"]
                if variant == "wrong_owner": commands[0]["owner"] = "beta"
                elif variant == "undeclared": commands[0]["job"] = "unknown"
                elif variant == "lease_reused": commands[2]["lease"] = "lease-a"
                elif variant == "flag_conflict": commands.append(dict(commands[1], success=False))
                elif variant == "bad_success": commands[1]["success"] = 1
                else: commands.insert(1, {"action": "cancel", "owner": "alpha", "job": "job-a"})
                self.check_result(packet, "hold")

    def test_artifact_identity_and_state(self):
        for variant in ("wrong_owner", "active_complete", "aborted", "missing", "extra", "duplicate"):
            with self.subTest(variant=variant):
                packet = sample_packet()
                record = packet["artifacts"][0]
                if variant == "wrong_owner": record["owner"] = "other"
                elif variant == "active_complete": record["state"] = "active"
                elif variant == "aborted": record.update(state="aborted", cells=[None] * 3)
                elif variant == "missing": packet["artifacts"] = []
                elif variant == "extra": packet["artifacts"].append(dict(record, upload="extra"))
                else: packet["artifacts"].append(deepcopy(record))
                self.check_result(packet, "hold")

    def test_artifact_validation(self):
        edits = [{"cells": [97, None, 99]}, {"digest": "0" * 64}, {"cells": [97, 98]},
                 {"cells": [True, 98, 99]}, {"size": -1}, {"state": "invented"}, {"digest": "F" * 64}]
        for edit in edits:
            with self.subTest(edit=edit):
                packet = sample_packet()
                packet["artifacts"][0].update(edit)
                self.check_result(packet, "hold")

    def test_swapped_per_job_amounts_with_correct_aggregate_hold(self):
        packet = two_jobs()
        first, second = packet["settlements"]
        first["operations"][0]["amount"], second["operations"][0]["amount"] = 7, 12
        self.check_result(packet, "hold")

    def test_swapped_tenants_with_correct_balances_hold(self):
        packet = two_tenants(equal_amounts=True)
        first, second = packet["settlements"]
        first["operations"][0]["from"] = "beta"
        first["expected"] = {"beta": 0, "__usage__": 0}
        second["operations"][0]["from"] = "alpha"
        second["expected"] = {"alpha": 0, "__usage__": 1}
        self.check_result(packet, "hold")

    def test_settlement_shape_routes_and_missing_batches(self):
        for variant in ("missing", "extra", "split", "self", "reverse", "wrong_request", "zero_batch", "not_list"):
            with self.subTest(variant=variant):
                packet = sample_packet()
                batch = packet["settlements"][0]
                if variant == "missing": packet["settlements"] = []
                elif variant == "extra": packet["settlements"].append(dict(batch, request="other"))
                elif variant == "split": batch["operations"] = [dict(batch["operations"][0], amount=6)] * 2
                elif variant == "self": batch["operations"][0]["to"] = "alpha"
                elif variant == "reverse": batch["operations"][0].update({"from": "__usage__", "to": "alpha"})
                elif variant == "wrong_request": batch["request"] = "settlement:JOB-A"
                elif variant == "zero_batch": packet["journal_events"][1]["amount"] = 0
                else: batch["operations"] = {"one": batch["operations"][0]}
                self.check_result(packet, "hold")

    def test_account_revision_guards_and_changed_retries(self):
        for expected in ({"alpha": 1, "__usage__": 0}, {"alpha": 0},
                         {"alpha": 0, "__usage__": 0, "extra": 0},
                         {"alpha": False, "__usage__": 0}, [], None):
            with self.subTest(expected=expected):
                packet = sample_packet()
                packet["settlements"][0]["expected"] = expected
                self.check_result(packet, "hold")
        packet = sample_packet()
        retry = deepcopy(packet["settlements"][0])
        retry["expected"] = {"alpha": 1, "__usage__": 1}
        packet["settlements"].append(retry)
        self.check_result(packet, "hold")

    def test_journal_component_failures_and_binding(self):
        for variant in ("cap", "owner", "extra", "missing", "canceled", "active", "changed_retry", "new_terminal"):
            with self.subTest(variant=variant):
                packet = sample_packet()
                events = packet["journal_events"]
                if variant == "cap": events[0]["amount"] = 39
                elif variant == "owner":
                    packet["initial_credits"]["beta"] = 100
                    for event in events: event["owner"] = "beta"
                elif variant == "extra": events.append(dict(events[0], id="extra", job="undeclared"))
                elif variant == "missing": packet["journal_events"] = []
                elif variant == "canceled": events[1].update(kind="cancel", amount=0)
                elif variant == "active": events.pop()
                elif variant == "changed_retry": events.append(dict(events[1], amount=11))
                else: events.append(dict(events[1], id="new-terminal"))
                self.check_result(packet, "hold")

    def test_job_structure_and_dependencies(self):
        for edit in ({"cap": 0}, {"cost": 6}, {"cost": 0}, {"deps": "job-a"},
                     {"deps": ["job-a", "job-a"]}, {"deps": ["unknown"]},
                     {"deps": ["job-b"]}, {"artifact": "report"}, {"job": "job-a"}, {"owner": "missing"}):
            with self.subTest(edit=edit):
                packet = two_jobs()
                packet["jobs"][1].update(edit)
                self.check_result(packet, "hold")
        packet = two_tenants()
        packet["jobs"][1]["deps"] = ["job-a"]
        self.check_result(packet, "hold")
        packet = two_jobs()
        packet["jobs"][0]["deps"] = ["job-b"]
        self.check_result(packet, "hold")

    def test_boolean_and_float_numeric_fields(self):
        paths = [("version",), ("capacity",), ("initial_credits", "alpha"),
            ("jobs", 0, "cap"), ("jobs", 0, "cost"), ("journal_events", 0, "amount"),
            ("journal_events", 1, "amount"), ("artifacts", 0, "size"), ("artifacts", 0, "cells", 0),
            ("settlements", 0, "operations", 0, "amount"), ("settlements", 0, "expected", "alpha")]
        for path in paths:
            for value in (True, 1.0):
                with self.subTest(path=path, value=value):
                    packet = sample_packet()
                    target = packet
                    for key in path[:-1]: target = target[key]
                    target[path[-1]] = value
                    self.check_result(packet, "hold")

    def test_malformed_packets_return_hold(self):
        for packet in (None, False, 0, "", [], {}, {"version": 1}):
            with self.subTest(packet=packet): self.check_result(packet, "hold")
        for field in sample_packet():
            with self.subTest(field=field):
                packet = sample_packet()
                packet[field] = None
                self.check_result(packet, "hold")
        packet = sample_packet()
        packet["extra"] = "retained in digest"
        self.check_result(packet, "hold")
        packet = sample_packet()
        packet["initial_credits"]["__usage__"] = 0
        self.check_result(packet, "hold")

    def test_missing_and_extra_nested_fields(self):
        for path in (("jobs", 0), ("journal_events", 0), ("schedule_commands", 0),
                     ("artifacts", 0), ("settlements", 0), ("settlements", 0, "operations", 0)):
            for extra in (False, True):
                with self.subTest(path=path, extra=extra):
                    packet = sample_packet()
                    target = packet
                    for key in path: target = target[key]
                    if extra: target["extra"] = 0
                    else: target.pop(next(iter(target)))
                    self.check_result(packet, "hold")

    def test_canonical_hash_key_order_and_unicode(self):
        def reverse_keys(value):
            if isinstance(value, dict): return {k: reverse_keys(v) for k, v in reversed(list(value.items()))}
            if isinstance(value, list): return [reverse_keys(v) for v in value]
            return value
        packet = sample_packet()
        packet["jobs"][0]["artifact"] = "résumé-雪"
        packet["artifacts"][0]["upload"] = "résumé-雪"
        first = self.check_result(packet, "release")
        self.assertEqual(first, self.check_result(reverse_keys(packet), "release"))

    def test_uncanonicalizable_input_has_null_digest(self):
        for value in (float("nan"), float("inf"), float("-inf"), "\ud800"):
            packet = sample_packet()
            packet["extra"] = value
            result = audit(packet)
            self.assertEqual(result["decision"], "hold")
            self.assertIsNone(result["packet_sha256"])
            self.assertTrue(result["reasons"])
            self.assertEqual(result["summary"], {})

    def test_input_and_output_isolation_and_failed_replay_recovery(self):
        packet = two_jobs()
        before = deepcopy(packet)
        result = self.check_result(packet, "release")
        saved = deepcopy(result)
        packet["artifacts"][0]["cells"][0] = 0
        self.assertEqual(result, saved)
        result["summary"]["wallets"]["alpha"]["available"] = -999
        result["summary"]["settled_credits"].clear()
        self.assertEqual(audit(before), saved)
        bad = deepcopy(before)
        bad["settlements"][1]["expected"]["alpha"] = 0
        self.check_result(bad, "hold")
        self.assertEqual(audit(before), saved)


if __name__ == "__main__":
    unittest.main()
