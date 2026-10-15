# SPDX-License-Identifier: Apache-2.0
"""Synthetic ABI and explicit actuator doubles exercise the separate Jobs browser boundary."""
import base64
import json
import pytest
from alpha_factory_v1.core.runtime import supplier_browser as adapter
from alpha_factory_v1.core.runtime.store import Journal, Conflict
from alpha_factory_v1.core.runtime.supplier_browser_spec import expected_report, read_spec
from test_supplier_browser_spec import specification, visible
from test_ecosystem_jobs import fixture, reader, WORKER, TX


class DoneAdvisor:
    def __init__(self, profile):
        self.identity = {"mode": profile.provider, "model": profile.model, "endpoint": profile.base_url}

    def next(self, task, observation):
        return {"done": True, "actions": [], "summary": "Controlled test double; inspect actual output"}


class FixtureComputer:
    text = ""
    fail_cleanup = False

    def __init__(self, *args):
        pass

    def observe(self):
        return {"png": base64.b64encode(b"CONTROLLED_SCREEN_DOUBLE").decode(), "text": self.text, "url": "about:blank"}

    def act(self, action):
        return self.observe()

    def close(self):
        if self.fail_cleanup:
            raise RuntimeError("cleanup test failure")


@pytest.fixture
def configured(tmp_path, monkeypatch):
    journal = Journal.initialize(tmp_path / "agent")
    profile, state = fixture()
    raw = specification().model_dump_json(by_alias=True).encode()
    state["calls"]["jobs(uint256)"][1][7] = bytes.fromhex(read_spec(raw)[1][2:])
    (journal.root / "jobs-v0-profile.json").write_text(profile.model_dump_json())
    executor = {
        "schema": "agialpha.supplier-browser-profile.v1",
        "scope": "synthetic-laboratory",
        "image": "sha256:" + "1" * 64,
        "provider": "responses",
        "model": "controlled-test-double",
        "base_url": "http://127.0.0.1:9999/v1",
        "key_env": "UNUSED_LAB_KEY",
    }
    (journal.root / "supplier-browser-profile.json").write_text(json.dumps(executor))
    monkeypatch.setattr(adapter.ecosystem, "ReadOnlyRPC", lambda url: reader(state))
    monkeypatch.setattr(adapter, "_advisor", DoneAdvisor)
    monkeypatch.setattr(FixtureComputer, "text", visible(expected_report(specification())))
    return journal, raw, state


def test_assignment_prepare_execute_separate_review_and_export(configured):
    journal, raw, state = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    assert adapter.admit(journal, raw, "1", WORKER, TX) == record
    permission = adapter.prepare(journal, record["id"])
    with pytest.raises(ValueError):
        adapter.execute(journal, record["id"], "wrong", _factory=FixtureComputer)
    result = adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert result["state"] == "review"
    with pytest.raises(Conflict):
        adapter.delivery(journal, record["id"])
    with pytest.raises(Conflict):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    with pytest.raises(Conflict):
        adapter.review(journal, record["id"], result["revision"], "wrong", True, "Reviewed")
    adapter.review(
        journal, record["id"], result["revision"], result["result_hash"], True, "Inspected controlled fixture"
    )
    first = adapter.delivery(journal, record["id"])
    assert first == adapter.delivery(journal, record["id"])
    exported = base64.b64decode(first["artifact_base64"])
    assert adapter.verify_delivery(exported, journal.public, record["observation"])["valid"]
    with pytest.raises(ValueError):
        adapter.verify_delivery(exported, "00" * 32, record["observation"])
    body = json.loads(exported)["body"]
    assert body["authority"] == [] and body["settlementApproved"] is False
    assert body["result"]["delivery"]["acceptance"]["accepted"]
    journal.verify()


@pytest.mark.parametrize("change", ["model", "image", "assignment", "profile"])
def test_substitution_after_prepare_refused(configured, change):
    journal, raw, state = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    if change in {"model", "image"}:
        path = journal.root / "supplier-browser-profile.json"
        value = json.loads(path.read_text())
        value[change] = "different-model" if change == "model" else "sha256:" + "2" * 64
        path.write_text(json.dumps(value))
    if change == "assignment":
        state["calls"]["jobs(uint256)"][1][1] = "0x" + "f" * 40
    if change == "profile":
        path = journal.root / "jobs-v0-profile.json"
        value = json.loads(path.read_text())
        value["confirmations"] = 2
        path.write_text(json.dumps(value))
    with pytest.raises((ValueError, Conflict)):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert journal.latest(record["id"])["state"] == "admitted"


def test_false_browser_success_is_retained_and_never_exported(configured, monkeypatch):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    monkeypatch.setattr(FixtureComputer, "text", "Supplier claimed success but no comparison exists")
    with pytest.raises(ValueError):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert journal.latest(record["id"])["state"] == "interrupted"
    with pytest.raises(Conflict):
        adapter.delivery(journal, record["id"])
    with pytest.raises(Conflict):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)


def test_profile_missing_fails_closed_without_provider_call(configured):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    (journal.root / "supplier-browser-profile.json").unlink()
    with pytest.raises(ValueError):
        adapter.prepare(journal, record["id"])


def test_cleanup_failure_stays_quarantined(configured, monkeypatch):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    monkeypatch.setattr(FixtureComputer, "fail_cleanup", True)
    with pytest.raises(RuntimeError):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert journal.latest(record["id"])["state"] == "quarantined"
    with pytest.raises(Conflict):
        adapter.delivery(journal, record["id"])


def test_stop_during_provider_response_preserves_revocation(configured, monkeypatch):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])

    class StopAdvisor(DoneAdvisor):
        def next(self, task, observation):
            adapter.stop(journal, record["id"])
            return super().next(task, observation)

    monkeypatch.setattr(adapter, "_advisor", StopAdvisor)
    with pytest.raises(Conflict):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert journal.latest(record["id"])["state"] == "stopped"
    guard = journal.latest("@successor-computer-task:" + permission["computer_commitment"])
    session = journal.latest("@successor-computer:" + guard["run_id"])
    assert session["state"] == "stopped" and session["cleanup"] == "VERIFIED"
    assert session["actions_reserved"] == 0


def test_stop_does_not_depend_on_still_valid_market_configuration(configured):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    (journal.root / "jobs-v0-profile.json").unlink()
    assert adapter.stop(journal, record["id"])["state"] == "stopped"


def test_explicit_reconciliation_requires_cleanup_and_rotates_permit(configured, monkeypatch):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    monkeypatch.setattr(FixtureComputer, "text", "missing comparison")
    with pytest.raises(ValueError):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    stopped = journal.latest(record["id"])
    with pytest.raises(ValueError):
        adapter.reconcile(journal, record["id"], stopped["revision"], False, "Inspected")
    fresh = adapter.reconcile(
        journal, record["id"], stopped["revision"], True, "Inspected screenshots and verified cleanup"
    )
    assert fresh["state"] == "admitted"
    new_permission = adapter.prepare(journal, record["id"])
    assert new_permission["permit"] != permission["permit"]
    with pytest.raises(ValueError):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    monkeypatch.setattr(FixtureComputer, "text", visible(expected_report(specification())))
    assert (
        adapter.execute(journal, record["id"], new_permission["permit"], _factory=FixtureComputer)["state"] == "review"
    )


def resign_wrapper(journal, value):
    from alpha_factory_v1.core.runtime.store import canonical, digest

    value["body"]["local_review"]["result_hash"] = digest(value["body"]["result"])
    value["sha256"] = digest(value["body"])
    value["signature"] = base64.b64encode(journal.key.sign(bytes.fromhex(value["sha256"]))).decode()
    return canonical(value)


def approved_delivery(journal, raw, job="1", tx=TX):
    record = adapter.admit(journal, raw, job, WORKER, tx)
    permission = adapter.prepare(journal, record["id"])
    result = adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    adapter.review(
        journal, record["id"], result["revision"], result["result_hash"], True, "Inspected exact synthetic output"
    )
    return record, permission, json.loads(base64.b64decode(adapter.delivery(journal, record["id"])["artifact_base64"]))


def test_same_spec_two_jobs_have_distinct_context_and_reject_receipt_swap(configured):
    journal, raw, state = configured
    first, first_permission, first_value = approved_delivery(journal, raw)
    tx = "0x" + "3" * 64
    state["receipt"]["transactionHash"] = tx
    state["receipt"]["logs"][0]["transactionHash"] = tx
    state["receipt"]["logs"][0]["topics"][1] = "0x" + (2).to_bytes(32).hex()
    second, second_permission, second_value = approved_delivery(journal, raw, "2", tx)
    assert first_permission["computer_commitment"] != second_permission["computer_commitment"]
    assert first["id"] != second["id"]
    assert adapter.verify_delivery(resign_wrapper(journal, second_value), journal.public, second["observation"])[
        "valid"
    ]
    second_value["body"]["result"]["computer_receipt"] = first_value["body"]["result"]["computer_receipt"]
    with pytest.raises(ValueError, match="permission"):
        adapter.verify_delivery(resign_wrapper(journal, second_value), journal.public, second["observation"])


@pytest.mark.parametrize("tamper", ["observed_text", "provider", "permission_extra", "context"])
def test_resigned_wrapper_cannot_substitute_signed_computer_evidence(configured, tamper):
    journal, raw, _ = configured
    record, _, value = approved_delivery(journal, raw)
    result = value["body"]["result"]
    if tamper == "observed_text":
        import hashlib

        result["visible_text"] = "Changed surrounding browser text\n" + result["visible_text"]
        result["observed_text_sha256"] = hashlib.sha256(result["visible_text"].encode()).hexdigest()
    if tamper == "provider":
        result["permission"]["executor_profile"]["model"] = "different-model"
    if tamper == "permission_extra":
        result["permission"]["automatic_settlement"] = True
    if tamper == "context":
        result["permission"]["execution_context"] = "a" * 64
    with pytest.raises(ValueError):
        adapter.verify_delivery(resign_wrapper(journal, value), journal.public, record["observation"])


def test_raw_whitespace_note_bound_is_enforced(configured):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    result = adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    with pytest.raises(ValueError):
        adapter.review(journal, record["id"], result["revision"], result["result_hash"], True, " " * 2000 + "x")


def test_concurrent_stop_while_provider_waits_prevents_completion(configured, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    entered, release = threading.Event(), threading.Event()

    class WaitingAdvisor(DoneAdvisor):
        def next(self, task, observation):
            entered.set()
            assert release.wait(5)
            return super().next(task, observation)

    monkeypatch.setattr(adapter, "_advisor", WaitingAdvisor)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(adapter.execute, journal, record["id"], permission["permit"], _factory=FixtureComputer)
        assert entered.wait(5)
        adapter.stop(journal, record["id"])
        release.set()
        with pytest.raises(Conflict):
            pending.result(timeout=5)
    assert journal.latest(record["id"])["state"] == "stopped"


def test_stop_before_computer_guard_prevents_actuator_start(configured, monkeypatch):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    original = adapter.computer.run_session

    def stop_then_run(*args, **kwargs):
        adapter.stop(journal, record["id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter.computer, "run_session", stop_then_run)
    with pytest.raises(Conflict):
        adapter.execute(
            journal, record["id"], permission["permit"], _factory=lambda *args: pytest.fail("revoked actuator started")
        )
    assert journal.latest(record["id"])["state"] == "stopped"


def test_observed_file_tamper_after_signed_receipt_is_rejected(configured, monkeypatch):
    from pathlib import Path

    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    original = adapter.computer.run_session

    def tamper_file(*args, **kwargs):
        result = original(*args, **kwargs)
        path = Path(result["output"]) / "visible-text.txt"
        path.write_bytes(b"Changed page context\n" + path.read_bytes())
        return result

    monkeypatch.setattr(adapter.computer, "run_session", tamper_file)
    with pytest.raises(Conflict, match="signed computer receipt"):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert journal.latest(record["id"])["state"] == "interrupted"


def test_concurrent_admission_retains_one_assignment_record(configured):
    from concurrent.futures import ThreadPoolExecutor

    journal, raw, _ = configured
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: adapter.admit(journal, raw, "1", WORKER, TX), range(8)))
    assert len({record["revision"] for record in records}) == 1
    assert len({record["id"] for record in records}) == 1
    journal.verify()


def test_prepare_interleaving_cannot_reuse_pre_reconciliation_permit(configured, monkeypatch):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    original = adapter.prepare
    permission = original(journal, record["id"])
    retained = {}

    def intervening_attempt(*args):
        monkeypatch.setattr(adapter, "prepare", original)
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
        stopped = adapter.stop(journal, record["id"])
        retained.update(adapter.reconcile(journal, record["id"], stopped["revision"], True, "Verified cleanup"))
        return permission

    monkeypatch.setattr(adapter, "prepare", intervening_attempt)
    with pytest.raises(Conflict):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert journal.latest(record["id"]) == retained


@pytest.mark.parametrize("next_state", ["admitted", "review", "quarantined"])
def test_stale_attempt_exception_cannot_overwrite_reconciled_attempt(configured, monkeypatch, next_state):
    journal, raw, _ = configured
    record = adapter.admit(journal, raw, "1", WORKER, TX)
    permission = adapter.prepare(journal, record["id"])
    original = adapter.computer.run_session
    retained = {}

    def interleave(*args, **kwargs):
        monkeypatch.setattr(adapter.computer, "run_session", original)
        stopped = adapter.stop(journal, record["id"])
        adapter.reconcile(journal, record["id"], stopped["revision"], True, "Stopped before actuator creation")
        if next_state != "admitted":
            fresh = adapter.prepare(journal, record["id"])
            if next_state == "quarantined":
                monkeypatch.setattr(FixtureComputer, "fail_cleanup", True)
                with pytest.raises(RuntimeError):
                    adapter.execute(journal, record["id"], fresh["permit"], _factory=FixtureComputer)
            else:
                adapter.execute(journal, record["id"], fresh["permit"], _factory=FixtureComputer)
        retained.update(journal.latest(record["id"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter.computer, "run_session", interleave)
    with pytest.raises(Conflict):
        adapter.execute(journal, record["id"], permission["permit"], _factory=FixtureComputer)
    assert retained["state"] == next_state
    assert journal.latest(record["id"]) == retained
    journal.verify()


@pytest.mark.parametrize("tamper", ["numeric_bool", "empty_note", "oversized_note", "extra_authority", "scope"])
def test_resigned_delivery_requires_exact_permission_and_review(configured, tamper):
    journal, raw, _ = configured
    record, _, value = approved_delivery(journal, raw)
    review = value["body"]["local_review"]
    if tamper == "numeric_bool":
        value["body"]["result"]["permission"]["productionApproved"] = 0
    elif tamper == "empty_note":
        review["note"] = "  "
    elif tamper == "oversized_note":
        review["note"] = "x" * 2001
    elif tamper == "extra_authority":
        review["settlementApproved"] = True
    else:
        review["scope"] = "marketplace settlement approval"
    with pytest.raises(ValueError):
        adapter.verify_delivery(resign_wrapper(journal, value), journal.public, record["observation"])
