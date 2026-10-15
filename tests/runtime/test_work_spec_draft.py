# SPDX-License-Identifier: Apache-2.0
"""Unsigned draft validation never admits, signs, executes or mutates authority."""
import base64
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.ecosystem_operator import draft, operate, DRAFT_MAX_BYTES
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.work_spec import read_spec


def encoded(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def document(work=None):
    return {
        "market": "agijobsv0-jobregistry-v2",
        "executor": "alpha-native-v1",
        "mission_base64": encoded(
            json.dumps(
                {
                    "goal": "Évaluer les données fournies",
                    "work": work
                    or {
                        "kind": "research",
                        "sources": [{"id": "a", "title": "Source", "text": "Observed sample data."}],
                    },
                },
                ensure_ascii=False,
            )
        ),
    }


@pytest.mark.parametrize(
    "work",
    [
        {"kind": "research", "sources": [{"id": "a", "title": "Input", "text": "Observed input."}]},
        {"kind": "allocation", "budget": 10, "items": [{"id": "a", "cost": 5, "value": 8}]},
        {"kind": "schedule", "jobs": [{"id": "a", "operations": [{"machine": "mill", "duration": 2}]}]},
        {"kind": "forecast", "observations": list(range(16))},
    ],
)
def test_all_four_kinds_export_exact_reimportable_bytes(work):
    result = draft(document(work))
    raw = base64.b64decode(result["spec_base64"], validate=True)
    spec, digest = read_spec(raw)
    assert result["spec_hash"] == digest == "0x" + hashlib.sha256(raw).hexdigest()
    assert spec.mission.work.kind == work["kind"] and spec.mission.goal == "Évaluer les données fournies"
    assert result["unsigned"] is True and result["authority"] == []
    assert len(raw) == result["bytes"] and raw.endswith(b"\n")
    assert draft(document(work)) == result


@pytest.mark.parametrize("mutation", ["market", "executor", "authority", "duplicates", "nonfinite", "code"])
def test_unsupported_or_ambiguous_inputs_fail_closed(mutation):
    value = document()
    if mutation == "market":
        value["market"] = "manager-usdc"
    if mutation == "executor":
        value["executor"] = "fleet-linux-v1"
    if mutation == "authority":
        value["install_profile"] = True
    if mutation == "duplicates":
        value["mission_base64"] = encoded('{"goal":"one","goal":"two","work":{}}')
    if mutation == "nonfinite":
        value["mission_base64"] = encoded('{"goal":"one","work":{"kind":"forecast","observations":[NaN]}}')
    if mutation == "code":
        value = document({"kind": "code", "heldout": [{"args": [], "expected": 1}]})
    with pytest.raises(ValueError):
        draft(value)


def test_exact_output_boundary_and_utf8_input_bound():
    work = {
        "kind": "research",
        "sources": [{"id": str(i), "title": "Input", "text": "x" * 20000} for i in range(17)]
        + [{"id": "last", "title": "Input", "text": "x"}],
    }
    initial = draft(document(work))["bytes"]
    work["sources"][-1]["text"] += "x" * (DRAFT_MAX_BYTES - initial)
    assert draft(document(work))["bytes"] == DRAFT_MAX_BYTES
    work["sources"][-1]["text"] += "x"
    with pytest.raises(ValueError, match="bound"):
        draft(document(work))
    value = document()
    value["mission_base64"] = encoded("é" * (DRAFT_MAX_BYTES // 2 + 1))
    with pytest.raises(ValueError):
        draft(value)


def test_authenticated_exact_journal_draft_has_no_state_or_rpc_effect(tmp_path, monkeypatch):
    journal = Journal.initialize(tmp_path / "agent")
    from alpha_factory_v1.core.runtime import ecosystem

    monkeypatch.setattr(ecosystem, "ReadOnlyRPC", lambda *_: pytest.fail("draft contacted RPC"))
    before = journal.missions()
    with journal.transaction() as cx:
        count = cx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    with TestClient(create_app(journal)) as client:
        endpoint = "/api/ecosystem/draft"
        assert client.post(endpoint, json=document()).status_code == 401
        headers = {"Authorization": "Bearer " + (journal.root / "api.token").read_text().strip()}
        assert client.post(endpoint, json=document(), headers=headers).status_code == 409
        headers["X-AGIALPHA-Journal"] = journal.identity
        result = client.post(endpoint, json=document(), headers=headers)
        assert result.status_code == 200 and result.json() == operate(journal, "draft", document())
    assert journal.missions() == before
    with journal.transaction() as cx:
        assert cx.execute("SELECT COUNT(*) FROM events").fetchone()[0] == count


def escaped_work():
    return {
        "kind": "research",
        "sources": [{"id": str(i), "title": "Quoted input", "text": '\\"' * 10000} for i in range(8)],
    }


def test_escaped_mission_fits_authenticated_transport_without_raising_api_cap(tmp_path):
    value = document(escaped_work())
    mission = base64.b64decode(value["mission_base64"]).decode()
    assert len(mission.encode()) < DRAFT_MAX_BYTES
    assert len(json.dumps({"mission_json": mission}).encode()) > 512 * 1024
    assert len(json.dumps(value).encode()) < 512 * 1024
    journal = Journal.initialize(tmp_path / "agent")
    headers = {
        "Authorization": "Bearer " + (journal.root / "api.token").read_text().strip(),
        "X-AGIALPHA-Journal": journal.identity,
    }
    with TestClient(create_app(journal)) as client:
        result = client.post("/api/ecosystem/draft", json=value, headers=headers)
        assert result.status_code == 200
        raw = base64.b64decode(result.json()["spec_base64"])
        assert read_spec(raw)[0].mission.work.sources[0].text == '\\"' * 10000
        assert (
            client.post(
                "/api/ecosystem/draft",
                content=b" " * (512 * 1024 + 1),
                headers={**headers, "Content-Type": "application/json"},
            ).status_code
            == 413
        )


@pytest.mark.parametrize("payload", ["%%%", "eA=", "wA=="])
def test_malformed_base64_or_utf8_is_rejected(payload):
    value = document()
    value["mission_base64"] = payload
    with pytest.raises(ValueError):
        draft(value)
