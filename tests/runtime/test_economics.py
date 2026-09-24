# SPDX-License-Identifier: Apache-2.0
"""Receipt attacks, wallet proof, precision and finality, using explicit RPC fixtures."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
import pytest

from alpha_factory_v1.core.runtime.chain import AGIALPHA, TRANSFER, Economics, RPC, units
from alpha_factory_v1.core.runtime.models import ChainConfig, RuntimeConfig, Mission
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest

TX = "0x" + "ab" * 32
BLOCK = "0x" + "cd" * 32
AMOUNT = str(10**18 + 37)


@pytest.fixture
def economy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Economics, str, dict[str, Any]]:
    chain = ChainConfig(
        rpc_url="http://127.0.0.1:8545", chain_id=31337, token_code_sha256="a" * 64, confirmations=2, reinvest_bps=2500
    )
    journal = Journal.initialize(tmp_path / "agent", RuntimeConfig(chain=chain))
    account, payer = Account.create(), Account.create()
    economics = Economics(journal)
    challenge = economics.challenge()
    signature = Account.sign_message(encode_defunct(text=challenge["message"]), account.key).signature.hex()
    assert economics.bind(signature)["address"] == account.address.lower()
    with pytest.raises(Conflict):
        economics.bind(signature)
    engine = Engine(journal)
    mission = Mission(
        goal="Verify a sample result before invoicing",
        work={"kind": "allocation", "budget": 3, "items": [{"id": "A", "cost": 2, "value": 5}]},
    )
    record = engine.execute(journal.submit(mission)["id"])
    engine.review(record["id"], record["revision"], digest(record["result"]), True, "Verified constraints")
    snapshot = {
        "chain_id": 31337,
        "head": 10,
        "confirmed_block": 9,
        "block_hash": BLOCK,
        "token": AGIALPHA,
        "decimals": 18,
        "environment": "test_chain",
    }
    monkeypatch.setattr(RPC, "verify_token", lambda self: copy.deepcopy(snapshot))
    invoice = economics.invoice(record["id"], payer.address, AMOUNT)
    receipt = {
        "transactionHash": TX,
        "status": "0x1",
        "blockNumber": "0xb",
        "blockHash": BLOCK,
        "logs": [
            {
                "address": AGIALPHA,
                "logIndex": "0x0",
                "transactionHash": TX,
                "blockHash": BLOCK,
                "removed": False,
                "data": "0x" + hex(int(AMOUNT))[2:].rjust(64, "0"),
                "topics": [
                    TRANSFER,
                    "0x" + payer.address[2:].lower().rjust(64, "0"),
                    "0x" + account.address[2:].lower().rjust(64, "0"),
                ],
            }
        ],
    }
    snapshot.update(head=12, confirmed_block=11)

    def call(self: RPC, method: str, params: list[Any]) -> Any:
        if method == "eth_getTransactionReceipt":
            return copy.deepcopy(receipt)
        if method == "eth_getBlockByNumber":
            return {"hash": BLOCK, "number": "0xb"}
        raise AssertionError(method)

    monkeypatch.setattr(RPC, "call", call)
    assert invoice["issued_after_block"] == 10
    return economics, record["id"], receipt


def test_exact_receipt_reinvestment_and_no_double_credit(economy: tuple[Economics, str, dict[str, Any]]) -> None:
    economics, ident, _ = economy
    result = economics.settle(ident, TX, 0)
    assert result["amount_units"] == AMOUNT
    assert result["reinvestment_earmark_units"] == str(int(AMOUNT) * 2500 // 10000)
    assert result["reinvestment_executed"] is False and result["environment"] == "test_chain"
    with pytest.raises(Conflict):
        economics.settle(ident, TX, 0)
    assert Journal(economics.journal.root).verify()["valid"]


@pytest.mark.parametrize(
    "attack",
    [
        "failed",
        "old",
        "unconfirmed",
        "reorg",
        "removed",
        "token",
        "amount",
        "payer",
        "recipient",
        "transaction",
        "ambiguous",
    ],
)
def test_rejects_invalid_payment(economy: tuple[Economics, str, dict[str, Any]], attack: str) -> None:
    economics, ident, receipt = economy
    log = receipt["logs"][0]
    if attack == "failed":
        receipt["status"] = "0x0"
    elif attack == "old":
        receipt["blockNumber"] = "0xa"
    elif attack == "unconfirmed":
        receipt["blockNumber"] = "0xc"
    elif attack == "reorg":
        receipt["blockHash"] = "0x" + "ef" * 32
    elif attack == "removed":
        log["removed"] = True
    elif attack == "token":
        log["address"] = "0x" + "ff" * 20
    elif attack == "amount":
        log["data"] = "0x" + "0" * 63 + "1"
    elif attack == "payer":
        log["topics"][1] = "0x" + "0" * 64
    elif attack == "recipient":
        log["topics"][2] = "0x" + "0" * 64
    elif attack == "transaction":
        log["transactionHash"] = "0x" + "00" * 32
    elif attack == "ambiguous":
        receipt["logs"].append(copy.deepcopy(log))
    with pytest.raises(ValueError):
        economics.settle(ident, TX, 0)
    assert economics.journal.latest("@invoice:" + ident)["state"] == "awaiting_payment"


def test_pause_blocks_payment(economy: tuple[Economics, str, dict[str, Any]]) -> None:
    economics, ident, _ = economy
    economics.journal.control(True)
    with pytest.raises(Conflict):
        economics.settle(ident, TX, 0)


@pytest.mark.parametrize("operation", ["invoice", "settle"])
@pytest.mark.parametrize(
    "change",
    [
        {"rpc_url": "http://127.0.0.1:8546"},
        {"token_code_sha256": "b" * 64},
        {"confirmations": 3},
        {"reinvest_bps": 5000},
    ],
)
def test_configuration_change_during_rpc_cannot_commit(
    economy: tuple[Economics, str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    change: dict[str, Any],
) -> None:
    economics, ident, _ = economy
    journal = economics.journal
    original_invoice = journal.latest("@invoice:" + ident)
    if operation == "invoice":
        engine = Engine(journal)
        mission = Mission.model_validate(journal.latest(ident)["request"])
        record = engine.execute(journal.submit(mission)["id"])
        ident = record["id"]
        engine.review(ident, record["revision"], digest(record["result"]), True, "Verified constraints")
    original_verify = RPC.verify_token

    def verify_then_reconfigure(rpc: RPC) -> dict[str, Any]:
        snapshot = original_verify(rpc)
        operator = Journal(journal.root)
        configuration = operator.config.model_dump()
        configuration["chain"].update(change)
        operator.control(True)
        operator.configure(RuntimeConfig.model_validate(configuration))
        operator.control(False)
        return snapshot

    monkeypatch.setattr(RPC, "verify_token", verify_then_reconfigure)
    with pytest.raises(Conflict, match="configuration changed"):
        if operation == "invoice":
            economics.invoice(ident, original_invoice["payer"], AMOUNT)
        else:
            economics.settle(ident, TX, 0)
    current = Journal(journal.root)
    if operation == "invoice":
        with pytest.raises(KeyError):
            current.latest("@invoice:" + ident)
    else:
        assert current.latest("@invoice:" + ident) == original_invoice
        with pytest.raises(KeyError):
            current.latest(f"@receipt:31337:{TX}:0")
    assert current.verify()["valid"]
    # A fresh operator may deliberately retry under the new active policy.
    monkeypatch.setattr(RPC, "verify_token", original_verify)
    refreshed = Economics(current)
    result = (
        refreshed.invoice(ident, original_invoice["payer"], AMOUNT)
        if operation == "invoice"
        else refreshed.settle(ident, TX, 0)
    )
    assert result["config_hash"] == current.latest("@control")["config_hash"]


@pytest.mark.parametrize("value", ["0", "-1", "1.1", "1e18", str(2**256)])
def test_rejects_inexact_units(value: str) -> None:
    with pytest.raises(ValueError):
        units(value)


def test_mainnet_uses_finality_not_just_head(monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib

    config = ChainConfig(rpc_url="https://rpc.example", token_code_sha256=hashlib.sha256(b"\x01").hexdigest())
    calls = []

    def call(self: RPC, method: str, params: list[Any]) -> Any:
        calls.append((method, params))
        if method == "eth_chainId":
            return "0x1"
        if method == "eth_blockNumber":
            return "0x64"
        if method == "eth_getCode":
            return "0x01"
        if method == "eth_call":
            return "0x12"
        return {"number": "0x50", "hash": BLOCK}

    monkeypatch.setattr(RPC, "call", call)
    assert RPC(config).verify_token()["confirmed_block"] == 80
    assert ("eth_getCode", [AGIALPHA, "0x50"]) in calls
