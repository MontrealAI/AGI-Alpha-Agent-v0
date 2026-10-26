"""Check transferred discovery results against the previously frozen recipient.

This semantic mapping checks facts, addresses and pointers, and is a construction
integration check. Campaign confirmation uses the independent frozen oracle.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalize_original(value: dict[str, Any]) -> list[str]:
    rows = []
    for change in value["changes"]:
        old, new = change["before"], change["after"]
        rows.append(
            canonical(
                {
                    "responseId": change["responseId"],
                    "address": change["address"],
                    "kind": change["kind"],
                    "oldFacts": old["facts"] if old else None,
                    "newFacts": new["facts"] if new else None,
                    "oldPointer": old["sourcePointer"] if old else None,
                    "newPointer": new["sourcePointer"] if new else None,
                }
            )
        )
    return sorted(rows)


def normalize_transferred(value: dict[str, Any]) -> list[str]:
    return sorted(
        canonical(
            {
                "responseId": change["responseId"],
                "address": change["address"],
                "kind": change["kind"].lower(),
                "oldFacts": change["oldFacts"],
                "newFacts": change["newFacts"],
                "oldPointer": change["oldPointer"],
                "newPointer": change["newPointer"],
            }
        )
        for change in value["dossier"]["changes"]
    )


def check(original: Path, transferred: Path) -> dict[str, Any]:
    before = json.loads(original.read_text())
    after = json.loads(transferred.read_text())
    assert normalize_original(before) == normalize_transferred(after), "complete changed tuple sets differ"
    for side in ("old", "new"):
        assert len(before[side]["nodes"]) == after["dossier"]["counts"][side]["nodes"], "inventory size differs"
    return {
        "status": "PASS",
        "kind": "recipient-integration-comparison-not-fresh-confirmation",
        "original": str(original),
        "transferred": str(transferred),
        "mode": after["mode"],
        "changedTuples": len(before["changes"]),
        "checks": ["exact changed tuple set", "fact values", "source pointers", "old node count", "new node count"],
        "limitation": "Same-session independently reconstructed comparator; no external customer acceptance. Warning vocabularies differ and are not asserted equivalent.",
    }


if __name__ == "__main__":
    result = check(Path(sys.argv[1]), Path(sys.argv[2]))
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
