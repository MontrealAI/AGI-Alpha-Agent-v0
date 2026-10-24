# SPDX-License-Identifier: Apache-2.0
"""Acknowledge earlier installed successes after upgrade, using a private copy of a stopped home."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import sqlite3
import sys

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import workbench
from alpha_factory_v1.core.runtime.successor.trust import JournalCheckpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--previous-load", type=Path, required=True)
    parser.add_argument("--previous-recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module = Path(workbench.__file__).resolve()
    assert module.is_relative_to(Path(sys.prefix).resolve())
    assert version("alpha-factory-v1") == "1.42.0"
    assert hashlib.sha256(module.read_bytes()).hexdigest() == (
        "87ad9f365ebf1b5c1e93edc275e6fe933b6c247e51b848b52dc66c34344a8492"
    )
    old_receipt = json.loads((args.previous_load / "load-samples.json").read_bytes())
    recovery = json.loads(args.previous_recovery.read_bytes())
    assert old_receipt["version"] == recovery["version"] == "1.41.1"
    (sample,) = [record for record in old_receipt["samples"] if record["missions"] == 4]
    source_home = args.previous_load / "load-4"
    source_journal = Journal(source_home)
    before = source_journal.verify()
    assert before == recovery["after"]
    original = sample["journal_checkpoint"]
    JournalCheckpoint(original["identity"], original["events"], original["head"]).verify(source_journal)

    root = args.output.resolve()
    root.mkdir(mode=0o700)
    home = root / "private-upgrade-home"
    # The prior finite run is stopped. Retain its keys privately and take a consistent SQLite snapshot.
    shutil.copytree(source_home, home, ignore=shutil.ignore_patterns("journal.sqlite3*"))
    with sqlite3.connect(source_journal.path) as source, sqlite3.connect(home / "journal.sqlite3") as target:
        source.backup(target)
    (home / "journal.sqlite3").chmod(0o600)
    assert source_journal.verify() == before
    journal = Journal(home)
    assert journal.verify() == before
    private_paths = [home / "identity.key", home / "api.token", home / "config.json"]
    private_paths.extend(sorted((home / "workbench-principals").iterdir()))
    private_hashes = {
        str(path.relative_to(home)): hashlib.sha256(path.read_bytes()).hexdigest() for path in private_paths
    }

    old_invoke = workbench.invoke
    operations = []

    def observe(request, *other):
        operations.append(request["operation"])
        assert request["operation"] != "run", "A previously successful worker was executed again"
        return old_invoke(request, *other)

    workbench.invoke = observe
    acknowledged = []
    try:
        for item in sample["results"]:
            record = journal.latest("@successor-work:" + item["run_id"])
            assert record["state"] == "review" and record["authority"] == []
            result = workbench.execute(home, record["request"], item["run_id"])
            assert result == record
            assert result["lifecycle"]["active_proof"] == result["lifecycle"]["active_authority"] == []
            expected_digest = item["result_digest"] if item["passed"] else recovery["result_digest"]
            assert result["result_digest"] == expected_digest
            acknowledged.append({"run_id": item["run_id"], "result_digest": expected_digest, "state": result["state"]})
    finally:
        workbench.invoke = old_invoke
    assert journal.verify() == before == source_journal.verify()
    assert private_hashes == {
        str(path.relative_to(home)): hashlib.sha256(path.read_bytes()).hexdigest() for path in private_paths
    }
    receipt = {
        "schema": "agialpha.installed-upgrade-acknowledgement.v1",
        "passed": True,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "1.42.0",
        "commit": args.commit,
        "previous_version": "1.41.1",
        "previous_commit": old_receipt["commit"],
        "private_copy": True,
        "source_home_unchanged": True,
        "private_inventory_unchanged": True,
        "retained_checkpoint": before,
        "acknowledged_successes": acknowledged,
        "worker_reexecutions": operations.count("run"),
        "operations": operations,
        "new_history_events": 0,
        "original_failed_sample_passed": False,
        "prior_explicit_recovery_interventions": 1,
        "fresh_proof_granted": False,
        "authority": [],
        "full_harness_qualification": False,
        "four_installed_tuple_qualification": False,
    }
    (root / "upgrade-acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": True, "acknowledged_successes": len(acknowledged), "new_history_events": 0}))


if __name__ == "__main__":
    main()
