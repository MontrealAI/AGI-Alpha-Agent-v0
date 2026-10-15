# SPDX-License-Identifier: Apache-2.0
"""Real fixed-work interruption boundaries with synthetic RPC and test principals.

Fresh subprocesses reopen retained journals without replaying execution. These
checks do not establish physical-device, external provider or live-chain recovery.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
from test_successor_ascension import CLOSE_TX
from test_successor_studio import prepared_runtime

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import ascension, studio, workbench
from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher
from alpha_factory_v1.core.runtime.successor.state import SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import sign_record


FRESH_READ = """
import json, sys
from alpha_factory_v1.core.runtime.store import Journal, Conflict
from alpha_factory_v1.core.runtime.successor import studio
value = json.load(sys.stdin)
journal = Journal(value['home'])
before = journal.verify()
try:
    result = studio.retained_work(journal, value['request'], value['binding'])
    output = {'status': 'retained', 'result': result}
except Conflict:
    output = {'status': 'requires-explicit-recovery'}
assert journal.verify() == before, 'Fresh retained read must not mutate or execute'
print(json.dumps(output))
"""


def fresh_read(home: Path, request: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    """Reopen journal in another interpreter with no recovered grant or client."""
    result = subprocess.run(
        [sys.executable, "-c", FRESH_READ],
        input=json.dumps({"home": str(home), "request": request, "binding": binding["digest"]}),
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("point", ["runtime-start", "after-computation-before-delivery"])
def test_native_interruption_keeps_reservation_and_fresh_process_refuses_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    request, _, store, _, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    actual = workbench.invoke
    calls = []

    def interrupted(value: dict[str, Any], checkpoint: Any = lambda: None) -> dict[str, Any]:
        if value.get("operation") == "run":
            calls.append(point)
            if point == "after-computation-before-delivery":
                actual(value, checkpoint)
            raise KeyboardInterrupt("Synthetic interruption at an actual fixed-work boundary")
        return actual(value, checkpoint)

    monkeypatch.setattr(workbench, "invoke", interrupted)
    with pytest.raises(KeyboardInterrupt):
        studio.execute_work(dispatcher, request, seal, binding, authorization)
    state = store.read("institution")
    assert state["resources"]["reserved"] == {"calls": 1}
    assert not state["grants"] and not state["admissions"] and state["serving_release"] is None
    assert fresh_read(tmp_path / "home", request, binding) == {"status": "requires-explicit-recovery"}
    reopened = SuccessorStore(Journal(tmp_path / "home"), store.trust)
    with pytest.raises(Conflict, match="do not replay"):
        studio.execute_work(JobDispatcher(reopened, "institution"), request, seal, binding, authorization)
    assert calls == [point]
    assert reopened.read("institution")["resources"] == state["resources"]


def test_lost_completed_output_response_is_recovered_in_fresh_process_without_new_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _, store, _, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    result = studio.execute_work(dispatcher, request, seal, binding, authorization)
    before = store.journal.verify()
    store.trust.revoke("local-controller")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Retained delivery recovery must not execute work")

    monkeypatch.setattr(workbench, "invoke", forbidden)
    restored = fresh_read(tmp_path / "home", request, binding)
    assert restored == {"status": "retained", "result": result}
    assert store.journal.verify() == before
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
    assert result["authority_status"] == "not_granted"


@pytest.mark.parametrize("point", ["review-acceptance", "settlement-import"])
def test_committed_response_loss_reopens_idempotently_without_duplicate_accounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    request, _, store, keys, rpc, reader, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    result = studio.execute_work(dispatcher, request, seal, binding, authorization)
    if point == "review-acceptance":
        decision = studio.acceptance_request(request, result, public_key=store.journal.public)
        signed = sign_record(keys["local-controller"], "local-controller", "job-acceptance", decision)
        actual = dispatcher.complete

        def lost_response(envelope: Any) -> dict[str, Any]:
            actual(envelope)
            raise KeyboardInterrupt("Committed acceptance response lost")

        monkeypatch.setattr(dispatcher, "complete", lost_response)
        with pytest.raises(KeyboardInterrupt):
            studio.accept_work(dispatcher, request, result, signed)
        reopened = SuccessorStore(Journal(tmp_path / "home"), store.trust)
        before = reopened.journal.verify()
        state = reopened.read("institution")
        recovered = studio.accept_work(JobDispatcher(reopened, "institution"), request, result, signed)
        assert recovered
        assert reopened.read("institution")["resources"] == state["resources"]
        assert state["resources"]["spent"] == {"calls": 1}
        assert state["resources"]["reserved"] == {"calls": 0}
        assert reopened.journal.verify() == before
    else:
        rpc.artifact_hash = result["artifact_keccak256"]
        rpc.close("paid")
        rpc.height = 4
        actual_import = ascension.import_settlement

        def lost_settlement(*args: Any, **kwargs: Any) -> dict[str, Any]:
            actual_import(*args, **kwargs)
            raise KeyboardInterrupt("Committed settlement response lost")

        monkeypatch.setattr(ascension, "import_settlement", lost_settlement)
        with pytest.raises(KeyboardInterrupt):
            studio.settle_work(store.journal, request, result, reader, settlement_tx=CLOSE_TX)
        monkeypatch.setattr(ascension, "import_settlement", actual_import)
        reopened_journal = Journal(tmp_path / "home")
        before = reopened_journal.verify()
        recovered = studio.settle_work(reopened_journal, request, result, reader, settlement_tx=CLOSE_TX)
        assert recovered["settlement_status"] == "paid"
        assert reopened_journal.verify() == before
        assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
    assert fresh_read(tmp_path / "home", request, binding)["result"] == result
