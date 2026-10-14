# SPDX-License-Identifier: Apache-2.0
"""Explicit market admission, exact artifacts and cross-market rejection."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
from typing import Any

import pytest
from eth_abi import encode

from alpha_factory_v1.core.runtime import ecosystem as eco
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest

ROOT = Path(__file__).resolve().parents[2]
SPEC = (ROOT / "examples/ecosystem/jobs-v0-work-spec.json").read_bytes()
WORKER = "0x" + "a" * 40
TX = "0x" + "1" * 64
BLOCK = "0x" + "2" * 64


def fixture() -> tuple[eco.JobsProfile, dict[str, Any]]:
    names = ["registry", "token", "stake", "validation", "identity", "configuration", "lifecycle", "settlement"]
    contracts = {
        name: {"address": "0x" + f"{i+1:040x}", "runtime_keccak256": "0x" + eco.keccak(b"code" + bytes([i])).hex()}
        for i, name in enumerate(names)
    }
    profile = eco.JobsProfile.model_validate(
        {
            "schema": "agialpha.jobs-v0-profile.v1",
            "backend": eco.BACKEND,
            "source_commit": "a" * 40,
            "rpc_url": "http://127.0.0.1:8547",
            "chain_id": 31337,
            "confirmations": 1,
            "scope": "disposable-local-fixture",
            "contracts": contracts,
        }
    )
    spec_hash = eco.read_spec(SPEC)[1]

    def address(name: str) -> str:
        return contracts[name]["address"]

    calls = {
        "version()": (["uint256"], [2]),
        "paused()": (["bool"], [False]),
        "implementationModules()": (["address[3]"], [[address(name) for name in names[5:]]]),
        "stakeManager()": (["address"], [address("stake")]),
        "validationModule()": (["address"], [address("validation")]),
        "identityRegistry()": (["address"], [address("identity")]),
        "token()": (["address"], [address("token")]),
        "decimals()": (["uint8"], [18]),
        "jobs(uint256)": (
            ["address", "address", "uint128", "uint96", "uint128", "bytes32", "bytes32", "bytes32", "uint256"],
            [
                "0x" + "b" * 40,
                WORKER,
                100,
                10,
                0,
                bytes(32),
                bytes(32),
                bytes.fromhex(spec_hash[2:]),
                2 | (2000 << 77) | (900 << 141),
            ],
        ),
    }
    state = {
        "calls": calls,
        "chain": "0x7a69",
        "code": {address(name): "0x" + (b"code" + bytes([i])).hex() for i, name in enumerate(names)},
        "block": {"number": "0xa", "hash": BLOCK, "timestamp": "0x3e8"},
        "receipt": {
            "transactionHash": TX,
            "blockNumber": "0x9",
            "blockHash": BLOCK,
            "status": "0x1",
            "from": WORKER,
            "to": address("registry"),
            "logs": [
                {
                    "address": address("registry"),
                    "removed": False,
                    "transactionHash": TX,
                    "blockNumber": "0x9",
                    "blockHash": BLOCK,
                    "topics": [
                        "0x" + eco.keccak(b"AgentAssigned(uint256,address,string)").hex(),
                        "0x" + (1).to_bytes(32).hex(),
                        "0x" + bytes(12).hex() + WORKER[2:],
                    ],
                    "data": "0x" + encode(["string"], ["worker"]).hex(),
                }
            ],
        },
    }
    return profile, state


def reader(state: dict[str, Any]):
    def read(method: str, params: list[Any]) -> Any:
        if method == "eth_chainId":
            return state["chain"]
        if method == "eth_blockNumber":
            return "0xa"
        if method == "eth_getCode":
            return state["code"][params[0]]
        if method == "eth_getTransactionReceipt":
            return state["receipt"]
        if method == "eth_getBlockByNumber":
            return {**state["block"], "number": params[0]}
        if method == "eth_call":
            for signature, (types, values) in state["calls"].items():
                if params[0]["data"].startswith("0x" + eco.keccak(signature.encode())[:4].hex()):
                    return "0x" + encode(types, values).hex()
        raise AssertionError((method, params))

    return read


def test_real_abi_assignment_and_state_mapping() -> None:
    profile, state = fixture()
    observed = eco.observe_assignment(profile, "1", WORKER, eco.read_spec(SPEC)[1], TX, rpc=reader(state))
    assert observed["state"] == 2 and observed["deadline"] == "2000" and observed["authority"] == "read-only"


@pytest.mark.parametrize(
    "mutation",
    [
        "chain",
        "code",
        "worker",
        "spec",
        "state",
        "expired",
        "failed",
        "removed",
        "duplicate",
        "emitter",
        "hash",
        "delegate",
        "paused",
        "token",
    ],
)
def test_adversarial_assignment_fails_closed(mutation: str) -> None:
    profile, state = fixture()
    job = state["calls"]["jobs(uint256)"][1]
    if mutation == "chain":
        state["chain"] = "0x1"
    if mutation == "code":
        state["code"][profile.contracts["registry"].address] = "0x00"
    if mutation == "worker":
        job[1] = "0x" + "c" * 40
    if mutation == "spec":
        job[7] = bytes(32)
    if mutation == "state":
        job[8] = (job[8] & ~7) | 4
    if mutation == "expired":
        state["block"]["timestamp"] = hex(2000)
    if mutation == "failed":
        state["receipt"]["status"] = "0x0"
    if mutation == "removed":
        state["receipt"]["logs"][0]["removed"] = True
    if mutation == "duplicate":
        state["receipt"]["logs"] *= 2
    if mutation == "emitter":
        state["receipt"]["logs"][0]["address"] = "0x" + "c" * 40
    if mutation == "hash":
        state["receipt"]["logs"][0]["blockHash"] = "0x" + "3" * 64
    if mutation == "delegate":
        state["calls"]["implementationModules()"][1][0][0] = "0x" + "c" * 40
    if mutation == "paused":
        state["calls"]["paused()"][1][0] = True
    if mutation == "token":
        state["calls"]["token()"][1][0] = "0x" + "c" * 40
    with pytest.raises(ValueError):
        eco.observe_assignment(profile, "1", WORKER, eco.read_spec(SPEC)[1], TX, rpc=reader(state))


def test_admit_execute_review_exact_delivery_and_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    profile, state = fixture()
    (journal.root / "jobs-v0-profile.json").write_text(profile.model_dump_json())
    monkeypatch.setattr(eco, "ReadOnlyRPC", lambda _url: reader(state))
    admitted = eco.admit(journal, SPEC, "1", WORKER, TX)
    before = journal.verify()
    assert eco.admit(journal, SPEC, "1", WORKER, TX)["replayed"]
    assert journal.verify() == before
    binding = admitted["binding"]["id"]
    result = eco.execute(journal, binding)
    assert result["state"] == "review"
    assert eco.execute(journal, binding) == result
    with pytest.raises(Conflict):
        eco.delivery(journal, binding)
    Engine(journal).review(
        result["id"],
        result["revision"],
        digest(result["result"]),
        True,
        "Disposable local test operator review; not independent marketplace approval",
    )
    packet = eco.delivery(journal, binding)
    assert packet["artifact_base64"] == eco.delivery(journal, binding)["artifact_base64"]
    raw = base64.b64decode(packet["artifact_base64"])
    checked = eco.verify_delivery(raw, journal.public, admitted["binding"]["observation"])
    assert checked["result_hash"] == packet["result_hash"]
    job = state["calls"]["jobs(uint256)"][1]
    job[8] = (job[8] & ~7) | 6
    job[6] = bytes.fromhex(packet["result_hash"][2:])
    assert eco.delivery(Journal(journal.root), binding)["artifact_base64"] == packet["artifact_base64"]
    job[6] = bytes(32)
    with pytest.raises(Conflict):
        eco.delivery(journal, binding)
    wrong = {**admitted["binding"]["observation"], "job_id": "2"}
    with pytest.raises(ValueError):
        eco.verify_delivery(raw, journal.public, wrong)
    altered = json.loads(raw)
    altered["body"]["authority"] = "spend"
    with pytest.raises(ValueError):
        eco.verify_delivery(json.dumps(altered).encode(), journal.public, admitted["binding"]["observation"])


def test_stateless_fleet_work_is_bounded_and_never_approves() -> None:
    from alpha_factory_v1.core.runtime.fleet_work import execute

    spec = json.loads(SPEC)
    with pytest.raises(ValueError):
        execute(SPEC)
    spec["executor"] = "fleet-linux-v1"
    raw = json.dumps(spec).encode()
    result = execute(raw)
    assert result["schema"] == "agialpha.fleet-work-result.v1"
    assert result["spec_hash"] == eco.read_spec(raw)[1]
    assert result["result_hash"] == digest(result["result"])
    assert result["authority"].startswith("computed-unreviewed")
    assert execute(raw) == result
    spec["mission"]["work"] = {"kind": "code", "candidate": "print('no')"}
    with pytest.raises(ValueError):
        execute(json.dumps(spec).encode())
