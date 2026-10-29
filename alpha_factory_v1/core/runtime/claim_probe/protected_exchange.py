# SPDX-License-Identifier: Apache-2.0
"""Simulated cleared-funds exchange with exposure-aware liquidity and durable remedies."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Callable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .contracts import canonical, digest


class SimulatedProvider:
    """Local trusted scenario oracle, never evidence of an external payment provider."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("provider key")
        self.key = key

    def issue(self, order: dict[str, Any], kind: str, source_tx: str | None = None) -> dict[str, Any]:
        """Bind a simulated funding/clearing observation to exact trade bytes."""
        payload = {k: order[k] for k in ["id", "price", "rail", "task_hash", "contract"]}
        payload.update(
            currencyUnit="simulated-microUSD",
            kind=kind,
            artifact_hash=order.get("artifact_hash"),
            cleared_cash=kind == "cleared",
            source_tx=source_tx or digest({"order": order["id"], "kind": kind}),
        )
        return {"payload": payload, "signature": hmac.new(self.key, canonical(payload), hashlib.sha256).hexdigest()}


class ProtectedExchange:
    """Private coordinator for simulated money; no network, provider or native authority."""

    def __init__(
        self,
        path: Path,
        *,
        key: bytes,
        contract: str,
        validate: Callable[[Any], Any],
        check: Callable[[Any, Any], dict[str, Any]],
        opening: int = 100_000_000,
        working: int = 1_000_000,
    ) -> None:
        if path.is_symlink() or type(opening) is not int or opening < 0 or type(working) is not int or working < 0:
            raise ValueError("exchange configuration")
        self.provider = SimulatedProvider(key)
        self.contract, self.validate, self.check = contract, validate, check
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        os.chmod(path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=DELETE;
        CREATE TABLE IF NOT EXISTS private_artifacts(id TEXT PRIMARY KEY,cipher BLOB,key BLOB,nonce BLOB,aad TEXT);
        CREATE TABLE IF NOT EXISTS investments(id TEXT PRIMARY KEY,cap TEXT NOT NULL,state TEXT NOT NULL,actual TEXT NOT NULL DEFAULT '0');
        CREATE TABLE IF NOT EXISTS investment_events(seq INTEGER PRIMARY KEY,investment_id TEXT NOT NULL,action TEXT NOT NULL,witness TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS config(id INTEGER PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS wallets(buyer TEXT PRIMARY KEY, balance TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS trades(id TEXT PRIMARY KEY,buyer TEXT NOT NULL,price TEXT NOT NULL,
         rail TEXT NOT NULL,task TEXT NOT NULL,task_hash TEXT NOT NULL,contract TEXT NOT NULL,
         deadline INTEGER NOT NULL,state TEXT NOT NULL,artifact_hash TEXT,cipher BLOB,key BLOB,nonce BLOB,
         custody INTEGER NOT NULL DEFAULT 0,refund_due TEXT NOT NULL DEFAULT '0',
         compensation_due TEXT NOT NULL DEFAULT '0',consent INTEGER NOT NULL DEFAULT 0,
         lost INTEGER NOT NULL DEFAULT 0,recovered INTEGER NOT NULL DEFAULT 0,blob_id TEXT);
        CREATE TABLE IF NOT EXISTS source_receipts(tx TEXT PRIMARY KEY,order_id TEXT,kind TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,order_id TEXT,raw TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS journal(seq INTEGER PRIMARY KEY,order_id TEXT,kind TEXT,amount TEXT);
        """)
        wanted = canonical(
            {
                "contract": contract,
                "opening": opening,
                "working": working,
                "providerKeyHash": hashlib.sha256(key).hexdigest(),
                "currencyUnit": "simulated-microUSD",
                "allocationPolicy": "incurred-cost-first-equity-protection/v2",
                "artifactStorage": "private-content-bound/v1",
            }
        ).decode()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            saved = self.db.execute("SELECT value FROM config WHERE id=1").fetchone()
            if saved and saved[0] != wanted:
                raise ValueError("persistent contract/configuration mismatch")
            self.db.execute("INSERT OR IGNORE INTO config VALUES(1,?)", (wanted,))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            self.db.close()
            raise
        self.opening, self.working = opening, working

    def close(self) -> None:
        self.db.close()

    def _entry(self, order: str, kind: str, amount: int) -> None:
        self.db.execute("INSERT INTO journal(order_id,kind,amount) VALUES(?,?,?)", (order, kind, str(amount)))

    def order(self, ident: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM trades WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise ValueError("unknown trade")
        return dict(row)

    def wallet(self, buyer: str, balance: int) -> None:
        if type(balance) is not int or balance < 0:
            raise ValueError("buyer funds")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO wallets VALUES(?,?)", (buyer, str(balance)))
            self._entry(buyer, "buyer_provision", balance)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _credit_wallet(self, buyer: str, amount: int) -> None:
        current = self.db.execute("SELECT balance FROM wallets WHERE buyer=?", (buyer,)).fetchone()
        if current is None:
            raise ValueError("unknown buyer wallet")
        self.db.execute("UPDATE wallets SET balance=? WHERE buyer=?", (str(int(current[0]) + amount), buyer))

    def offer(self, ident: str, buyer: str, price: int, rail: str, task: Any, deadline: int) -> None:
        self.validate(task)
        if (
            type(price) is not int
            or not 200_000 <= price <= 10**12
            or rail not in {"reversible", "nonrecourse-simulated"}
        ):
            raise ValueError("price or supported rail")
        if type(deadline) is not int or deadline < 0 or not ident or ident.startswith("investment:") or not buyer:
            raise ValueError("trade identity/deadline")
        self.db.execute(
            "INSERT INTO trades(id,buyer,price,rail,task,task_hash,contract,deadline,state) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                ident,
                buyer,
                str(price),
                rail,
                canonical(task).decode(),
                digest(task),
                self.contract,
                deadline,
                "offered",
            ),
        )

    def snapshot(self) -> dict[str, Any]:
        sums: dict[str, int] = {}
        for row in self.db.execute("SELECT kind,amount FROM journal"):
            sums[row["kind"]] = sums.get(row["kind"], 0) + int(row["amount"])
        revenue = sums.get("revenue", 0) - sums.get("contra_revenue", 0)
        costs, paid = sums.get("expense", 0), sums.get("expense_paid", 0)
        collections = sums.get("collections", 0) - sums.get("reversal_paid", 0)
        recovery = sums.get("recovery_income", 0)
        cash = self.opening + collections + recovery - paid - sums.get("investment_paid", 0)
        orders = [dict(x) for x in self.db.execute("SELECT * FROM trades")]
        refund_due = sum(int(x["refund_due"]) for x in orders)
        custody = sum(int(x["price"]) for x in orders if x["custody"])
        # A custody-loss compensation expense is already in expense payables.
        custody_reserve = sum(int(x["price"]) for x in orders if x["custody"] and x["state"] in {"funded", "verified"})
        tail = sum(int(x["price"]) + 200_000 for x in orders if x["state"] == "released")
        payable = max(0, costs - paid) + refund_due
        free = max(0, cash - payable - custody_reserve - tail - self.working)
        conditional = max(
            0,
            min(
                max(0, cash - payable - custody_reserve - self.working),
                collections - paid - sums.get("investment_paid", 0) - payable - custody_reserve - self.working,
            ),
        )
        safe_earned = max(
            0,
            min(
                free,
                collections - paid - sums.get("investment_paid", 0) - payable - custody_reserve - tail - self.working,
            ),
        )
        strict_earned = safe_earned
        net_earned = collections - paid - payable - sums.get("investment_paid", 0)
        equity_witness = max(0, self.opening + recovery + min(0, net_earned))
        protection = custody_reserve + tail + self.working
        equity_backing = min(protection, equity_witness)
        earned_protection = max(0, protection - equity_backing)
        safe_earned = max(0, min(free, max(0, net_earned) - earned_protection))
        stopped = sums.get("breach", 0) > 0
        reserved_investment = sum(
            int(x[0]) for x in self.db.execute("SELECT cap FROM investments WHERE state='reserved'")
        )
        safe_earned = max(0, safe_earned - reserved_investment)
        free = max(0, free - reserved_investment)
        return {
            "reservedInvestment": reserved_investment,
            "revenue": revenue,
            "expenses": costs,
            "recoveryIncome": recovery,
            "profit": revenue + recovery - costs,
            "cash": cash,
            "collections": collections,
            "expensePaid": paid,
            "payables": payable,
            "custodyRestricted": custody,
            "custodyReserve": custody_reserve,
            "tailReserve": tail,
            "workingCapital": self.working,
            "available": free,
            "unrestrictedEarned": 0 if stopped else safe_earned,
            "strictEarnedControl": 0 if stopped else strict_earned,
            "equityProtectionBacking": equity_backing,
            "earnedProtectionBacking": earned_protection,
            "netEarnedAfterIncurredObligations": net_earned,
            "fundingScope": "Bounded principal-plus-fee exposure; arbitrary additional debits are not guaranteed",
            "conditionalEarned": 0 if stopped else conditional,
            "investmentStopped": stopped,
            "assuranceScope": "Local provider assumption only; full late-debit reserve retained for conservative investment",
        }

    def cost(self, event: str, amount: int) -> None:
        """Recognize genuine costs even if liquidity prevents immediate payment."""
        if type(amount) is not int or amount < 0:
            raise ValueError("cost")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if self.db.execute("SELECT 1 FROM events WHERE id=?", (event,)).fetchone():
                raise ValueError("cost identifier already consumed")
            state = self.snapshot()
            payment = min(amount, state["available"])
            self._entry("", "expense", amount)
            self._entry("", "expense_paid", payment)
            self.db.execute("INSERT INTO events VALUES(?,?,?)", (event, "", canonical({"cost": amount}).decode()))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def reserve_investment(
        self, ident: str, cap: int, expected_net_value: int, *, intent_hash: str = ""
    ) -> dict[str, Any]:
        """Reserve only earned cash after all incurred obligations and explicit protection."""
        if type(cap) is not int or cap <= 0 or type(expected_net_value) is not int or expected_net_value <= 0:
            raise ValueError("investment valuation/budget")
        if not ident or (
            intent_hash and (len(intent_hash) != 64 or any(c not in "0123456789abcdef" for c in intent_hash))
        ):
            raise ValueError("investment identity/intent")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.snapshot()
            if state["investmentStopped"] or state["unrestrictedEarned"] < cap:
                raise ValueError("earned funds or exposure qualification unavailable")
            self.db.execute("INSERT INTO investments(id,cap,state) VALUES(?,?,'reserved')", (ident, str(cap)))
            witness = {
                "before": state,
                "cap": cap,
                "expectedNetValue": expected_net_value,
                "valuationScope": "caller assumption, not realized demand",
                "intentHash": intent_hash,
                "journalThrough": self.db.execute("SELECT COALESCE(MAX(seq),0) FROM journal").fetchone()[0],
                "eventRowidThrough": self.db.execute("SELECT COALESCE(MAX(rowid),0) FROM events").fetchone()[0],
            }
            self.db.execute(
                "INSERT INTO investment_events(investment_id,action,witness) VALUES(?,'reserve',?)",
                (ident, canonical(witness).decode()),
            )
            self.db.execute("COMMIT")
            return {
                "decision": "CONSTRUCT",
                "funding": "earned after incurred costs; equity separately backs protection",
                "cap": cap,
                "before": state,
                "witness": witness,
            }
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def cancel_investment(self, ident: str) -> None:
        """Release an unspent commitment; incurred failed work remains a separate cost."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT state FROM investments WHERE id=?", (ident,)).fetchone()
            if row is None or row[0] != "reserved":
                raise ValueError("no cancellable investment")
            before = self.snapshot()
            self.db.execute("UPDATE investments SET state='cancelled' WHERE id=?", (ident,))
            self.db.execute(
                "INSERT INTO investment_events(investment_id,action,witness) VALUES(?,'cancel',?)",
                (ident, canonical({"before": before}).decode()),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def finish_investment(self, ident: str, actual: int, artifact_hash: str) -> dict[str, Any]:
        """Charge consumed construction once; unused reserved funds are released."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT * FROM investments WHERE id=?", (ident,)).fetchone()
            if (
                row is None
                or row["state"] != "reserved"
                or type(actual) is not int
                or not 0 <= actual <= int(row["cap"])
            ):
                raise ValueError("construction budget/state")
            if (
                not isinstance(artifact_hash, str)
                or len(artifact_hash) != 64
                or any(c not in "0123456789abcdef" for c in artifact_hash)
            ):
                raise ValueError("construction evidence identity")
            before = self.snapshot()
            self.db.execute("UPDATE investments SET state='complete',actual=? WHERE id=?", (str(actual), ident))
            state = self.snapshot()
            self._entry("investment:" + ident, "expense", actual)
            self._entry("investment:" + ident, "expense_paid", min(actual, state["available"]))
            self.db.execute(
                "INSERT INTO investment_events(investment_id,action,witness) VALUES(?,'finish',?)",
                (ident, canonical({"before": before, "actual": actual, "artifactHash": artifact_hash}).decode()),
            )
            self.db.execute(
                "INSERT INTO events VALUES(?,?,?)",
                ("investment-" + ident, "", canonical({"artifactHash": artifact_hash, "consumed": actual}).decode()),
            )
            self.db.execute("COMMIT")
            return self.snapshot()
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _receipt(self, row: dict[str, Any], receipt: Any, kind: str) -> None:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("payload"), dict):
            raise ValueError("receipt schema")
        source_tx = receipt["payload"].get("source_tx")
        if not isinstance(source_tx, str) or not 1 <= len(source_tx) <= 200:
            raise ValueError("source transaction")
        expected = self.provider.issue(row, kind, source_tx)
        if not isinstance(receipt, dict) or set(receipt) != {"payload", "signature"}:
            raise ValueError("receipt schema")
        if receipt["payload"] != expected["payload"] or not hmac.compare_digest(
            str(receipt["signature"]), expected["signature"]
        ):
            raise ValueError("unbound or forged provider observation")
        self.db.execute("INSERT INTO source_receipts VALUES(?,?,?)", (source_tx, row["id"], kind))

    def event(self, ident: str, event: str, action: str, payload: Any, now: int, *, crash: bool = False) -> str:
        """Apply one durable trade transition; authenticated receipts are scenario authority only."""
        if type(now) is not int or now < 0:
            raise ValueError("time")
        event_payload = {"artifactHash": digest(payload)} if action == "prepare" else payload
        raw = canonical({"action": action, "payload": event_payload, "now": now}).decode()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            prior = self.db.execute("SELECT * FROM events WHERE id=?", (event,)).fetchone()
            if prior:
                if prior["raw"] != raw or prior["order_id"] != ident:
                    raise ValueError("event rebound")
                self.db.execute("COMMIT")
                return str(self.order(ident)["state"])
            row = self.order(ident)
            previous = [
                json.loads(x[0])["now"] for x in self.db.execute("SELECT raw FROM events WHERE order_id=?", (ident,))
            ]
            if previous and now < max(previous):
                raise ValueError("time regression")
            price, state = int(row["price"]), row["state"]
            if action == "consent":
                terms = {k: row[k] for k in ["id", "buyer", "price", "rail", "task_hash", "contract", "deadline"]}
                if state != "offered" or payload != {"buyer": row["buyer"], "termsHash": digest(terms)}:
                    raise ValueError("bound consent required")
                self.db.execute("UPDATE trades SET consent=1 WHERE id=?", (ident,))
            elif action == "cancel":
                if state != "offered" or payload != {}:
                    raise ValueError("cancellation state")
                self.db.execute("UPDATE trades SET state='cancelled' WHERE id=?", (ident,))
            elif action == "fund":
                if state != "offered" or not row["consent"] or now > row["deadline"]:
                    raise ValueError("funding state/expiry")
                self._receipt(row, payload, "funded")
                wallet = self.db.execute("SELECT balance FROM wallets WHERE buyer=?", (row["buyer"],)).fetchone()
                if wallet is None or int(wallet[0]) < price or self.snapshot()["available"] < price:
                    raise ValueError("buyer funds or collateral unavailable")
                self.db.execute(
                    "UPDATE wallets SET balance=? WHERE buyer=?", (str(int(wallet[0]) - price), row["buyer"])
                )
                self.db.execute("UPDATE trades SET state='funded',custody=1 WHERE id=?", (ident,))
            elif action == "prepare":
                if state != "funded":
                    raise ValueError("preparation state")
                raw_artifact = canonical(payload)
                if len(raw_artifact) > 1_000_000:
                    raise ValueError("artifact cap")
                captured_task, captured_artifact = json.loads(row["task"]), json.loads(raw_artifact)
                result = self.check(captured_task, captured_artifact)
                if canonical(captured_task).decode() != row["task"] or canonical(captured_artifact) != raw_artifact:
                    raise ValueError("checker mutated its evidence frame")
                if (
                    not isinstance(result, dict)
                    or result.get("accepted") is not True
                    or result.get("decisive") is not True
                ):
                    raise ValueError("independent acceptance failed")
                artifact_hash = hashlib.sha256(raw_artifact).hexdigest()
                aad = digest({"contract": self.contract, "taskHash": row["task_hash"], "artifactHash": artifact_hash})
                if self.db.execute("SELECT 1 FROM private_artifacts WHERE id=?", (aad,)).fetchone() is None:
                    key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
                    ciphertext = AESGCM(key).encrypt(nonce, raw_artifact, aad.encode())
                    self.db.execute(
                        "INSERT INTO private_artifacts VALUES(?,?,?,?,?)", (aad, ciphertext, key, nonce, aad)
                    )
                self.db.execute(
                    "UPDATE trades SET state='verified',blob_id=?,artifact_hash=? WHERE id=?",
                    (aad, artifact_hash, ident),
                )
            elif action == "release":
                if (
                    state != "verified"
                    or row["rail"] != "nonrecourse-simulated"
                    or now > row["deadline"]
                    or not row["custody"]
                ):
                    raise ValueError("unassured or expired settlement")
                self._receipt(row, payload, "cleared")
                raw_check = self._decrypt(row)
                captured_task, captured_artifact = json.loads(row["task"]), json.loads(raw_check)
                verdict = self.check(captured_task, captured_artifact)
                if canonical(captured_task).decode() != row["task"] or canonical(captured_artifact) != raw_check:
                    raise ValueError("release checker mutated evidence")
                if (
                    not isinstance(verdict, dict)
                    or verdict.get("accepted") is not True
                    or verdict.get("decisive") is not True
                ):
                    raise ValueError("release requalification failed")
                self.db.execute("UPDATE trades SET state='released',custody=0 WHERE id=?", (ident,))
                self._entry(ident, "revenue", price)
                self._entry(ident, "collections", price)
            elif action == "custody_loss":
                if state not in {"funded", "verified"} or not row["custody"] or payload != {}:
                    raise ValueError("custody-loss state")
                self.db.execute(
                    "UPDATE trades SET state='custody-lost',custody=0,lost=1,compensation_due=price WHERE id=?",
                    (ident,),
                )
                self._entry(ident, "expense", price)
                self._entry(ident, "breach", 1)
            elif action in {"refund", "pay_reversal_due"} and state == "breached":
                if state != "breached" or int(row["refund_due"]) <= 0 or payload != {}:
                    raise ValueError("no reversal remedy due")
                amount = int(row["refund_due"])
                paid = min(amount, max(0, self.snapshot()["cash"]))
                self._entry(ident, "reversal_paid", paid)
                self._credit_wallet(row["buyer"], paid)
                self.db.execute("UPDATE trades SET refund_due=? WHERE id=?", (str(amount - paid), ident))
            elif action == "refund":
                if payload != {} or state not in {"funded", "verified", "custody-lost", "refund-due"}:
                    raise ValueError("refund state")
                amount = price if state != "refund-due" else int(row["compensation_due"])
                if row["custody"]:
                    paid = amount
                else:
                    paid = min(amount, max(0, self.snapshot()["cash"]))
                    self._entry(ident, "expense_paid", paid)
                self._credit_wallet(row["buyer"], paid)
                self.db.execute(
                    "UPDATE trades SET state=?,custody=0,refund_due='0',compensation_due=? WHERE id=?",
                    ("refunded" if paid == amount else "refund-due", str(amount - paid), ident),
                )
                # Unpaid compensation remains expense payable; do not count it twice as refund_due.
            elif action == "recover_custody":
                if not row["lost"] or row["recovered"]:
                    raise ValueError("recovery not due")
                self._receipt(row, payload, "recovered")
                self._entry(ident, "recovery_income", price)
                self.db.execute("UPDATE trades SET recovered=1 WHERE id=?", (ident,))
            elif action == "provider_debit":
                if (
                    not isinstance(payload, dict)
                    or set(payload) != {"amount"}
                    or type(payload["amount"]) is not int
                    or not 0 < payload["amount"] <= 10**12
                ):
                    raise ValueError("adverse debit")
                self._entry(ident, "expense", payload["amount"])
                self._entry(ident, "expense_paid", min(payload["amount"], max(0, self.snapshot()["cash"])))
                self._entry(ident, "breach", 1)
            elif action == "late_reversal":
                if state != "released" or payload != {}:
                    raise ValueError("late reversal state")
                paid = min(price, max(0, self.snapshot()["cash"]))
                self._entry(ident, "contra_revenue", price)
                self._entry(ident, "reversal_paid", paid)
                self._entry(ident, "breach", 1)
                self._credit_wallet(row["buyer"], paid)
                self.db.execute(
                    "UPDATE trades SET state='breached',refund_due=? WHERE id=?", (str(price - paid), ident)
                )
            else:
                raise ValueError("unsupported transition")
            if crash:
                raise InterruptedError("before transaction commit")
            self.db.execute("INSERT INTO events VALUES(?,?,?)", (event, ident, raw))
            self.db.execute("COMMIT")
            return str(self.order(ident)["state"])
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _decrypt(self, row: dict[str, Any]) -> bytes:
        blob = self.db.execute("SELECT * FROM private_artifacts WHERE id=?", (row["blob_id"],)).fetchone()
        expected = digest(
            {"contract": self.contract, "taskHash": row["task_hash"], "artifactHash": row["artifact_hash"]}
        )
        if blob is None or blob["id"] != expected or blob["aad"] != expected:
            raise ValueError("private artifact task/contract binding")
        raw = AESGCM(blob["key"]).decrypt(blob["nonce"], blob["cipher"], expected.encode())
        if hashlib.sha256(raw).hexdigest() != row["artifact_hash"]:
            raise ValueError("artifact substituted")
        return raw

    def preview(self, ident: str) -> dict[str, Any]:
        row = self.order(ident)
        return {k: row[k] for k in ["id", "rail", "price", "state", "artifact_hash", "deadline"]}

    def download(self, ident: str, buyer: str) -> bytes:
        row = self.order(ident)
        if row["buyer"] != buyer or row["state"] != "released":
            raise PermissionError("assured simulated release required")
        return self._decrypt(row)
