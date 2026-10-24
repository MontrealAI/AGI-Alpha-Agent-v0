# SPDX-License-Identifier: Apache-2.0
"""Explicitly recover the refused 1.41.1 cold-start submission, preserving earlier successes."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import workbench
from alpha_factory_v1.core.runtime.successor.trust import JournalCheckpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert version("alpha-factory-v1") == "1.41.1"
    assert (
        hashlib.sha256(Path(workbench.__file__).read_bytes()).hexdigest()
        == "6efb59f24b67dbaf0932166ba8161eb9797b9866cbc36c123015b4465bfd737c"
    )
    original = json.loads((args.load_output / "load-samples.json").read_bytes())
    (sample,) = [sample for sample in original["samples"] if sample["missions"] == 4]
    (refused,) = [result for result in sample["results"] if not result["passed"]]
    successes = [result for result in sample["results"] if result["passed"]]
    home = args.load_output / "load-4"
    journal = Journal(home)
    before = journal.verify()
    assert before == sample["journal_checkpoint"]
    retained = [journal.latest("@successor-work:" + result["run_id"]) for result in successes]
    assert all(record["result_digest"] == result["result_digest"] for record, result in zip(retained, successes))
    try:
        journal.latest("@successor-work:" + refused["run_id"])
    except KeyError:
        pass
    else:
        raise AssertionError("Refused submission now has a record; inspect it before retrying")
    result = workbench.execute(home, retained[0]["request"], refused["run_id"])
    assert result["state"] == "review" and result["attempts"] == 1 and result["authority"] == []
    after = journal.verify()
    JournalCheckpoint(before["identity"], before["events"], before["head"]).verify(journal)
    assert all(
        journal.latest("@successor-work:" + old["run_id"])["result_digest"] == old["result_digest"] for old in successes
    )
    receipt = {
        "schema": "agialpha.public-cold-start-explicit-recovery.v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "1.41.1",
        "commit": original["commit"],
        "original_sample_passed": False,
        "original_failure": refused,
        "failed_before_work_record_registration": True,
        "explicit_resubmission": True,
        "automatic_retry": False,
        "external_effects_replayed": False,
        "resubmitted_run_id": result["run_id"],
        "result_digest": result["result_digest"],
        "state": result["state"],
        "attempts_after_registration": result["attempts"],
        "earlier_successes_preserved": len(successes),
        "before": before,
        "after": after,
        "operator_recovery_interventions": 1,
        "authority": [],
        "meaning": "One explicit resubmission after local setup completed; does not erase the original load failure or qualify scale.",
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"recovered": True, "earlier_successes_preserved": len(successes), "state": result["state"]}))


if __name__ == "__main__":
    main()
