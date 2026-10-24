# SPDX-License-Identifier: Apache-2.0
"""Deterministically expose a concurrent first-use failure in public Alpha 1.41.1."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import threading
import uuid

from alpha_factory_v1.core.runtime import store
from alpha_factory_v1.core.runtime.successor import trust, workbench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert version("alpha-factory-v1") == "1.41.1"
    module = Path(workbench.__file__)
    assert (
        hashlib.sha256(module.read_bytes()).hexdigest()
        == "6efb59f24b67dbaf0932166ba8161eb9797b9866cbc36c123015b4465bfd737c"
    )
    root = args.output.resolve()
    root.mkdir(mode=0o700)
    home = root / "private-home"
    journal = store.Journal.initialize(home)
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    waiting, release = threading.Event(), threading.Event()
    original_write = store.private_write

    def pause_first_key(path, data):
        if path == home / "workbench-principals/local-controller.key":
            waiting.set()
            assert release.wait(5), "Test driver did not release the first writer"
        return original_write(path, data)

    store.private_write = pause_first_key
    failure = None
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(workbench.execute, home, spec, str(uuid.uuid4()))
            try:
                assert waiting.wait(5), "First request did not reach cold role creation"
                try:
                    workbench.execute(home, spec, str(uuid.uuid4()))
                except ValueError as error:
                    failure = {"type": type(error).__name__, "message": str(error)}
            finally:
                release.set()
            winner = first.result(timeout=10)
    finally:
        store.private_write = original_write
    assert failure and failure["message"] == "local principal state is incomplete; do not silently replace role keys"
    assert winner["state"] == "review"
    checked = journal.verify()
    assert checked["valid"]
    result = {
        "schema": "agialpha.public-cold-start-reproduction.v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "1.41.1",
        "commit": "787bc547f8c44854931b316d7286b8bc9f9c8bba",
        "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "trust_module_sha256": hashlib.sha256(Path(trust.__file__).read_bytes()).hexdigest(),
        "procedure_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fault": "Pause the original first role-key write after its directory is created; do not alter any key bytes",
        "concurrent_request": failure,
        "earlier_success_retained": winner["state"],
        "journal": checked,
        "confirmed": True,
        "original_load_sample_attribution": "Consistent with its ValueError; the original sample did not capture its exact message",
        "authority": [],
        "transactions_sent": False,
    }
    (root / "reproduction.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"confirmed": True, "failure": failure, "winner": winner["state"], "journal_valid": checked["valid"]}
        )
    )


if __name__ == "__main__":
    main()
