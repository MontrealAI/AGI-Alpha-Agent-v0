# SPDX-License-Identifier: Apache-2.0
"""Generate genuine reviewed native evidence for disposable-EVM acceptance only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

# The acceptance process must import this checkout, even with an editable install
# or virtual environment shared with a different worktree.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from alpha_factory_v1.core.runtime.ascension import compile_plan, delivery, verify_delivery
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal, digest


def native_delivery(plan: dict[str, Any], index: int = 0) -> tuple[bytes, dict[str, Any]]:
    """Execute, explicitly review, sign and independently replay one native job."""
    mission = Mission.model_validate(
        {
            "goal": plan["jobs"][index]["spec"]["goal"],
            "work": {
                "kind": "allocation",
                "budget": 10,
                "items": [{"id": "one", "cost": 3, "value": 8}, {"id": "two", "cost": 7, "value": 10}],
            },
        }
    )
    # Never retain the signing secret in the public acceptance artifacts.
    with TemporaryDirectory(prefix="nova-native-acceptance-") as directory:
        journal = Journal.initialize(Path(directory) / "state")
        engine = Engine(journal)
        record = engine.execute(journal.submit(mission)["id"])
        assert record["state"] == "review" and record["result"]["value"] == 18
        engine.review(
            record["id"],
            record["revision"],
            digest(record["result"]),
            True,
            "Synthetic local acceptance operator recomputed both allocations; not an independent human validator.",
        )
        data = delivery(journal, plan, index, record["id"])
        verified = verify_delivery(data, journal.public, plan["planRoot"])
        assert verified["valid"] is True and verified["jobIndex"] == index
        return data, {
            "resultHash": verified["resultHash"],
            "byteSHA256": hashlib.sha256(data).hexdigest(),
            "signer": journal.public,
            "planRoot": plan["planRoot"],
            "index": index,
            "signatureVerified": True,
            "executionReplayed": True,
            "connected": False,
            "nativeVerification": verified["nativeVerification"],
            "reviewScope": verified["reviewScope"],
        }


def main() -> None:
    source = json.load(sys.stdin)
    if sys.argv[1:] == ["--compile-plans"]:
        print(json.dumps([compile_plan(specs) for specs in source]))
        return
    if len(sys.argv) != 2:
        raise ValueError("Usage: native_fixture.py OUTPUT or --compile-plans; JSON input on stdin")
    data, report = native_delivery(source)
    destination = Path(sys.argv[1])
    destination.write_bytes(data)
    report["artifact"] = destination.name
    print(json.dumps(report))


if __name__ == "__main__":
    main()
