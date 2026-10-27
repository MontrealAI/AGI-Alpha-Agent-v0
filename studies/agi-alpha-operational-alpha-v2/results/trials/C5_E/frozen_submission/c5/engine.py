# SPDX-License-Identifier: Apache-2.0
"""Read-only, finite campaign evidence replay and cross-service reconciliation."""
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
    """Return a deterministic release/hold packet without retaining caller state.

    Component replays validate their own transitions and retries. The checks here
    bind those independently valid histories to the same declared campaign.
    """
    digest = None
    stage = "packet encoding"
    try:
        # Hash the entire submitted evidence, including rejected fields/retries.
        encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        packet = deepcopy(packet)
        stage = "packet structure"
        required = {"version", "initial_credits", "capacity", "jobs", "journal_events",
                    "schedule_commands", "artifacts", "settlements"}
        require(isinstance(packet, dict) and set(packet) == required, "packet fields")
        require(type(packet["version"]) is int and packet["version"] == 1, "version")
        initial = packet["initial_credits"]
        require(isinstance(initial, dict) and bool(initial) and "__usage__" not in initial, "owners")
        require(all(name(k) and whole(v) for k, v in initial.items()), "initial credits")
        require(whole(packet["capacity"], 1), "capacity")
        jobs = packet["jobs"]
        require(isinstance(jobs, list) and bool(jobs), "jobs")

        stage = "scheduler declaration"
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
            require(len(deps) == len(set(deps)) and all(
                dep in declared and declared[dep]["owner"] == job["owner"] for dep in deps),
                "dependencies must be distinct earlier jobs of the same owner")
            key = (job["owner"], job["artifact"])
            require(key not in artifact_keys, "artifact reused by jobs")
            artifact_keys.add(key)
            scheduler.add(job["owner"], job["job"], job["cost"], deps)
            declared[job["job"]] = job

        stage = "scheduler replay"
        require(isinstance(packet["schedule_commands"], list), "schedule commands")
        command_keys = {"claim": {"action", "owner", "job", "lease"},
                        "finish": {"action", "owner", "job", "lease", "success"},
                        "cancel": {"action", "owner", "job"}}
        for command in packet["schedule_commands"]:
            require(isinstance(command, dict), "schedule command")
            action = command.get("action")
            require(isinstance(action, str) and action in command_keys
                    and set(command) == command_keys[action], "command fields")
            require(name(command["job"]) and command["job"] in declared
                    and name(command["owner"])
                    and command["owner"] == declared[command["job"]]["owner"], "command job ownership")
            args = [command["owner"], command["job"]]
            if action in {"claim", "finish"}:
                require(name(command["lease"]), "command lease")
                args.append(command["lease"])
            if action == "finish":
                require(type(command["success"]) is bool, "finish success flag")
                args.append(command["success"])
            getattr(scheduler, action)(*args)
        scheduling = scheduler.snapshot()
        require(set(scheduling["jobs"]) == set(declared), "scheduler job set")
        succeeded = sum(row["state"] == "succeeded" for row in scheduling["jobs"].values())
        require(succeeded == len(declared), "not every declared job succeeded")
        require(scheduling["used"] == 0, "campaign still running")

        stage = "journal replay and binding"
        require(isinstance(packet["journal_events"], list), "journal events")
        journal = Journal.replay(initial, packet["journal_events"])
        recording = journal.snapshot()
        require(set(recording["jobs"]) == set(declared), "journal job set")
        for identity, job in declared.items():
            row = recording["jobs"][identity]
            require(row == {"owner": job["owner"], "cap": job["cap"], "state": "settled"},
                    "journal job binding")
        # Only accepted events appear in this log; event-ID retries count once.
        actual = {row["job"]: row["amount"] for row in journal.export_log() if row["kind"] == "settle"}
        require(set(actual) == set(declared), "settled job consumption missing")
        settled = {owner: 0 for owner in initial}
        for identity, job in declared.items():
            require(whole(actual[identity]) and actual[identity] <= job["cap"], "actual consumption")
            settled[job["owner"]] += actual[identity]

        stage = "artifact restore and binding"
        store = ArtifactStore.restore(packet["artifacts"])
        artifacts = store.snapshot()
        require(len(artifacts) == len(artifact_keys)
                and {(a["owner"], a["upload"]) for a in artifacts} == artifact_keys,
                "artifact owner/upload set")
        require(all(a["state"] == "committed" for a in artifacts), "artifact not committed")
        # Restore validates checkpoints; idempotent commits verify and read bytes.
        # Active snapshots are rejected above, never promoted into evidence.
        artifact_bytes = sum(len(store.commit(a["owner"], a["upload"])) for a in artifacts)

        stage = "account replay and per-job binding"
        book = AccountBook(dict(initial, __usage__=0))
        require(isinstance(packet["settlements"], list), "settlements")
        expected_batches = {"settlement:" + identity: identity
                            for identity, amount in actual.items() if amount > 0}
        seen = set()
        for batch in packet["settlements"]:
            require(isinstance(batch, dict) and set(batch) == {"request", "operations", "expected"},
                    "batch fields")
            request = batch["request"]
            require(name(request) and request in expected_batches, "unexpected settlement")
            identity = expected_batches[request]
            operations = batch["operations"]
            require(isinstance(operations, list) and len(operations) == 1,
                    "one settlement operation required")
            operation = operations[0]
            require(isinstance(operation, dict) and set(operation) == {"from", "to", "amount"},
                    "settlement operation fields")
            require(operation["from"] == declared[identity]["owner"] and operation["to"] == "__usage__",
                    "settlement route does not match job owner and usage sink")
            require(whole(operation["amount"], 1) and operation["amount"] == actual[identity],
                    "settlement amount does not match job consumption")
            # AccountBook checks revisions and exact retry identity, including
            # retries whose original expected revisions have since become stale.
            book.transact(request, operations, batch["expected"])
            seen.add(request)
        require(seen == set(expected_batches), "missing settlement")

        stage = "final reconciliation"
        accounting = book.snapshot()
        require(set(recording["wallets"]) == set(initial), "journal owner set")
        require(set(accounting["balances"]) == set(initial) | {"__usage__"}, "account owner set")
        for owner, wallet in recording["wallets"].items():
            require(wallet["reserved"] == 0 and wallet["available"] == accounting["balances"][owner]
                    and wallet["spent"] == settled[owner]
                    and initial[owner] - accounting["balances"][owner] == settled[owner],
                    "owner reconciliation")
        require(accounting["balances"]["__usage__"] == sum(settled.values())
                == sum(wallet["spent"] for wallet in recording["wallets"].values()), "usage reconciliation")
        summary = dict(jobs=len(jobs), succeeded=succeeded, running_units=scheduling["used"],
                       artifact_bytes=artifact_bytes, wallets=recording["wallets"], settled_credits=settled,
                       usage_sink=accounting["balances"]["__usage__"])
        return dict(schema="campaign-audit/1", decision="release", packet_sha256=digest, reasons=[], summary=summary)
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError, RecursionError) as error:
        return dict(schema="campaign-audit/1", decision="hold", packet_sha256=digest,
                    reasons=[stage + ": " + (str(error) or type(error).__name__)], summary={})
