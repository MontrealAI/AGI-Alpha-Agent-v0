# SPDX-License-Identifier: Apache-2.0
"""Wallet identity and confirmed $AGIALPHA receipts, without private wallet keys.

No network call is made until the operator configures an RPC. Token balances,
receipt evidence and local reinvestment earmarks are distinct from simulated
governance stakes in the original demos. No funds are sent by this module.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from typing import Any

import httpx

from .models import ChainConfig
from .store import Conflict, Journal

AGIALPHA = "0xa61a3b3a130a9c20768eebf97e21515a6046a1fa"
DECIMALS = 18
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def address(value: str) -> str:
    """Normalize an exact, nonzero Ethereum address."""
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", value) or int(value[2:], 16) == 0:
        raise ValueError("invalid or zero wallet address")
    return value.lower()


def units(value: str) -> int:
    """Parse token base units without floating-point rounding."""
    if not re.fullmatch(r"[1-9][0-9]{0,77}", value):
        raise ValueError("amount must be a positive integer string of token base units")
    amount = int(value)
    if amount >= 2**256:
        raise ValueError("amount exceeds uint256")
    return amount


class RPC:
    """Bounded JSON-RPC reads against the configured chain."""

    def __init__(self, config: ChainConfig) -> None:
        self.config = config

    def call(self, method: str, params: list[Any]) -> Any:
        """Execute only explicitly supported read operations, never broadcasts."""
        allowed = {
            "eth_chainId",
            "eth_getCode",
            "eth_call",
            "eth_blockNumber",
            "eth_getTransactionReceipt",
            "eth_getBlockByNumber",
        }
        if method not in allowed:
            raise ValueError("RPC method is not a supported read")
        local = httpx.URL(self.config.rpc_url).host in {"127.0.0.1", "localhost", "::1"}
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=not local) as client:
            with client.stream(
                "POST", self.config.rpc_url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            ) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 2 * 1024**2:
                        raise ValueError("RPC response exceeds 2 MiB")
        import json

        body = json.loads(raw)
        if body.get("id") != 1 or body.get("jsonrpc") != "2.0" or "error" in body or "result" not in body:
            raise ValueError("RPC returned an invalid response")
        return body["result"]

    def verify_token(self) -> dict[str, Any]:
        """Check chain, bytecode pin and decimals at a confirmed block."""
        chain_id = int(self.call("eth_chainId", []), 16)
        if chain_id != self.config.chain_id:
            raise ValueError("RPC chain ID mismatch")
        head = int(self.call("eth_blockNumber", []), 16)
        confirmed = head - self.config.confirmations + 1
        if chain_id == 1:
            finalized = self.call("eth_getBlockByNumber", ["finalized", False])
            if not finalized:
                raise ValueError("mainnet RPC must expose finalized blocks")
            confirmed = min(confirmed, int(finalized["number"], 16))
        if confirmed < 0:
            raise ValueError("chain has insufficient confirmed blocks")
        block = self.call("eth_getBlockByNumber", [hex(confirmed), False])
        if not block or int(block["number"], 16) != confirmed:
            raise ValueError("confirmed block unavailable")
        code = bytes.fromhex(self.call("eth_getCode", [AGIALPHA, hex(confirmed)])[2:])
        if not code or hashlib.sha256(code).hexdigest() != self.config.token_code_sha256:
            raise ValueError("token bytecode does not match configured pin")
        decimals = int(self.call("eth_call", [{"to": AGIALPHA, "data": "0x313ce567"}, hex(confirmed)]), 16)
        if decimals != DECIMALS:
            raise ValueError("token decimals mismatch")
        return {
            "chain_id": chain_id,
            "head": head,
            "confirmed_block": confirmed,
            "block_hash": block["hash"],
            "token": AGIALPHA,
            "decimals": decimals,
            "environment": "mainnet" if chain_id == 1 else "test_chain",
        }


class Economics:
    """Bind a proved wallet and record confirmed receipts once per transfer log."""

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        journal.verify()

    def challenge(self) -> dict[str, Any]:
        """Create a single-use, ten-minute identity binding challenge."""
        expires = time.time_ns() + 600 * 10**9
        nonce = secrets.token_hex(32)
        message = (
            f"AGIALPHA Agent wallet binding v1\nIdentity: {self.journal.identity}\n"
            f"Nonce: {nonce}\nExpires: {expires}\nThis signs identity only; no spending permission."
        )
        with self.journal.transaction() as cx:
            return self.journal.append(cx, "@challenge", {"message": message, "expires_ns": expires, "used": False})

    def bind(self, signature: str) -> dict[str, Any]:
        """Verify an EIP-191 signature; retain the public proof, never a wallet key."""
        from eth_account import Account
        from eth_account.messages import encode_defunct

        with self.journal.transaction() as cx:
            challenge = self.journal.latest("@challenge", cx)
            if challenge["used"] or challenge["expires_ns"] < time.time_ns():
                raise Conflict("wallet challenge expired or already used")
            wallet = address(Account.recover_message(encode_defunct(text=challenge["message"]), signature=signature))
            try:
                current = self.journal.latest("@wallet", cx)
            except KeyError:
                current = None
            if current and current["address"] != wallet:
                raise Conflict("wallet identity is already bound; use a new installation for a different wallet")
            self.journal.append(cx, "@challenge", {**self.journal.document(challenge), "used": True})
            return self.journal.append(
                cx,
                "@wallet",
                {
                    "address": wallet,
                    "proof": "EIP-191 wallet control",
                    "message": challenge["message"],
                    "signature": signature,
                    "ens_ownership_verified": False,
                },
            )

    def invoice(self, ident: str, payer: str, amount: str) -> dict[str, Any]:
        """Record expected payment terms before a transfer is observed."""
        cfg = self.journal.config.chain
        if cfg is None:
            raise ValueError("configure and pin a chain before requesting payment")
        amount_int, sender = units(amount), address(payer)
        snapshot = RPC(cfg).verify_token()
        with self.journal.transaction() as cx:
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("agent is paused")
            mission = self.journal.latest(ident, cx)
            if mission["state"] != "completed":
                raise Conflict("only approved completed work can request payment")
            wallet = self.journal.latest("@wallet", cx)["address"]
            if sender == wallet:
                raise ValueError("self-payments are not recorded as earned value")
            key = f"@invoice:{ident}"
            try:
                self.journal.latest(key, cx)
            except KeyError:
                return self.journal.append(
                    cx,
                    key,
                    {
                        "mission": ident,
                        "result_hash": mission["review"]["result_hash"],
                        "payer": sender,
                        "recipient": wallet,
                        "amount_units": str(amount_int),
                        "chain_id": cfg.chain_id,
                        "token": AGIALPHA,
                        "issued_after_block": snapshot["head"],
                        "state": "awaiting_payment",
                    },
                )
            raise Conflict("mission already has an invoice")

    def settle(self, ident: str, tx_hash: str, log_index: int) -> dict[str, Any]:
        """Verify a canonical confirmed Transfer and consume it atomically once."""
        cfg = self.journal.config.chain
        if cfg is None or not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash) or log_index < 0:
            raise ValueError("configured chain, transaction hash and log index required")
        invoice = self.journal.latest(f"@invoice:{ident}")
        if invoice["state"] != "awaiting_payment" or invoice["chain_id"] != cfg.chain_id:
            raise Conflict("invoice is not awaiting payment on the configured chain")
        rpc = RPC(cfg)
        snapshot = rpc.verify_token()
        receipt = rpc.call("eth_getTransactionReceipt", [tx_hash])
        if (
            not receipt
            or receipt.get("transactionHash", "").lower() != tx_hash.lower()
            or int(receipt["status"], 16) != 1
        ):
            raise ValueError("transaction is missing, mismatched or failed")
        block_number = int(receipt["blockNumber"], 16)
        if block_number <= invoice["issued_after_block"] or block_number > snapshot["confirmed_block"]:
            raise ValueError("payment predates the invoice or lacks confirmations")
        block = rpc.call("eth_getBlockByNumber", [receipt["blockNumber"], False])
        if not block or block["hash"].lower() != receipt["blockHash"].lower():
            raise ValueError("receipt is not on the canonical chain")
        matches = [log for log in receipt["logs"] if int(log["logIndex"], 16) == log_index]
        if len(matches) != 1:
            raise ValueError("transfer log is missing or ambiguous")
        log = matches[0]
        topics = log.get("topics", [])
        expected = [
            TRANSFER,
            "0x" + invoice["payer"][2:].rjust(64, "0"),
            "0x" + invoice["recipient"][2:].rjust(64, "0"),
        ]
        if log.get("removed") or log["address"].lower() != AGIALPHA or [t.lower() for t in topics] != expected:
            raise ValueError("log is not the expected AGIALPHA transfer")
        if (
            log.get("transactionHash", "").lower() != tx_hash.lower()
            or log.get("blockHash", "").lower() != receipt["blockHash"].lower()
        ):
            raise ValueError("transfer provenance mismatch")
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", log["data"]) or int(log["data"], 16) != int(invoice["amount_units"]):
            raise ValueError("payment amount does not match the invoice")
        amount = int(invoice["amount_units"])
        key = f"@receipt:{cfg.chain_id}:{tx_hash.lower()}:{log_index}"
        with self.journal.transaction() as cx:
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("agent is paused")
            latest = self.journal.latest(f"@invoice:{ident}", cx)
            if latest["revision"] != invoice["revision"]:
                raise Conflict("invoice changed during verification")
            try:
                self.journal.latest(key, cx)
            except KeyError:
                pass
            else:
                raise Conflict("transfer was already consumed")
            evidence = {
                "mission": ident,
                "chain_id": cfg.chain_id,
                "environment": snapshot["environment"],
                "transaction_hash": tx_hash.lower(),
                "log_index": log_index,
                "block_number": block_number,
                "block_hash": receipt["blockHash"],
                "confirmations": snapshot["head"] - block_number + 1,
                "amount_units": str(amount),
                "token": AGIALPHA,
                "decimals": DECIMALS,
                "reinvestment_earmark_units": str(amount * cfg.reinvest_bps // 10000),
                "reinvestment_executed": False,
                "association": "operator-linked invoice; ERC20 transfer has no mission memo",
            }
            self.journal.append(cx, key, evidence)
            self.journal.append(
                cx, f"@invoice:{ident}", {**self.journal.document(invoice), "state": "paid", "receipt": key}
            )
            return evidence

    def balance(self) -> dict[str, Any]:
        """Read the proved wallet's balance at a confirmed block."""
        cfg = self.journal.config.chain
        if cfg is None:
            raise ValueError("no chain configured")
        rpc = RPC(cfg)
        snapshot = rpc.verify_token()
        wallet = self.journal.latest("@wallet")["address"]
        data = "0x70a08231" + wallet[2:].rjust(64, "0")
        balance = int(rpc.call("eth_call", [{"to": AGIALPHA, "data": data}, hex(snapshot["confirmed_block"])]), 16)
        return {**snapshot, "wallet": wallet, "balance_units": str(balance)}
