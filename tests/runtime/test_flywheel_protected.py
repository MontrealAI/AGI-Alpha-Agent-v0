# SPDX-License-Identifier: Apache-2.0
"""Synthetic signer/RPC conformance fixtures; never live ENS/model qualification."""

from __future__ import annotations
import copy
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak
from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.flywheel_access import (
    ENSAuthority,
    ENSPins,
    REGISTRAR,
    REGISTRY,
    WRAPPER,
    AccessRequest,
    ResourceAccess,
    ServiceIdentity,
    direct_name,
    namehash,
)
from alpha_factory_v1.core.runtime.successor.flywheel_capsules import (
    BRANCH,
    AlphaEvidence,
    CapsuleManifest,
    EvaluationPlan,
    Invocation,
    ProtectedLibrary,
)
from alpha_factory_v1.core.runtime.successor.flywheel_checkpoint import DurableCheckpoint
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge, CostLedger
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation import SelectionProgram, pilot_document, pilot_request
from alpha_factory_v1.core.runtime.successor.transformation_library import TransformationLibrary
from alpha_factory_v1.core.runtime.successor.trust import SignedEnvelope, TrustAnchor, TrustRegistry, sign_record

ZERO = "0" * 64
BETA, POLICY = "b" * 64, "c" * 64
CODE = "0x60006000"
PIN = hashlib.sha256(bytes.fromhex(CODE[2:])).hexdigest()


class FixtureRPC:
    """Fictional chain state with real ABI encoding, including wrapped ancestors."""

    def __init__(self, wallet: str, now: int) -> None:
        self.wallet, self.now = wallet.lower(), now
        self.block = {"number": "0x64", "hash": "0x" + "a1" * 32, "timestamp": hex(now)}
        self.owners = {
            namehash(name).hex(): self.wallet
            for name in ("agi.eth", "agent.agi.eth", "one.agent.agi.eth", "two.agent.agi.eth")
        }
        self.expiry = now + 86400
        self.wrapped_expiry = now + 3600
        self.wrapped = False
        self.change_code = False
        self.calls: list[str] = []

    def call(self, method: str, params: list[Any]) -> Any:
        self.calls.append(method)
        if method == "eth_chainId":
            return "0x1"
        if method == "eth_getBlockByNumber":
            return copy.deepcopy(self.block)
        if method == "eth_getCode":
            return "0x6001" if self.change_code else CODE if params[0] in {REGISTRY, WRAPPER, REGISTRAR} else "0x"
        if method == "eth_call":
            call = params[0]
            selector, argument = call["data"][2:10], call["data"][10:]
            if selector == keccak(text="nameExpires(uint256)")[:4].hex():
                return "0x" + format(self.expiry, "064x")
            if selector == keccak(text="owner(bytes32)")[:4].hex():
                owner = WRAPPER if self.wrapped else self.owners.get(argument, "0x" + "00" * 20)
                return "0x" + owner[2:].rjust(64, "0")
            if selector == keccak(text="getData(uint256)")[:4].hex():
                return "0x" + self.wallet[2:].rjust(64, "0") + format(0, "064x") + format(self.wrapped_expiry, "064x")
        raise AssertionError((method, params))


def readers(wallet: str) -> tuple[ENSAuthority, tuple[FixtureRPC, FixtureRPC]]:
    now = int(time.time())
    pair = (FixtureRPC(wallet, now), FixtureRPC(wallet, now))
    return ENSAuthority(pair, ENSPins(registry_sha256=PIN, wrapper_sha256=PIN, registrar_sha256=PIN)), pair


@pytest.mark.parametrize(
    "name",
    [
        "one.agent.agi.eth.evil",
        "a.b.agent.agi.eth",
        "agent.agi.eth",
        "one.club.agi.eth",
        "One.agent.agi.eth",
        "xn--one.agent.agi.eth",
        "-one.agent.agi.eth",
        "one..agent.agi.eth",
    ],
)
def test_direct_label_policy_refuses_unsupported_names(name: str) -> None:
    with pytest.raises(ValueError):
        direct_name(name)


def test_actual_abi_owner_and_wrapped_owner_checks() -> None:
    wallet = Account.create().address
    authority, pair = readers(wallet)
    assert namehash("eth").hex() == "93cdeb708b7545dc668eb9280176169d1c33cfd8ed6f04690a0bcc88a93fc4ae"
    for wrapped in (False, True):
        for rpc in pair:
            rpc.wrapped = wrapped
        proof = authority.verify("two.agent.agi.eth", wallet)
        assert proof["wallet"] == wallet.lower() and len(proof["owners"]) == 3
    assert all(not any("send" in call or "sign" in call for call in rpc.calls) for rpc in pair)


@pytest.mark.parametrize(
    "attack",
    [
        "owner",
        "stale",
        "future",
        "root-expired",
        "wrapper-expired",
        "code",
        "disagreement",
        "malformed-abi",
        "missing-chain",
    ],
)
def test_authority_refuses_unavailable_or_changed_chain(attack: str, monkeypatch: pytest.MonkeyPatch) -> None:
    wallet = Account.create().address
    authority, pair = readers(wallet)
    if attack == "owner":
        pair[1].owners[namehash("two.agent.agi.eth").hex()] = Account.create().address.lower()
    elif attack in {"stale", "future"}:
        for rpc in pair:
            rpc.block["timestamp"] = hex(rpc.now + (10 if attack == "future" else -121))
    elif attack == "root-expired":
        pair[0].expiry = pair[0].now
    elif attack == "wrapper-expired":
        pair[0].wrapped, pair[0].wrapped_expiry = True, pair[0].now
    elif attack == "code":
        pair[0].change_code = True
    elif attack == "disagreement":
        pair[1].block["hash"] = "0x" + "ff" * 32
    else:
        original = pair[0].call

        def broken(method: str, params: list[Any]) -> Any:
            if attack == "missing-chain" and method == "eth_chainId":
                raise TimeoutError("fictional reader unavailable")
            if method == "eth_call":
                return "0x01"
            return original(method, params)

        monkeypatch.setattr(pair[0], "call", broken)
    with pytest.raises((ValueError, TimeoutError)):
        authority.verify("two.agent.agi.eth", wallet)


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    roles = {
        "producer": {"producer"},
        "evaluator": {"verifier"},
        "validator": {"verifier"},
        "controller": {"controller"},
        "executor": {"execution"},
        "acceptor": {"acceptance"},
        "accountant": {"accounting"},
    }
    keys = {name: Ed25519PrivateKey.generate() for name in roles}
    trust = TrustRegistry(
        {
            name: TrustAnchor(
                key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset(roles[name])
            )
            for name, key in keys.items()
        }
    )
    journal = Journal.initialize(tmp_path / "fixture-service")
    costs = CostLedger(journal, trust)
    wallet = Account.create()
    origin_wallet = Account.create()
    from alpha_factory_v1.core.runtime.chain import Economics

    economics = Economics(journal)
    challenge = economics.challenge()
    economics.bind(Account.sign_message(encode_defunct(text=challenge["message"]), origin_wallet.key).signature.hex())
    authority, rpc = readers(wallet.address)
    for reader in rpc:
        reader.owners[namehash("one.agent.agi.eth").hex()] = origin_wallet.address.lower()
    access = ResourceAccess(journal, ServiceIdentity(origin="https://fixture-service.example"), authority)
    library = TransformationLibrary(journal, trust, producer="producer")
    checkpoint = DurableCheckpoint.initialize(tmp_path / "separate-custody.sqlite3", journal)
    service = ProtectedLibrary(library, costs, access, {"fixture-key": secrets_bytes()}, "fixture-key", checkpoint)
    return {
        "journal": journal,
        "costs": costs,
        "wallet": wallet,
        "origin_wallet": origin_wallet,
        "rpc": rpc,
        "access": access,
        "library": library,
        "service": service,
        "keys": keys,
        "trust": trust,
    }


def secrets_bytes() -> bytes:
    import secrets

    return secrets.token_bytes(32)


def signed(s: dict[str, Any], domain: str, role: str, record: Any, operation: str) -> SignedEnvelope:
    return sign_record(
        s["keys"][role],
        role,
        "flywheel-" + domain,
        {"journal_identity": s["journal"].identity, "operation_id": operation, "record": record},
    )


def account(s: dict[str, Any], action: str, record: Any, operation: str) -> None:
    s["costs"].apply(
        sign_record(
            s["keys"]["accountant"],
            "accountant",
            "flywheel-cost-command",
            {"journal_identity": s["journal"].identity, "operation_id": operation, "action": action, "record": record},
        )
    )


def paid_origin(s: dict[str, Any]) -> dict[str, Any]:
    journal = s["journal"]
    with journal.transaction() as cx:
        origin = journal.append(
            cx, "fixture-origin", {"state": "accepted", "request_hash": ZERO, "result": {"fixture": True}}
        )
    for category in sorted(CATEGORIES):
        record = Charge(
            activity_id="origin/" + category,
            mission_id="fixture-origin",
            bucket="A",
            category=category,
            accrued_micro_usd=1,
            paid_micro_usd=0,
            basis="attested",
            evidence_digest=ZERO,
            note="Synthetic category-completeness fixture",
        ).model_dump()
        account(s, "charge", record, category)
    account(
        s, "seal", {"mission_id": "fixture-origin", "evidence_digest": ZERO, "categories": sorted(CATEGORIES)}, "seal"
    )
    account(
        s,
        "capital",
        {
            "record_id": "fixture-funding",
            "mission_id": "fixture-origin",
            "amount_micro_usd": 10_000,
            "evidence_digest": ZERO,
        },
        "capital",
    )
    return origin


def retain(s: dict[str, Any]) -> str:
    origin = paid_origin(s)
    service = s["service"]
    service.configure(signed(s, "configure", "controller", {"beta_digest": BETA, "policy_digest": POLICY}, "configure"))
    program = SelectionProgram(representation="argument-graph", production="closure-search")
    manifest = CapsuleManifest(
        skill_id="bounded-selector",
        version=1,
        origin_mission=origin["id"],
        origin_record_digest=origin["digest"],
        origin_agent="one.agent.agi.eth",
        origin_wallet=s["origin_wallet"].address.lower(),
        content_digest=digest("flywheel-program", program),
        supported_scope="bounded-public-source-selection/v1",
        prerequisites=[],
        limitations="Synthetic protocol fixture; no live model or ENS qualification.",
        rights="cleared-for-authenticated-network",
        rights_evidence=ZERO,
        dependency_digests=[],
    )
    ident = digest("flywheel-manifest", manifest)
    assert (
        service.retain(manifest, program, signed(s, "candidate", "producer", {"manifest_digest": ident}, "retain"))
        == ident
    )
    return ident


def entry(s: dict[str, Any], ident: str) -> dict[str, Any]:
    return s["library"].snapshot()[BRANCH]["entries"][ident]


def evaluate(s: dict[str, Any], ident: str, saving: int = 20, correct: bool = True) -> str:
    service = s["service"]
    plan = EvaluationPlan(
        candidate_digest=ident,
        beta_digest=BETA,
        model_id="fictional-frontier-receipt-fixture",
        reasoning_mode="fixture",
        policy_digest=POLICY,
        matched_tools_digest=ZERO,
        resource_rules_digest=ZERO,
        recipient_capabilities_digest=ZERO,
        retention_cost_record="retention/" + ident,
        origin_input_digests=[ZERO],
        fresh_input_digests=["1" * 64, "2" * 64],
        planned_reuses=10,
        remaining_retention_micro_usd=1,
        prospective_basis="Synthetic conservative horizon assumption",
    )
    plan_signed = signed(s, "plan", "evaluator", plan.model_dump(), "plan")
    service.freeze(plan_signed)
    pairs: list[list[SignedEnvelope]] = [[], [], []]
    for input_digest in plan.fresh_input_digests:
        outputs = ["3" * 64, "4" * 64]
        for arm in range(2):
            receipt = {
                "candidate_digest": ident if arm == 0 else None,
                "input_digest": input_digest,
                "output_digest": outputs[arm],
                "beta_digest": BETA,
                "model_id": "fictional-frontier-receipt-fixture",
                "reasoning_mode": "fixture",
                "tools_digest": ZERO,
                "resource_rules_digest": ZERO,
                "provider_response_digest": ZERO,
                "billing_evidence_digest": ZERO,
                "actual_cost_micro_usd": 10 if arm == 0 else 30,
                "usage": {"fixture_tokens": 1},
                "started_at": int(time.time()),
                "finished_at": int(time.time()),
                "evidence_basis": "configured-executor-attestation",
            }
            pairs[arm].append(sign_record(s["keys"]["executor"], "executor", "flywheel-frontier-run", receipt))
        accepted = {
            "plan_digest": digest("flywheel-plan", plan_signed.model_dump()),
            "input_digest": input_digest,
            "candidate_output": outputs[0],
            "beta_output": outputs[1],
            "candidate_digest": ident,
            "candidate_correct": correct,
            "beta_correct": True,
            "evidence_digest": ZERO,
        }
        pairs[2].append(sign_record(s["keys"]["acceptor"], "acceptor", "flywheel-pair-acceptance", accepted))
    evidence = AlphaEvidence(
        plan_digest=digest("flywheel-plan", plan_signed.model_dump()),
        candidate_runs=pairs[0],
        beta_runs=pairs[1],
        acceptance=pairs[2],
        lower_net_saving_per_use_micro_usd=saving,
        uncertainty_basis="Synthetic protocol lower bound, not empirical uncertainty calibration",
        false_passes=0,
        false_rejections=0,
        abstentions=0,
        correlated_failure_analysis="Fixture signatures establish mechanics only",
    )
    for arm, receipts in enumerate(pairs[:2]):
        for index, receipt in enumerate(receipts):
            charge = Charge(
                activity_id=f"evaluation/{arm}/{index}",
                mission_id="retention/" + ident,
                bucket="B",
                category="model",
                accrued_micro_usd=receipt.payload["actual_cost_micro_usd"],
                paid_micro_usd=0,
                basis="attested",
                evidence_digest=digest("flywheel-frontier-run-record", receipt.model_dump()),
                note="Synthetic paired invocation accounting",
            )
            account(s, "charge", charge.model_dump(), f"eval-cost-{arm}-{index}")
    for category in sorted(CATEGORIES - {"model"}):
        charge = Charge(
            activity_id="retention/" + category,
            mission_id="retention/" + ident,
            bucket="B",
            category=category,
            accrued_micro_usd=0,
            paid_micro_usd=0,
            basis="attested",
            evidence_digest=ZERO,
            note="Synthetic explicit zero-cost category attestation",
        )
        account(s, "charge", charge.model_dump(), "retention-cost-" + category)
    account(
        s,
        "seal-retention",
        {"mission_id": "retention/" + ident, "evidence_digest": ZERO, "categories": sorted(CATEGORIES)},
        "retention-seal",
    )
    return service.evaluate(signed(s, "evidence", "evaluator", evidence.model_dump(), "evidence"))


def control(s: dict[str, Any], ident: str, action: str, operation: str | None = None) -> None:
    record = {
        "candidate_digest": ident,
        "previous_digest": digest("flywheel-entry", entry(s, ident)),
        "reason": "Synthetic protocol transition",
        "expires_at": int(time.time()) + 300,
    }
    s["service"].control(
        signed(s, action, "validator" if action == "validate" else "controller", record, operation or action), action
    )


def admitted(s: dict[str, Any]) -> str:
    ident = retain(s)
    assert evaluate(s, ident) == "assessed"
    control(s, ident, "validate")
    control(s, ident, "admit")
    return ident


def proof(s: dict[str, Any], ident: str, action: str, request_digest: str) -> AccessRequest:
    challenge = s["access"].challenge("two.agent.agi.eth", s["wallet"].address, ident, action, request_digest)
    signature = Account.sign_message(encode_defunct(text=challenge["message"]), s["wallet"].key).signature.hex()
    return AccessRequest(challenge_id=challenge["challenge_id"], signature=signature)


def test_no_plaintext_or_admission_bypass(setup: dict[str, Any]) -> None:
    s = setup
    ident = retain(s)
    current = entry(s, ident)
    assert current["state"] == "candidate" and "program" not in current
    assert "closure-search" not in s["journal"].path.read_bytes().decode(errors="replace")
    for action in ("validate", "admit"):
        with pytest.raises((Conflict, ValueError)):
            control(s, ident, action)
    assert entry(s, ident)["state"] == "candidate"


@pytest.mark.parametrize("saving,correct", [(0, True), (-1, True), (20, False)])
def test_correct_rejection_is_retained(setup: dict[str, Any], saving: int, correct: bool) -> None:
    s = setup
    ident = retain(s)
    assert evaluate(s, ident, saving, correct) == "rejected"
    with pytest.raises(Conflict):
        control(s, ident, "admit")
    assert entry(s, ident)["evidence"] is not None


def test_manifest_retrieval_proof_is_single_use_and_resource_bound(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    token = proof(s, ident, "discover", digest("flywheel-discover", {"candidate_digest": ident}))
    manifest = s["service"].manifest(ident, token)
    assert manifest["authorization"]["name"] == "two.agent.agi.eth"
    assert "ciphertext" not in manifest and "program" not in manifest
    with pytest.raises(Conflict):
        s["service"].manifest(ident, token)


def invocation() -> Invocation:
    document = pilot_document(confirmation=True).model_dump()
    document["title"] += " fresh peer case"
    document["claims"][0]["text"] += " independently fresh text"
    return Invocation(
        mission_id="fresh-peer",
        document=document,
        charter=pilot_request().charter,
        beta_digest=BETA,
        policy_digest=POLICY,
        prerequisite_digests=[],
        logical_limit=10_000,
        cost_cap_micro_usd=100,
    )


def test_actual_bounded_invocation_is_not_mislabeled_useful_reuse(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    request = invocation()
    token = proof(s, ident, "invoke", digest("flywheel-invocation", request))
    receipt = s["service"].invoke(ident, request, token)
    assert receipt["result"] and receipt["logical_units"] > 0
    assert receipt["successful_reuse"] is False and receipt["additional_value"] is None
    assert s["costs"].report()["available_funds"] is None
    assert s["costs"].snapshot()["charges"]["reuse/fresh-peer"]["bucket"] == "B"
    assert s["journal"].verify()["valid"]
    with pytest.raises(Conflict):
        s["service"].invoke(ident, request, token)


def test_failed_execution_is_costed_and_not_retried(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    request = invocation().model_copy(update={"logical_limit": 1})
    token = proof(s, ident, "invoke", digest("flywheel-invocation", request))
    receipt = s["service"].invoke(ident, request, token)
    assert receipt["status"] == "failed" and receipt["logical_units"] > 1
    assert s["costs"].report()["unknown_costs"]


@pytest.mark.parametrize("attack", ["changed-owner", "expired", "different-service", "changed-request", "wrong-signer"])
def test_proof_boundary_attacks(setup: dict[str, Any], attack: str) -> None:
    s = setup
    ident = admitted(s)
    request = invocation()
    token = proof(s, ident, "invoke", digest("flywheel-invocation", request))
    if attack == "changed-owner":
        for rpc in s["rpc"]:
            rpc.owners[namehash("two.agent.agi.eth").hex()] = Account.create().address.lower()
    elif attack == "expired":
        with s["journal"].transaction() as cx:
            key = "@flywheel-challenge:" + token.challenge_id
            record = s["journal"].document(s["journal"].latest(key, cx))
            record["payload"]["expires_at"] = int(time.time())
            s["journal"].append(cx, key, record)
    elif attack == "different-service":
        s["access"].service = ServiceIdentity(origin="https://another-service.example")
    elif attack == "changed-request":
        request = request.model_copy(update={"logical_limit": 500})
    else:
        token = token.model_copy(
            update={
                "signature": Account.sign_message(encode_defunct(text="wrong"), Account.create().key).signature.hex()
            }
        )
    with pytest.raises((Conflict, ValueError)):
        s["service"].invoke(ident, request, token)
    assert s["library"].snapshot()[BRANCH]["invocations"] == {}


def test_revocation_blocks_stale_proofs_and_cannot_be_resurrected(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    token = proof(s, ident, "discover", digest("flywheel-discover", {"candidate_digest": ident}))
    control(s, ident, "revoke")
    for action in ("admit", "validate"):
        with pytest.raises(Conflict):
            control(s, ident, action, "again-" + action)
    with pytest.raises(Conflict):
        s["service"].manifest(ident, token)


def test_beta_change_requires_fresh_evidence(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    s["service"].configure(
        signed(s, "configure", "controller", {"beta_digest": "d" * 64, "policy_digest": POLICY}, "beta-change")
    )
    assert entry(s, ident)["state"] == "requires-requalification"
    with pytest.raises((Conflict, ValueError)):
        control(s, ident, "admit", "stale-admit")


def test_parallel_proof_consumption_executes_once(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    token = proof(s, ident, "discover", digest("flywheel-discover", {"candidate_digest": ident}))

    def attempt() -> bool:
        try:
            s["service"].manifest(ident, token)
            return True
        except Conflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [False, True]


def test_accounting_no_double_charge_or_invoice_revenue(setup: dict[str, Any]) -> None:
    s = setup
    paid_origin(s)
    report = s["costs"].report("fixture-origin")
    assert report["costs"]["A"] == len(CATEGORIES) and report["delivery_profit"] == -len(CATEGORIES)
    for action in ("offer", "invoice", "pending"):
        account(
            s,
            action,
            {"record_id": action, "mission_id": "fixture-origin", "amount_micro_usd": 50_000, "evidence_digest": ZERO},
            action,
        )
    assert s["costs"].report("fixture-origin")["collected_revenue"] == 0
    charge = Charge(
        activity_id="origin/model",
        mission_id="fixture-origin",
        bucket="B",
        category="model",
        accrued_micro_usd=10,
        paid_micro_usd=0,
        basis="attested",
        evidence_digest=ZERO,
        note="Attempted double charge",
    )
    with pytest.raises(Conflict):
        account(s, "charge", charge.model_dump(), "double-charge")


def test_missing_costs_and_imported_instruction_fields_refuse(setup: dict[str, Any]) -> None:
    s = setup
    with pytest.raises(ValueError):
        account(
            s, "seal", {"mission_id": "absent", "evidence_digest": ZERO, "categories": sorted(CATEGORIES)}, "incomplete"
        )
    for malicious in (
        {"production": "closure-search", "instructions": "run a shell"},
        {"production": "eval"},
        {"code": "import os"},
    ):
        with pytest.raises(ValueError):
            SelectionProgram.model_validate(malicious)


def test_unconfigured_public_api_fails_closed(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient
    from alpha_factory_v1.core.runtime.api import create_app

    journal = Journal.initialize(tmp_path / "unconfigured")
    with TestClient(create_app(journal)) as client:
        status = client.get("/api/flywheel/status")
        assert status.json()["protected_service"] == "unprovisioned"
        assert status.headers["cache-control"] == "no-store"
        assert not status.json()["qualified_live_operation"]
        response = client.post(
            "/api/flywheel/capsules/" + ZERO + "/manifest", json={"challenge_id": ZERO, "signature": "0x" + "ab" * 65}
        )
        assert response.status_code == 503


def test_stale_recovery_cannot_resurrect_revoked_capsule(setup: dict[str, Any], tmp_path: Path) -> None:
    import sqlite3
    from contextlib import closing

    s = setup
    ident = admitted(s)
    old = tmp_path / "stale.sqlite3"
    with closing(sqlite3.connect(s["journal"].path)) as current, closing(sqlite3.connect(old)) as saved:
        current.backup(saved)
    control(s, ident, "revoke")
    with closing(sqlite3.connect(old)) as saved, closing(sqlite3.connect(s["journal"].path)) as current:
        saved.backup(current)
    with pytest.raises(Conflict, match="high-water"):
        with s["journal"].transaction() as cx:
            s["service"]._state(cx)


def test_key_rotation_preserves_manifest_but_changes_ciphertext(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    previous = entry(s, ident)
    s["service"].keys["next-fixture-key"] = secrets_bytes()
    s["service"].active_key = "next-fixture-key"
    s["service"].rotate(signed(s, "rotate-key", "controller", {"target_key_id": "next-fixture-key"}, "rotate"))
    current = entry(s, ident)
    assert current["manifest"] == previous["manifest"] and current["ciphertext"] != previous["ciphertext"]
    request = invocation()
    receipt = s["service"].invoke(ident, request, proof(s, ident, "invoke", digest("flywheel-invocation", request)))
    assert receipt["result"] is not None


def test_revoked_executor_cannot_support_future_access(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    token = proof(s, ident, "discover", digest("flywheel-discover", {"candidate_digest": ident}))
    s["trust"].revoke("executor")
    with pytest.raises(ValueError):
        s["service"].manifest(ident, token)


def test_reconciled_acceptance_required_for_successful_reuse(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    request = invocation()
    receipt = s["service"].invoke(ident, request, proof(s, ident, "invoke", digest("flywheel-invocation", request)))
    source = receipt["input_digest"]
    baseline = {
        "candidate_digest": None,
        "input_digest": source,
        "output_digest": ZERO,
        "beta_digest": BETA,
        "model_id": "fictional-frontier-receipt-fixture",
        "reasoning_mode": "fixture",
        "tools_digest": ZERO,
        "resource_rules_digest": ZERO,
        "provider_response_digest": ZERO,
        "billing_evidence_digest": ZERO,
        "actual_cost_micro_usd": 50,
        "usage": {"fixture_tokens": 1},
        "started_at": int(time.time()),
        "finished_at": int(time.time()),
        "evidence_basis": "configured-executor-attestation",
    }
    record = {
        "mission_id": request.mission_id,
        "receipt_digest": digest("flywheel-reuse-receipt", receipt),
        "beta_run": sign_record(s["keys"]["executor"], "executor", "flywheel-frontier-run", baseline).model_dump(),
        "candidate_correct": True,
        "beta_correct": True,
        "independent_tests_digest": ZERO,
        "residual_interventions_digest": ZERO,
        "limitations": "Synthetic qualification fixture; no real frontier trial",
    }
    approval = signed(s, "reuse-acceptance", "acceptor", record, "accept-reuse")
    with pytest.raises(ValueError, match="complete"):
        s["service"].accept_reuse(approval)
    for category in sorted(CATEGORIES):
        charge = Charge(
            activity_id="reuse/" + request.mission_id if category == "compute" else "reuse-check/" + category,
            mission_id=request.mission_id,
            bucket="B",
            category=category,
            accrued_micro_usd=1,
            paid_micro_usd=0,
            basis="attested",
            evidence_digest=ZERO,
            note="Synthetic all-resource reconciliation",
        )
        account(s, "resolve" if category == "compute" else "charge", charge.model_dump(), "reuse-cost-" + category)
    account(
        s,
        "seal-reuse",
        {"mission_id": request.mission_id, "evidence_digest": ZERO, "categories": sorted(CATEGORIES)},
        "reuse-seal",
    )
    result = s["service"].accept_reuse(approval)
    assert result["successful_reuse"] is True
    assert result["additional_value"] == 50 - len(CATEGORIES)
    assert s["costs"].report("fixture-origin")["costs"]["A"] == len(CATEGORIES)
    with pytest.raises(Conflict):
        s["service"].accept_reuse(approval)


def test_corrupt_private_capsule_fails_without_plaintext_and_records_attempt(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    with s["journal"].transaction() as cx:
        state, network = s["service"]._state(cx)
        network["entries"][ident]["ciphertext"] = "AA=="
        s["service"]._commit(cx, state)
    request = invocation()
    receipt = s["service"].invoke(ident, request, proof(s, ident, "invoke", digest("flywheel-invocation", request)))
    assert receipt["status"] == "failed" and receipt["error"] == "InvalidTag"
    assert receipt["result"] is None and s["costs"].report()["unknown_costs"]


def test_challenge_capacity_is_bounded_and_interrupted_flow_grants_nothing(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    for _ in range(5):
        s["access"].challenge("two.agent.agi.eth", s["wallet"].address, ident, "discover", ZERO)
    with pytest.raises(Conflict, match="rate"):
        s["access"].challenge("two.agent.agi.eth", s["wallet"].address, ident, "discover", ZERO)
    assert s["library"].snapshot()[BRANCH]["invocations"] == {}


def test_frontier_connector_reports_precise_missing_configuration(setup: dict[str, Any]) -> None:
    from alpha_factory_v1.core.runtime.successor.flywheel_frontier import FrontierConnector

    s = setup
    status = FrontierConnector(s["journal"], s["trust"], s["costs"]).status()
    assert status["ready_for_signed_permit"] is False and status["blockers"]
    assert status["actual_model_id_verified"] is False and status["billing_verified"] is False


def test_frontier_attempt_preserves_unknown_failure_cost_and_never_retries(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from alpha_factory_v1.core.runtime.successor.flywheel_frontier import FrontierConnector, FrontierPermit
    from alpha_factory_v1.core.runtime import provider
    from alpha_factory_v1.core.runtime.models import RuntimeConfig

    s = setup
    paid_origin(s)
    s["journal"].control(True)
    s["journal"].configure(RuntimeConfig(llm_url="http://127.0.0.1:9999/v1", llm_model="fictional-test-provider"))
    s["journal"].control(False)
    request = pilot_request()
    permit = FrontierPermit(
        operation_id="fixture-attempt",
        mission_id="fixture-model-delivery",
        bucket="A",
        model_id=s["journal"].config.llm_model,
        requested_reasoning_mode="fixture",
        request_digest=digest("flywheel-model-request", request),
        config_digest=digest("flywheel-model-config", s["journal"].config.model_dump()),
        tools_digest=digest("flywheel-model-tools", {"tools": [], "output": "selection-program/v1"}),
        quota_evidence_digest=ZERO,
        max_charge_micro_usd=10,
        expires_at=int(time.time()) + 300,
    )
    authorization = sign_record(
        s["keys"]["controller"],
        "controller",
        "flywheel-model-permit",
        {"journal_identity": s["journal"].identity, "permit": permit.model_dump()},
    )

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise TimeoutError("Synthetic lost response; no actual provider request")

    monkeypatch.setattr(provider, "complete_json", fail)
    connector = FrontierConnector(s["journal"], s["trust"], s["costs"])
    result = connector.run(request, authorization)
    assert result["state"] == "failed-or-uncertain" and result["usage"] is None
    assert s["costs"].snapshot()["charges"]["model/fixture-attempt"]["accrued_micro_usd"] is None
    with pytest.raises(Conflict):
        connector.run(request, authorization)


def test_existing_operator_parser_exposes_opt_in_commands() -> None:
    from alpha_factory_v1.core.runtime.cli import parser

    args = parser().parse_args(["serve"])
    assert args.flywheel_deployment is None
    args = parser().parse_args(
        ["flywheel", "--deployment", "/operator/provisioned.json", "--output", "/operator/status.json", "status"]
    )
    assert args.flywheel_action == "status"


def test_configured_api_uses_fresh_wallet_proof_without_plaintext_endpoint(setup: dict[str, Any]) -> None:
    from fastapi.testclient import TestClient
    from alpha_factory_v1.core.runtime.api import create_app

    s = setup
    ident = admitted(s)
    with TestClient(
        create_app(s["journal"], protected_library=s["service"]), base_url=s["access"].service.origin
    ) as client:
        challenge = client.post(
            "/api/flywheel/challenge",
            json={
                "name": "two.agent.agi.eth",
                "wallet": s["wallet"].address,
                "resource": ident,
                "action": "discover",
                "request_digest": digest("flywheel-discover", {"candidate_digest": ident}),
            },
        )
        assert challenge.status_code == 200
        data = challenge.json()
        signature = Account.sign_message(encode_defunct(text=data["message"]), s["wallet"].key).signature.hex()
        response = client.post(
            "/api/flywheel/capsules/" + ident + "/manifest",
            json={"challenge_id": data["challenge_id"], "signature": signature},
        )
        assert response.status_code == 200 and "ciphertext" not in response.json()
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/flywheel/capsules/" + ident).status_code == 404
        assert (
            client.post(
                "/api/flywheel/capsules/" + ident + "/manifest",
                json={"challenge_id": data["challenge_id"], "signature": signature},
            ).status_code
            == 409
        )


def test_authenticated_catalog_is_network_wide_and_rechecks_revocation(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    resource = s["service"].catalog_resource()
    token = proof(s, resource, "discover", digest("flywheel-catalog-request", {"resource": resource}))
    catalog = s["service"].catalog(token)
    assert [row["candidate_digest"] for row in catalog["manifests"]] == [ident]
    assert "ciphertext" not in str(catalog)
    control(s, ident, "revoke")
    token = proof(s, resource, "discover", digest("flywheel-catalog-request", {"resource": resource}))
    assert s["service"].catalog(token)["manifests"] == []


def test_dependency_revocation_invalidates_future_discovery(setup: dict[str, Any]) -> None:
    s = setup
    ident = admitted(s)
    with s["journal"].transaction() as cx:
        state, network = s["service"]._state(cx)
        dependent = copy.deepcopy(network["entries"][ident])
        dependent["manifest"]["skill_id"] = "dependent-fixture"
        dependent["manifest"]["dependency_digests"] = [ident]
        dependent_id = digest("flywheel-manifest", dependent["manifest"])
        network["entries"][dependent_id] = dependent
        network["active"]["dependent-fixture"] = dependent_id
        s["service"]._commit(cx, state)
    control(s, ident, "revoke")
    assert entry(s, dependent_id)["state"] == "requires-requalification"
    token = proof(s, dependent_id, "discover", digest("flywheel-discover", {"candidate_digest": dependent_id}))
    with pytest.raises(Conflict):
        s["service"].manifest(dependent_id, token)
