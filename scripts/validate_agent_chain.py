#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise real local EVM transfers through the agent; never contact mainnet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak
import httpx

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from alpha_factory_v1.core.runtime.chain import AGIALPHA, Economics
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import ChainConfig, Mission, RuntimeConfig
from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest


def validate(root: Path) -> dict[str, Any]:
    """Start an ephemeral dev chain and prove receipt verification end to end."""
    contracts = root / "tests/contracts"
    artifact = json.loads((contracts / "artifacts/contracts/v2/mocks/MockAGI.sol/MockAGI.json").read_bytes())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="alpha-chain-validation-") as temp:
        folder = Path(temp)
        with (folder / "evm.log").open("w") as log:
            server = subprocess.Popen(
                [
                    shutil.which("node") or "node",
                    "node_modules/hardhat/internal/cli/cli.js",
                    "node",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=contracts,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                url = f"http://127.0.0.1:{port}"
                with httpx.Client(timeout=15, trust_env=False) as client:

                    def rpc(method: str, params: list[Any]) -> Any:
                        body = client.post(
                            url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
                        ).json()
                        if "error" in body:
                            raise RuntimeError(body["error"])
                        return body["result"]

                    for _ in range(100):
                        try:
                            if rpc("eth_chainId", []) == "0x7a69":
                                break
                        except httpx.ConnectError:
                            time.sleep(0.1)
                    else:
                        raise RuntimeError("local EVM startup failed")
                    payer = rpc("eth_accounts", [])[0]

                    def send(data: str, to: str | None = None) -> dict[str, Any]:
                        tx = {"from": payer, "data": data, "gas": "0x7a1200"}
                        if to:
                            tx["to"] = to
                        txid = rpc("eth_sendTransaction", [tx])
                        receipt = rpc("eth_getTransactionReceipt", [txid])
                        assert receipt["status"] == "0x1"
                        return receipt

                    deployed = send(artifact["bytecode"] + hex(18)[2:].rjust(64, "0"))
                    code = rpc("eth_getCode", [deployed["contractAddress"], "latest"])
                    rpc("hardhat_setCode", [AGIALPHA, code])
                    amount = 10**18 + 37
                    mint = (
                        "0x"
                        + keccak(text="mint(address,uint256)")[:4].hex()
                        + payer[2:].rjust(64, "0")
                        + hex(amount)[2:].rjust(64, "0")
                    )
                    send(mint, AGIALPHA)
                    rpc("evm_mine", [])
                    config = RuntimeConfig(
                        chain=ChainConfig(
                            rpc_url=url,
                            chain_id=31337,
                            token_code_sha256=hashlib.sha256(bytes.fromhex(code[2:])).hexdigest(),
                            confirmations=2,
                            reinvest_bps=2500,
                        )
                    )
                    journal = Journal.initialize(folder / "agent", config)
                    economics = Economics(journal)
                    wallet = Account.create()  # Ephemeral local-chain fixture; never funded on a public chain.
                    challenge = economics.challenge()
                    signature = Account.sign_message(
                        encode_defunct(text=challenge["message"]), wallet.key
                    ).signature.hex()
                    economics.bind(signature)
                    mission = Mission.model_validate_json((root / "examples/missions/allocation.json").read_bytes())
                    engine = Engine(journal)
                    record = engine.execute(journal.submit(mission)["id"])
                    engine.review(
                        record["id"], record["revision"], digest(record["result"]), True, "Local EVM acceptance test"
                    )
                    economics.invoice(record["id"], payer, str(amount))
                    transfer = "0xa9059cbb" + wallet.address[2:].lower().rjust(64, "0") + hex(amount)[2:].rjust(64, "0")
                    paid = send(transfer, AGIALPHA)
                    try:
                        economics.settle(record["id"], paid["transactionHash"], 0)
                        raise AssertionError("unconfirmed payment accepted")
                    except ValueError:
                        pass
                    rpc("evm_mine", [])
                    settlement = economics.settle(record["id"], paid["transactionHash"], 0)
                    balance = economics.balance()
                    assert balance["balance_units"] == str(amount)
                    assert settlement["reinvestment_earmark_units"] == str(amount // 4)
                    try:
                        Economics(Journal(journal.root)).settle(record["id"], paid["transactionHash"], 0)
                        raise AssertionError("duplicate payment accepted")
                    except Conflict:
                        pass
                    journal.backup(folder / "backup.zip")
                    restored = Journal.restore(folder / "backup.zip", folder / "restored")
                    assert restored.verify() == journal.verify()
                    return {
                        "environment": "ephemeral Hardhat EVM, chain 31337; no public-chain funds",
                        "token_contract": AGIALPHA,
                        "token_code_sha256": config.chain.token_code_sha256,
                        "wallet_proof": "real EIP-191 signature recovered",
                        "settlement": settlement,
                        "balance_units": balance["balance_units"],
                        "checks": [
                            "approved work",
                            "exact ERC20 amount",
                            "confirmation delay",
                            "replay rejected after restart",
                            "backup/restore preserves all events",
                        ],
                        "journal": journal.verify(),
                    }
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(Path(__file__).resolve().parents[1])
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "output": str(args.output)}))


if __name__ == "__main__":
    main()
