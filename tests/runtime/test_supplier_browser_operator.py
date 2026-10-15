# SPDX-License-Identifier: Apache-2.0
"""Exact authenticated operator requests cannot create implicit computer authority."""
import base64
import pytest
from fastapi.testclient import TestClient
from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime import supplier_browser_operator as operator
from test_supplier_browser_jobs import configured as supplier_configured

configured = supplier_configured


def test_operator_api_auth_identity_confirmation_and_closed_setup(configured):
    journal, raw, _ = configured
    client = TestClient(create_app(journal))
    auth = {"Authorization": "Bearer " + (journal.root / "api.token").read_text().strip()}
    exact = {**auth, "X-AGIALPHA-Journal": journal.identity}
    assert client.get("/api/supplier-browser/status").status_code == 401
    assert client.get("/api/supplier-browser/status", headers=auth).status_code == 200
    from test_ecosystem_jobs import WORKER, TX

    body = {
        "spec_base64": base64.b64encode(raw).decode(),
        "job_id": "1",
        "worker": WORKER,
        "assignment_tx": TX,
        "confirm": True,
    }
    assert client.post("/api/supplier-browser/admit", headers=auth, json=body).status_code == 409
    before = journal.verify()
    for value in [False, 1, "true", None]:
        assert (
            client.post("/api/supplier-browser/admit", headers=exact, json={**body, "confirm": value}).status_code
            == 422
        )
    assert journal.verify() == before
    record = client.post("/api/supplier-browser/admit", headers=exact, json=body).json()
    assert record["state"] == "admitted"
    permission = client.post("/api/supplier-browser/prepare", headers=exact, json={"binding": record["id"]}).json()
    assert permission["productionApproved"] is False
    assert journal.latest(record["id"])["state"] == "admitted"
    (journal.root / "supplier-browser-profile.json").unlink()
    status = client.get("/api/supplier-browser/status", headers=auth).json()
    assert status["profiles"]["executor"] is None and status["production_ready"] is False
    assert (
        client.post("/api/supplier-browser/show", headers=exact, json={"binding": record["id"]}).json()["state"]
        == "admitted"
    )


def test_operator_execute_defaults_to_production_boundary(configured, monkeypatch):
    journal, _, _ = configured
    captured = []

    def execute(*args, **kwargs):
        captured.append((args, kwargs))
        return {"state": "review"}

    monkeypatch.setattr(operator.adapter, "execute", execute)
    body = {"binding": "@supplier-browser:" + "a" * 64, "permit": "b" * 64, "confirm": True}
    assert operator.operate(journal, "execute", body)["state"] == "review"
    assert captured == [((journal, body["binding"], body["permit"]), {})]
    with pytest.raises(ValueError):
        operator.operate(journal, "execute", {**body, "_factory": "host-browser"})
