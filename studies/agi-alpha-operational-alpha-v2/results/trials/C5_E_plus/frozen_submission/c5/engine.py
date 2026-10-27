# SPDX-License-Identifier: Apache-2.0
"""Read-only, sequential reconciliation of a complete campaign evidence packet."""
from copy import deepcopy
import hashlib
import json

from components.accounts import AccountBook
from components.artifacts import ArtifactStore
from components.journal import Journal
from components.scheduler import Scheduler


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def whole(value, lower=0):
    return type(value) is int and value >= lower


def name(value):
    return isinstance(value, str) and bool(value)


def audit(packet):
    """Return release only after each replay and all cross-record checks succeed.

    Every invocation constructs fresh components. The digest covers the original
    evidence, including retries and malformed fields, whenever encoding succeeds.
    """
    digest = None
    try:
        encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        packet = deepcopy(packet)
        required = {"version", "initial_credits", "capacity", "jobs", "journal_events",
                    "schedule_commands", "artifacts", "settlements"}
        require(isinstance(packet, dict) and set(packet) == required, "packet fields")
        require(type(packet["version"]) is int and packet["version"] == 1, "version must be integer 1")
        initial = packet["initial_credits"]
        require(isinstance(initial, dict) and bool(initial) and "__usage__" not in initial, "owners")
        require(all(name(k) and whole(v) for k, v in initial.items()), "initial credits")
        require(whole(packet["capacity"], 1), "capacity")
        jobs = packet["jobs"]
        require(isinstance(jobs, list) and bool(jobs), "jobs")

        # Declare identities once; component add retries must not admit duplicate
        # declarations or two jobs claiming one tenant's artifact.
        scheduler = Scheduler(packet["capacity"])
        declared, artifact_keys = {}, set()
        for job in jobs:
            require(isinstance(job, dict) and set(job) == {"owner", "job", "cap", "cost", "deps", "artifact"},
                    "job fields")
            require(name(job["owner"]) and job["owner"] in initial and name(job["job"]) and name(job["artifact"]),
                    "job identity")
            require(whole(job["cap"], 1), "job cap")
            require(whole(job["cost"], 1) and job["cost"] <= packet["capacity"], "job cost")
            require(job["job"] not in declared, "duplicate job")
            key = (job["owner"], job["artifact"])
            require(key not in artifact_keys, "artifact reused by jobs")
            # Scheduler validates the ordered dependency list, earlier existence,
            # same-owner authority, and uniqueness.
            scheduler.add(job["owner"], job["job"], job["cost"], job["deps"])
            artifact_keys.add(key)
            declared[job["job"]] = job

        require(isinstance(packet["schedule_commands"], list), "schedule commands")
        command_keys = {"claim": {"action", "owner", "job", "lease"},
                        "finish": {"action", "owner", "job", "lease", "success"},
                        "cancel": {"action", "owner", "job"}}
        for command in packet["schedule_commands"]:
            require(isinstance(command, dict), "schedule command")
            action = command.get("action")
            require(isinstance(action, str) and action in command_keys
                    and set(command) == command_keys[action], "command fields")
            args = [command["owner"], command["job"]]
            if action in {"claim", "finish"}:
                args.append(command["lease"])
            if action == "finish":
                args.append(command["success"])
            getattr(scheduler, action)(*args)
        scheduling = scheduler.snapshot()
        require(set(scheduling["jobs"]) == set(declared), "scheduler job set")
        succeeded = sum(row["state"] == "succeeded" for row in scheduling["jobs"].values())
        require(succeeded == len(declared), "every declared job must succeed")
        require(scheduling["used"] == 0, "campaign still running")

        journal = Journal.replay(initial, packet["journal_events"])
        recording = journal.snapshot()
        require(set(recording["jobs"]) == set(declared), "journal job set")
        for identity, job in declared.items():
            row = recording["jobs"][identity]
            require(row == {"owner": job["owner"], "cap": job["cap"], "state": "settled"},
                    "journal job binding: " + identity)
        # export_log contains only first accepted events, so exact event retries
        # cannot increase consumption. A zero actual amount remains a real settle.
        actual = {event["job"]: event["amount"] for event in journal.export_log()
                  if event["kind"] == "settle"}
        require(set(actual) == set(declared), "settled consumption missing")

        store = ArtifactStore.restore(packet["artifacts"])
        artifacts = store.snapshot()
        require({(row["owner"], row["upload"]) for row in artifacts} == artifact_keys,
                "artifact tenant and upload set")
        require(all(row["state"] == "committed" for row in artifacts), "artifact not committed")
        # Revalidate complete bytes/digest only after verifying the supplied
        # committed state; auditing must not turn an active upload into evidence.
        artifact_bytes = sum(len(store.commit(row["owner"], row["upload"])) for row in artifacts)

        book = AccountBook(dict(initial, __usage__=0))
        require(isinstance(packet["settlements"], list), "settlements")
        expected_batches = {"settlement:" + job: job for job, amount in actual.items() if amount > 0}
        seen = set()
        for batch in packet["settlements"]:
            require(isinstance(batch, dict) and set(batch) == {"request", "operations", "expected"},
                    "batch fields")
            request = batch["request"]
            require(name(request) and request in expected_batches, "unexpected settlement")
            identity = expected_batches[request]
            owner = declared[identity]["owner"]
            operations, expected = batch["operations"], batch["expected"]
            require(isinstance(operations, list) and len(operations) == 1,
                    "one settlement operation required")
            operation = operations[0]
            require(isinstance(operation, dict) and set(operation) == {"from", "to", "amount"},
                    "settlement operation fields")
            # Validate integer types even before exact retries: Python's mapping
            # equality alone treats True == 1 and 1.0 == 1.
            require(whole(operation["amount"], 1), "settlement amount must be a positive integer")
            require(operation == {"from": owner, "to": "__usage__", "amount": actual[identity]},
                    "settlement must bind the job owner, usage sink and actual amount")
            require(isinstance(expected, dict) and set(expected) == {owner, "__usage__"}
                    and all(whole(revision) for revision in expected.values()),
                    "settlement revision guard")
            # AccountBook enforces ordered revision guards and exact request retry
            # identity, including retries after intervening successful batches.
            book.transact(request, operations, expected)
            seen.add(request)
        require(seen == set(expected_batches), "missing settlement")

        # Check redundant reconciliation explicitly against accepted journal
        # consumption as well as final account and wallet snapshots.
        accounting = book.snapshot()
        settled = {owner: 0 for owner in initial}
        for identity, amount in actual.items():
            settled[declared[identity]["owner"]] += amount
        require(set(recording["wallets"]) == set(initial), "wallet owner set")
        for owner, wallet in recording["wallets"].items():
            require(wallet["reserved"] == 0, "outstanding reserved credits: " + owner)
            require(wallet["available"] == accounting["balances"][owner]
                    and wallet["spent"] == settled[owner]
                    and initial[owner] - accounting["balances"][owner] == settled[owner],
                    "owner reconciliation: " + owner)
        require(accounting["balances"]["__usage__"] == sum(settled.values()),
                "usage reconciliation")
        summary = dict(jobs=len(jobs), succeeded=succeeded, running_units=scheduling["used"],
                       artifact_bytes=artifact_bytes, wallets=recording["wallets"], settled_credits=settled,
                       usage_sink=accounting["balances"]["__usage__"])
        return dict(schema="campaign-audit/1", decision="release", packet_sha256=digest,
                    reasons=[], summary=summary)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, IndexError, RecursionError) as error:
        return dict(schema="campaign-audit/1", decision="hold", packet_sha256=digest,
                    reasons=[str(error) or type(error).__name__], summary={})
