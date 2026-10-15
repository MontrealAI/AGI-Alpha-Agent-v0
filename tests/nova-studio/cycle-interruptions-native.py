# SPDX-License-Identifier: Apache-2.0
"""Opt-in disposable-EVM retained observer; reuse the existing real executor."""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys
from typing import Any, cast

from alpha_factory_v1.core.runtime.successor.ascension import list_settlements
from alpha_factory_v1.core.runtime.successor.studio import retained_work

base = runpy.run_path(str(Path(__file__).with_name("cycle-native.py")))


def main(source: dict[str, Any]) -> dict[str, Any]:
    """Recover persisted output/settlement without execution or a new grant."""
    operation = source["operation"]
    if operation not in {"recover-output", "recover-settlement"}:
        return cast(dict[str, Any], base["main"](source))
    home = Path(source["home"])
    assert home.is_dir() and (home / "cycle-local-fixture-principals").is_dir(), "Retain fixture trust separately"
    store, _ = base["local_store"](home, source["worker"])
    before = store.journal.verify()
    request = source["request"]
    institution = "cycle-" + request["cycle_id"] + "-" + str(request["plan_index"])
    if operation == "recover-output":
        recovered = retained_work(store.journal, request, source["binding"]["digest"])
    else:
        matches = [
            record
            for record in list_settlements(store.journal, institution)
            if record["settlement"]["delivery_digest"] == source["result"]["delivery"]["digest"]
        ]
        assert len(matches) == 1
        recovered = {"settlement": matches[0]["settlement"], "record": matches[0]}
    after = store.journal.verify()
    assert before == after, "Retained observation must not append, execute or sign another result"
    return {
        "recovered": recovered,
        "journalBefore": before,
        "journalAfter": after,
        "resources": store.read(institution)["resources"],
        "executionReplayed": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps({"result": main(json.loads(sys.stdin.readline()))}), flush=True)
    except Exception as error:
        print(json.dumps({"error": type(error).__name__ + ": " + str(error)}), flush=True)
        raise
