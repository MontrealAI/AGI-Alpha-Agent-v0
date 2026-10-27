"""Infrastructure-only recovery of an interrupted deterministic training stream.

Uses the unchanged frozen training function and preserves the complete ordered prefix.
No parameter, policy, seed, selection rule, or simulator behavior is changed.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src import run_study as study


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interrupted", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    study.verify_freeze(args.out)
    raw = args.interrupted.read_bytes()
    pieces = raw.splitlines(keepends=True)
    records, complete_bytes = [], 0
    for line in pieces:
        if not line.endswith(b"\n"):
            break
        records.append(json.loads(line))
        complete_bytes += len(line)
    original_execute = study.execute

    def resumed_execute(tasks, workers):
        if len(records) >= len(tasks):
            raise RuntimeError("Expected a genuinely interrupted prefix.")
        for index, record in enumerate(records):
            case, scenario, policy, seed, arm, retain = tasks[index]
            if (record["case"] != case or record["scenario"] != scenario.name
                    or record["policy"] != study.asdict(policy)
                    or record["seed"] != seed or record["arm"] != arm or retain):
                raise RuntimeError(f"Interrupted prefix does not match task {index}.")
            yield record
        yield from original_execute(tasks[len(records):], workers)

    receipt = {
        "kind": "infrastructure-interruption-recovery",
        "reason": "Shared overlay disk exhausted; no confirmation had begun.",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": study.digest(args.out / "protocol_freeze.json"),
        "interrupted_sha256": hashlib.sha256(raw).hexdigest(),
        "interrupted_bytes": len(raw), "complete_prefix_rows": len(records),
        "complete_prefix_bytes": complete_bytes,
        "incomplete_tail_bytes": len(raw) - complete_bytes,
        "incomplete_tail_sha256": hashlib.sha256(raw[complete_bytes:]).hexdigest(),
        "wrapper_sha256": study.digest(Path(__file__)),
        "frozen_source_modified": False, "workers_after_resume": args.workers,
        "selection_or_seed_changes": False,
    }
    study.write_json(args.out / "training_interruption.json", receipt)
    study.execute = resumed_execute
    result = study.train(args.out, args.workers)
    receipt["completed_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["resumed_training_sha256"] = result["training_results_sha256"]
    study.write_json(args.out / "training_interruption.json", receipt)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
