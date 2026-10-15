# SPDX-License-Identifier: Apache-2.0
"""Real SQLite race, crash, retry and authenticated reservation boundaries."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.budget import BudgetCommand, BudgetScope, inspect, operate
from alpha_factory_v1.core.runtime.store import Conflict, Journal

SCOPE = BudgetScope(owner="0x" + "a" * 40, chain_id=31337, token="0x" + "b" * 40)


def command(action: str, revision: int, request: str, **kwargs: Any) -> BudgetCommand:
    return BudgetCommand.model_validate(
        dict(
            scope=SCOPE.model_dump(),
            action=action,
            expected_revision=revision,
            request_id=request,
            purpose=kwargs.pop("purpose", "Reviewed planning terms"),
            **kwargs,
        )
    )


@pytest.fixture
def journal(tmp_path: Path) -> Journal:
    return Journal.initialize(tmp_path / "agent")


def test_exact_large_units_retry_reconcile_and_restart(journal: Journal) -> None:
    limit = str(2**200)
    initial = operate(journal, command("set_limit", 0, "init", amount=limit))
    reserve = command("reserve", initial["revision"], "request", reservation_id="project-A", amount="9007199254740993")
    active = operate(journal, reserve)
    before = journal.verify()
    assert operate(Journal(journal.root), reserve)["replayed"] is True
    assert journal.verify() == before
    assert active["available"] == str(2**200 - 9007199254740993)
    assert active["external_transfers_prevented"] is False
    committed = operate(journal, command("commit", active["revision"], "commit", reservation_id="project-A"))
    assert committed["reserved"] == "0"
    assert committed["committed"] == "9007199254740993"
    assert committed["available"] == active["available"]
    assert inspect(Journal(journal.root), SCOPE)["committed"] == committed["committed"]
    with pytest.raises(Conflict):
        operate(journal, command("release", committed["revision"], "release", reservation_id="project-A"))
    with pytest.raises(Conflict):
        operate(journal, command("set_limit", committed["revision"], "shrink", amount="0"))
    assert journal.missions() == []
    assert journal.verify()["valid"]


def test_release_frees_exact_amount_but_cannot_reuse_identity(journal: Journal) -> None:
    first = operate(journal, command("set_limit", 0, "init", amount="10"))
    active = operate(journal, command("reserve", first["revision"], "reserve", reservation_id="A", amount="10"))
    end = operate(journal, command("release", active["revision"], "release", reservation_id="A"))
    assert end["available"] == "10"
    with pytest.raises(Conflict):
        operate(journal, command("reserve", end["revision"], "new", reservation_id="A", amount="1"))


def test_two_native_processes_cannot_double_allocate(journal: Journal) -> None:
    first = operate(journal, command("set_limit", 0, "init", amount="10"))
    script = """import json,sys
from alpha_factory_v1.core.runtime.budget import BudgetCommand,operate
from alpha_factory_v1.core.runtime.store import Journal,Conflict
try:
 operate(Journal(sys.argv[1]),BudgetCommand.model_validate_json(sys.argv[2]))
 print("reserved")
except Conflict:
 print("conflict")
"""

    def run(index: int) -> str:
        value = command("reserve", first["revision"], f"request-{index}", reservation_id=f"project-{index}", amount="7")
        return subprocess.check_output(
            [sys.executable, "-c", script, str(journal.root), value.model_dump_json()], text=True
        ).strip()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == ["conflict", "reserved"]
    assert inspect(journal, SCOPE)["reserved"] == "7"
    fresh = inspect(journal, SCOPE)
    with pytest.raises(Conflict):
        operate(journal, command("reserve", fresh["revision"], "too-much", reservation_id="third", amount="4"))


@pytest.mark.parametrize("after_append", [False, True])
def test_process_death_before_commit_rolls_back(journal: Journal, after_append: bool) -> None:
    initial = operate(journal, command("set_limit", 0, "init", amount="10"))
    before = journal.verify()
    value = command("reserve", initial["revision"], "crash", reservation_id="A", amount="7")
    script = """import os,sys
from alpha_factory_v1.core.runtime.budget import BudgetCommand,operate
from alpha_factory_v1.core.runtime.store import Journal
j=Journal(sys.argv[1]); original=j.append
def die(*args,**kwargs):
 if sys.argv[3]=="True": original(*args,**kwargs)
 os._exit(29)
j.append=die
operate(j,BudgetCommand.model_validate_json(sys.argv[2]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(journal.root), value.model_dump_json(), str(after_append)]
    )
    assert result.returncode == 29
    assert Journal(journal.root).verify() == before
    assert operate(journal, value)["reserved"] == "7"


def test_lost_committed_response_retries_without_second_effect(journal: Journal) -> None:
    first = operate(journal, command("set_limit", 0, "init", amount="10"))
    value = command("reserve", first["revision"], "lost", reservation_id="A", amount="7")
    script = """import os,sys
from alpha_factory_v1.core.runtime.budget import BudgetCommand,operate
from alpha_factory_v1.core.runtime.store import Journal
operate(Journal(sys.argv[1]),BudgetCommand.model_validate_json(sys.argv[2]))
os._exit(29)
"""
    assert subprocess.run([sys.executable, "-c", script, str(journal.root), value.model_dump_json()]).returncode == 29
    before = journal.verify()
    assert operate(journal, value)["replayed"]
    assert journal.verify() == before
    with pytest.raises(Conflict):
        operate(journal, value.model_copy(update={"amount": "8"}))


def test_api_auth_origin_strict_scope_and_no_private_token_changes(journal: Journal) -> None:
    token = (journal.root / "api.token").read_bytes()
    key = (journal.root / "identity.key").read_bytes()
    headers = {"Authorization": "Bearer " + token.decode(), "X-AGIALPHA-Journal": journal.identity}
    value = command("set_limit", 0, "init", amount="10").model_dump()
    with TestClient(create_app(journal)) as client:
        assert client.post("/api/budget/operate", json=value).status_code == 401
        assert (
            client.post(
                "/api/budget/operate", json=value, headers={"Authorization": headers["Authorization"]}
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/budget/operate", json=value, headers={**headers, "Origin": "https://evil.test"}
            ).status_code
            == 403
        )
        assert client.post("/api/budget/operate", json={**value, "amount": 10}, headers=headers).status_code == 422
        assert (
            client.post(
                "/api/budget/operate", json=value, headers={**headers, "X-AGIALPHA-Journal": "wrong"}
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/budget/operate", json=value, headers={**headers, "X-AGIALPHA-Journal": journal.identity}
            ).status_code
            == 200
        )
        result = client.post("/api/budget/inspect", json=SCOPE.model_dump(), headers=headers)
        assert result.status_code == 200 and result.json()["available"] == "10"
        other = {**SCOPE.model_dump(), "chain_id": 1}
        assert client.post("/api/budget/inspect", json=other, headers=headers).status_code == 404
    assert (journal.root / "api.token").read_bytes() == token
    assert (journal.root / "identity.key").read_bytes() == key


@pytest.mark.parametrize(
    "change",
    [
        dict(amount="-1"),
        dict(amount="1.0"),
        dict(amount="01"),
        dict(amount=str(2**256)),
        dict(action="reserve", reservation_id="A", amount="0"),
        dict(action="release", reservation_id="A", amount="1"),
        dict(reservation_id="A"),
    ],
)
def test_invalid_terms_fail_without_mutating(journal: Journal, change: dict[str, Any]) -> None:
    before = journal.verify()
    with pytest.raises((ValueError, Conflict)):
        operate(
            journal,
            BudgetCommand.model_validate({**command("set_limit", 0, "init", amount="10").model_dump(), **change}),
        )
    assert journal.verify() == before


def test_identical_concurrent_requests_commit_once(journal: Journal) -> None:
    initial = operate(journal, command("set_limit", 0, "init", amount="10"))
    value = command("reserve", initial["revision"], "same", reservation_id="A", amount="7")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: operate(Journal(journal.root), value), range(8)))
    assert sum(not result["replayed"] for result in results) == 1
    assert journal.verify()["events"] == 3
    end_command = command("release", results[0]["revision"], "release", reservation_id="A")
    released = operate(journal, end_command)
    assert released["available"] == "10"
    before = journal.verify()
    assert operate(journal, end_command)["available"] == "10"
    assert journal.verify() == before
    assert operate(journal, value)["reservations"]["A"]["state"] == "released"


def test_scope_canonicalization_and_independent_token_pools(journal: Journal) -> None:
    initial = operate(journal, command("set_limit", 0, "init", amount="10"))
    uppercase = SCOPE.model_copy(update={"owner": "0x" + "A" * 40, "token": "0x" + "B" * 40})
    assert inspect(journal, uppercase)["revision"] == initial["revision"]
    for scope in [
        SCOPE.model_copy(update={"chain_id": 1}),
        SCOPE.model_copy(update={"owner": "0x" + "c" * 40}),
        SCOPE.model_copy(update={"token": "0x" + "c" * 40}),
    ]:
        with pytest.raises(KeyError):
            inspect(journal, scope)
    with pytest.raises(ValueError):
        inspect(journal, SCOPE.model_copy(update={"owner": "0x" + "0" * 40}))


def test_signed_record_corruption_fails_closed(journal: Journal) -> None:
    first = operate(journal, command("set_limit", 0, "init", amount="10"))
    with journal.transaction() as cx:
        cx.execute(
            'UPDATE events SET body=replace(body, \'"limit":"10"\', \'"limit":"99"\') WHERE mission LIKE \'@budget:%\''
        )
    with pytest.raises(ValueError):
        operate(journal, command("reserve", first["revision"], "bad", reservation_id="A", amount="20"))


def test_retention_reserves_headroom_for_terminal_reconciliation(journal: Journal) -> None:
    from alpha_factory_v1.core.runtime.budget import _key, _scope

    first = operate(journal, command("set_limit", 0, "init", amount="10"))
    operate(journal, command("reserve", first["revision"], "reserve", reservation_id="A", amount="7"))
    key = _key(_scope(SCOPE))
    with journal.transaction() as cx:
        record = Journal.document(journal.latest(key, cx))
        record["requests"] = {f"request-{i}": "0" * 64 for i in range(4095)}
        retained = journal.append(cx, key, record)
    with pytest.raises(Conflict, match="retention"):
        operate(journal, command("set_limit", retained["revision"], "new-limit", amount="11"))
    released = operate(journal, command("release", retained["revision"], "release", reservation_id="A"))
    assert released["available"] == "10"
    with pytest.raises(Conflict, match="retention"):
        operate(journal, command("set_limit", released["revision"], "full", amount="11"))


def test_history_byte_limit_preserves_all_terminal_slots(journal: Journal, monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.core.runtime import budget

    monkeypatch.setattr(budget, "MAX_HISTORY_BYTES", 80_000)
    result = operate(journal, command("set_limit", 0, "init", amount="1000000"))
    reserved = []
    for index in range(100):
        try:
            result = operate(
                journal,
                command(
                    "reserve",
                    result["revision"],
                    f"reserve-{index}",
                    reservation_id=f"A-{index}",
                    amount="1",
                    purpose="😀" * 500,
                ),
            )
            reserved.append(f"A-{index}")
        except Conflict as error:
            assert "byte limit" in str(error)
            break
    else:
        pytest.fail("Bounded history must refuse unlimited full snapshots")
    assert len(reserved) > 1
    for index, reservation_id in enumerate(reserved):
        result = operate(
            journal,
            command(
                "release" if index % 2 else "commit",
                result["revision"],
                f"terminal-{index}",
                reservation_id=reservation_id,
                purpose="😀" * 500,
            ),
        )
    assert result["reserved"] == "0"
    assert journal.verify()["valid"]
    with journal.transaction() as cx:
        size = cx.execute(
            "SELECT SUM(length(CAST(body AS BLOB)) + 512) FROM events WHERE mission LIKE '@budget:%'"
        ).fetchone()[0]
    assert size < budget.MAX_HISTORY_BYTES
