# SPDX-License-Identifier: Apache-2.0
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
    digest = None
    try:
        encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        packet = deepcopy(packet)
        required = {"version", "initial_credits", "capacity", "jobs", "journal_events",
                    "schedule_commands", "artifacts", "settlements"}
        require(isinstance(packet, dict) and set(packet) == required, "packet fields")
        require(whole(packet["version"], 1) and packet["version"] == 1, "version")
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
            require(name(job["owner"]) and job["owner"] in initial and name(job["job"]) and name(job["artifact"]),
                    "job identity")
            require(whole(job["cap"], 1), "job cap")
            require(job["job"] not in declared, "duplicate job")
            key = (job["owner"], job["artifact"])
            require(key not in artifact_keys, "artifact reused by jobs")
            artifact_keys.add(key)
            scheduler.add(job["owner"], job["job"], job["cost"], job["deps"])
            declared[job["job"]] = job
        require(isinstance(packet["schedule_commands"], list), "schedule commands")
        for command in packet["schedule_commands"]:
            require(isinstance(command, dict), "schedule command")
            action = command.get("action")
            keys = {"claim": {"action", "owner", "job", "lease"},
                    "finish": {"action", "owner", "job", "lease", "success"},
                    "cancel": {"action", "owner", "job"}}
            require(isinstance(action, str) and action in keys and set(command) == keys[action], "command fields")
            args = [command["owner"], command["job"]]
            if action in {"claim", "finish"}:
                args.append(command["lease"])
            if action == "finish":
                args.append(command["success"])
            getattr(scheduler, action)(*args)
        scheduling = scheduler.snapshot()
        succeeded = sum(row["state"] == "succeeded" for row in scheduling["jobs"].values())
        require(scheduling["used"] == 0, "campaign still running")
        journal = Journal.replay(initial, packet["journal_events"])
        recording = journal.snapshot()
        require(set(recording["jobs"]) == set(declared), "journal job set")
        for identity, job in declared.items():
            row = recording["jobs"][identity]
            require(row == {"owner": job["owner"], "cap": job["cap"], "state": "settled"}, "journal job binding")
        actual = {row["job"]: row["amount"] for row in journal.export_log() if row["kind"] == "settle"}
        store = ArtifactStore.restore(packet["artifacts"])
        artifacts = store.snapshot()
        require({a["upload"] for a in artifacts} == {key[1] for key in artifact_keys}, "artifact names")
        require(all(a["state"] != "aborted" for a in artifacts), "artifact aborted")
        artifact_bytes = sum(len(store.commit(a["owner"], a["upload"])) for a in artifacts)
        book = AccountBook(dict(initial, __usage__=0))
        require(isinstance(packet["settlements"], list), "settlements")
        expected_batches = {"settlement:" + j: j for j, amount in actual.items() if amount > 0}
        seen = set()
        for batch in packet["settlements"]:
            require(isinstance(batch, dict) and set(batch) == {"request", "operations", "expected"}, "batch fields")
            request = batch["request"]
            require(name(request) and request in expected_batches, "unexpected settlement")
            job = expected_batches[request]
            require(len(batch["operations"]) == 1, "one settlement operation required")
            book.transact(request, batch["operations"], batch["expected"])
            seen.add(request)
        require(seen == set(expected_batches), "missing settlement")
        accounting = book.snapshot()
        settled = {owner: initial[owner] - accounting["balances"][owner] for owner in initial}
        for owner, wallet in recording["wallets"].items():
            require(wallet["reserved"] == 0 and wallet["available"] == accounting["balances"][owner]
                    and wallet["spent"] == settled[owner], "owner reconciliation")
        require(accounting["balances"]["__usage__"] == sum(settled.values()), "usage reconciliation")
        summary = dict(jobs=len(jobs), succeeded=succeeded, running_units=scheduling["used"],
                       artifact_bytes=artifact_bytes, wallets=recording["wallets"], settled_credits=settled,
                       usage_sink=accounting["balances"]["__usage__"])
        digest = hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()
        return dict(schema="campaign-audit/1", decision="release", packet_sha256=digest, reasons=[], summary=summary)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        return dict(schema="campaign-audit/1", decision="hold", packet_sha256=digest,
                    reasons=[str(error) or type(error).__name__], summary={})
