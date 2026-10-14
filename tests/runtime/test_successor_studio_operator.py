# SPDX-License-Identifier: Apache-2.0
"""Authenticated local browser operations with actual work and explicitly synthetic RPC."""

from __future__ import annotations

import json
import secrets
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from fastapi.testclient import TestClient
from test_successor_ascension import AWARD_TX, CLOSE_TX, POST_TX, WORKER
from test_successor_studio import StudioRPC, request

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.store import Conflict, Journal, private_write
from alpha_factory_v1.core.runtime.successor import studio, studio_operator as operator, workbench
from alpha_factory_v1.core.runtime.successor.protocol import Institution, MissionConstitution, canonical
from alpha_factory_v1.core.runtime.successor.state import SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, local_principals, sign_record


def installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, ...]:
    incoming = request()
    proposed = studio.prepare_work(
        incoming,
        institution_id="institution",
        mission_id="mission",
        producer="local-producer",
        acceptance_owner="local-controller",
        valid_until="2099-01-01T00:00:00Z",
    )
    trust, keys = local_principals()
    anchors = dict(trust._anchors)
    anchors[WORKER] = TrustAnchor(
        keys["local-producer"].public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"worker"})
    )
    journal = Journal.initialize(tmp_path / "home")
    store = SuccessorStore(journal, TrustRegistry(anchors))
    store.create_institution(
        Institution(
            id="institution",
            controller="local-controller",
            constitution=MissionConstitution(
                mission_id="mission", owner="local-controller", objective="Test exact numerical work"
            ),
        ),
        {"calls": 10},
    )
    rpc = StudioRPC(incoming["plan"], incoming["plan_index"])
    monkeypatch.setattr(operator, "ReadOnlyRPC", lambda _url: rpc)
    trust_document = {
        "schema_version": 1,
        "principals": {
            principal: {
                "public_key": anchor.public_key,
                "roles": sorted(anchor.roles),
                "provenance": anchor.provenance,
                "independence_attestation": anchor.independence_attestation,
            }
            for principal, anchor in anchors.items()
        },
    }
    (journal.root / "successor-trust.json").write_bytes(canonical(trust_document))
    companion_jobs = [
        dict(proposed["job_contract"], job_id="companion-" + family, family=family)
        for family in ("constitution", "evidence", "formation", "challenge", "admission", "renewal")
    ]
    profile = {
        "project_id": incoming["project_id"],
        "cycle_id": incoming["cycle_id"],
        "plan_index": incoming["plan_index"],
        "institution_id": "institution",
        "mission_id": "mission",
        "producer": "local-producer",
        "acceptance_owner": "local-controller",
        "valid_until": "2099-01-01T00:00:00Z",
        "market_context": rpc.context.model_dump(mode="json"),
        "rpc_url": "http://127.0.0.1:8545",
        "companion_jobs": companion_jobs,
        "edges": [],
    }
    (journal.root / "studio-operator.json").write_bytes(
        canonical(
            {
                "schema": "agialpha.ascension.studio-operator.v1",
                "profiles": [profile],
            }
        )
    )
    return incoming, journal, store, keys, rpc


def phase(record: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"request_digest": record["request_digest"], "revision": record["revision"], **extra}


def bound_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, ...]:
    incoming, journal, store, keys, rpc = installed(tmp_path, monkeypatch)
    prepared = operator.operate(journal, "prepare", {"request": incoming})
    sealed = operator.operate(journal, "seal", phase(prepared, confirm=True))
    rpc.height = 3
    bound = operator.operate(
        journal,
        "bind",
        phase(
            sealed,
            market_job_id="1",
            posting_tx=POST_TX,
            assignment_tx=AWARD_TX,
            acting_identity=WORKER,
            expires_at="2098-01-01T00:00:00Z",
        ),
    )
    return incoming, journal, store, keys, rpc, bound


def grant(keys: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return sign_record(
        keys["local-controller"], "local-controller", "execution", record["grant_request"]["payload"]
    ).model_dump(mode="json")


def test_unconfigured_api_retains_auth_origin_host_and_no_implicit_trust(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    token = (journal.root / "api.token").read_text()
    before = journal.verify()
    with TestClient(create_app(journal)) as client:
        assert client.get("/api/ascension-studio/status").status_code == 401
        assert client.get("/ascension-studio", headers={"Host": "hostile.example"}).status_code == 400
        page = client.get("/ascension-studio")
        assert page.status_code == 200 and token not in page.text
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        assert client.get("/ascension-studio.js").status_code == 200
        assert client.get("/ascension-studio-setup").status_code == 200
        client.headers["Authorization"] = "Bearer " + token
        assert client.get("/api/ascension-studio/status").json()["configured"] is False
        blocked = client.post(
            "/api/ascension-studio/prepare", json={"request": {}}, headers={"Origin": "https://hostile.example"}
        )
        assert blocked.status_code == 403
        assert client.post("/api/ascension-studio/prepare", json={"request": {"keys": {}}}).status_code == 422
    assert journal.verify() == before
    assert not (journal.root / "successor-trust.json").exists()


def test_browser_api_full_cycle_preserves_negative_result_and_separate_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming, journal, store, keys, rpc = installed(tmp_path, monkeypatch)
    with TestClient(create_app(journal)) as client:
        client.headers["Authorization"] = "Bearer " + (journal.root / "api.token").read_text()
        assert client.get("/api/ascension-studio/status").json()["configured"]

        def post(action: str, body: dict[str, Any]) -> dict[str, Any]:
            response = client.post("/api/ascension-studio/" + action, json=body)
            assert response.status_code == 200, response.text
            return response.json()

        prepared = post("import", {"request_json": json.dumps(incoming)})
        assert prepared["state"] == "prepared" and not store.read("institution")["grants"]
        assert post("prepare", {"request": incoming})["revision"] == prepared["revision"]
        sealed = post("seal", phase(prepared, confirm=True))
        rpc.height = 3
        bound = post(
            "bind",
            phase(
                sealed,
                market_job_id="1",
                posting_tx=POST_TX,
                assignment_tx=AWARD_TX,
                acting_identity=WORKER,
                expires_at="2098-01-01T00:00:00Z",
            ),
        )
        assert "signature" not in bound["grant_request"]
        assert store.read("institution")["resources"]["reserved"] == {}
        bad = sign_record(
            keys["local-producer"], "local-producer", "execution", bound["grant_request"]["payload"]
        ).model_dump(mode="json")
        assert (
            client.post("/api/ascension-studio/run", json=phase(bound, authorization=bad, confirm=True)).status_code
            == 422
        )
        delivered = post("run", phase(bound, authorization=grant(keys, bound), confirm=True))
        assert delivered["state"] == "delivered" and delivered["result"]["candidate_verdict"] == "FAIL"
        assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
        exported = client.get("/api/ascension-studio/work/" + bound["request_digest"] + "/export").json()
        assert exported == delivered["result"] and exported["schema"] == studio.RESULT_SCHEMA
        decision = delivered["review_requests"]["accept"]
        acceptance = sign_record(
            keys["local-controller"], decision["principal"], decision["domain"], decision["payload"]
        ).model_dump(mode="json")
        accepted = post("accept", phase(delivered, acceptance=acceptance, confirm=True))
        assert accepted["state"] == "delivered" and accepted["local_acceptance"]["payload"]["accepted"]
        assert store.read("institution")["resources"]["reserved"] == {"calls": 0}
        rpc.artifact_hash = delivered["result"]["artifact_keccak256"]
        rpc.close("paid")
        rpc.height = 4
        settled = post("settle", phase(accepted, settlement_tx=CLOSE_TX))
        assert settled["settlement"]["settlement_status"] == "paid"
        assert settled["settlement"]["candidate_verdict"] == "FAIL"
        history = client.get("/api/ascension-studio/work/" + bound["request_digest"] + "/settlement").json()
        assert history["schema"] == "agialpha.ascension.journal-settlement.v1"
        assert history["settlement"] == settled["settlement"]
        assert (
            client.post(
                "/api/ascension-studio/run", json=phase(settled, authorization=grant(keys, bound), confirm=True)
            ).status_code
            == 409
        )
    assert store.read("institution")["resources"]["spent"] == {"calls": 1}
    assert not store.read("institution")["admissions"] and journal.verify()["valid"]


def test_import_rejects_duplicate_keys_hidden_rpc_and_stale_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    incoming, journal, _, _, _ = installed(tmp_path, monkeypatch)
    original_config = (journal.root / "studio-operator.json").read_bytes()
    before = journal.verify()
    duplicate = '{"schema":"bad",' + json.dumps(incoming)[1:]
    with pytest.raises(ValueError, match="duplicate"):
        operator.operate(journal, "import", {"request_json": duplicate})
    malicious = deepcopy(incoming)
    malicious["rpc_url"] = "http://169.254.169.254/latest/meta-data"
    with pytest.raises(ValueError, match="unexpected"):
        operator.operate(journal, "prepare", {"request": malicious})
    assert journal.verify() == before
    prepared = operator.operate(journal, "prepare", {"request": incoming})
    with pytest.raises(ValueError, match="confirmation"):
        operator.operate(journal, "seal", phase(prepared, confirm=False))
    with pytest.raises(Conflict, match="revision"):
        operator.operate(journal, "seal", {**phase(prepared, confirm=True), "revision": 1})
    assert (journal.root / "studio-operator.json").read_bytes() == original_config


def test_completed_native_result_recovery_does_not_require_current_trust_or_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming, journal, _, keys, _, bound = bound_runtime(tmp_path, monkeypatch)
    transition = journal.transition

    def lost_response(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if len(args) > 3 and args[3] == "delivered":
            raise RuntimeError("simulated process loss before browser record updates")
        return transition(*args, **kwargs)

    monkeypatch.setattr(journal, "transition", lost_response)
    with pytest.raises(RuntimeError, match="simulated"):
        operator.operate(journal, "run", phase(bound, authorization=grant(keys, bound), confirm=True))
    running = operator.show(journal, bound["request_digest"])
    assert running["state"] == "running"
    monkeypatch.setattr(journal, "transition", transition)
    (journal.root / "studio-operator.json").unlink()
    (journal.root / "successor-trust.json").unlink()
    result = operator.export(journal, bound["request_digest"])
    assert studio.verify_work_result(incoming, result, public_key=journal.public)
    recovered = operator.operate(journal, "recover", phase(running))
    assert recovered["state"] == "delivered" and recovered["result"] == result
    assert operator.export(journal, bound["request_digest"]) == result


def test_disk_trust_revocation_is_checked_at_actual_worker_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, journal, store, keys, _, bound = bound_runtime(tmp_path, monkeypatch)
    invoke = workbench.invoke

    def revoke(request: dict[str, Any], checkpoint: Any = lambda: None) -> dict[str, Any]:
        if request.get("operation") == "run":
            path = journal.root / "successor-trust.json"
            trust = json.loads(path.read_bytes())
            del trust["principals"][WORKER]
            path.write_bytes(canonical(trust))
        return invoke(request, checkpoint)

    monkeypatch.setattr(workbench, "invoke", revoke)
    with pytest.raises(ValueError, match="failure retained") as failure:
        operator.operate(journal, "run", phase(bound, authorization=grant(keys, bound), confirm=True))
    assert isinstance(failure.value.__cause__, Conflict)
    assert operator.show(journal, bound["request_digest"])["state"] == "interrupted"
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
    with pytest.raises(Conflict, match="completed Studio output"):
        operator.export(journal, bound["request_digest"])


def test_second_profile_cannot_rebind_first_request_and_does_not_disable_its_seal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming, journal, _, _, _ = installed(tmp_path, monkeypatch)
    prepared = operator.operate(journal, "prepare", {"request": incoming})
    path = journal.root / "studio-operator.json"
    config = json.loads(path.read_bytes())
    second = deepcopy(config["profiles"][0])
    second["cycle_id"] = "06a44b28-fc8e-431f-8a99-912ba1af8d90"
    second["market_context"]["seed_id"] = "2"
    config["profiles"].append(second)
    path.write_bytes(canonical(config))
    sealed = operator.operate(journal, "seal", phase(prepared, confirm=True))
    assert sealed["market_context"]["seed_id"] == "1"
    assert sealed["seal"]["body"]["market_context"]["seed_id"] == "1"


def install_template(journal: Journal, keys: dict[str, Any], rpc: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """Explicit test operator provisions keys and separate credentials out of band."""
    (journal.root / "studio-operator.json").unlink()
    (journal.root / "studio-approval").mkdir(mode=0o700)
    tokens, signers = {}, []
    for principal in ("local-controller", "local-verifier"):
        tokens[principal] = secrets.token_urlsafe(32)
        private_write(
            journal.root / (principal + ".key"),
            keys[principal].private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
        )
        private_write(journal.root / operator.approval_slot(principal), tokens[principal].encode())
        signers.append(
            {
                "principal": principal,
                "key_file": principal + ".key",
                "approval_token_file": operator.approval_slot(principal),
            }
        )
    template = {
        "template_id": "bounded-test",
        "controller": "local-controller",
        "producer": "local-producer",
        "acceptance_owner": "local-verifier",
        "valid_until": "2099-01-01T00:00:00Z",
        "market_context": rpc.context.model_dump(mode="json"),
        "rpc_url": "http://127.0.0.1:8545",
        "max_calls": 7,
    }
    return {"template": template, "signers": signers, "confirm": True}, tokens


def test_first_install_pair_and_separate_local_role_approvals_need_no_handwritten_work_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming, journal, _, keys, rpc = installed(tmp_path, monkeypatch)
    install, tokens = install_template(journal, keys, rpc)
    assert operator.status(journal)["setup_roles"]
    assert operator.operate(journal, "install", install)["configured"]
    with pytest.raises(Conflict, match="overwrite"):
        operator.operate(journal, "install", install)
    prepared = operator.operate(
        journal,
        "pair",
        {"request_json": json.dumps(incoming), "template_id": "bounded-test", "seed_id": "1", "confirm": True},
    )
    assert prepared["prepared"]["job_contract"]["institution_id"] != "institution"
    assert len(prepared["graph"]["jobs"]) == 7
    assert prepared["prepared"]["active_authority"] == []
    assert not (journal.root / "studio-operator.json").read_text().find('"profiles":[]') == -1
    sealed = operator.operate(journal, "seal", phase(prepared, confirm=True))
    rpc.height = 3
    bound = operator.operate(
        journal,
        "bind",
        phase(
            sealed,
            market_job_id="1",
            posting_tx=POST_TX,
            assignment_tx=AWARD_TX,
            acting_identity=WORKER,
            expires_at="2098-01-01T00:00:00Z",
        ),
    )
    with pytest.raises(ValueError, match="invalid"):
        operator.operate(journal, "sign-grant", phase(bound, approval_token=tokens["local-verifier"], confirm=True))
    signed = operator.operate(
        journal, "sign-grant", phase(bound, approval_token=tokens["local-controller"], confirm=True)
    )
    assert signed["state"] == "bound" and "result" not in signed
    delivered = operator.operate(journal, "run-signed", phase(signed, confirm=True))
    assert delivered["result"]["candidate_verdict"] == "FAIL"
    with pytest.raises(ValueError, match="invalid"):
        operator.operate(
            journal,
            "sign-review",
            phase(delivered, approval_token=tokens["local-controller"], decision="accept", confirm=True),
        )
    accepted = operator.operate(
        journal,
        "sign-review",
        phase(delivered, approval_token=tokens["local-verifier"], decision="reject", confirm=True),
    )
    assert accepted["local_acceptance"]["payload"]["accepted"] is False
    assert all(token not in json.dumps(accepted) for token in tokens.values())
    assert operator.export(journal, signed["request_digest"])["candidate_verdict"] == "FAIL"


@pytest.mark.parametrize(
    "path", ["config.json", "api.token", "api.token/", "../api.token", "studio-approval/known.token"]
)
def test_signer_cannot_use_known_or_arbitrary_private_file_as_role_approval(path: str) -> None:
    with pytest.raises(ValueError):
        operator.OperatorSigner(principal="local-controller", key_file="role.key", approval_token_file=path)


def test_signed_file_duplicate_keys_rejected_before_grant_or_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, journal, _, keys, _, bound = bound_runtime(tmp_path, monkeypatch)
    signed = json.dumps(grant(keys, bound))
    ambiguous = '{"principal":"attacker",' + signed[1:]
    before = journal.verify()
    with pytest.raises(ValueError, match="duplicate"):
        operator.operate(journal, "run-import", phase(bound, authorization_json=ambiguous, confirm=True))
    assert journal.verify() == before
