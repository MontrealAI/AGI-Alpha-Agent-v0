# SPDX-License-Identifier: Apache-2.0
"""Real lifecycle, arithmetic, adversarial evidence and recovery tests."""

from __future__ import annotations

import base64
import copy
import json
import os
import subprocess
from pathlib import Path
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from typing import Any
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient
import pytest

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission, RuntimeConfig
from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest
from alpha_factory_v1.core.runtime.work import verify_result

ROOT = Path(__file__).resolve().parents[2]


def mission(kind: str) -> Mission:
    return Mission.model_validate_json((ROOT / "examples/missions" / f"{kind}.json").read_bytes())


@pytest.fixture
def journal(tmp_path: Path) -> Journal:
    return Journal.initialize(tmp_path / "agent")


@pytest.mark.parametrize("existing", [False, True])
def test_container_initializes_empty_home_and_reuses_identity(tmp_path: Path, monkeypatch: Any, existing: bool) -> None:
    from alpha_factory_v1.core.runtime import container

    root = tmp_path / "mounted-home"
    if existing:
        root.mkdir()
    monkeypatch.setenv("ALPHA_AGENT_HOME", str(root))
    monkeypatch.setattr(container.uvicorn, "run", lambda *args, **kwargs: None)
    container.main()
    first = Journal(root).verify()
    key = (root / "identity.key").read_bytes()
    token = (root / "api.token").read_bytes()
    container.main()
    assert Journal(root).verify() == first
    assert (root / "identity.key").read_bytes() == key
    assert (root / "api.token").read_bytes() == token
    if os.name == "nt":
        script = r"""
$ErrorActionPreference = 'Stop'
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach ($path in @($env:ALPHA_PRIVATE_PATH, (Join-Path $env:ALPHA_PRIVATE_PATH 'identity.key'))) {
    $acl = Get-Acl -LiteralPath $path
    if (-not $acl.AreAccessRulesProtected) { throw 'ACL inherits other accounts' }
    foreach ($rule in $acl.Access) {
        if ($rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -ne $sid) {
            throw 'Another account can access private state'
        }
    }
    if ($acl.Access.Count -ne 1) { throw 'Expected one owner access rule' }
}
"""
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            env={**os.environ, "ALPHA_PRIVATE_PATH": str(root)},
            check=True,
            timeout=30,
        )
    else:
        assert root.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("existing_file", ["identity.key", "config.json", "unrelated.txt"])
def test_empty_mount_initialization_never_overwrites_partial_home(tmp_path: Path, existing_file: str) -> None:
    root = tmp_path / "mounted-home"
    root.mkdir()
    (root / existing_file).write_bytes(b"preserve this operator data")
    with pytest.raises(FileExistsError):
        Journal.initialize(root, allow_empty=True)
    assert {path.name: path.read_bytes() for path in root.iterdir()} == {existing_file: b"preserve this operator data"}


@pytest.mark.parametrize("kind", ["research", "allocation", "schedule", "forecast"])
def test_complete_lifecycle_and_portable_signature(journal: Journal, kind: str) -> None:
    engine = Engine(journal)
    queued = journal.submit(mission(kind))
    record = engine.execute(queued["id"])
    assert record["state"] == "review"
    assert [stage["role"] for stage in record["stages"]] == [
        "planning",
        "research",
        "strategy",
        "market",
        "codegen",
        "safety",
        "memory",
    ]
    assert record["verification"]["passed"] is True
    assert record["stages"][3]["detail"]["realized_revenue"] is None
    with pytest.raises(Conflict):
        engine.export(record["id"])
    completed = engine.review(
        record["id"], record["revision"], digest(record["result"]), True, "Checked against supplied inputs."
    )
    assert completed["state"] == "completed"
    artifact = engine.export(record["id"])
    receipt = artifact["receipt"]
    assert digest(receipt["body"]) == receipt["hash"]
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(artifact["public_key"])).verify(
        base64.b64decode(receipt["signature"]), bytes.fromhex(receipt["hash"])
    )
    assert journal.verify()["valid"]


def test_allocation_reports_real_objective_values(journal: Journal) -> None:
    result = Engine(journal).execute(journal.submit(mission("allocation"))["id"])["result"]
    assert result["selected"] == ["B", "C"]
    assert result["cost"] == 10 and result["value"] == 22 and result["risk"] == 3
    assert result["optimality_proven"] and result["optimal_value"] == 22
    assert result["improvement"] == 0  # baseline is already optimal; never invent a gain


def test_learning_reuses_only_approved_matching_work(journal: Journal) -> None:
    engine = Engine(journal)
    first = engine.execute(journal.submit(mission("schedule"))["id"])
    second = engine.execute(journal.submit(mission("schedule"))["id"])
    assert second["stages"][1]["detail"]["parent"] is None
    approved = engine.review(first["id"], first["revision"], digest(first["result"]), True, "Feasibility checked.")
    third = engine.execute(journal.submit(mission("schedule"))["id"])
    assert third["stages"][1]["detail"]["parent"] == first["id"]
    assert third["stages"][1]["detail"]["parent_digest"] == approved["digest"]
    assert verify_result(mission("schedule"), third["result"])["passed"]


def test_review_is_compare_and_swap_and_hash_bound(journal: Journal) -> None:
    engine = Engine(journal)
    record = engine.execute(journal.submit(mission("research"))["id"])
    with pytest.raises(Conflict):
        engine.review(record["id"], record["revision"], "0" * 64, True, "Wrong artifact")

    def approve() -> str:
        try:
            engine.review(record["id"], record["revision"], digest(record["result"]), True, "Reviewed")
            return "accepted"
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: approve(), range(2)))
    assert sorted(results) == ["accepted", "conflict"]


def test_idempotency_rejects_changed_payload(journal: Journal) -> None:
    ident = str(uuid.uuid4())
    original = journal.submit(mission("research"), ident)
    assert journal.submit(mission("research"), ident)["revision"] == original["revision"]
    with pytest.raises(Conflict):
        journal.submit(mission("schedule"), ident)


@pytest.mark.parametrize("form", ["upper", "hex", "braces", "urn"])
def test_idempotency_normalizes_uuid_forms_after_restart(journal: Journal, form: str) -> None:
    key = uuid.UUID("ef0457e0-81c1-4f0c-a26b-c08c7099d2c1")
    canonical_id = str(key)
    variants = {"upper": canonical_id.upper(), "hex": key.hex, "braces": "{" + canonical_id + "}", "urn": key.urn}
    original = journal.submit(mission("research"), variants[form])
    assert original["id"] == canonical_id
    executed = Engine(journal).execute(original["id"])
    restarted = Journal(journal.root)
    with ThreadPoolExecutor(max_workers=4) as pool:
        retries = list(pool.map(lambda ident: restarted.submit(mission("research"), ident), variants.values()))
    assert all(item["id"] == canonical_id and item["revision"] == executed["revision"] for item in retries)
    assert len(restarted.missions()) == 1
    with pytest.raises(Conflict):
        restarted.submit(mission("schedule"), variants[form])
    assert restarted.verify()["valid"]


def test_persistent_pause_blocks_execution_and_review(journal: Journal) -> None:
    engine = Engine(journal)
    queued = journal.submit(mission("allocation"))
    journal.control(True)
    restarted = Journal(journal.root)
    with pytest.raises(Conflict):
        Engine(restarted).execute(queued["id"])
    restarted.control(False)
    record = engine.execute(queued["id"])
    journal.control(True)
    with pytest.raises(Conflict):
        engine.review(record["id"], record["revision"], digest(record["result"]), True, "Reviewed")


@pytest.mark.parametrize("phase", ["provider", "generation", "sandbox", "final"])
def test_reconfiguration_invalidates_running_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    from alpha_factory_v1.core.runtime import engine as engine_module

    config = RuntimeConfig(
        llm_url="http://127.0.0.1:1234/v1" if phase in {"provider", "generation"} else "",
        llm_model="fixture" if phase in {"provider", "generation"} else "",
        allow_code_execution=phase in {"sandbox", "generation"},
    )
    journal = Journal.initialize(tmp_path / "agent", config)
    engine = Engine(journal)

    def reconfigure() -> None:
        operator = Journal(journal.root)
        replacement = operator.config.model_dump()
        replacement.update(llm_url="", llm_model="", allow_code_execution=False, max_evaluations=100)
        operator.control(True)
        operator.configure(RuntimeConfig.model_validate(replacement))
        operator.control(False)

    if phase == "provider":

        def synthesize_then_revoke(*args: Any) -> tuple[dict[str, Any], dict[str, Any]]:
            reconfigure()
            return {}, {"fixture": True}

        monkeypatch.setattr(engine_module, "synthesize", synthesize_then_revoke)
        request = mission("research")
    elif phase in {"sandbox", "generation"}:

        def coding_then_revoke(*args: Any) -> dict[str, Any]:
            reconfigure()
            return {"method": "fixture sandbox result"}

        monkeypatch.setattr(engine_module.work, "coding", coding_then_revoke)
        request = Mission(
            goal="Exercise policy revocation during isolated evaluation",
            work={
                "kind": "code",
                "candidate": "def solve(x): return x" if phase == "sandbox" else "",
                "heldout": [{"args": [1], "expected": 1}],
            },
        )
        if phase == "generation":

            def generate_then_revoke(*args: Any) -> tuple[str, dict[str, Any]]:
                reconfigure()
                return "def solve(x): return x", {"fixture": True}

            def must_not_execute(*args: Any) -> dict[str, Any]:
                raise AssertionError("code execution was revoked during generation")

            monkeypatch.setattr(engine_module, "generate_code", generate_then_revoke)
            monkeypatch.setattr(engine_module.work, "coding", must_not_execute)
    else:
        transition = journal.transition

        def change_before_commit(
            ident: str, revision: int, allowed: set[str], state: str, **kwargs: Any
        ) -> dict[str, Any]:
            if state == "review":
                reconfigure()
            return transition(ident, revision, allowed, state, **kwargs)

        monkeypatch.setattr(journal, "transition", change_before_commit)
        request = mission("allocation")
    queued = journal.submit(request)
    with pytest.raises(Conflict, match="configuration changed"):
        engine.execute(queued["id"])
    current = Journal(journal.root)
    failed = current.latest(queued["id"])
    assert failed["state"] == "failed" and failed["error"] == "Conflict"
    assert failed["execution_config_hash"] != current.latest("@control")["config_hash"]
    assert current.verify()["valid"]
    with pytest.raises(Conflict):
        Engine(current).export(queued["id"])
    assert Engine(current).recover(queued["id"])["state"] == "queued"


def test_reconfiguration_during_review_cannot_approve(journal: Journal, monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.core.runtime import engine as engine_module

    engine = Engine(journal)
    record = engine.execute(journal.submit(mission("allocation"))["id"])
    original_verify = engine_module.work.verify_result

    def verify_then_reconfigure(*args: Any) -> dict[str, Any]:
        result = original_verify(*args)
        operator = Journal(journal.root)
        configuration = operator.config.model_dump()
        configuration["max_evaluations"] = 100
        operator.control(True)
        operator.configure(RuntimeConfig.model_validate(configuration))
        operator.control(False)
        return result

    monkeypatch.setattr(engine_module.work, "verify_result", verify_then_reconfigure)
    with pytest.raises(Conflict, match="configuration changed"):
        engine.review(record["id"], record["revision"], digest(record["result"]), True, "Reviewed constraints")
    assert Journal(journal.root).latest(record["id"]) == record


def test_recovery_detects_corruption_and_never_overwrites(journal: Journal, tmp_path: Path) -> None:
    Engine(journal).execute(journal.submit(mission("forecast"))["id"])
    before = journal.verify()
    archive = tmp_path / "private-backup.zip"
    journal.backup(archive)
    restored = Journal.restore(archive, tmp_path / "restored")
    assert restored.verify() == before
    assert restored.missions() == journal.missions()
    with pytest.raises(FileExistsError):
        Journal.restore(archive, tmp_path / "restored")
    with sqlite3.connect(restored.path) as cx:
        cx.execute("UPDATE events SET body=replace(body,'forecast','forgery') WHERE mission NOT LIKE '@%'")
    with pytest.raises(ValueError):
        restored.verify()


def test_journal_closes_connections_after_recovery_and_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connections: list[sqlite3.Connection] = []
    connect = sqlite3.connect

    def tracked_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    journal = Journal.initialize(tmp_path / "agent")
    journal.submit(mission("forecast"))
    before = journal.verify()
    journal.missions()
    with pytest.raises(RuntimeError, match="rollback"):
        with journal.transaction() as cx:
            cx.execute("DELETE FROM events")
            raise RuntimeError("rollback")
    assert journal.verify() == before
    archive = tmp_path / "backup.zip"
    journal.backup(archive)
    assert Journal.restore(archive, tmp_path / "restored").verify() == before
    assert not list(journal.root.glob("backup-*.sqlite3"))
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_configuration_tamper_fails_closed(journal: Journal) -> None:
    cfg_path = journal.root / "config.json"
    data = json.loads(cfg_path.read_bytes())
    data["max_evaluations"] = 9999
    cfg_path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        Engine(journal)


def test_research_rejects_fabricated_citations(journal: Journal) -> None:
    record = Engine(journal).execute(journal.submit(mission("research"))["id"])
    changed = copy.deepcopy(record["result"])
    changed["findings"][0]["quote"] = "Guaranteed billions in profit."
    with pytest.raises(ValueError):
        verify_result(mission("research"), changed)


def test_schedule_independent_validator_rejects_overlap(journal: Journal) -> None:
    record = Engine(journal).execute(journal.submit(mission("schedule"))["id"])
    changed = copy.deepcopy(record["result"])
    changed["operations"][1]["start"] = 0
    with pytest.raises(ValueError):
        verify_result(mission("schedule"), changed)


def test_forecast_selection_cannot_see_holdout(journal: Journal) -> None:
    first = mission("forecast")
    second = first.model_dump()
    second["work"]["observations"][-4:] = [1000.0, -1000.0, 500.0, -500.0]
    engine = Engine(journal)
    a = engine.execute(journal.submit(first)["id"])["result"]
    b = engine.execute(journal.submit(Mission.model_validate(second))["id"])["result"]
    assert a["training_scores"] == b["training_scores"] and a["policy"] == b["policy"]
    assert a["holdout_mae"] == 0 and b["holdout_mae"] > 0


def test_failed_provider_is_not_replaced_with_simulated_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = RuntimeConfig(llm_url="http://127.0.0.1:1/v1", llm_model="unavailable")
    journal = Journal.initialize(tmp_path / "agent", cfg)
    engine = Engine(journal)

    def unavailable(*args: object) -> None:
        raise ConnectionError("provider credential must not leak")

    monkeypatch.setattr("alpha_factory_v1.core.runtime.engine.synthesize", unavailable)
    ident = journal.submit(mission("research"))["id"]
    with pytest.raises(ConnectionError):
        engine.execute(ident)
    record = journal.latest(ident)
    assert record["state"] == "failed" and record["error"] == "ConnectionError"
    assert "provider credential" not in json.dumps(record)
    assert engine.recover(ident)["state"] == "queued"


def test_active_lease_cannot_be_recovered(journal: Journal) -> None:
    import time

    record = journal.submit(mission("research"))
    journal.transition(
        record["id"], record["revision"], {"queued"}, "running", fields={"lease_expires_ns": time.time_ns() + 10**12}
    )
    with pytest.raises(Conflict):
        Engine(journal).recover(record["id"])


def test_api_auth_origin_size_and_real_workflow(journal: Journal) -> None:
    token = (journal.root / "api.token").read_text()
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(create_app(journal)) as client:
        assert client.get("/api/status").status_code == 401
        page = client.get("/")
        assert page.status_code == 200 and token not in page.text
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        assert (
            client.post(
                "/api/control", json={"state": "paused"}, headers={**headers, "Origin": "https://attacker.example"}
            ).status_code
            == 403
        )
        assert client.post("/api/missions", content=b"x" * (512 * 1024 + 1), headers=headers).status_code == 413
        submitted = client.post("/api/missions", json=mission("schedule").model_dump(), headers=headers)
        assert submitted.status_code == 201
        ident = submitted.json()["id"]
        response = client.post(f"/api/missions/{ident}/execute", json={}, headers=headers)
        assert response.status_code == 200
        record = response.json()
        approval = client.post(
            f"/api/missions/{ident}/review",
            json={
                "revision": record["revision"],
                "result_hash": digest(record["result"]),
                "approve": True,
                "note": "Checked schedule.",
            },
            headers=headers,
        )
        assert approval.status_code == 200
        assert client.get(f"/api/missions/{ident}/export", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "update",
    [
        {"llm_url": "http://example.com/v1", "llm_model": "model", "allow_remote_llm": True},
        {"llm_url": "https://example.com/v1", "llm_model": "model"},
        {"llm_url": "http://127.0.0.1:8000/v1"},
        {"max_evaluations": 0},
    ],
)
def test_invalid_provider_or_budget_configuration(update: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        RuntimeConfig.model_validate(update)


def test_coding_requires_opt_in(journal: Journal) -> None:
    ident = journal.submit(mission("code"))["id"]
    with pytest.raises(ValueError, match="explicit operator"):
        Engine(journal).execute(ident)
    assert journal.latest(ident)["state"] == "failed"


def test_coding_never_uses_host_without_sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

    monkeypatch.setattr("shutil.which", lambda name: None)
    journal = Journal.initialize(tmp_path / "agent", RuntimeConfig(allow_code_execution=True))
    ident = journal.submit(mission("code"))["id"]
    with pytest.raises(SandboxUnavailable):
        Engine(journal).execute(ident)
    assert journal.latest(ident)["state"] == "failed"


def test_code_generation_withholds_benchmark_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.core.runtime.provider import generate_code

    def completion(payload: dict, config: RuntimeConfig) -> tuple[dict, dict]:
        prompt = json.loads(payload["messages"][1]["content"])
        assert set(prompt) == {"goal", "examples"}
        assert "heldout" not in json.dumps(payload)
        return {"code": "def solve(values): return sum(x*x for x in values)"}, {"mode": "explicit fixture"}

    monkeypatch.setattr("alpha_factory_v1.core.runtime.provider.complete_json", completion)
    code, _ = generate_code(mission("code"), RuntimeConfig(llm_url="http://127.0.0.1:9999/v1", llm_model="fixture"))
    assert code.startswith("def solve")


def test_portable_export_requires_trusted_identity_and_intact_content(journal: Journal) -> None:
    from alpha_factory_v1.core.runtime.engine import verify_export

    engine = Engine(journal)
    record = engine.execute(journal.submit(mission("allocation"))["id"])
    engine.review(record["id"], record["revision"], digest(record["result"]), True, "Verified")
    artifact = engine.export(record["id"])
    assert verify_export(artifact, journal.public)["valid"]
    with pytest.raises(ValueError):
        verify_export(artifact, "a" * 64)
    artifact["receipt"]["body"]["document"]["result"]["value"] += 1
    with pytest.raises(ValueError):
        verify_export(artifact, journal.public)


def test_export_portable_canonical_bytes_match_signed_record(journal: Journal) -> None:
    from alpha_factory_v1.core.runtime.engine import verify_export
    from alpha_factory_v1.core.runtime.store import canonical

    engine = Engine(journal)
    queued = journal.submit(mission("forecast"))
    record = engine.execute(queued["id"])
    engine.review(record["id"], record["revision"], digest(record["result"]), True, "Checked temporal split")
    artifact = engine.export(record["id"])
    receipt = artifact["receipt"]
    assert receipt["canonical_body"].encode() == canonical(receipt["body"])
    assert receipt["canonical_result"].encode() == canonical(receipt["body"]["document"]["result"])
    assert verify_export(artifact, journal.public)["valid"]
    receipt["canonical_body"] += " "
    with pytest.raises(ValueError, match="canonical body mismatch"):
        verify_export(artifact, journal.public)
