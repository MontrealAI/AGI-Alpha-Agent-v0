# SPDX-License-Identifier: Apache-2.0
"""Read-only reconciliation of a finite campaign's four evidence streams."""
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
    """Return a release/hold packet without changing submitted evidence.

    The hash commits to all supplied evidence, including exact retries. Components
    validate their own replay rules; the checks here bind those replays to the
    same declared jobs, tenant artifacts and per-job consumption.
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
        require(whole(packet["version"], 1) and packet["version"] == 1, "version must be integer 1")
        initial = packet["initial_credits"]
        require(isinstance(initial, dict) and bool(initial) and "__usage__" not in initial, "owners")
        require(all(name(k) and whole(v) for k, v in initial.items()), "initial credits")
        require(whole(packet["capacity"], 1), "capacity")
        jobs = packet["jobs"]
        require(isinstance(jobs, list) and bool(jobs), "jobs")

        scheduler = Scheduler(packet["capacity"])
        declared, artifact_keys = {}, set()
        for job in jobs:
            require(isinstance(job, dict) and set(job) == {"owner", "job", "cap", "cost", "deps", "artifact"},
                    "job fields")
            require(name(job["owner"]) and job["owner"] in initial and name(job["job"])
                    and name(job["artifact"]), "job identity")
            require(whole(job["cap"], 1), "job cap")
            require(whole(job["cost"], 1) and job["cost"] <= packet["capacity"], "job cost")
            require(job["job"] not in declared, "duplicate job")
            deps = job["deps"]
            require(isinstance(deps, list) and all(name(dep) for dep in deps), "job dependencies")
            require(len(deps) == len(set(deps)), "duplicate dependency")
            require(all(dep in declared and declared[dep]["owner"] == job["owner"] for dep in deps),
                    "dependencies must be earlier jobs owned by the same tenant")
            key = (job["owner"], job["artifact"])
            require(key not in artifact_keys, "artifact reused by jobs")
            artifact_keys.add(key)
            scheduler.add(job["owner"], job["job"], job["cost"], deps)
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

        require(isinstance(packet["journal_events"], list), "journal events")
        journal = Journal.replay(initial, packet["journal_events"])
        recording = journal.snapshot()
        require(set(recording["jobs"]) == set(declared), "journal job set")
        for identity, job in declared.items():
            row = recording["jobs"][identity]
            require(row == {"owner": job["owner"], "cap": job["cap"], "state": "settled"},
                    "journal job binding: " + identity)
        # The component exports only first accepted events, so retries do not
        # consume credits again. Each settled job has one terminal settle event.
        actual = {row["job"]: row["amount"] for row in journal.export_log() if row["kind"] == "settle"}
        require(set(actual) == set(declared), "every job requires settled consumption")
        settled = {owner: 0 for owner in initial}
        for identity, amount in actual.items():
            settled[declared[identity]["owner"]] += amount

        require(isinstance(packet["artifacts"], list), "artifact snapshot")
        store = ArtifactStore.restore(packet["artifacts"])
        artifacts = store.snapshot()
        require({(a["owner"], a["upload"]) for a in artifacts} == artifact_keys,
                "artifact tenant and upload pairs must exactly match declared deliveries")
        require(all(a["state"] == "committed" for a in artifacts), "every artifact must already be committed")
        # restore verifies committed snapshots; commit is then an idempotent read
        # of their complete, digest-verified bytes, never an upgrade of evidence.
        artifact_bytes = sum(len(store.commit(a["owner"], a["upload"])) for a in artifacts)

        book = AccountBook(dict(initial, __usage__=0))
        require(isinstance(packet["settlements"], list), "settlements")
        expected_batches = {"settlement:" + identity: identity
                            for identity, amount in actual.items() if amount > 0}
        seen = set()
        for batch in packet["settlements"]:
            require(isinstance(batch, dict) and set(batch) == {"request", "operations", "expected"},
                    "batch fields")
            request = batch["request"]
            require(name(request) and request in expected_batches, "unexpected settlement request")
            identity = expected_batches[request]
            owner = declared[identity]["owner"]
            operations = batch["operations"]
            require(isinstance(operations, list) and len(operations) == 1,
                    "one settlement operation required")
            operation = operations[0]
            require(isinstance(operation, dict) and set(operation) == {"from", "to", "amount"},
                    "settlement operation fields")
            require(operation["from"] == owner and operation["to"] == "__usage__"
                    and whole(operation["amount"], 1) and operation["amount"] == actual[identity],
                    "settlement must transfer this job's actual consumption from its owner to __usage__")
            expected = batch["expected"]
            require(isinstance(expected, dict) and set(expected) == {owner, "__usage__"}
                    and all(whole(revision) for revision in expected.values()), "settlement revision fields")
            # AccountBook checks current revisions for first acceptance and
            # accepts exact retries with their original, now-stale revisions.
            book.transact(request, operations, expected)
            seen.add(request)
        require(seen == set(expected_batches), "missing settlement")

        accounting = book.snapshot()
        require(set(recording["wallets"]) == set(initial), "journal wallet set")
        for owner, wallet in recording["wallets"].items():
            require(wallet["reserved"] == 0
                    and wallet["available"] == accounting["balances"][owner]
                    and wallet["spent"] == settled[owner], "owner reconciliation: " + owner)
        require(accounting["balances"]["__usage__"] == sum(settled.values()), "usage reconciliation")
        summary = dict(jobs=len(jobs), succeeded=succeeded, running_units=scheduling["used"],
                       artifact_bytes=artifact_bytes, wallets=recording["wallets"], settled_credits=settled,
                       usage_sink=accounting["balances"]["__usage__"])
        return dict(schema="campaign-audit/1", decision="release", packet_sha256=digest, reasons=[], summary=summary)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as error:
        return dict(schema="campaign-audit/1", decision="hold", packet_sha256=digest,
                    reasons=[str(error) or type(error).__name__], summary={})
