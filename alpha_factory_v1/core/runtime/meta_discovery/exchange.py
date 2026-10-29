# SPDX-License-Identifier: Apache-2.0
"""Durable local simulated exchange. No payment provider or network authority."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .checker import check
from .instrument import canonical, digest, validate

ROUTES = {"manager-usdc": ("USDC", 6), "jobs-agialpha": ("AGIALPHA", 18)}


class Exchange:
    def __init__(
        self,
        path: Path,
        *,
        contract_id: str = "meta-discovery/v1",
        task_validator: Callable[[dict[str, Any]], Any] = validate,
        result_checker: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = check,
    ) -> None:
        if path.is_symlink():
            raise ValueError("database symlink")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        if not isinstance(contract_id, str) or not contract_id or len(contract_id) > 200:
            raise ValueError("trusted application contract identity")
        self._validate_task = task_validator
        self._check_result = result_checker
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        os.chmod(path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA foreign_keys=ON;
        PRAGMA journal_mode=DELETE;
        CREATE TABLE IF NOT EXISTS wallets(buyer TEXT,route TEXT,balance TEXT NOT NULL,PRIMARY KEY(buyer,route));
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,campaign TEXT NOT NULL,buyer TEXT NOT NULL,route TEXT NOT NULL,
         currency TEXT NOT NULL,decimals INTEGER NOT NULL,price TEXT NOT NULL,task TEXT NOT NULL,artifact_hash TEXT,
         ciphertext BLOB,key BLOB,nonce BLOB,state TEXT NOT NULL,consent INTEGER NOT NULL DEFAULT 0,
         verified INTEGER NOT NULL DEFAULT 0,entitlement INTEGER NOT NULL DEFAULT 0,deadline INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,order_id TEXT NOT NULL,action TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS journal(seq INTEGER PRIMARY KEY AUTOINCREMENT,order_id TEXT,route TEXT,kind TEXT,amount TEXT);
        CREATE TABLE IF NOT EXISTS application_contract(id INTEGER PRIMARY KEY CHECK(id=1),name TEXT NOT NULL);
        """)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            saved = self.db.execute("SELECT name FROM application_contract WHERE id=1").fetchone()
            if saved is not None and saved["name"] != contract_id:
                raise ValueError("persistent acceptance contract mismatch")
            if saved is None:
                if contract_id != "meta-discovery/v1" and self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]:
                    raise ValueError("legacy orders cannot change acceptance contract")
                self.db.execute("INSERT OR IGNORE INTO application_contract VALUES(1,?)", (contract_id,))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            self.db.close()
            raise

    def close(self) -> None:
        self.db.close()

    def provision_simulated_buyer(self, buyer: str, route: str, amount: int) -> None:
        if route not in ROUTES or type(amount) is not int or amount < 0:
            raise ValueError("simulated balance")
        self.db.execute("INSERT INTO wallets VALUES(?,?,?)", (buyer, route, str(amount)))

    def offer(
        self,
        ident: str,
        campaign: str,
        buyer: str,
        route: str,
        currency: str,
        decimals: int,
        price: int,
        task: dict[str, Any],
        deadline: int,
    ) -> None:
        self._validate_task(task)
        if route not in ROUTES or ROUTES[route] != (currency, decimals) or type(price) is not int or price <= 0:
            raise ValueError("route denomination")
        if (
            type(deadline) is not int
            or deadline < 0
            or not all(isinstance(x, str) and x for x in (ident, campaign, buyer))
        ):
            raise ValueError("order identity")
        self.db.execute(
            "INSERT INTO orders(id,campaign,buyer,route,currency,decimals,price,task,state,deadline) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                ident,
                campaign,
                buyer,
                route,
                currency,
                decimals,
                str(price),
                canonical(task).decode(),
                "offered",
                deadline,
            ),
        )

    def _row(self, ident: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM orders WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise ValueError("unknown order")
        return dict(row)

    def _entry(self, row: dict[str, Any], kind: str, amount: int) -> None:
        self.db.execute(
            "INSERT INTO journal(order_id,route,kind,amount) VALUES(?,?,?,?)",
            (row["id"], row["route"], kind, str(amount)),
        )

    def event(
        self, ident: str, event_id: str, action: str, payload: dict[str, Any], now: int = 0, crash: bool = False
    ) -> str:
        if type(now) is not int or now < 0:
            raise ValueError("bounded event time")
        if action not in {
            "consent",
            "fund",
            "deliver",
            "verify",
            "settle",
            "refund",
            "timeout",
            "chargeback",
            "dispute",
            "credit",
        }:
            raise ValueError("unsupported operation")
        raw = canonical({"action": action, "payload": payload, "now": now}).decode()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
            if old:
                if old["order_id"] != ident or old["payload"] != raw:
                    raise ValueError("event id rebound")
                self.db.execute("COMMIT")
                return str(self._row(ident)["state"])
            row = self._row(ident)
            previous_times = [
                json.loads(e["payload"])["now"]
                for e in self.db.execute("SELECT payload FROM events WHERE order_id=?", (ident,))
            ]
            if previous_times and now < max(previous_times):
                raise ValueError("event time regression")
            state = row["state"]
            price = int(row["price"])
            if action == "credit":
                raise ValueError("credit disabled; no qualified credit route")
            if action == "consent":
                if (
                    set(payload) != {"buyer", "termsHash"}
                    or payload["buyer"] != row["buyer"]
                    or payload["termsHash"] != self.terms_hash(ident)
                    or state != "offered"
                ):
                    raise ValueError("consent binding")
                self.db.execute("UPDATE orders SET consent=1 WHERE id=?", (ident,))
            elif action == "fund":
                if payload != {"buyer": row["buyer"]} or not row["consent"] or now > row["deadline"]:
                    raise ValueError("funding consent or expiry")
                if state == "offered":
                    wallet = self.db.execute(
                        "SELECT balance FROM wallets WHERE buyer=? AND route=?", (row["buyer"], row["route"])
                    ).fetchone()
                    if wallet is None or int(wallet["balance"]) < price:
                        raise ValueError("insufficient buyer cash")
                    self.db.execute(
                        "UPDATE wallets SET balance=? WHERE buyer=? AND route=?",
                        (str(int(wallet["balance"]) - price), row["buyer"], row["route"]),
                    )
                    self.db.execute("UPDATE orders SET state='funded' WHERE id=?", (ident,))
                    self._entry(row, "restricted_funding", price)
                elif state not in {"funded", "delivered", "verified", "settled"}:
                    raise ValueError("terminal order")
            elif action == "deliver":
                if state != "funded" or set(payload) != {"artifact"}:
                    raise ValueError("delivery precondition")
                artifact = canonical(payload["artifact"])
                if len(artifact) > 1_000_000:
                    raise ValueError("artifact size")
                key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
                cipher = AESGCM(key).encrypt(nonce, artifact, ident.encode())
                self.db.execute(
                    "UPDATE orders SET state='delivered',artifact_hash=?,ciphertext=?,key=?,nonce=? WHERE id=?",
                    (hashlib.sha256(artifact).hexdigest(), cipher, key, nonce, ident),
                )
            elif action == "verify":
                if state != "delivered" or payload:
                    raise ValueError("verification precondition")
                artifact = self._decrypt(row)
                verdict = self._check_result(json.loads(row["task"]), json.loads(artifact))
                if not verdict["accepted"] or verdict.get("decisive") is False:
                    raise ValueError("independent acceptance failed")
                self.db.execute("UPDATE orders SET state='verified',verified=1 WHERE id=?", (ident,))
            elif action in {"settle", "dispute"}:
                if payload:
                    raise ValueError("untrusted success flag")
                if state == "verified":
                    if now > row["deadline"]:
                        raise ValueError("expired; refund required")
                    self._decrypt(row)
                    self.db.execute("UPDATE orders SET state='settled',entitlement=1 WHERE id=?", (ident,))
                    self._entry(row, "earned_revenue", price)
                    self._entry(row, "collections", price)
                    self._entry(row, "restricted_release", price)
                elif state != "settled":
                    raise ValueError("unverified settlement")
            elif action in {"refund", "timeout", "chargeback"}:
                if payload:
                    raise ValueError("unexpected reversal fields")
                if action == "timeout" and now <= row["deadline"]:
                    raise ValueError("deadline not reached")
                if action == "chargeback" and state not in {"settled", "reversed"}:
                    raise ValueError("not settled")
                if state in {"funded", "delivered", "verified", "settled"}:
                    if action == "timeout" and state == "settled":
                        raise ValueError("settled timeout")
                    wallet = self.db.execute(
                        "SELECT balance FROM wallets WHERE buyer=? AND route=?", (row["buyer"], row["route"])
                    ).fetchone()
                    self.db.execute(
                        "UPDATE wallets SET balance=? WHERE buyer=? AND route=?",
                        (str(int(wallet["balance"]) + price), row["buyer"], row["route"]),
                    )
                    if state == "settled":
                        self._entry(row, "contra_revenue", price)
                        self._entry(row, "refund_payment", price)
                    else:
                        self._entry(row, "restricted_refund", price)
                    self.db.execute("UPDATE orders SET state='reversed',entitlement=0 WHERE id=?", (ident,))
                elif state not in {"reversed", "offered"}:
                    raise ValueError("reversal state")
            if crash:
                raise InterruptedError("simulated interruption before commit")
            self.db.execute("INSERT INTO events VALUES(?,?,?,?)", (event_id, ident, action, raw))
            self.db.execute("COMMIT")
            return str(self._row(ident)["state"])
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def terms_hash(self, ident: str) -> str:
        row = self._row(ident)
        return digest(
            {
                k: row[k]
                for k in ["id", "campaign", "buyer", "route", "currency", "decimals", "price", "task", "deadline"]
            }
        )

    def _decrypt(self, row: dict[str, Any]) -> bytes:
        if row["ciphertext"] is None:
            raise ValueError("delivery unavailable")
        artifact = AESGCM(row["key"]).decrypt(row["nonce"], row["ciphertext"], row["id"].encode())
        if hashlib.sha256(artifact).hexdigest() != row["artifact_hash"]:
            raise ValueError("substituted artifact")
        return artifact

    def preview(self, ident: str) -> dict[str, Any]:
        row = self._row(ident)
        return {
            k: row[k]
            for k in ["id", "campaign", "route", "currency", "decimals", "price", "state", "artifact_hash", "deadline"]
        }

    def download(self, ident: str, buyer: str) -> bytes:
        row = self._row(ident)
        if row["buyer"] != buyer or row["state"] != "settled" or not row["entitlement"]:
            raise PermissionError("assured simulated settlement required")
        return self._decrypt(row)

    def accounting(self, route: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for row in self.db.execute("SELECT kind,amount FROM journal WHERE route=?", (route,)):
            result[row["kind"]] = result.get(row["kind"], 0) + int(row["amount"])
        result["revenue"] = result.get("earned_revenue", 0) - result.get("contra_revenue", 0)
        result["cash"] = result.get("collections", 0) - result.get("refund_payment", 0)
        result["restricted"] = (
            result.get("restricted_funding", 0)
            - result.get("restricted_release", 0)
            - result.get("restricted_refund", 0)
        )
        return result
