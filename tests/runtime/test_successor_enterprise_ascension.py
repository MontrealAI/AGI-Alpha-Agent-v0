# SPDX-License-Identifier: Apache-2.0
"""Enterprise journey integration: real fixed work, explicitly synthetic chain."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import test_successor_studio_operator as fixtures
from test_successor_ascension import AWARD_TX, CLOSE_TX, POST_TX, WORKER
from test_successor_studio import request

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor import enterprise, enterprise_ascension as journey
from alpha_factory_v1.core.runtime.successor.trust import sign_record


def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, ...]:
    incoming = request()
    incoming["cycle_id"] = incoming["project_id"]
    monkeypatch.setattr(fixtures, "request", lambda: deepcopy(incoming))
    _, journal, store, keys, rpc = fixtures.installed(tmp_path, monkeypatch)
    config = {
        "schema": enterprise.SCHEMA,
        "enterprise_id": incoming["project_id"],
        "name": "Bound enterprise",
        "work": incoming["work_spec"],
        "parent": None,
    }
    enterprise.activate(journal.root, config)
    return incoming, journal, store, keys, rpc


def test_real_work_full_journey_preserves_synthetic_scope_and_separate_acceptance(tmp_path, monkeypatch):
    incoming, journal, store, keys, rpc = setup(tmp_path, monkeypatch)
    args = (journal.root, incoming["project_id"], incoming["plan"], incoming["plan_index"])
    prepared = journey.prepare(*args)
    assert prepared["state"] == "prepared"
    assert prepared["chain_scope"] == "disposable-local-fixture"
    assert journey.prepare(*args)["revision"] == prepared["revision"]
    assert not store.read("institution")["grants"]
    sealed = journey.advance(*args, "seal", {"revision": prepared["revision"], "confirm": True})
    rpc.height = 3
    bound = journey.advance(
        *args,
        "bind",
        {
            "revision": sealed["revision"],
            "market_job_id": "1",
            "posting_tx": POST_TX,
            "assignment_tx": AWARD_TX,
            "acting_identity": WORKER,
            "expires_at": "2098-01-01T00:00:00Z",
        },
    )
    delivered = journey.advance(
        *args,
        "run",
        {"revision": bound["revision"], "authorization": fixtures.grant(keys, bound["record"]), "confirm": True},
    )
    assert delivered["state"] == "delivered"
    assert delivered["local_work_state"] == "planned"  # Never relabel another local run as commissioned work.
    assert delivered["settlement"] is None
    assert delivered["record"]["result"]["candidate_verdict"] == "FAIL"
    decision = delivered["record"]["review_requests"]["accept"]
    signed = sign_record(keys["local-controller"], decision["principal"], decision["domain"], decision["payload"])
    accepted = journey.advance(
        *args,
        "accept",
        {"revision": delivered["revision"], "acceptance": signed.model_dump(mode="json"), "confirm": True},
    )
    rpc.artifact_hash = delivered["record"]["result"]["artifact_keccak256"]
    rpc.close("paid")
    rpc.height = 4
    settled = journey.advance(*args, "settle", {"revision": accepted["revision"], "settlement_tx": CLOSE_TX})
    assert settled["settlement"]["settlement_status"] == "paid"
    assert settled["chain_scope"] == "disposable-local-fixture"
    assert settled["transactions_sent"] is False
    assert settled["authority_created"] is False
    assert store.read("institution")["resources"]["spent"] == {"calls": 1}
    assert journal.verify()["valid"]


def test_no_cross_enterprise_rebinding_or_implicit_installation(tmp_path, monkeypatch):
    incoming, journal, _, _, _ = setup(tmp_path, monkeypatch)
    args = (journal.root, incoming["project_id"], incoming["plan"], incoming["plan_index"])
    journey.prepare(*args)
    other = enterprise.new("numerical", "Unrelated")
    enterprise.activate(journal.root, other)
    with pytest.raises(KeyError):
        journey.show(journal.root, other["enterprise_id"], incoming["plan"], incoming["plan_index"])
    for action in ("install", "pair", "sign-grant", "sign-review", "approve", "unpause"):
        with pytest.raises(ValueError, match="Unsupported"):
            journey.advance(*args, action, {})


def test_identity_override_stale_revision_and_unconfirmed_phase_rejected(tmp_path, monkeypatch):
    incoming, journal, _, _, _ = setup(tmp_path, monkeypatch)
    args = (journal.root, incoming["project_id"], incoming["plan"], incoming["plan_index"])
    prepared = journey.prepare(*args)
    before = journal.verify()
    with pytest.raises(ValueError, match="caller-selected"):
        journey.advance(*args, "seal", {"request_digest": prepared["request_digest"]})
    with pytest.raises(Conflict, match="changed"):
        journey.advance(*args, "seal", {"revision": 999, "confirm": True})
    with pytest.raises(ValueError, match="confirmation"):
        journey.advance(*args, "seal", {"revision": prepared["revision"], "confirm": False})
    assert journal.verify() == before


def test_tampered_plan_and_wrong_grant_do_not_execute(tmp_path, monkeypatch):
    incoming, journal, store, keys, rpc = setup(tmp_path, monkeypatch)
    args = (journal.root, incoming["project_id"], incoming["plan"], incoming["plan_index"])
    changed = deepcopy(incoming["plan"])
    changed["totalBounty"] = "1"
    with pytest.raises(ValueError):
        journey.prepare(journal.root, incoming["project_id"], changed, incoming["plan_index"])
    prepared = journey.prepare(*args)
    sealed = journey.advance(*args, "seal", {"revision": prepared["revision"], "confirm": True})
    rpc.height = 3
    bound = journey.advance(
        *args,
        "bind",
        {
            "revision": sealed["revision"],
            "market_job_id": "1",
            "posting_tx": POST_TX,
            "assignment_tx": AWARD_TX,
            "acting_identity": WORKER,
            "expires_at": "2098-01-01T00:00:00Z",
        },
    )
    bad = sign_record(
        keys["local-producer"], "local-producer", "execution", bound["record"]["grant_request"]["payload"]
    ).model_dump(mode="json")
    with pytest.raises(ValueError):
        journey.advance(*args, "run", {"revision": bound["revision"], "authorization": bad, "confirm": True})
    assert journey.show(*args)["state"] == "bound"
    assert store.read("institution")["resources"]["spent"] == {}


def test_cli_show_is_read_only_and_uses_retained_identity(tmp_path, monkeypatch, capsys):
    import json

    incoming, journal, _, _, _ = setup(tmp_path, monkeypatch)
    args = (journal.root, incoming["project_id"], incoming["plan"], incoming["plan_index"])
    prepared = journey.prepare(*args)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(incoming["plan"]))
    before = journal.verify()
    assert (
        journey.main(
            [
                "--home",
                str(journal.root),
                "--enterprise-id",
                incoming["project_id"],
                "--plan",
                str(plan),
                "--index",
                str(incoming["plan_index"]),
                "show",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["request_digest"] == prepared["request_digest"]
    assert journal.verify() == before
